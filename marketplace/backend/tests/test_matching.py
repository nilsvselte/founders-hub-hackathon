import unittest
from concurrent.futures import ThreadPoolExecutor
from threading import Event
from unittest.mock import patch

from app import main


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
