# SECE AI

A self-branded, ChatGPT-style agentic assistant built for **Sri Eshwar
College of Engineering (SECE)**: a chat UI, an authenticated backend, and
**three working specialist agents** behind a message router — Faculty &
Student Assistant (RAG over your uploaded documents), Research Agent (web
research), and Admin Agent (drafts circulars/notices grounded in policy
documents) — plus an architecture meant to grow into more agents, tools, and
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
(`agents/prompts.py`), built on demand by `agents/registry.py`. All three
currently share the same tool set (`search_documents` + optional
`web_search`) and are differentiated by prompt/behavior; see Roadmap for
giving agents distinct tool sets as they grow more specialized.

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
page (there's no separate seed/admin script yet — the first registered user
is a normal user like any other; see Roadmap for role-based access).

Then, from the chat sidebar, upload a PDF/DOCX/TXT (a syllabus, circular,
policy document, etc.) under "Knowledge base", start a new chat, and either
leave the agent as **Auto** or pin one from the dropdown. Ask a document
question and the Faculty & Student Assistant will call `search_documents`
and cite the source filename; ask a research question ("what's the latest
work on...") and Auto should route it to the Research Agent instead; ask it
to draft a notice and it should route to the Admin Agent.

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
2. **Roles & permissions.** `User.role` (student/faculty/admin) exists but
   isn't enforced yet. Add per-route role checks (e.g. only faculty/admin
   can upload institution-wide documents vs. personal ones, or use the Admin
   Agent), and a shared vs. private document distinction.
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
