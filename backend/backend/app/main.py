"""FastAPI application entrypoint: CORS, routers, startup DB init."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .database import init_db
from .routers import agents, auth, chat, conversations, documents

app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(conversations.router)
app.include_router(documents.router)
app.include_router(chat.router)
app.include_router(agents.router)


@app.on_event("startup")
def on_startup():
    # init_db() prints its own progress (see database.py) so a hang or
    # failure here shows up clearly in the deploy logs instead of the app
    # just silently never finishing startup (what "no open ports detected"
    # on Render actually means: the ASGI startup event never returned).
    try:
        init_db()
    except Exception:
        print("init_db FAILED during startup:", flush=True)
        raise


@app.get("/health")
def health():
    return {"status": "ok", "app": settings.app_name}
