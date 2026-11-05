"""Web push notifications for hosts and bookers, with per-user settings.

The one call the rest of the backend needs is ``notify(user_id, kind, title, body, url)``.
It runs off the request path, checks the user's settings, sends to every browser the
user subscribed, drops subscriptions the push service says are gone, and never raises.

The event helpers below (``offer_created``, ``booking_confirmed``, ``occupancy_changed``,
``check_booked_empty``) look up who to tell and call ``notify``. Each is also safe to
call from a request handler: it returns at once and logs failures.

VAPID keys come from VAPID_PUBLIC_KEY, VAPID_PRIVATE_KEY and VAPID_SUBJECT. Without
them notify() logs once and does nothing.
"""

import asyncio
import json
import logging
import os
from concurrent.futures import ThreadPoolExecutor
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, ConfigDict, Field

from . import db
from .accounts import Account, require_browser_mutation, require_user

logger = logging.getLogger(__name__)

Kind = Literal["room_booked", "occupied_unbooked", "booked_empty", "offer_ready"]
KINDS: tuple[str, ...] = ("room_booked", "occupied_unbooked", "booked_empty", "offer_ready")

OCCUPIED_UNBOOKED_REPEAT_MINUTES = 30
BOOKED_EMPTY_AFTER_MINUTES = 10
WATCH_INTERVAL_SECONDS = 60

_workers = ThreadPoolExecutor(max_workers=2, thread_name_prefix="push-notify")
_warned_unconfigured = False


# ---------------------------------------------------------------- public interface


def notify(user_id: UUID | str | None, kind: str, title: str, body: str, url: str) -> None:
    """Send a push to every device of one user, unless they switched this kind off."""
    if user_id is None:
        return
    _background(_deliver, str(user_id), kind, title, body, url)


def offer_created(offer_id: UUID | str) -> None:
    """A standby request got an offer (or, with auto-confirm, a booking)."""
    _background(_offer_created, str(offer_id))


def booking_confirmed(offer_id: UUID | str) -> None:
    """A booker accepted an offer: tell the room's host."""
    _background(_booking_confirmed, str(offer_id))


def occupancy_changed(room_id: str) -> None:
    """A sensor reported occupancy: tell the host if people are in an unbooked room."""
    _background(_occupancy_changed, room_id)


async def watch_booked_empty() -> None:
    """Every minute, tell hosts about bookings whose room is still empty after 10 minutes."""
    while True:
        await asyncio.sleep(WATCH_INTERVAL_SECONDS)
        if os.getenv("DATABASE_URL"):
            await asyncio.get_running_loop().run_in_executor(_workers, _safe, check_booked_empty)


# ---------------------------------------------------------------- delivery


def _background(function, *args) -> None:
    try:
        _workers.submit(_safe, function, *args)
    except Exception:  # noqa: BLE001 - notifications must never break the caller
        logger.exception("Could not queue a push notification")


def _safe(function, *args) -> None:
    try:
        function(*args)
    except Exception:  # noqa: BLE001
        logger.exception("Push notification failed")


def _vapid() -> tuple[str, str, str] | None:
    global _warned_unconfigured
    public, private = os.getenv("VAPID_PUBLIC_KEY", "").strip(), os.getenv("VAPID_PRIVATE_KEY", "").strip()
    subject = os.getenv("VAPID_SUBJECT", "").strip() or "mailto:hello@standbyroom.com"
    if not public or not private:
        if not _warned_unconfigured:
            _warned_unconfigured = True
            logger.warning("Push notifications are off: set VAPID_PUBLIC_KEY and VAPID_PRIVATE_KEY")
        return None
    return public, private, subject


class Gone(Exception):
    """The push service no longer knows this subscription (HTTP 404 or 410)."""


def _send(subscription: dict, payload: str, private_key: str, subject: str) -> None:
    from pywebpush import WebPushException, webpush

    try:
        webpush(
            subscription_info={
                "endpoint": subscription["endpoint"],
                "keys": {"p256dh": subscription["p256dh"], "auth": subscription["auth"]},
            },
            data=payload,
            vapid_private_key=private_key,
            vapid_claims={"sub": subject},
            ttl=3600,
            timeout=10,
        )
    except WebPushException as error:
        status = getattr(error.response, "status_code", None)
        if status in (404, 410):
            raise Gone from error
        raise


def _deliver(user_id: str, kind: str, title: str, body: str, url: str) -> None:
    if kind not in KINDS:
        logger.warning("Unknown notification kind %s", kind)
        return
    vapid = _vapid()
    if vapid is None:
        return
    _public, private_key, subject = vapid
    if not load_settings(user_id)[kind]:
        return
    with db._connect() as connection:
        subscriptions = connection.execute(
            "SELECT endpoint, p256dh, auth FROM marketplace_push_subscriptions WHERE user_id = %s",
            (user_id,),
        ).fetchall()
    payload = json.dumps({"kind": kind, "title": title, "body": body, "url": url})
    for subscription in subscriptions:
        try:
            _send(subscription, payload, private_key, subject)
        except Gone:
            delete_subscription(user_id, subscription["endpoint"])
        except Exception as error:  # noqa: BLE001 - one bad device must not stop the others
            logger.warning("Push to one device failed: %s", type(error).__name__)


