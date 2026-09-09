# SECE AI

A self-branded, ChatGPT-style agentic assistant built for **Sri Eshwar
College of Engineering (SECE)**: a chat UI, an authenticated backend, and
**eleven working specialist agents** behind a message router, in two groups
in the agent picker:

- **General** — Faculty & Student Assistant (RAG over your uploaded
  documents, and a full general-purpose assistant besides), Research Agent
  (web research), and Admin Agent (drafts circulars/notices grounded in
  policy documents).
- **Research Command Centre** — eight agents covering institutional
  research management: Research Super Agent, Funding Opportunity &
  Proposal Agent, Publication Intelligence Agent, Patent & Innovation
  Agent, Ph.D. Scholar Monitoring Agent, Research Ethics & Compliance
  Agent, Faculty Research Performance Agent, and Research Dashboard &
  Management Agent. See **Institutional Research Agentic AI** below for
  what these can and can't do yet.

All eleven are built on the same architecture: an LLM + prompt +
shared tools, meant to grow into more agents, distinct per-agent tools, and
eventually your own locally hosted models.

This is a working MVP scaffold, not a finished product — see
[Roadmap](#roadmap) for what's intentionally left as a next step.

## Architecture

```
                    Next.js chat UI  (frontend/)
                 login, chat, sidebar, agent picker,
                    file upload, streaming badges
                              │
                              ▼  REST + SSE
                    FastAPI backend  (backend/)
                 auth (JWT), conversations, documents (RAG ingest)
                              │
                              ▼
                    POST /chat/stream (routers/chat.py)
                              │
              conversation.agent == "auto"?
                    │                    │
                   yes                   no
                    ▼                    ▼
        agents/router.py         use the conversation's
        (LLM classifier)          pinned agent key
                    │                    │
                    └─────────┬──────────┘
                               ▼
                agents/registry.py: AGENT_REGISTRY
        ┌──────────────────────┼───────────────────────┐
        ▼                      ▼                        ▼
  Faculty & Student      Research Agent            Admin Agent
    Assistant           (web-search led)      (drafts circulars/notices,
 (RAG + web fallback)                          grounded in policy docs)
        │                      │                        │
        └──────────────────────┴────────────────────────┘
                               │
                 shared tools: search_documents (pgvector),
                        web_search (Tavily, optional)
                               │
                               ▼
                    Postgres + pgvector
       (users, conversations, messages, documents, document_chunks)
```

Each agent is a LangGraph `create_react_agent` with its own system prompt
(`agents/prompts.py`), built on demand by `agents/registry.py`. All eleven
currently share the same tool set (`search_documents` + optional
`web_search`) and are differentiated by prompt/behavior; see Roadmap for
giving agents distinct tool sets as they grow more specialized. Each
`AgentSpec` also has a `group` field, which only affects the UI (which
`<optgroup>` it's listed under in the picker) — routing behaves identically
regardless of group.

**Routing.** A `Conversation.agent` of `"auto"` means every message in that
conversation is classified by a cheap LLM call (`agents/router.py`) against
the `AGENT_REGISTRY` descriptions and dispatched accordingly - so one
conversation can bounce between agents turn to turn. Picking a specific
agent instead (via the UI dropdown on a new chat, or `agent` in the
`POST /conversations` / `POST /chat/stream` body) pins every message in that
conversation to it. Either way, the resolved agent is announced via an
`agent` SSE event before the first token and stored on the saved assistant
`Message`, so the UI can show which specialist actually answered - not just
which one was requested.

## Stack

| Layer | Technology |
|---|---|
| Chat UI | Next.js 14 (App Router) + React + Tailwind |
| Backend | FastAPI + SQLAlchemy |
| Agent engine | LangGraph (`create_react_agent`) + LangChain, multi-agent router |
| LLM | OpenAI API (`gpt-4o-mini` by default) |
| Embeddings | OpenAI `text-embedding-3-small` |
| Knowledge base / RAG | Postgres + pgvector |
| File storage | local disk volume (swap for MinIO/S3 later) |
| Web search tool | Tavily API (optional — omit the key to disable it) |
| Auth | JWT (email + password) |
| Deployment | Docker Compose |

## Running it locally

Prerequisites: Docker + Docker Compose, and an OpenAI API key.

```bash
cp .env.example .env
# edit .env: set OPENAI_API_KEY, and JWT_SECRET to a long random string.
# TAVILY_API_KEY is optional - leave blank to disable the web_search tool.

docker compose up --build
```

Then open:
- Frontend: http://localhost:3000
- Backend API docs (Swagger): http://localhost:8000/docs

First run: create an account from the "Create account" tab on the login
page. It won't be able to log in yet — new accounts need admin approval
(see **Roles, account approval & the Admin Panel** below) — and on a fresh
`docker compose` database there's no admin yet to approve it from the UI.
Bootstrap yourself as admin once with:
```bash
docker compose exec db psql -U sece -d sece_ai -c \
  "UPDATE users SET role = 'admin', is_approved = true WHERE email = 'you@example.com';"
```
(adjust `-U`/`-d` if you changed `POSTGRES_USER`/`POSTGRES_DB` in `.env`),
then log in normally. Every account after that can be approved and have
its role changed from the Admin Panel instead of touching SQL again.

Then, from the chat sidebar, upload a PDF/DOCX/TXT (a syllabus, circular,
policy document, etc.) under "Knowledge base", start a new chat, and either
leave the agent as **Auto** or pin one from the dropdown. Ask a document
question and the Faculty & Student Assistant will call `search_documents`
and cite the source filename; ask a research question ("what's the latest
work on...") and Auto should route it to the Research Agent instead; ask it
to draft a notice and it should route to the Admin Agent.

### Roles, account approval & the Admin Panel

There are three roles (`User.role`): `student`, `faculty`, `admin`. Every
self-registered account is `student` — there's no signup dropdown to pick a
different role (an earlier version of this app had one; it was removed
because it let anyone register themselves as "Admin" with no verification).

**New accounts need admin approval before they can sign in.** Registering
(`POST /auth/register`) creates the account but does **not** log you in or
return a usable session — the response is just a "pending approval"
message. An admin approves it from the **Admin Panel** (visible as a
sidebar button only when you're logged in as admin, or go to `/admin`
directly), after which that account can log in normally. This is enforced
in two places, not just the UI: `routers/auth.py::login` rejects an
unapproved account at sign-in with a 403 ("Your account is pending admin
approval"), and `auth.py::get_current_user` checks it again on *every*
request — so revoking someone's approval takes effect immediately, not just
at their next login. Admin accounts always bypass this check (see that
function's comment for why that's still safe: only direct database access
can grant the admin role in the first place).

**⚠️ This changes local dev too.** `docker compose up` gives you a totally
fresh database, so the *first* account you register there also starts
unapproved and can't log in - see "Running it locally" above, which now
includes the one-time `docker compose exec db psql ...` command to approve
it (there's no admin yet to click "Approve" for you the very first time).

The Admin Panel (`app/admin/page.tsx`, backed by `routers/admin.py`, all
routes 403 server-side for non-admins) covers everything requested for this
feature:
- **Approve or reject pending signups**, with each user's email/name and
  registration date.
- **See every user with basic activity**: role, conversation count, message
  count, and last-active timestamp (derived from their conversations'
  `updated_at` — there's no separate analytics/event-logging table, this is
  a live query over existing data, not a stored metric).
- **Change any user's role** directly from a dropdown (student/faculty/
  admin) — this replaces the old "you have to run SQL to promote someone"
  step for every promotion *after* the first. An admin can't change their
  own role from here (prevents accidentally locking yourself out — do that
  from a different admin account, or via SQL if you're down to one).
- **Delete a user** (cascades to their conversations, messages, and
  documents) — used for rejecting a pending signup or removing an account
  entirely.
- **See and delete every document in the knowledge base**, across every
  user, not just your own — including who uploaded it and whether it's
  shared or private. (Uploading a *new* shared document still happens from
  the regular chat sidebar's "Add to shared knowledge base" checkbox, which
  only shows for admin accounts — the Admin Panel is for oversight/cleanup
  of what's already there, not a second upload path.)

**Bootstrapping your very first admin account** still has to happen outside
the app (nobody can click "Approve" or set a role before an admin exists).
Connect to the database directly (locally: `psql` into your Docker Compose
`db` service; on Render: the **Connect** tab on your database → PSQL
Command) and run:
```sql
UPDATE users SET role = 'admin', is_approved = true WHERE email = 'someone@example.com';
```
Every promotion after that first one can go through the Admin Panel's role
dropdown instead.

`search_documents` labels each result "Official/shared source" or "User's
own upload" so the model can tell the difference and answer accordingly
(see `agents/prompts.py`) — e.g. trusting a shared attendance policy over
a random student's personal notes if the two ever disagree.

Faculty currently behaves the same as student beyond the role label itself
(register, get approved, chat, search shared + own documents) — it doesn't
yet get anything admin doesn't, beyond existing as a distinct value for
future use (e.g. giving faculty shared-upload rights too).

### Institutional Research Agentic AI (Research Command Centre)

Eight specialist agents (`agents/prompts.py`, `agents/registry.py`, all in
the `"Research Command Centre"` group) cover institutional research
management: **Research Super Agent** (front desk / strategic overview),
**Funding Opportunity & Proposal Agent**, **Publication Intelligence
Agent**, **Patent & Innovation Agent**, **Ph.D. Scholar Monitoring Agent**,
**Research Ethics & Compliance Agent**, **Faculty Research Performance
Agent**, and **Research Dashboard & Management Agent**.

**What this is right now (Phase 1):** eleven agents deep, zero database
tables deep. All eight share the exact same two tools every other agent
has — `search_documents` (the shared knowledge base + whoever's logged in
own uploads) and `web_search` — differentiated purely by system prompt.
That makes them genuinely useful for exactly what those tools can do:
finding current funding calls and checking journal indexing on the open
web, answering from an uploaded ethics policy or a scholar's uploaded
progress report, drafting a proposal or appraisal summary. It does **not**
mean there's a live grants tracker, a publications database, a patent
register, or real-time faculty performance metrics behind any of them —
each prompt says so explicitly rather than letting the model imply
visibility it doesn't have. The **Research Dashboard & Management Agent**
in particular is a document summarizer today, not a live analytics
dashboard.

**Phase 2 (not built):** real per-domain data models (a grants table, a
publications registry with actual citation data, a patent log, a Ph.D.
scholar roster with tracked milestones, faculty performance metrics) with
proper CRUD UI and an actual live dashboard, plus five more agents —
Collaboration, Commercialization, Consultancy, Research Equipment, and
Accreditation — extending the same registry pattern. Each domain here is
realistically its own scoped build (schema + endpoints + UI), not a single
follow-up task.

Naming: the umbrella app stays **SECE AI** (same login, same deployment) —
"Research Command Centre" is used as the agent-picker group label for this
set, so the two proposed platform names (*ResearchAI*, *CFRD AI Research
Command Centre*) are available later if these become a genuinely separate
product rather than a section of this one.

### Deploying to Render (cloud hosting)

This also runs on [Render](https://render.com) — a `render.yaml` Blueprint
in the project root deploys the database, backend, and frontend together.
See **RENDER_DEPLOY.md** for the full walkthrough, including two
Dockerfile/compose fixes that were necessary to make it work there
(dynamic `$PORT` binding, and passing `NEXT_PUBLIC_API_BASE_URL` as a Docker
build arg rather than a runtime env var, since Next.js bakes it into the
client bundle at build time).

### Running without Docker (dev loop)

Backend:
```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
# point DATABASE_URL at a Postgres instance with the pgvector extension available
uvicorn app.main:app --reload
```

Frontend:
```bash
cd frontend
npm install
npm run dev
```

## Project layout

```
sece-ai/
├── docker-compose.yml
├── .env.example
├── backend/
│   ├── requirements.txt
│   ├── Dockerfile
│   └── app/
│       ├── main.py            # FastAPI app, CORS, router wiring, startup DB init
│       ├── config.py          # Settings (env-driven)
│       ├── database.py        # SQLAlchemy engine/session, init_db()
│       ├── models.py          # User, Conversation, Message, Document, DocumentChunk
│       ├── schemas.py         # Pydantic request/response models
│       ├── auth.py            # password hashing, JWT, get_current_user
│       ├── routers/
│       │   ├── auth.py            # /auth/register, /auth/login, /auth/me
│       │   ├── conversations.py   # CRUD for chat threads
│       │   ├── documents.py       # upload/list/delete institutional docs
│       │   ├── agents.py          # GET /agents - lists the picker options
│       │   └── chat.py            # POST /chat/stream (routes + streams via SSE)
│       ├── agents/
│       │   ├── prompts.py     # one system prompt per specialist agent
│       │   ├── tools.py       # search_documents + web_search tool factory
│       │   ├── registry.py    # AGENT_REGISTRY + build_agent(key, db, user_id)
│       │   └── router.py      # classify_agent(message) for "auto" conversations
│       └── rag/
│           ├── parsing.py     # PDF/DOCX/TXT -> text
│           ├── chunking.py    # text -> overlapping chunks
│           ├── embeddings.py  # OpenAI embeddings client
│           ├── ingest.py      # parse -> chunk -> embed -> persist
│           └── retriever.py   # pgvector cosine-distance similarity search
└── frontend/
    ├── package.json, tsconfig.json, tailwind.config.js, next.config.js
    ├── Dockerfile
    ├── lib/api.ts             # typed API client incl. SSE stream parser
    ├── components/
    │   ├── Sidebar.tsx, FileUpload.tsx, ChatWindow.tsx, MessageBubble.tsx
    └── app/
        ├── login/page.tsx     # sign in / create account
        └── chat/page.tsx      # main ChatGPT-style interface + agent state
```

## Roadmap

This scaffold deliberately gets a few agents working end-to-end behind a
real router rather than stubbing out many more. Natural next steps, in
rough priority order:

1. **Per-agent tool sets.** All three agents currently share
   `build_tools()`. As they diverge (e.g. Admin Agent drafting into a real
   templating system, Research Agent hitting a scholarly API instead of
   general web search), give `AgentSpec` its own tool list instead of a
   single shared one.
2. **More role-based permissions.** `User.role` now gates admin-only shared
   document uploads, and there's a full Admin Panel for approving accounts,
   changing roles, and managing the knowledge base (see **Roles, account
   approval & the Admin Panel** above) - only the very first admin account
   still needs a one-off SQL command. Natural next steps: giving faculty
   upload rights too, role checks on other routes (e.g. who can use the
   Admin Agent), and turning "delete a user" into a softer suspend/reactivate
   instead of an irreversible cascade delete.
3. **Background ingestion.** Document ingestion currently runs synchronously
   inside the upload request. Move it to a task queue (Celery/RQ/Arq) once
   uploads are large or frequent, so the request returns immediately with
   `status: processing` and the UI polls or gets a websocket push.
4. **Object storage.** Swap the local `/data/uploads` volume for MinIO/S3 so
   file storage scales past a single host.
5. **Real migrations.** `init_db()` uses `Base.metadata.create_all`, fine for
   an MVP. Move to Alembic once the schema needs versioned migrations.
6. **Local/private LLM option.** Agents are built against OpenAI's API via
   `langchain-openai`. Because `ChatOpenAI` accepts a custom `base_url`, you
   can point it at a self-hosted **vLLM** OpenAI-compatible endpoint serving
   Llama/Qwen/Mistral with no code changes — add `OPENAI_BASE_URL` to
   `config.py`/`.env` and pass it through in `agents/registry.py`. This lets
   you route some requests to a private model and others to OpenAI, per the
   hybrid architecture in the original design notes.
7. **Auth hardening.** Add refresh tokens, rate limiting, and (for an
   institutional deployment) SSO via Keycloak/Auth0/SAML instead of
   email+password only.
8. **Conversation titles.** Titles are currently just the first ~60
   characters of the user's first message. A cheap follow-up is a short LLM
   call to generate a real title once a conversation has a few turns.
9. **Tests.** No automated tests yet — start with the `rag/chunking.py` and
   `rag/retriever.py` modules (pure functions / DB-only, easy to unit test)
   and a couple of FastAPI `TestClient` integration tests for
   register → login → upload → chat, plus `agents/router.py`'s fallback
   behavior on a bad/slow classification call.

## Notes

- The `search_documents` tool is scoped to the *current user's* documents
  (`Document.owner_id == user_id`). There's no shared/institution-wide
  knowledge base yet — see Roadmap item 2.
- `web_search` is only registered as a tool when `TAVILY_API_KEY` is set, so
  every agent gracefully has just `search_documents` if you don't want the
  web-search dependency yet.
- `agents/router.py`'s `classify_agent` always returns a valid agent key,
  even if the classification call itself fails (network issue, bad key) - it
  falls back to `faculty_student_assistant` rather than ever raising and
  breaking the chat request.
- Chat streams over Server-Sent Events (a plain `POST` + `ReadableStream`
  reader on the frontend, not the browser's `EventSource` API, since that
  only supports `GET`). See `lib/api.ts`'s `streamChat`.
- **A bug worth knowing about if you extend `routers/chat.py`:** LangGraph's
  `stream_mode="messages"` yields *every* message that passes through the
  graph - including the input `HumanMessage` itself and any `ToolMessage`
  results - not just the model's own output tokens. The streaming loop
  filters to `isinstance(message_chunk, AIMessageChunk)` for exactly this
  reason; removing that check silently echoes the user's own message (and
  raw tool output) back as if the assistant had said it.
