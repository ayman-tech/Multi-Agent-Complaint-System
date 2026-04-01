"""Embedding model factory — choose between FREE local models and paid OpenAI.

Cost comparison (embedding 50 000 complaint docs, ~400 tokens each):
──────────────────────────────────────────────────────────────────────
  Model                         Dim    Cost      Speed       Quality
  ─────────────────────────────────────────────────────────────────
  all-MiniLM-L6-v2 (local)     384    $0.00     ~fast       Good
  BAAI/bge-small-en-v1.5        384    $0.00     ~fast       Better
  BAAI/bge-base-en-v1.5         768    $0.00     ~moderate   Very good
  text-embedding-3-small (OAI) 1536    ~$0.40    ~API-bound  Very good
  text-embedding-3-large (OAI) 3072    ~$2.60    ~API-bound  Best

Default: ``BAAI/bge-small-en-v1.5`` — **free**, runs locally on CPU,
produces 384‑dim vectors with strong retrieval quality.

Override via the ``EMBEDDING_PROVIDER`` env var:
    EMBEDDING_PROVIDER=openai     → OpenAI text‑embedding‑3‑small (paid)
    EMBEDDING_PROVIDER=huggingface → local HuggingFace model      (free) ← default
"""

from __future__ import annotations

import logging
import os

from langchain_core.embeddings import Embeddings

logger = logging.getLogger(__name__)

# ── Configuration via environment variables ──────────────────────────────────

EMBEDDING_PROVIDER = os.getenv("EMBEDDING_PROVIDER", "huggingface").lower()

# HuggingFace (local, free) settings
HF_MODEL_NAME = os.getenv("HF_EMBEDDING_MODEL", "BAAI/bge-small-en-v1.5")
HF_DEVICE = os.getenv("HF_DEVICE", "cpu")  # "cpu", "cuda", "mps"

# OpenAI (paid) settings
OPENAI_MODEL_NAME = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")

# ── Dimension lookup ─────────────────────────────────────────────────────────
# Must match the Vector(dim) in the DB models. Add new models here as needed.
_MODEL_DIMENSIONS: dict[str, int] = {
    # HuggingFace (local, free)
    "BAAI/bge-small-en-v1.5": 384,
    "BAAI/bge-base-en-v1.5": 768,
    "sentence-transformers/all-MiniLM-L6-v2": 384,
    "sentence-transformers/all-mpnet-base-v2": 768,
    # OpenAI (paid)
    "text-embedding-3-small": 1536,
    "text-embedding-3-large": 3072,
    "text-embedding-ada-002": 1536,
}


def get_embedding_dim() -> int:
    """Return the vector dimension for the configured embedding model."""
    if EMBEDDING_PROVIDER == "openai":
        model = OPENAI_MODEL_NAME
    else:
        model = HF_MODEL_NAME

    dim = _MODEL_DIMENSIONS.get(model)
    if dim is None:
        logger.warning(
            "Unknown embedding model '%s' — defaulting to 384 dims. "
            "Add it to _MODEL_DIMENSIONS if this is wrong.",
            model,
        )
        return 384
    return dim


def get_embeddings() -> Embeddings:
    """Create and return the configured embedding model instance.

    Returns a LangChain ``Embeddings`` object that exposes
    ``.embed_documents()`` and ``.embed_query()``.
    """
    if EMBEDDING_PROVIDER == "openai":
        from langchain_openai import OpenAIEmbeddings

        logger.info("Using OpenAI embeddings: %s (PAID — $0.02/1M tokens)", OPENAI_MODEL_NAME)
        return OpenAIEmbeddings(model=OPENAI_MODEL_NAME)

    else:
        from langchain_huggingface import HuggingFaceEmbeddings

        logger.info(
            "Using local HuggingFace embeddings: %s on %s (FREE)",
            HF_MODEL_NAME,
            HF_DEVICE,
        )
        return HuggingFaceEmbeddings(
            model_name=HF_MODEL_NAME,
            model_kwargs={"device": HF_DEVICE},
            encode_kwargs={"normalize_embeddings": True},  # important for cosine similarity
        )
