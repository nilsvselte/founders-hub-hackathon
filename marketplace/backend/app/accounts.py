import hashlib
import os
import re
import secrets
from collections.abc import Awaitable, Callable
from threading import BoundedSemaphore
from typing import Annotated, Literal
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute
from fastapi.security.utils import get_authorization_scheme_param
from pydantic import BaseModel, SecretStr, field_validator

from . import db


class AccountRoute(APIRoute):
    def get_route_handler(self) -> Callable[[Request], Awaitable[Response]]:
        handler = super().get_route_handler()

        async def handle(request: Request) -> Response:
            try:
                return await handler(request)
            except RequestValidationError:
                # FastAPI's default errors can include the full submitted body.
                return JSONResponse(
                    {"detail": "Enter valid account details"},
                    status_code=422,
                    headers={"Cache-Control": "no-store"},
                )

        return handle


router = APIRouter(prefix="/auth", tags=["accounts"], route_class=AccountRoute)
_COOKIE = "marketplace_session"
_SESSION_SECONDS = 7 * 24 * 60 * 60
_EMAIL = re.compile(r"[^\s@\x00]+@[^\s@\x00]+\.[^\s@\x00]+")
_TOKEN = re.compile(r"[A-Za-z0-9_-]{43}")
_AGENT_TOKEN = re.compile(r"sra_[A-Za-z0-9_-]{43}")
_HASH_SLOTS = BoundedSemaphore(4)


class Credentials(BaseModel):
    email: str
    password: SecretStr

    @field_validator("*", mode="before")
    @classmethod
    def validate_utf8(cls, value: object) -> object:
        if isinstance(value, str):
            try:
                value.encode("utf-8")
            except UnicodeEncodeError:
                raise ValueError("Enter valid text") from None
        return value


class Registration(Credentials):
    name: str
    role: Literal["renter", "host"] = "renter"


class Account(BaseModel):
    id: UUID
    name: str
    email: str
    role: Literal["renter", "host"]


def require_browser_mutation(request: Request) -> None:
    if request.headers.get("x-marketplace-request") != "1":
        raise HTTPException(status_code=403, detail="Missing marketplace request header")


def _connect():
    if not os.getenv("DATABASE_URL"):
        raise HTTPException(status_code=503, detail="Database connection is not configured")
    return db._connect()


def _hash_password(password: str, salt: bytes) -> bytes:
    if not _HASH_SLOTS.acquire(blocking=False):
        raise HTTPException(status_code=429, detail="Please wait a moment and try again")
    try:
        return hashlib.scrypt(
            password.encode("utf-8"), salt=salt, n=2**14, r=8, p=5, dklen=32,
            maxmem=64 * 1024 * 1024,
        )
    finally:
        _HASH_SLOTS.release()


def _cookie_hash(request: Request) -> bytes | None:
    token = request.cookies.get(_COOKIE, "")
    if _TOKEN.fullmatch(token):
        return hashlib.sha256(token.encode("ascii")).digest()
    return None


def _issue_session(connection, request: Request, user_id: UUID) -> str:
    token = secrets.token_urlsafe(32)
    if old_hash := _cookie_hash(request):
        connection.execute("DELETE FROM marketplace_sessions WHERE token_hash = %s", (old_hash,))
    connection.execute(
        "DELETE FROM marketplace_sessions WHERE user_id = %s AND expires_at <= now()",
        (user_id,),
    )
    connection.execute(
        """
        INSERT INTO marketplace_sessions (token_hash, user_id, expires_at)
        VALUES (%s, %s, now() + make_interval(secs => %s))
        """,
        (hashlib.sha256(token.encode("ascii")).digest(), user_id, _SESSION_SECONDS),
    )
    return token


def _cookie_options() -> dict:
    return {
        "httponly": True,
        "secure": os.getenv("MARKETPLACE_SECURE_COOKIES") == "1",
        "samesite": "lax",
        "path": "/",
    }


def _set_session_cookie(response: Response, token: str) -> None:
    response.headers["Cache-Control"] = "no-store"
    response.set_cookie(_COOKIE, token, max_age=_SESSION_SECONDS, **_cookie_options())


