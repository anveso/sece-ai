"""
SQLAlchemy engine/session setup, plus the FastAPI dependency used by routers
to get a request-scoped DB session.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from .config import settings

# connect_timeout is the important part here: without it, a bad/unreachable
# DATABASE_URL (wrong host, DB not ready yet, network issue) makes psycopg2
# hang on the TCP connect with NO error for minutes - which on Render looks
# like "the app never opens its port" with no useful log at all, since the
# startup event (init_db(), below) never returns. 10s means a real
# connection problem now fails fast with an actual traceback in the logs
# instead of a silent hang.
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    connect_args={"connect_timeout": 10},
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """
    Create tables and the pgvector extension if they don't exist yet.

    This is an MVP convenience (no Alembic migration history). Once the
    schema stabilizes, replace this with real Alembic migrations - see the
    README roadmap.
    """
    from sqlalchemy import text

    # Import models so they're registered on Base.metadata before create_all.
    from . import models  # noqa: F401

    # Plain print(), not logging - guaranteed to show up in Render's log
    # stream with no extra config, and this is exactly the sequence you want
    # visible if startup ever hangs or fails again: which of these three
    # steps it got stuck/failed on.
    print("init_db: connecting to database...", flush=True)
    with engine.connect() as conn:
        print("init_db: connected. Ensuring pgvector extension...", flush=True)
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        conn.commit()

    print("init_db: creating tables...", flush=True)
    Base.metadata.create_all(bind=engine)

    # create_all only creates missing TABLES, not missing COLUMNS on tables
    # that already exist (e.g. on a database that was already deployed
    # before this column was added). Postgres supports IF NOT EXISTS on
    # ADD COLUMN directly, so this is safe to run every startup - a real
    # migration tool (Alembic) should replace this once the schema needs
    # more than a couple of these. See README roadmap.
    with engine.connect() as conn:
        conn.execute(
            text(
                "ALTER TABLE documents "
                "ADD COLUMN IF NOT EXISTS is_shared BOOLEAN NOT NULL DEFAULT FALSE"
            )
        )
        conn.commit()

    # Same pattern for users.is_approved, but with a deliberate two-step
    # backfill: add it with DEFAULT TRUE first so every account that already
    # existed on a deployed database (including whoever's already using this
    # app) is grandfathered in as approved - nobody gets locked out by this
    # change. Then flip the column's default to FALSE so every *new* row
    # from here on requires explicit admin approval (routers/auth.py's
    # register() also sets this explicitly either way, via the ORM - this
    # second step just makes the DB-level default match for any direct-SQL
    # insert too).
    with engine.connect() as conn:
        conn.execute(
            text(
                "ALTER TABLE users "
                "ADD COLUMN IF NOT EXISTS is_approved BOOLEAN NOT NULL DEFAULT TRUE"
            )
        )
        conn.execute(text("ALTER TABLE users ALTER COLUMN is_approved SET DEFAULT FALSE"))
        conn.commit()
    print("init_db: done.", flush=True)