# ---------------------------------------------------------------- storage


def load_settings(user_id: UUID | str) -> dict[str, bool]:
    with db._connect() as connection:
        row = connection.execute(
            f"SELECT {', '.join(KINDS)} FROM marketplace_notification_settings WHERE user_id = %s",
            (user_id,),
        ).fetchone()
    return {kind: True if row is None else bool(row[kind]) for kind in KINDS}


def save_settings(user_id: UUID | str, changes: dict[str, bool]) -> dict[str, bool]:
    values = {**load_settings(user_id), **changes}
    columns = ", ".join(KINDS)
    updates = ", ".join(f"{kind} = EXCLUDED.{kind}" for kind in KINDS)
    with db._connect() as connection:
        connection.execute(
            f"""
            INSERT INTO marketplace_notification_settings (user_id, {columns}, updated_at)
            VALUES (%s, {', '.join(['%s'] * len(KINDS))}, now())
            ON CONFLICT (user_id) DO UPDATE SET {updates}, updated_at = now()
            """,
            (user_id, *(values[kind] for kind in KINDS)),
        )
    return load_settings(user_id)


def save_subscription(user_id: UUID | str, endpoint: str, p256dh: str, auth: str) -> None:
    with db._connect() as connection:
        connection.execute(
            """
            INSERT INTO marketplace_push_subscriptions (user_id, endpoint, p256dh, auth)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (endpoint) DO UPDATE SET user_id = EXCLUDED.user_id,
                p256dh = EXCLUDED.p256dh, auth = EXCLUDED.auth
            """,
            (user_id, endpoint, p256dh, auth),
        )


def delete_subscription(user_id: UUID | str, endpoint: str) -> None:
    with db._connect() as connection:
        connection.execute(
            "DELETE FROM marketplace_push_subscriptions WHERE user_id = %s AND endpoint = %s",
            (user_id, endpoint),
        )


def _claim(connection, key: str, repeat_minutes: int | None = None) -> bool:
    """Record that a notification is going out; False if it already went out (recently)."""
    if repeat_minutes is None:
        row = connection.execute(
            "INSERT INTO marketplace_notification_log (key) VALUES (%s) ON CONFLICT DO NOTHING RETURNING key",
            (key,),
        ).fetchone()
    else:
        row = connection.execute(
            """
            INSERT INTO marketplace_notification_log (key) VALUES (%s)
            ON CONFLICT (key) DO UPDATE SET sent_at = now()
            WHERE marketplace_notification_log.sent_at < now() - make_interval(mins => %s)
            RETURNING key
            """,
            (key, repeat_minutes),
        ).fetchone()
    return row is not None


# ---------------------------------------------------------------- events


def _offer(connection, offer_id: str) -> dict | None:
    return connection.execute(
        """
        SELECT o.id, o.request_id, o.room_id, o.start_at, o.confirmed_at,
            r.name AS room_name, r.owner_id, q.user_id AS booker_id
        FROM marketplace_offers o
        JOIN marketplace_rooms r ON r.id = o.room_id
        JOIN marketplace_requests q ON q.id = o.request_id
        WHERE o.id = %s
        """,
        (offer_id,),
    ).fetchone()


def _when(offer: dict) -> str:
    return db._datetime(offer["start_at"]).astimezone(db._OSLO).strftime("%H:%M")


def _offer_created(offer_id: str) -> None:
    with db._connect() as connection:
        offer = _offer(connection, offer_id)
        if offer is None or not _claim(connection, f"offer_ready:{offer_id}"):
            return
    url = f"/bookings/{offer['request_id']}"
    if offer["confirmed_at"]:
        notify(offer["booker_id"], "offer_ready", "Room booked for you",
               f"{offer['room_name']} at {_when(offer)} is yours.", url)
        _booking_confirmed(offer_id)
    else:
        notify(offer["booker_id"], "offer_ready", "A room freed up",
               f"{offer['room_name']} at {_when(offer)}. Accept within 5 minutes.", url)


def _booking_confirmed(offer_id: str) -> None:
    with db._connect() as connection:
        offer = _offer(connection, offer_id)
        if offer is None or not offer["confirmed_at"] or offer["owner_id"] is None:
            return
        if not _claim(connection, f"room_booked:{offer_id}"):
            return
    notify(offer["owner_id"], "room_booked", "Your room was booked",
           f"{offer['room_name']} is booked from {_when(offer)}.", "/host")