def require_user(request: Request) -> Account:
    token_hash = _cookie_hash(request)
    if token_hash is not None:
        with _connect() as connection:
            account = connection.execute(
                """
                SELECT u.id, u.name, u.email, u.role
                FROM marketplace_sessions s
                JOIN marketplace_users u ON u.id = s.user_id
                WHERE s.token_hash = %s AND s.expires_at > now()
                """,
                (token_hash,),
            ).fetchone()
        if account is not None:
            return Account.model_validate(account)
    raise HTTPException(status_code=401, detail="Sign in to continue")


def require_agent_or_user(request: Request) -> Account:
    """Authenticate a renter token on routes that explicitly opt in."""
    authorization = request.headers.get("authorization")
    if authorization is None:
        return require_user(request)

    scheme, token = get_authorization_scheme_param(authorization)
    if scheme.lower() == "bearer" and _AGENT_TOKEN.fullmatch(token):
        token_hash = hashlib.sha256(token.encode("ascii")).digest()
        with _connect() as connection:
            account = connection.execute(
                """
                SELECT u.id, u.name, u.email, u.role
                FROM marketplace_agent_tokens t
                JOIN marketplace_users u ON u.id = t.user_id
                WHERE t.token_hash = %s AND u.role = 'renter'
                """,
                (token_hash,),
            ).fetchone()
        if account is not None:
            return Account.model_validate(account)
    raise HTTPException(
        status_code=401,
        detail="Invalid marketplace agent token",
        headers={"WWW-Authenticate": "Bearer", "Cache-Control": "no-store"},
    )


def _agent_token_owner(account: Annotated[Account, Depends(require_user)]) -> Account:
    if account.role != "renter":
        raise HTTPException(status_code=403, detail="A renter account is required")
    return account


AgentTokenOwner = Annotated[Account, Depends(_agent_token_owner)]


@router.get("/agent-token")
def get_agent_token_status(account: AgentTokenOwner, response: Response) -> dict[str, bool]:
    response.headers["Cache-Control"] = "no-store"
    with _connect() as connection:
        active = connection.execute(
            "SELECT EXISTS(SELECT 1 FROM marketplace_agent_tokens WHERE user_id = %s) AS active",
            (account.id,),
        ).fetchone()["active"]
    return {"active": active}


@router.post("/agent-token", status_code=201, dependencies=[Depends(require_browser_mutation)])
def issue_agent_token(account: AgentTokenOwner, response: Response) -> dict[str, str]:
    response.headers["Cache-Control"] = "no-store"
    token = f"sra_{secrets.token_urlsafe(32)}"
    token_hash = hashlib.sha256(token.encode("ascii")).digest()
    with _connect() as connection:
        connection.execute(
            """
            INSERT INTO marketplace_agent_tokens (user_id, token_hash)
            VALUES (%s, %s)
            ON CONFLICT (user_id) DO UPDATE SET token_hash = EXCLUDED.token_hash
            """,
            (account.id, token_hash),
        )
    return {"token": token}


@router.delete("/agent-token", status_code=204, dependencies=[Depends(require_browser_mutation)])
def revoke_agent_token(account: AgentTokenOwner) -> Response:
    with _connect() as connection:
        connection.execute("DELETE FROM marketplace_agent_tokens WHERE user_id = %s", (account.id,))
    return Response(status_code=204, headers={"Cache-Control": "no-store"})


@router.post("/register", status_code=201, dependencies=[Depends(require_browser_mutation)])
def register(body: Registration, request: Request, response: Response) -> Account:
    name = body.name.strip()
    email = body.email.strip().casefold()
    password = body.password.get_secret_value()
    if not 1 <= len(name) <= 100 or "\x00" in name:
        raise HTTPException(status_code=422, detail="Enter a name up to 100 characters")
    if len(email) > 254 or not _EMAIL.fullmatch(email):
        raise HTTPException(status_code=422, detail="Enter a valid email address")
    if not 12 <= len(password) <= 128:
        raise HTTPException(status_code=422, detail="Use a password between 12 and 128 characters")

    salt = secrets.token_bytes(16)
    password_hash = _hash_password(password, salt)
    with _connect() as connection:
        account = connection.execute(
            """
            INSERT INTO marketplace_users (id, name, email, role, password_salt, password_hash)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (email) DO NOTHING
            RETURNING id, name, email, role
            """,
            (uuid4(), name, email, body.role, salt, password_hash),
        ).fetchone()
        if account is None:
            raise HTTPException(status_code=409, detail="An account already exists for this email")
        token = _issue_session(connection, request, account["id"])

    _set_session_cookie(response, token)
    return Account.model_validate(account)


