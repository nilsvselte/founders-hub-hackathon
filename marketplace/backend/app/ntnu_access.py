"""Boundary for institution-approved, per-student TP connections.

The website never reads the developer's local TP session file. A configured
integration owns Feide callbacks and credentials, and returns an MCP session
authorized for the server-authenticated marketplace user ID.
"""

import importlib
import os
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from functools import lru_cache
from typing import Protocol
from urllib.parse import urlsplit

from fastapi import HTTPException
from mcp import ClientSession
from pydantic import BaseModel


class Connection(BaseModel):
    connected: bool = False
    connectable: bool = False
    label: str | None = None


class StudentIntegration(Protocol):
    async def status(self, user_id: str) -> Connection: ...
    async def authorize(self, user_id: str, return_path: str) -> str: ...
    def session(self, user_id: str) -> AbstractAsyncContextManager[ClientSession]: ...


def configured() -> bool:
    return bool(os.getenv("NTNU_INTEGRATION_FACTORY", "").strip())


@lru_cache(maxsize=4)
def _load(factory: str) -> StudentIntegration:
    try:
        module, name = factory.split(":", 1)
        integration = getattr(importlib.import_module(module), name)()
        if not all(callable(getattr(integration, method, None))
                   for method in ("status", "authorize", "session")):
            raise ValueError
        return integration
    except (ImportError, AttributeError, ValueError, TypeError):
        raise HTTPException(503, "The NTNU connection is temporarily unavailable") from None


def provider() -> StudentIntegration:
    if not configured():
        raise HTTPException(503, "NTNU booking is awaiting integration setup. You can try the demo.")
    return _load(os.environ["NTNU_INTEGRATION_FACTORY"].strip())


async def connection_status(user_id: str) -> Connection:
    return Connection.model_validate(await provider().status(user_id))


async def authorization_url(user_id: str) -> str:
    url = await provider().authorize(user_id, "/ntnu")
    parsed = urlsplit(url)
    origin = f"{parsed.scheme}://{parsed.netloc}"
    allowed = {value.strip().rstrip("/") for value in
               os.getenv("NTNU_AUTH_ALLOWED_ORIGINS", "").split(",") if value.strip()}
    if parsed.scheme != "https" or parsed.username or parsed.password or origin not in allowed:
        raise HTTPException(503, "The NTNU sign-in connection is not configured correctly")
    return url


@asynccontextmanager
async def student_session(user_id: str):
    if not (await connection_status(user_id)).connected:
        raise HTTPException(409, "Connect your NTNU account before searching or booking")
    async with provider().session(user_id) as session:
        yield session