def _occupancy_changed(room_id: str) -> None:
    with db._connect() as connection:
        room = connection.execute(
            """
            SELECT r.name, r.owner_id
            FROM marketplace_rooms r
            JOIN marketplace_room_occupancy occ ON occ.room_id = r.id
            WHERE r.id = %s AND occ.occupied AND r.owner_id IS NOT NULL
              AND NOT EXISTS (
                SELECT 1 FROM marketplace_offers o
                WHERE o.room_id = r.id AND o.confirmed_at IS NOT NULL
                  AND o.start_at <= now() AND o.end_at > now())
              AND NOT EXISTS (
                SELECT 1 FROM marketplace_device_blocks b
                WHERE b.room_id = r.id AND b.start_at <= now() AND b.end_at > now())
            """,
            (room_id,),
        ).fetchone()
        if room is None or not _claim(connection, f"occupied_unbooked:{room_id}", OCCUPIED_UNBOOKED_REPEAT_MINUTES):
            return
    notify(room["owner_id"], "occupied_unbooked", "People in an unbooked room",
           f"The sensor sees people in {room['name']}, but nothing is booked now.", "/host")


def check_booked_empty() -> None:
    with db._connect() as connection:
        offers = connection.execute(
            """
            SELECT o.id, o.start_at, r.name AS room_name, r.owner_id
            FROM marketplace_offers o
            JOIN marketplace_rooms r ON r.id = o.room_id
            LEFT JOIN marketplace_room_occupancy occ ON occ.room_id = o.room_id
            WHERE o.confirmed_at IS NOT NULL AND r.owner_id IS NOT NULL
              AND o.start_at <= now() - make_interval(mins => %s) AND o.end_at > now()
              AND (occ.occupied IS NULL OR NOT occ.occupied)
              AND NOT EXISTS (
                SELECT 1 FROM marketplace_notification_log l WHERE l.key = 'booked_empty:' || o.id::text)
            """,
            (BOOKED_EMPTY_AFTER_MINUTES,),
        ).fetchall()
        claimed = [offer for offer in offers if _claim(connection, f"booked_empty:{offer['id']}")]
    for offer in claimed:
        notify(offer["owner_id"], "booked_empty", "Booked room looks empty",
               f"{offer['room_name']} was booked from {_when(offer)}, but no one is there.", "/host")


# ---------------------------------------------------------------- HTTP


class SubscriptionKeys(BaseModel):
    model_config = ConfigDict(extra="ignore")
    p256dh: str = Field(min_length=1, max_length=512)
    auth: str = Field(min_length=1, max_length=512)


class SubscriptionInput(BaseModel):
    model_config = ConfigDict(extra="ignore")
    endpoint: str = Field(min_length=1, max_length=2048, pattern=r"^https://")
    keys: SubscriptionKeys


class SubscriptionDelete(BaseModel):
    model_config = ConfigDict(extra="ignore")
    endpoint: str = Field(min_length=1, max_length=2048)


class NotificationSettings(BaseModel):
    room_booked: bool = True
    occupied_unbooked: bool = True
    booked_empty: bool = True
    offer_ready: bool = True


class NotificationSettingsInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    room_booked: bool | None = None
    occupied_unbooked: bool | None = None
    booked_empty: bool | None = None
    offer_ready: bool | None = None


router = APIRouter(tags=["notifications"])
User = Annotated[Account, Depends(require_user)]


@router.get("/push/public-key")
def public_key(_account: User, response: Response) -> dict[str, str]:
    key = os.getenv("VAPID_PUBLIC_KEY", "").strip()
    if not key:
        raise HTTPException(status_code=503, detail="Push notifications are not configured")
    response.headers["Cache-Control"] = "no-store"
    return {"publicKey": key}


@router.post("/push/subscriptions", status_code=204, dependencies=[Depends(require_browser_mutation)])
def subscribe(body: SubscriptionInput, account: User) -> Response:
    save_subscription(account.id, body.endpoint, body.keys.p256dh, body.keys.auth)
    return Response(status_code=204)


@router.delete("/push/subscriptions", status_code=204, dependencies=[Depends(require_browser_mutation)])
def unsubscribe(body: SubscriptionDelete, account: User) -> Response:
    delete_subscription(account.id, body.endpoint)
    return Response(status_code=204)


@router.get("/notifications/settings", response_model=NotificationSettings)
def get_settings(account: User, response: Response) -> dict[str, bool]:
    response.headers["Cache-Control"] = "no-store"
    return load_settings(account.id)


@router.put(
    "/notifications/settings", response_model=NotificationSettings, dependencies=[Depends(require_browser_mutation)],
)
def put_settings(body: NotificationSettingsInput, account: User, response: Response) -> dict[str, bool]:
    response.headers["Cache-Control"] = "no-store"
    return save_settings(account.id, body.model_dump(exclude_none=True))
