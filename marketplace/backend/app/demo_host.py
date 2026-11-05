"""Give a demo host account the unowned Mesh/Digs demo rooms.

Run inside the API container (demo mode only), from marketplace/:

    docker compose exec -e DEMO_HOST_PASSWORD='<12+ chars>' api \
        .venv/bin/python -m app.demo_host host@example.test

Creates the host account if the email is new (needs DEMO_HOST_PASSWORD), then
assigns every `digs` room that has no owner to it. Safe to run again.
"""

import os
import secrets
import sys
from uuid import uuid4

from . import db
from .accounts import _hash_password

DEMO_VENUE = "digs"


def claim_demo_rooms(email: str, password: str | None) -> list[str]:
    email = email.strip().casefold()
    with db._connect() as connection:
        user = connection.execute(
            "SELECT id, role FROM marketplace_users WHERE email = %s", (email,)
        ).fetchone()
        if user is None:
            if not password or len(password) < 12:
                raise SystemExit("New account: set DEMO_HOST_PASSWORD (12+ characters)")
            salt = secrets.token_bytes(16)
            user = connection.execute(
                """
                INSERT INTO marketplace_users (id, name, email, role, password_salt, password_hash)
                VALUES (%s, 'Demo host', %s, 'host', %s, %s)
                RETURNING id, role
                """,
                (uuid4(), email, salt, _hash_password(password, salt)),
            ).fetchone()
        if user["role"] != "host":
            raise SystemExit(f"{email} is a renter account; use a separate host email")
        rows = connection.execute(
            """
            UPDATE marketplace_rooms SET owner_id = %s
            WHERE venue = %s AND (owner_id IS NULL OR owner_id = %s)
            RETURNING id
            """,
            (user["id"], DEMO_VENUE, user["id"]),
        ).fetchall()
    return sorted(row["id"] for row in rows)


def main() -> None:
    if os.getenv("MARKETPLACE_DEMO_MODE") != "1":
        raise SystemExit("Demo host setup only runs with MARKETPLACE_DEMO_MODE=1")
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python -m app.demo_host <host email>")
    db.check_ready()
    rooms = claim_demo_rooms(sys.argv[1], os.getenv("DEMO_HOST_PASSWORD"))
    print(f"Demo host owns: {', '.join(rooms) or 'no rooms'}")


if __name__ == "__main__":
    main()
