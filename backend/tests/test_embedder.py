"""Shared embedder tests — the model must load ONCE per process.

Both tools/knowledge.py (RAG) and semantic_guard.py route through agent.embedder.get_embedder, so
they share one cached SentenceTransformer instead of each loading their own. These tests DO load the
embedding model (slower than the keyword-only suite).
"""
from agent.embedder import get_embedder
from agent import semantic_guard
from agent.tools import knowledge


def test_get_embedder_is_singleton():
    assert get_embedder() is get_embedder()


def test_knowledge_and_semantic_share_one_embedder():
    """The whole point of agent.embedder: one model instance across both consumers."""
    knowledge_model = knowledge._load_index()[2]
    semantic_model = semantic_guard._model()
    assert knowledge_model is semantic_model is get_embedder()
