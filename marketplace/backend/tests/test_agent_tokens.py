import hashlib
import json
import os
import unittest
from unittest.mock import patch
from uuid import uuid4

import psycopg
from fastapi import Depends, FastAPI
from psycopg import sql
from psycopg.conninfo import make_conninfo

from app import db
from app.accounts import require_agent_or_user, router


@unittest.skipUnless(os.environ.get("MARKETPLACE_TEST_DATABASE_URL"), "requires disposable PostgreSQL")
class AgentTokenTests(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        admin_dsn = os.environ["MARKETPLACE_TEST_DATABASE_URL"]
        schema_name = f"agent_token_test_{uuid4().hex}"
        schema = sql.Identifier(schema_name)
        with psycopg.connect(admin_dsn, autocommit=True) as connection:
            connection.execute(sql.SQL("CREATE SCHEMA {}").format(schema))

        def drop_schema():
            with psycopg.connect(admin_dsn, autocommit=True) as connection:
                connection.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(schema))

        cls.addClassCleanup(drop_schema)
        dsn = make_conninfo(admin_dsn, options=f"-csearch_path={schema_name}")
        environment = patch.dict(os.environ, {"DATABASE_URL": dsn})
        environment.start()
        cls.addClassCleanup(environment.stop)
        db.check_ready()

    def setUp(self):
        self.app = FastAPI()
        self.app.include_router(router)

        @self.app.get("/agent-enabled")
        def agent_enabled(account=Depends(require_agent_or_user)):
            return {"id": account.id}

    async def request(self, method, path, *, cookie=None, token=None, mutation_header=True, data=None):
        messages = []
        headers = [(b"content-type", b"application/json")]
        if cookie is not None:
            headers.append((b"cookie", cookie))
        if token is not None:
            headers.append((b"authorization", f"Bearer {token}".encode()))
        if mutation_header:
            headers.append((b"x-marketplace-request", b"1"))
        scope = {"type": "http", "method": method, "path": path, "query_string": b"", "headers": headers}

        async def receive():
            return {"type": "http.request", "body": json.dumps(data).encode() if data else b""}

        async def send(message):
            messages.append(message)

        await self.app(scope, receive, send)
        body = messages[1]["body"]
        return messages[0]["status"], dict(messages[0]["headers"]), json.loads(body) if body else None

    async def register(self, role):
        status, headers, account = await self.request("POST", "/auth/register", data={
            "name": "Test Account", "email": f"{uuid4().hex}@example.test",
            "password": "synthetic-test-password", "role": role,
        })
        self.assertEqual(status, 201)
        return account, headers[b"set-cookie"].split(b";", 1)[0]

    async def test_token_is_hashed_rotated_and_revoked(self):
        account, cookie = await self.register("renter")
        path = "/auth/agent-token"
        status, headers, body = await self.request("GET", path, cookie=cookie)
        self.assertEqual((status, headers[b"cache-control"], body), (200, b"no-store", {"active": False}))

        status, headers, body = await self.request("POST", path, cookie=cookie)
        self.assertEqual((status, headers[b"cache-control"]), (201, b"no-store"))
        token = body["token"]
        with db._connect() as connection:
            stored = connection.execute(
                "SELECT token_hash FROM marketplace_agent_tokens WHERE user_id = %s", (account["id"],),
            ).fetchone()["token_hash"]
        self.assertTrue(stored == hashlib.sha256(token.encode()).digest(), "token digest did not match")
        status, _, body = await self.request("GET", path, cookie=cookie)
        self.assertEqual((status, body), (200, {"active": True}))
        status, _, body = await self.request("GET", "/agent-enabled", token=token)
        self.assertEqual((status, body), (200, {"id": account["id"]}))

        status, _, body = await self.request("POST", path, cookie=cookie)
        self.assertEqual(status, 201)
        replacement = body["token"]
        self.assertEqual((await self.request("GET", "/agent-enabled", token=token))[0], 401)
        self.assertEqual((await self.request("GET", "/agent-enabled", token=replacement))[0], 200)
        status, headers, _ = await self.request("DELETE", path, cookie=cookie)
        self.assertEqual((status, headers[b"cache-control"]), (204, b"no-store"))
        self.assertEqual((await self.request("GET", "/agent-enabled", token=replacement))[0], 401)
        self.assertEqual((await self.request("GET", "/agent-enabled", cookie=cookie))[0], 200)

    async def test_only_browser_renter_can_manage_tokens(self):
        path = "/auth/agent-token"
        _, renter_cookie = await self.register("renter")
        _, host_cookie = await self.register("host")
        status, _, body = await self.request("POST", path, cookie=renter_cookie)
        self.assertEqual(status, 201)
        token = body["token"]
        for method in ("GET", "POST", "DELETE"):
            with self.subTest(method=method):
                self.assertEqual((await self.request(method, path, token=token))[0], 401)
                self.assertEqual((await self.request(method, path, cookie=host_cookie))[0], 403)
        for method in ("POST", "DELETE"):
            status, _, _ = await self.request(method, path, cookie=renter_cookie, mutation_header=False)
            self.assertEqual(status, 403)
        self.assertEqual((await self.request("GET", "/auth/me", token=token))[0], 401)
