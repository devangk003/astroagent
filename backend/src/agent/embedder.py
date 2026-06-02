"""Shared sentence-transformers embedder — one process-wide cached instance.

Both tools/knowledge.py (RAG) and semantic_guard.py (the semantic rail fallback) need the same
all-MiniLM-L6-v2 model. Routing them through this single cached loader means the model loads ONCE
per process instead of once per module, and the local HF cache is preferred so there is no runtime
Hub download (and no HF_TOKEN warning) on the common path.
"""
from __future__ import annotations

from functools import lru_cache

_MODEL_NAME = "all-MiniLM-L6-v2"


@lru_cache(maxsize=1)
def get_embedder():
    """Return the shared, process-cached SentenceTransformer (loaded on first use)."""
    from sentence_transformers import SentenceTransformer

    # Prefer the local HF cache: local_files_only skips the Hub metadata request, so there is no
    # "set a HF_TOKEN" warning and a faster cold start. (Set per-call on the constructor — env vars
    # like HF_HUB_OFFLINE are read at huggingface import time, too late to set here.) Fall back to a
    # one-time online download if the model isn't cached yet (fresh install).
    try:
        return SentenceTransformer(_MODEL_NAME, local_files_only=True)
    except Exception:
        return SentenceTransformer(_MODEL_NAME)
