# Deploying SECE AI to Render

Yes — this runs fine on [Render](https://render.com). The three pieces map
directly onto three Render resources:

| Local (docker-compose) | Render |
|---|---|
| `db` (Postgres + pgvector) | a Render **Postgres** database (pgvector is supported natively — see [Render's docs](https://render.com/docs/postgresql-extensions)) |
| `backend` (FastAPI, Dockerfile) | a Render **Web Service**, Docker runtime |
| `frontend` (Next.js, Dockerfile) | a Render **Web Service**, Docker runtime |

A `render.yaml` **Blueprint** file is included in the project root — it
describes all three resources so Render can create them together in one
step, instead of you clicking through three separate "New +" flows.

Two small Dockerfile changes were needed to make this actually work on
Render (already applied in this project, explained here so you know why):

1. **Dynamic port binding.** Render assigns each web service its own
   `$PORT` (commonly `10000`) and requires the app to bind to it — a
   hardcoded port fails. `backend/Dockerfile`'s CMD now reads
   `${PORT:-8000}` (falls back to 8000 for local `docker compose`, which
   doesn't set `PORT`). The frontend didn't need a change: `next start`
   already respects `$PORT` automatically.
2. **Build-time API URL.** Next.js bakes `NEXT_PUBLIC_*` variables into the
   client JS bundle *at build time*, not at container startup. Render does
   pass a Docker service's env vars through as build args automatically,
   but the Dockerfile still has to declare `ARG NEXT_PUBLIC_API_BASE_URL` to
   actually consume it — that's now in `frontend/Dockerfile`.

---

## Steps

### 1. Push this project to a GitHub repo

Render deploys from a Git repo, not a local zip.

```bash
cd sece-ai
git init
git add .
git commit -m "Initial commit"
```

Create an empty repo on GitHub (github.com/new, don't initialize it with a
README), then:

```bash
git remote add origin https://github.com/<your-username>/<repo-name>.git
git branch -M main
git push -u origin main
```

**Double-check `.env` is NOT in that commit** — `.gitignore` already
excludes it, but confirm with `git status` before pushing. Your real
`OPENAI_API_KEY` should never end up in a GitHub repo, public or private.

### 2. Create a Render account and deploy the Blueprint

1. Go to **[render.com](https://render.com)** and sign up (GitHub login is
   the easiest — it also handles repo access in one step).
2. Click **New +** → **Blueprint**.
3. Connect the GitHub repo you just pushed.
4. Render detects `render.yaml` automatically and shows you the three
   resources it's about to create (`sece-ai-db`, `sece-ai-backend`,
   `sece-ai-frontend`).
5. You'll be prompted for the values marked `sync: false` in the blueprint:
   - **OPENAI_API_KEY** — your real key (see the earlier guide for how to
     get one)
   - **TAVILY_API_KEY** — optional, leave blank to skip the web-search tool
6. Click **Apply**. Render creates the database first, then builds and
   deploys both web services. First build takes several minutes — watch the
   logs for each service in the Render dashboard.

### 3. Confirm the pgvector extension is enabled

The backend already tries to enable this itself on startup
(`CREATE EXTENSION IF NOT EXISTS vector`), and Render's databases normally
allow this without extra privileges — so this usually just works with no
action from you.

**If the backend logs show a permission error** related to `CREATE
EXTENSION`, enable it manually instead:
1. Open the `sece-ai-db` database in the Render dashboard.
2. On its **Info** page, copy the **PSQL Command**.
3. Run it in your terminal (opens a `psql` session to your Render database).
4. Run: `CREATE EXTENSION vector;`
5. Type `\q` to exit, then restart the backend service from the Render
   dashboard.

### 4. Verify the two service URLs

`render.yaml` guesses each service's URL as `https://<name>.onrender.com`
(e.g. `https://sece-ai-backend.onrender.com`) to wire the frontend and
backend together. This is right **as long as those exact names weren't
already taken** by someone else on Render.

After both services finish deploying, open each one in the Render dashboard
and check the URL shown at the top against what's in `render.yaml`
(`CORS_ORIGINS` on the backend, `NEXT_PUBLIC_API_BASE_URL` on the frontend).

**If they match:** nothing to do.

**If they don't match** (Render appended something to a taken name):
1. Go to the backend service → **Environment** → update `CORS_ORIGINS` to
   the frontend's actual URL → save (this triggers a redeploy automatically).
2. Go to the frontend service → **Environment** → update
   `NEXT_PUBLIC_API_BASE_URL` to the backend's actual URL → save.
3. **Manually redeploy the frontend** (Manual Deploy → Deploy latest commit)
   — updating the env var alone isn't enough, since the value has to be
   re-baked into the JS bundle at build time (see the note above).

### 5. Use it

Open the frontend's URL in a browser — same app, same steps as local:
create an account, upload a document, chat.

---

## Things to know about Render's free tier

- **Free web services spin down after 15 minutes of inactivity.** The next
  request after idle takes 30-60 seconds to "wake up" the container. Fine
  for testing/demoing, not for something people need to load instantly.
- **Free Postgres databases expire after 30 days** and are then deleted.
  For anything beyond a trial, upgrade the database to a paid plan before
  that window closes, or you'll lose all accounts/conversations/documents.
- **Uploaded file copies on local disk are ephemeral on the free plan** (no
  persistent disk without a paid add-on) — a redeploy or restart wipes
  `/data/uploads`. This doesn't break RAG/chat, though: the actual searchable
  data (the embedded chunks) lives in Postgres, which does persist. Only the
  redundant raw-file backup copy on disk is at risk. See the README roadmap
  item about moving file storage to S3/MinIO if this matters for you.
- Both web services and the database can be upgraded to paid plans
  individually from their Settings page whenever you're ready for
  always-on hosting.
