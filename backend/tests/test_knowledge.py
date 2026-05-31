"""Phase 4 — knowledge_lookup: semantic retrieval from BPHS corpus."""
import pytest

st = pytest.importorskip("sentence_transformers", reason="pip install 'astroagent[rag]' needed")


def test_returns_list_of_strings():
    from agent.tools.knowledge import knowledge_lookup
    result = knowledge_lookup.invoke({"query": "Saturn karma discipline", "k": 3})
    assert isinstance(result, list)
    assert all(isinstance(r, str) for r in result)


def test_k_limits_results():
    from agent.tools.knowledge import knowledge_lookup
    assert len(knowledge_lookup.invoke({"query": "moon sign", "k": 2})) <= 2
    assert len(knowledge_lookup.invoke({"query": "moon sign", "k": 1})) <= 1


def test_graha_query_relevant():
    from agent.tools.knowledge import knowledge_lookup
    # BPHS Ch.3 describes the Sun physically — "honey-coloured eyes, square body, bilious"
    results = knowledge_lookup.invoke({"query": "Sun planet description complexion bilious royal", "k": 3})
    joined = " ".join(results).lower()
    assert "sun" in joined or "bilious" in joined or "planet" in joined


def test_bhava_query_relevant():
    from agent.tools.knowledge import knowledge_lookup
    results = knowledge_lookup.invoke({"query": "seventh house marriage partnership spouse", "k": 3})
    joined = " ".join(results).lower()
    assert "7th" in joined or "seventh" in joined or "partner" in joined or "spouse" in joined or "kalatra" in joined


def test_not_stub():
    from agent.tools.knowledge import knowledge_lookup
    result = knowledge_lookup.invoke({"query": "nakshatra meaning", "k": 1})
    assert "not yet implemented" not in result[0].lower()
