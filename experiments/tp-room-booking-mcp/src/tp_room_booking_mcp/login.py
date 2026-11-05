"""User-run, headed login helper. The user completes Feide, including any MFA."""

import argparse
import json
import os
import tempfile
from pathlib import Path
from urllib.parse import quote

from .client import BASE, TP_COOKIE_DOMAINS, Settings


def save_cookies(path: Path, cookies: list[dict]):
    # Store only the TP application's cookies, not Feide/NTNU identity-provider cookies.
    cookies = [cookie for cookie in cookies if cookie["domain"].lstrip(".") in TP_COOKIE_DOMAINS]
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(dir=path.parent, prefix=".session-")
    try:
        with os.fdopen(fd, "w") as out:
            json.dump({"cookies": cookies, "origins": []}, out)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--channel", default="chrome", help="Installed browser channel (chrome/msedge)"
    )
    args = parser.parse_args()
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        parser.error("Install the login extra: uv sync --extra login")
    settings = Settings.from_env()
    with sync_playwright() as p:
        browser = p.chromium.launch(channel=args.channel, headless=False)
        try:
            context = browser.new_context()
            page = context.new_page()
            redirect = quote("/ntnu/app/rombestilling/", safe="")
            page.goto(f"{BASE}/login/?redirect={redirect}", wait_until="domcontentloaded")
            print("Complete Feide login in the browser. No password is read by this helper.")
            input("When TP room booking is visible, press Enter here: ")
            response = context.request.get(f"{BASE}/ws/user/session.php", max_redirects=0)
            try:
                data = response.json()
            except ValueError:
                data = None
            if not response.ok or not isinstance(data, dict) or not data.get("username"):
                raise SystemExit("TP did not confirm a logged-in session. Nothing was saved.")
            save_cookies(settings.state_file, context.cookies())
            print(f"Saved TP session to {settings.state_file} (owner-only file permissions).")
            print("Restart the MCP server or call session_status to use the new session.")
        finally:
            browser.close()
