"""Database engine, session factory, and pgvector extension bootstrap."""

from __future__ import annotations

import logging
import os

from dotenv import load_dotenv

load_dotenv()
from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.db.models import Base

logger = logging.getLogger(__name__)

# ── Connection URL ───────────────────────────────────────────────────────────
# Default points to a local Postgres with pgvector installed.
# Override via the DATABASE_URL environment variable.
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg2://postgres:postgres@localhost:5432/complaints",
)

engine = create_engine(
    DATABASE_URL,
    echo=bool(os.getenv("SQL_ECHO", "")),
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def init_db() -> None:
    """Enable the pgvector extension and create all tables (idempotent).

    Must be called once at application startup (or during migrations).
    """
    with engine.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        conn.commit()
        logger.info("pgvector extension ensured")

    Base.metadata.create_all(bind=engine)
    logger.info("All database tables created / verified")


@contextmanager
def get_db() -> Generator[Session, None, None]:
    """Yield a transactional DB session and handle cleanup."""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
