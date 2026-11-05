# Deploy the marketplace

Deploy the Next.js app to Vercel. The marketplace serves room browsing at `/` and the landing page at `/welcome`. Run `node marketplace/frontend/scripts/sync-landing.mjs` after editing `website/` to refresh the committed bundle used by frontend-only deployments. Run FastAPI on a separate container host with PostgreSQL so the existing Uvicorn process can finish background matching after it sends the response. The browser uses the Next.js `/api/*` rewrite on the frontend origin. Its session cookie does not need a shared domain with the API.

## Start a test API

Use an existing HTTPS host for FastAPI and PostgreSQL, or connect the repository to a new [Render Blueprint](https://render.com/docs/infrastructure-as-code) with **Blueprint Path** set to `marketplace/render.preview.yaml`. It uses the backend Dockerfile, attaches a separate test database, and checks `/ready`. Deploy the backend revision you plan to test before deploying the frontend.

The preview Blueprint enables simulated availability and demo matching. To test Claude matching, set `ANTHROPIC_API_KEY` in the API host's environment. To test device releases, set `MARKETPLACE_DEVICE_TOKEN` there and send events directly to the API host. Keep these values on the API service.

Render's free service can sleep when idle and the free database expires after 30 days. Use test accounts and listings. [Render free instance limits](https://render.com/docs/free)

```sh
curl --fail --silent --show-error https://YOUR_API_HOST/ready
```

## Configure the Vercel project

1. Create or link a Vercel project for this repository. In its project settings, set **Root Directory** to `marketplace/frontend`, select the **Next.js** preset, and use Node.js 22 or newer. The repository configuration pins pnpm for reproducible installs. [Vercel monorepos](https://vercel.com/docs/monorepos)
2. Add `MARKETPLACE_API_URL` to the project's **Preview** environment with the API's HTTPS origin. The build uses the value for its API rewrite. Redeploy after changing it. [Vercel environment variables](https://vercel.com/docs/environment-variables)
3. Keep Vercel Authentication enabled for previews. Deploy from a non-production Git branch or install the Vercel CLI and link the Git-connected project from the repository root. The Vercel Git integration deploys pushes to `main` to Production. [Vercel deployment protection](https://vercel.com/docs/deployment-protection)

```sh
vercel login
vercel link --repo
vercel deploy
```

Use the same Vercel project for subsequent previews. Open its preview URL and verify the listings load. Register a test host, publish a room and release an opening. Register a renter in another session, request that room and confirm the booking. The authenticated `GET /api/auth/me` should return the signed-in user and `GET /api/ready` should report database readiness. For protected previews, use `vercel curl /api/ready --deployment <preview-url>` or test from the authenticated browser. [Deploy from the Vercel CLI](https://vercel.com/docs/projects/deploy-from-cli)

For a private Daytona test API, set `MARKETPLACE_API_MODE=private-proxy` in Preview and add its signed HTTPS origin as the **Sensitive** Preview variable `MARKETPLACE_PRIVATE_API_URL`. The Next.js server forwards marketplace requests without exposing the signed origin to the browser. Redeploy after changing the origin or when the signed URL expires. [Daytona signed preview URLs](https://www.daytona.io/docs/en/preview/#signed-preview-url)

## Persistent Daytona demo

Keep the sandbox private and run Next.js on port 3000, Uvicorn on loopback port 8000, and PostgreSQL on its Unix socket. In Daytona v0, a TTL of zero disables scheduled destruction, an auto-stop interval of zero disables inactivity stops, and an auto-delete interval of minus one preserves the sandbox when stopped. Container archives preserve its filesystem. Check the organization's credit runway before leaving the sandbox running. [Daytona persistence](https://www.daytona.io/docs/en/persistence/) · [Daytona billing](https://www.daytona.io/docs/en/billing/)

Once an operator installs and starts the poller, it checks public `main` every minute. It builds that exact revision and checks it against a temporary copy of the database before restarting the app. The public repository can be fetched without credentials. Install the scripts outside the checkout so a failing candidate cannot replace the release runner.

Run setup inside the Daytona sandbox as the same Linux user that owns the PostgreSQL database and the current app processes. Replace the example paths and database name as needed. Keep a mode-600 runtime environment file.

```sh
install -d -m 700 "$HOME/.local/share/standbyroom/bin" "$HOME/.config/standbyroom"
install -m 700 marketplace/deploy/daytona-*.sh "$HOME/.local/share/standbyroom/bin/"
(
  umask 077
  cat >"$HOME/.config/standbyroom/runtime.env" <<'ENV'
STANDBYROOM_INITIAL_RELEASE=/home/daytona/demo-8409dbc
DATABASE_URL='postgresql:///standbyroom_live_demo?host=/var/run/postgresql'
MARKETPLACE_DEMO_MODE=1
ENV
)
setsid nohup "$HOME/.local/share/standbyroom/bin/daytona-poll.sh" \
  >"$HOME/.local/share/standbyroom/poll.log" 2>&1 </dev/null &
```

The poller needs Git, curl, Python 3, Node.js with Corepack, uv, the PostgreSQL server and client tools, and the standard Linux process utilities. Start PostgreSQL before the poller. After a stop and start, restart PostgreSQL and the poller or configure these commands as supervised startup services on the host.

Each release installs locked dependencies, builds Next.js, and checks new migrations against a temporary copy of PostgreSQL. It then stops the previous app, takes a pre-migration backup, and checks the new backend and frontend. The active release serves `/api/ready` and `/.well-known/standbyroom-release.json` on port 3000. A failed cutover restarts the previous app and stops automatic attempts for that SHA. The next validated revision can deploy, or the operator can clear `~/.local/share/standbyroom/failed-release` after addressing the failure.

Keep migrations compatible with the previous release so process rollback can reuse the same database. Keep private `pg_dump` backups outside the sandbox and test restoring them. A Daytona FUSE-backed volume can store backup files. Keep PostgreSQL's live data directory on the sandbox filesystem. Daytona fixes ephemeral status at creation. A sandbox created with auto-delete zero is deleted when it stops even with no TTL. [Daytona volumes](https://www.daytona.io/docs/en/volumes/)

An operator can create a short-lived port-3000 link using `daytona preview-url`. A stable Vercel origin needs an approved HTTPS gateway scoped to the marketplace, with any gateway credential supplied by the Vercel server. Keep the Daytona management token and PostgreSQL off that path. [Daytona preview access](https://www.daytona.io/docs/en/preview/)

## Production

Use a dedicated API service and database with backups. Set the backend's `DATABASE_URL` and `MARKETPLACE_SECURE_COOKIES=1`. Leave demo mode off and configure `ANTHROPIC_API_KEY` for matching. Set the Vercel project's **Production** `MARKETPLACE_API_URL` to the production API origin. Verify the production API's `/ready` and run `vercel deploy --prod` from the linked repository root when the release is ready.

The public landing site links to `https://app.standbyroom.com`. The Vercel marketplace uses `https://api.standbyroom.com`, the API service on the team server. Vercel production builds reject `vercel.run` sandbox origins because those endpoints expire when the sandbox stops.
