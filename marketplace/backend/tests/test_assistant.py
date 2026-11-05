import os
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.main import app

HEADERS = {"X-Marketplace-Request": "1"}


class AssistantTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_requires_browser_header(self):
        response = self.client.post("/assistant/understand", json={"message": "a room"})
        self.assertEqual(response.status_code, 403)

    def test_without_key_is_unavailable(self):
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": ""}):
            response = self.client.post("/assistant/understand", json={"message": "a room"}, headers=HEADERS)
        self.assertEqual(response.status_code, 503)

    def test_returns_claude_criteria(self):
        call = SimpleNamespace(type="tool_use", name="set_criteria", input={
            "date": "2026-11-06", "from_time": "14:00", "to_time": "17:00", "duration_minutes": 30,
            "people": 4, "equipment": ["screen"], "max_price_nok": 500, "reply": "Searching.",
        })
        client = AsyncMock()
        client.__aenter__.return_value = client
        client.messages.create.return_value = SimpleNamespace(content=[call])
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test"}), patch("app.assistant.AsyncAnthropic", return_value=client):
            response = self.client.post("/assistant/understand", json={"message": "4 people tomorrow after 14"}, headers=HEADERS)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["people"], 4)
        self.assertEqual(response.json()["from_time"], "14:00")

    def test_rejects_answer_without_criteria(self):
        client = AsyncMock()
        client.__aenter__.return_value = client
        client.messages.create.return_value = SimpleNamespace(content=[SimpleNamespace(type="text", text="hi")])
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test"}), patch("app.assistant.AsyncAnthropic", return_value=client):
            response = self.client.post("/assistant/understand", json={"message": "hello"}, headers=HEADERS)
        self.assertEqual(response.status_code, 503)


if __name__ == "__main__":
    unittest.main()
