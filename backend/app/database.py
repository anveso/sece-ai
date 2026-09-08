"""
SQLAlchemy engine/session setup, plus the FastAPI dependency used by routers
to get a request-scoped DB session.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from .config import settings

engine = create_engine(settings.database_url, pool_pre_ping=True)
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

    with engine.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        conn.commit()

    Base.metadata.create_all(bind=engine)
