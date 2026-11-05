# standbyroom meeting room marketplace

standbyroom is a marketplace for meeting rooms across venues. Renters browse listings and request a time; hosts manage rooms and release unused time. Sensors in each room report occupancy, prices move with time and demand, and a Claude agent matches requests to openings. Mesh and Digs are the original pilot context. How the agent side works: [docs/agentic-platform](docs/agentic-platform/README.md).

## Repository layout

| Folder | Owns |
| --- | --- |
| `website/` | Public landing page that explains the product and directs buyers to the marketplace. |
| `marketplace/frontend/` | Next.js marketplace for browsing rooms, renter bookings, and host listings. |
| `marketplace/backend/` | FastAPI app served by Uvicorn. Owns accounts, inventory, pricing, holds, bookings, and the Claude agent's tools. Uses PostgreSQL. |
| `marketplace/agent/` | The marketplace agent that suggests rooms from your calendar. |
| `device/` | Atech ESP32 sensors and a FastAPI device server that tracks room occupancy. See [device/README.md](device/README.md). |
| `docs/` | How the product and platform work, for humans and agents. Index: [docs/README.md](docs/README.md). |
| `.agents/skills/` | Project skills: how to do a task here. `.claude/skills` is a symlink to it. |

Local startup and checks: [marketplace/README.md](marketplace/README.md).

## Rules

- Availability, price limits, and booking confirmation live in the marketplace backend, so the agent works from the same rules as the rest of the product. Claude chooses among eligible openings and explains the fit; the backend controls the quote, hold, and booking.
- `device/` reports physical facts only. The marketplace owns bookings and decides on no-shows, overstays, auto-release, and pricing.
- Room IDs are shared between the marketplace and the device server (e.g. `digs-demo-1`).
- This repo is public: secrets go in `.env` files (git ignores them); files hold no tokens, personal emails, or phone numbers.
- Always `git pull --rebase` before editing and again before pushing; teammates push to main often.
- Edit this file directly; `CLAUDE.md` only imports it. Keep it under about 60 lines: longer how-to goes into a skill (see `skill-system`).

## Skills

Each lives in `.agents/skills/<name>/SKILL.md`. Read the skill before doing its task.

| Skill | Use when |
| --- | --- |
| `skill-system` | Finding, adding, or editing a skill, or an `AGENTS.md` / `CLAUDE.md` here or in a subfolder. |
| `docs-system` | Writing or updating `docs/`, or deciding whether content belongs in docs, a skill, or `AGENTS.md`. |
| `device-integration` | Connecting the marketplace to the device server: occupancy events, presence checks, the release button. |
| `hackathon-demo` | Preparing or running the live demo. |

The marketplace agent's skills (calendar scan, preferences, room matching, booking, calendar write-back, marketplace MCP) live in [marketplace/agent/AGENTS.md](marketplace/agent/AGENTS.md).