@router.post("/login", dependencies=[Depends(require_browser_mutation)])
def login(body: Credentials, request: Request, response: Response) -> Account:
    email = body.email.strip().casefold()
    password = body.password.get_secret_value()
    invalid = HTTPException(status_code=401, detail="Email or password is incorrect")
    if len(email) > 254 or not 12 <= len(password) <= 128 or not _EMAIL.fullmatch(email):
        raise invalid

    with _connect() as connection:
        account = connection.execute(
            "SELECT id, name, email, role, password_salt, password_hash FROM marketplace_users WHERE email = %s",
            (email,),
        ).fetchone()
    # Match the password work for missing and existing accounts.
    salt = account["password_salt"] if account else bytes(16)
    expected = account["password_hash"] if account else bytes(32)
    if not secrets.compare_digest(_hash_password(password, salt), expected) or account is None:
        raise invalid

    with _connect() as connection:
        token = _issue_session(connection, request, account["id"])
    _set_session_cookie(response, token)
    return Account.model_validate(account)


DEMO_GUEST_EMAIL = "demo-guest@standbyroom.demo"


def demo_guest_enabled() -> bool:
    """Shared signed-out demo renter. On unless MARKETPLACE_DEMO_GUEST=0."""
    return os.getenv("MARKETPLACE_DEMO_GUEST", "1") != "0"


@router.post("/demo-session", dependencies=[Depends(require_browser_mutation)])
def demo_session(request: Request, response: Response) -> Account:
    """Sign the visitor in as the shared demo renter. That account has no usable password."""
    if not demo_guest_enabled():
        raise HTTPException(status_code=404, detail="Not found")
    with _connect() as connection:
        connection.execute(
            """
            INSERT INTO marketplace_users (id, name, email, role, password_salt, password_hash)
            VALUES (%s, 'Demo guest', %s, 'renter', %s, %s)
            ON CONFLICT (email) DO NOTHING
            """,
            (uuid4(), DEMO_GUEST_EMAIL, secrets.token_bytes(16), secrets.token_bytes(32)),
        )
        account = connection.execute(
            "SELECT id, name, email, role FROM marketplace_users WHERE email = %s AND role = 'renter'",
            (DEMO_GUEST_EMAIL,),
        ).fetchone()
        if account is None:
            raise HTTPException(status_code=503, detail="Demo guest is unavailable")
        token = _issue_session(connection, request, account["id"])
    _set_session_cookie(response, token)
    return Account.model_validate(account)


DEMO_HOST_EMAIL = "demo-host@example.test"


@router.post("/demo-host-session", dependencies=[Depends(require_browser_mutation)])
def demo_host_session(request: Request, response: Response) -> Account:
    """Sign the visitor in as the seeded demo host (DEMO.md setup). Same flag as the demo guest."""
    if not demo_guest_enabled():
        raise HTTPException(status_code=404, detail="Not found")
    with _connect() as connection:
        account = connection.execute(
            "SELECT id, name, email, role FROM marketplace_users WHERE email = %s AND role = 'host'",
            (DEMO_HOST_EMAIL,),
        ).fetchone()
        if account is None:
            raise HTTPException(status_code=503, detail="Demo host is not set up")
        token = _issue_session(connection, request, account["id"])
    _set_session_cookie(response, token)
    return Account.model_validate(account)


@router.get("/me")
def me(response: Response, account: Account = Depends(require_user)) -> Account:
    response.headers["Cache-Control"] = "no-store"
    return account


@router.post("/logout", status_code=204, dependencies=[Depends(require_browser_mutation)])
def logout(request: Request) -> Response:
    if token_hash := _cookie_hash(request):
        with _connect() as connection:
            connection.execute("DELETE FROM marketplace_sessions WHERE token_hash = %s", (token_hash,))
    response = Response(status_code=204, headers={"Cache-Control": "no-store"})
    response.delete_cookie(_COOKIE, **_cookie_options())
    return response
