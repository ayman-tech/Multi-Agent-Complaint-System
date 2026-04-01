"""Centralised logging and observability configuration."""

from __future__ import annotations

import logging
import os
import sys
from datetime import datetime, timezone


class JSONFormatter(logging.Formatter):
    """Emit structured JSON log lines for easy ingestion by log aggregators."""

    def format(self, record: logging.LogRecord) -> str:
        import json

        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        if record.exc_info and record.exc_info[1]:
            log_entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_entry)


def setup_logging(level: str | None = None) -> None:
    """Configure root logger with structured JSON output.

    Parameters
    ──────────
    level : str, optional
        Logging level name (DEBUG, INFO, WARNING, …).
        Defaults to the ``LOG_LEVEL`` env var or ``INFO``.
    """
    log_level = (level or os.getenv("LOG_LEVEL", "INFO")).upper()

    root = logging.getLogger()
    root.setLevel(log_level)

    # Clear existing handlers to avoid duplicates on re‑init
    root.handlers.clear()

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JSONFormatter())
    root.addHandler(handler)

    # Silence noisy third‑party loggers
    for noisy in ("httpcore", "httpx", "openai", "urllib3"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    logging.info("Logging initialised at level %s", log_level)
