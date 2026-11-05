import json
import unittest
from concurrent.futures import ThreadPoolExecutor
from threading import Event
from unittest.mock import patch

from app import main, matching


class ClaudeMatchingTests(unittest.TestCase):
    def test_flexible_request_compares_venues_and_oslo_times_without_internal_ids(self):
        request = {
            "id": "request-id", "user_id": "user-id", "preferences": "Prefer Mesh after 16:00",
            "earliest_start": "2026-10-24T13:00:00Z", "latest_end": "2026-10-25T16:00:00Z",
        }
        candidates = [
            {
                "room_id": "room-id", "opening_id": "opening-id", "room_name": "Driv",
                "room_venue": "Mesh at Digs", "room_city": "Trondheim",
                "start_at": "2026-10-24T14:00:00Z", "end_at": "2026-10-24T14:30:00Z",
            },
        ]
        response = {
            "stop_reason": "tool_use",
            "content": [{
                "type": "tool_use", "name": "propose_match",
                "input": {"candidate_index": 0, "reason": "Driv is at Mesh and starts at 16:00."},
            }],
        }
        with (
            patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-only"}),
            patch.object(matching, "_send_messages", return_value=response) as send,
        ):
            decision = matching.select_match(request, candidates)

        self.assertEqual(decision, matching.MatchDecision(0, "Driv is at Mesh and starts at 16:00.", "claude"))
        payload = json.loads(send.call_args.args[1]["messages"][0]["content"])
        self.assertEqual(payload["request"]["latest_end"], "2026-10-25T17:00:00+01:00")
        self.assertEqual(payload["candidates"][0]["start_at"], "2026-10-24T16:00:00+02:00")
        self.assertEqual(payload["candidates"][0]["room_venue"], "Mesh at Digs")
        self.assertEqual(payload["candidates"][0]["room_city"], "Trondheim")
        self.assertTrue({"id", "user_id"}.isdisjoint(payload["request"]))
        self.assertTrue({"room_id", "opening_id"}.isdisjoint(payload["candidates"][0]))

    def test_invalid_tool_output_cannot_be_written_as_an_offer(self):
        for tool_input in (
            {"candidate_index": 1, "reason": "Out of range"},
            {"candidate_index": 0, "reason": "Bad\0reason"},
            {"candidate_index": 0, "reason": "Bad\ud800reason"},
            {"candidate_index": 0, "reason": "Extra input", "price_ore": 1},
        ):
            response = {
                "stop_reason": "tool_use",
                "content": [{"type": "tool_use", "name": "propose_match", "input": tool_input}],
            }
            with self.subTest(tool_input=tool_input), self.assertRaises(matching.MatchingUnavailable):
                matching._parse_decision(response, 1)


class ConcurrentMatchingTests(unittest.TestCase):
    def test_simultaneous_retries_share_one_model_call(self):
        entered, release = Event(), Event()

        def choose(*_args):
            entered.set()
            if not release.wait(5):
                raise TimeoutError("test never released the matcher")
            return None

        with (
            patch.object(main.db, "get_request", return_value={"status": "waiting"}),
            patch.object(main.db, "list_candidates", return_value=[{"opening_id": "one"}]),
            patch.object(main, "select_match", side_effect=choose) as model,
            ThreadPoolExecutor(max_workers=16) as pool,
        ):
            first = pool.submit(main.match_request, "same-request")
            try:
                self.assertTrue(entered.wait(5))
                retries = [pool.submit(main.match_request, "same-request") for _ in range(15)]
                for retry in retries:
                    retry.result(timeout=5)
            finally:
                release.set()
            first.result(timeout=5)
            self.assertEqual(model.call_count, 1)

    def test_new_opening_is_checked_after_current_match(self):
        entered, release = Event(), Event()
        candidates = [{"opening_id": "old"}]
        seen = []

        def choose(_request, available):
            seen.append([item["opening_id"] for item in available])
            if len(seen) == 1:
                entered.set()
                if not release.wait(5):
                    raise TimeoutError("test never released the matcher")
            return None

        with (
            patch.object(main.db, "get_request", return_value={"status": "waiting"}),
            patch.object(main.db, "list_candidates", side_effect=lambda _: candidates.copy()),
            patch.object(main, "select_match", side_effect=choose),
            ThreadPoolExecutor(max_workers=1) as pool,
        ):
            current = pool.submit(main.match_request, "new-opening")
            try:
                self.assertTrue(entered.wait(5))
                candidates.append({"opening_id": "new"})
                main.match_request("new-opening")
            finally:
                release.set()
            current.result(timeout=5)
            self.assertEqual(seen, [["old"], ["old", "new"]])
