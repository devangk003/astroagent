"""Pytest config: keep the unit suite keyword-only + hermetic.

The semantic guard layer loads a sentence-transformers model and embeds text. We disable it by
default for the unit suite so tests stay fast and deterministic (graph tests then exercise the
keyword fast-path only). Dedicated semantic tests (test_semantic_guard.py) re-enable it explicitly
via monkeypatch.setenv. The eval harness runs with it enabled (env unset → default on).
"""
import os

os.environ.setdefault("ASTRO_SEMANTIC_GUARD", "0")
