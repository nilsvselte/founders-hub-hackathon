# Docs

How standbyroom works and why, for teammates and coding agents. For how to do a task, see the skills in [`.agents/skills/`](../.agents/skills/); for the entry point, see [`AGENTS.md`](../AGENTS.md). The `docs-system` skill says what belongs here and how to keep it current.

| Doc | Covers |
| --- | --- |
| [Agentic platform](agentic-platform/README.md) | The marketplace agent, agents that find and book rooms, and how they use sensor data and dynamic prices. |
| [Notifications](notifications.md) | Web push to hosts and bookers: kinds, triggers, settings, VAPID keys, testing a push. |
| [Phone app](phone-app.md) | Installing the marketplace on a phone's home screen, the service worker, and subscribing a device to push. |

Related READMEs:

- [marketplace/README.md](../marketplace/README.md): running the marketplace locally, demo mode, pilot venues.
- [device/README.md](../device/README.md): sensors, occupancy, and the device API contract.
