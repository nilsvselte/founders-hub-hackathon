"""A renter's About, Preferences and agent settings, and the compact summary the marketplace agent reads."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute

from . import db
from .accounts import Account, require_agent_or_user, require_browser_mutation, require_user
from .schemas import AboutYou, AgentSettings, CatalogOptions, RoomPreferences, UserPreferences, UserPreferencesInput

class PreferencesRoute(APIRoute):
    def get_route_handler(self):
        handler = super().get_route_handler()

        async def handle(request: Request) -> Response:
            try:
                return await handler(request)
            except RequestValidationError:
                return JSONResponse(
                    {"detail": "Enter valid room preferences"},
                    status_code=422,
                    headers={"Cache-Control": "no-store"},
                )

        return handle


router = APIRouter(tags=["preferences"], route_class=PreferencesRoute)

_ABOUT = tuple(AboutYou.model_fields)
_PREFERENCES = tuple(RoomPreferences.model_fields)
_AGENT = tuple(AgentSettings.model_fields)
_COLUMNS = (*_ABOUT, *_PREFERENCES, *_AGENT)


def require_renter_account(account: Annotated[Account, Depends(require_user)]) -> Account:
    if account.role != "renter":
        raise HTTPException(status_code=403, detail="A renter account is required")
    return account


RenterAccount = Annotated[Account, Depends(require_renter_account)]


def require_context_account(account: Annotated[Account, Depends(require_agent_or_user)]) -> Account:
    return require_renter_account(account)


ContextAccount = Annotated[Account, Depends(require_context_account)]


def load_preferences(user_id) -> UserPreferences:
    """The saved row, or defaults when the renter hasn't saved anything yet."""
    with db._connect() as connection:
        row = connection.execute(
            f"SELECT {', '.join(_COLUMNS)}, updated_at FROM marketplace_user_preferences WHERE user_id = %s",
            (user_id,),
        ).fetchone()
    if row is None:
        return UserPreferences()
    return UserPreferences(
        about={key: row[key] for key in _ABOUT},
        preferences={key: row[key] for key in _PREFERENCES},
        agent={key: row[key] for key in _AGENT},
        updated_at=row["updated_at"],
    )


@router.get("/me/preferences", response_model=UserPreferences)
def get_preferences(account: RenterAccount, response: Response) -> UserPreferences:
    response.headers["Cache-Control"] = "no-store"
    return load_preferences(account.id)


@router.put("/me/preferences", response_model=UserPreferences, dependencies=[Depends(require_browser_mutation)])
def put_preferences(body: UserPreferencesInput, account: RenterAccount, response: Response) -> UserPreferences:
    values = {**body.about.model_dump(), **body.preferences.model_dump(), **body.agent.model_dump()}
    try:
        for value in values.values():
            for item in value if isinstance(value, list) else (value,):
                if isinstance(item, str) and b"\0" in item.encode("utf-8"):
                    raise ValueError("Text contains a null byte")
    except ValueError:
        raise HTTPException(
            status_code=422, detail="Enter valid room preferences", headers={"Cache-Control": "no-store"},
        ) from None
    values["equipment"] = db._equipment(values["equipment"])
    columns = ", ".join(_COLUMNS)
    placeholders = ", ".join(["%s"] * len(_COLUMNS))
    updates = ", ".join(f"{column} = EXCLUDED.{column}" for column in _COLUMNS)
    with db._connect() as connection:
        connection.execute(
            f"""
            INSERT INTO marketplace_user_preferences (user_id, {columns}, updated_at)
            VALUES (%s, {placeholders}, now())
            ON CONFLICT (user_id) DO UPDATE SET {updates}, updated_at = now()
            """,
            (account.id, *(values[column] for column in _COLUMNS)),
        )
    response.headers["Cache-Control"] = "no-store"
    return load_preferences(account.id)


def agent_context(saved: UserPreferences) -> dict[str, Any]:
    """Only what helps match rooms: no name, email, account id or team name."""
    about, prefs, agent = saved.about, saved.preferences, saved.agent
    home = None
    if about.home_area or about.home_lat is not None:
        home = {
            "area": about.home_area or None,
            # Round to about 1 km so the agent gets a rough point, not an address.
            "lat": round(about.home_lat, 2) if about.home_lat is not None else None,
            "lon": round(about.home_lon, 2) if about.home_lon is not None else None,
        }
    return {
        "has_saved_preferences": saved.updated_at is not None,
        "about": {
            "what_we_do": about.what_we_do or None,
            "usual_party_size": about.usual_party_size,
            "meeting_types": about.meeting_types,
            "home": home,
            "notes_for_agent": about.agent_notes or None,
        },
        "hard_filters": {
            "max_hourly_price_ore": prefs.max_hourly_ore,
            "must_have_equipment": prefs.equipment,
            "avoid_venue_ids": prefs.avoid_venues,
            "max_travel_minutes": prefs.max_travel_minutes,
        },
        "soft_preferences": {
            "room_kinds": prefs.room_kinds,
            "preferred_venue_ids": prefs.preferred_venues,
            "wishes": prefs.wishes or None,
        },
        "suggestions": {
            "suggest_for_unroomed_meetings": agent.suggest_for_unroomed_meetings,
            "lead_days": agent.suggestion_lead_days,
            "min_attendees": agent.min_attendees_to_suggest,
            "skip_online_meetings": agent.skip_online_meetings,
        },
        "notifications": {
            "allowed": agent.allow_notifications,
            "channels": agent.notification_channels if agent.allow_notifications else [],
            "quiet_hours": (
                {"start": agent.quiet_hours_start.strftime("%H:%M"), "end": agent.quiet_hours_end.strftime("%H:%M"),
                 "timezone": "Europe/Oslo"}
                if agent.quiet_hours_start and agent.quiet_hours_end else None
            ),
        },
    }


@router.get("/me/agent-context")
def get_agent_context(account: ContextAccount, response: Response) -> dict[str, Any]:
    response.headers["Cache-Control"] = "no-store"
    return agent_context(load_preferences(account.id))


@router.get("/catalog/options", response_model=CatalogOptions)
def catalog_options() -> dict:
    """Room kinds, equipment and venues used by published listings, for preference pickers."""
    with db._connect() as connection:
        rooms = connection.execute(
            """
            SELECT venue, venue_name, city, kind, equipment, owner_id FROM marketplace_rooms
            WHERE published AND city IS NOT NULL
            """
        ).fetchall()
    kinds: dict[str, str] = {}
    equipment: set[str] = set()
    venues: dict[str, dict] = {}
    for room in rooms:
        if room["kind"]:
            label = room["kind"].strip()
            kinds.setdefault(label.casefold(), label[:1].upper() + label[1:].lower())
        equipment.update(room["equipment"] or [])
        # Host-created listings carry a placeholder venue id, so only catalog venues are offered.
        if room["venue"] and room["owner_id"] is None:
            venues.setdefault(room["venue"], {"id": room["venue"], "name": room["venue_name"], "city": room["city"]})
    return {
        "room_kinds": sorted(kinds.values()),
        "equipment": sorted(equipment),
        "venues": sorted(venues.values(), key=lambda venue: (venue["name"].casefold(), venue["id"])),
    }
