"""Knowledge lookup tool — semantic search over BPHS + nakshatra reference corpus."""
from __future__ import annotations

import json
import pathlib
from functools import lru_cache

import numpy as np
from langchain_core.tools import tool

_CORPUS_PATH = pathlib.Path(__file__).parent.parent / "knowledge" / "corpus.json"


@lru_cache(maxsize=1)
def _load_index() -> tuple[list[str], np.ndarray, object]:
    """Load corpus, embed with sentence-transformers, cache for process lifetime."""
    from agent.embedder import get_embedder

    entries = json.loads(_CORPUS_PATH.read_text(encoding="utf-8"))
    texts = [e["text"] for e in entries]
    model = get_embedder()  # shared instance (also used by semantic_guard) → model loads once
    embeddings = model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
    return texts, embeddings, model


@tool
def knowledge_lookup(query: str, k: int = 3) -> list[str]:
    """Retrieve relevant passages from BPHS and Vedic astrology reference notes.

    Uses sentence-transformers semantic search over graha, rashi, bhava, and nakshatra content.
    Call this before interpreting any planetary placement, house, or sign.
    """
    try:
        texts, embeddings, model = _load_index()
        q_emb = model.encode([query], normalize_embeddings=True)[0]
        scores: np.ndarray = embeddings @ q_emb
        top_k = min(k, len(texts))
        indices = np.argsort(scores)[::-1][:top_k]
        return [texts[int(i)] for i in indices]
    except FileNotFoundError:
        return [f"Knowledge base unavailable: corpus file not found at {_CORPUS_PATH}."]
    except (json.JSONDecodeError, KeyError) as exc:
        return [f"Knowledge base unavailable: corpus file is malformed ({exc})."]
    except Exception as exc:
        # Most often the embedding model couldn't be loaded/downloaded.
        return [f"Knowledge base unavailable: could not load the search model ({exc})."]
