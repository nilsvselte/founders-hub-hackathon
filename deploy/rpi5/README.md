# Hackathon deployment on a Raspberry Pi 5

This is how the marketplace and device server ran during the hackathon demo on 5 November 2026. A Raspberry Pi 5 ran them behind a Cloudflare Tunnel. The services were stopped afterwards. The landing page at `standbyroom.com` is deployed separately and was not part of this setup.

| Service | URL | Port | Unit |
| --- | --- | --- | --- |
| Device server (`device/server`) | `https://device.standbyroom.com` | 8012 | `standbyroom-device.service` |
| Marketplace API (`marketplace/backend`) | `https://api.standbyroom.com` | 8013 | `standbyroom-api.service` |
| Marketplace frontend (`marketplace/frontend`) | `https://app.standbyroom.com` | 8014 | `standbyroom-app.service` |

The device server pushes events to the API over localhost. The frontend proxies `/api/*` to the API. The Atech board posts to `https://device.standbyroom.com/v1/telemetry` over HTTPS.

## Set it up again

The commands assume the repository is cloned to `~/projects/founders-hub-hackathon` with uv and Node 24 (fnm) installed.

1. Run `install-system.sh` with sudo. It installs PostgreSQL, creates the `marketplace` role and database, and adds the three hostnames to `/etc/cloudflared/config.yml` through the existing `cf_ingress.py` helper. Then it validates the config and restarts cloudflared, or rolls back if validation fails.
2. Create the DNS records with `cloudflared tunnel --origincert <cert for standbyroom.com> route dns <tunnel id> <host>` for `device`, `api`, and `app`.
3. Copy `device.env.example` and `backend.env.example` to `~/deploy/standbyroom-apps/device.env` and `backend.env`. Fill in the secrets and set the same `MARKETPLACE_DEVICE_TOKEN` in both files.
4. Install dependencies and build the frontend. Run `uv sync` in `device/server` and `marketplace/backend`. In `marketplace/frontend`, run `pnpm install --frozen-lockfile` and `MARKETPLACE_API_URL=http://127.0.0.1:8013 pnpm run build`.
5. Copy the three units to `~/.config/systemd/user/`, then run `systemctl --user daemon-reload` and `systemctl --user enable --now standbyroom-device standbyroom-api standbyroom-app`. Lingering must be on so the services run without a login session.

To redeploy, run `git pull`, sync the dependencies, rebuild the frontend, and restart the three units.

## Demo data

The marketplace only offers time a host has released. For the demo, Driv (`digs-demo-1`) was the only published room. Other rooms were unpublished, and a Monday opening was inserted by hand because the host dashboard can only release time starting now. Run `python -m app.demo_host demo-host@example.test` with `MARKETPLACE_DEMO_MODE=1` in `marketplace/backend` to give the demo host the Digs rooms.
