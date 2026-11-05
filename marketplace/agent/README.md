# Run the standbyroom calendar assistant locally

The marketplace tools run in a local MCP process. Claude uses its own Google Calendar connector to find meetings and the MCP tools to find available rooms, get prices, and book after approval.

## Set up

1. Start the [marketplace API](../README.md#develop-with-hot-reload) with `MARKETPLACE_DEMO_MODE=1` and no `ANTHROPIC_API_KEY`. Claude does the reasoning in the assistant, so this setup uses the marketplace's deterministic matcher.
2. Sign in as a renter, open **Calendar assistant** at `/agent`, and create an agent token. Copy `.env.example` to `.env` in this folder and put the token in `MARKETPLACE_API_TOKEN`. Set `MARKETPLACE_API_URL` if your backend is on a different port. The default is `http://127.0.0.1:8001`; Docker Compose uses port 8000.
3. Connect Google Calendar in Claude. Follow the local setup for your client below.

For Claude Code, run this from the repository root:

```sh
claude mcp add --transport stdio standbyroom -- \
  uv --directory "$PWD/marketplace/agent" run --locked --env-file .env python -m mcp_server.server
```

For [Claude Desktop](https://modelcontextprotocol.io/docs/develop/connect-local-servers), add a server under `mcpServers` in its local config and restart it. Use the full path from `command -v uv` and the full path to this folder:

```json
{
  "mcpServers": {
    "standbyroom": {
      "command": "/absolute/path/to/uv",
      "args": [
        "--directory", "/absolute/path/to/repo/marketplace/agent",
        "run", "--locked", "--env-file", ".env", "python", "-m", "mcp_server.server"
      ]
    }
  }
}
```

Try this in Claude: “Look at my next seven days for in-person meetings that need a room. Show available rooms and prices, then ask me before booking a specific option.” The marketplace receives only meeting times, headcount, room requirements, rough area and budget. Keep event titles, names, emails and descriptions in the calendar connector.

The tools mark `hold_room` and `confirm_booking` as actions requiring approval and show a confirmation form in clients that support it. Keep your client's ask permissions enabled for both. Approve only the displayed room, time and maximum total in Norwegian kroner. If a hold disappears, a new option needs its own approval. In **Calendar assistant**, you can revoke the token at any time.

## Check locally

```sh
uv --directory marketplace/agent run --locked python -m unittest discover -s tests -v
```
