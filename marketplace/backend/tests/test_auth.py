import json
import unittest

from fastapi import FastAPI

from app.accounts import router


class AccountValidationTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.app = FastAPI()
        self.app.include_router(router)

    async def post(self, path, fields):
        messages = []
        scope = {
            "type": "http",
            "method": "POST",
            "path": path,
            "query_string": b"",
            "headers": [(b"content-type", b"application/json"), (b"x-marketplace-request", b"1")],
        }

        async def receive():
            return {"type": "http.request", "body": json.dumps(fields).encode()}

        async def send(message):
            messages.append(message)

        await self.app(scope, receive, send)
        return messages[0]["status"], dict(messages[0]["headers"]), messages[1]["body"]

    async def test_auth_validation_never_echoes_a_password(self):
        password = "synthetic-secret-8912"
        cases = (
            ("/auth/register", {"email": "tester@example.test", "password": password}),
            ("/auth/login", {"email": "tester@example.test", "password": {"text": password}}),
        )
        for path, fields in cases:
            with self.subTest(path=path):
                status, headers, body = await self.post(path, fields)
                self.assertEqual(status, 422)
                self.assertEqual(headers[b"cache-control"], b"no-store")
                self.assertNotIn(password.encode(), body)

    async def test_auth_rejects_unpaired_unicode_surrogates(self):
        valid = {"name": "Tester", "email": "tester@example.test", "password": "synthetic-secret-8912"}
        for field in valid:
            with self.subTest(field=field):
                status, _, body = await self.post("/auth/register", {**valid, field: valid[field] + chr(0xD800)})
                self.assertEqual(status, 422)
                self.assertNotIn(b"synthetic-secret-8912", body)
