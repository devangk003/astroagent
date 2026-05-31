# AstroAgent — Functional & Non-Functional Requirements Checklist

> Derived from the assignment brief (`astroagent-markdown.md`) and the PRD (`docs/astroagent-prd.md`).
> This is the **contract to check the build against**. Status reflects an audit of the current code
> on 2026-05-29. Legend: ✅ met · ⚠️ partial / fragile · ❌ broken or missing · 🔍 needs runtime verification.
>
> Source tags: `[A]` = assignment brief, `[P]` = PRD. Rubric weights from brief §06 in parentheses.

---

## 1. Functional Requirements (what the app must DO)

### FR-A · Agent core & graph (rubric: Agent architecture 25%)
| ID | Requirement | Source | Status |
|----|-------------|--------|--------|
| FR-A1 | Stateful LangGraph graph with a reasoning node, a tool node, and conditional routing | A, P§10 | ✅ |
| FR-A2 | ReAct-style tool loop: reason → call tool → observe → repeat until no tool call | A, P§10 | ✅ |
| FR-A3 | Router node classifies intent (chart / daily-transit / free-form) and selects prompt slant | A, P§10 | ⚠️ router only does crisis/injection short-circuit; no intent-based prompt slant |
| FR-A4 | Shared state schema: `messages` + `birth_details` + cached `chart` | P§10 | ❌ `chart` key missing from `state.py`; chart is never cached in state |
| FR-A5 | Tool-call validation + retry on malformed/error tool calls | A, P§10 | ⚠️ retry is a soft system-prompt nudge only; no arg validation/repair before execution |
| FR-A6 | Step / tool-call budget enforced (no runaway loops) | A (EV02) | ❌ no max-step / recursion cap configured on the graph |

### FR-B · Tools (rubric: Tools & correctness 20%)
| ID | Requirement | Source | Status |
|----|-------------|--------|--------|
| FR-B1 | `compute_birth_chart` uses a REAL ephemeris (Kerykeion/Lahiri sidereal, whole-sign) — never invented | A, P§11/13 | ✅ |
| FR-B2 | Chart math accurate within ~1° vs a reference chart | A, P§13 | 🔍 no reference-tolerance assertion proven to pass |
| FR-B3 | `geocode_place` resolves place → {lat, lng, tz} | A, P§11 | ✅ |
| FR-B4 | `get_daily_transits` returns today's transits related to natal moon/lagna | A, P§11 | ⚠️ requires the LLM to re-pass full natal dict as a tool arg (fragile on open models) |
| FR-B5 | `knowledge_lookup` RAG over a curated corpus (≥3 of 4 tools required) | A, P§11 | ✅ (cut-first per PRD) |
| FR-B6 | All tools handle bad input gracefully (return `{error}`, never crash) | A, P§11 | ✅ for tools; ⚠️ `make_model` raises (uncaught) on missing key |
| FR-B7 | Unknown birth time → return rashi + nakshatra, omit lagna/houses, explain limitation | P§13 | ✅ chart omits lagna/houses (SVG rendering removed — see FR-C7) |

### FR-C · Frontend / companion (rubric: Frontend craft 20%)
| ID | Requirement | Source | Status |
|----|-------------|--------|--------|
| FR-C1 | React chat interface, responsive, calm tone | A | ✅ |
| FR-C2 | Birth-details form with validation (date/time/place) | A, P | ⚠️ year capped at 2025 (now 2026); no Feb-30-type client validation |
| FR-C3 | "Unknown birth time" toggle | P | ✅ |
| FR-C4 | Responses stream token-by-token | A | ⚠️ streaming enabled for Ollama path only; not set on OpenRouter client |
| FR-C5 | Visible tool-call activity as it happens | A | ✅ |
| FR-C6 | Error and loading states | A | ✅ |
| FR-C7 | Visual birth-chart / transit chart rendering | P (implied) | ❌ **cut** — `render_chart_svg` tool + frontend chart card + `/api/chart` route removed for latency (see DECISIONS.md 2026-05-30 02:00); chart delivered as text only |
| FR-C8 | Model/provider selector (BYOK) | P§12 | ✅ UI present |
| FR-C9 | Conversation persistence — returning user keeps history | A (Day 5) | ⚠️ relies on `langgraph dev` in-mem store; lost on restart |

### FR-D · Guardrails & safety (rubric: Product judgment 5%; "never cut")
| ID | Requirement | Source | Status |
|----|-------------|--------|--------|
| FR-D1 | Certainty reframing — no medical/legal/financial fact, reframe to reflection | A, P§6/14 | ✅ keyword + system prompt |
| FR-D2 | Crisis → care + helplines, never a reading (fires before any tool) | A, P§6/14 | ✅ (⚠️ keyword false-positive risk) |
| FR-D3 | Anti-fatalism — tendencies, not doom | A, P§14 | ✅ system prompt |
| FR-D4 | Birth-data validation — impossible date / unknown time handled gracefully | A (EV05), P§14 | ✅ backend validates date/coords/tz |
| FR-D5 | Prompt-injection resistance — system prompt wins | A, P§14 | ✅ (⚠️ keyword false-positive risk on "act as", "your system") |
| FR-D6 | Privacy — no key/data leakage; minimal birth-data handling | P§12/14 | ❌ live API key committed in `.env` + hardcoded in `eval/run_eval.py` |

### FR-E · Evaluation harness (rubric: Evaluation rigor 20% — weighted heavily)
| ID | Requirement | Source | Status |
|----|-------------|--------|--------|
| FR-E1 | Versioned golden set, 20–30 cases, JSONL, valid+invalid+vague+off-topic+adversarial | A (EV01), P§15 | ✅ file present (verify count ≥20) |
| FR-E2 | Deterministic checks in code (right tool, chart tolerance, JSON, step budget, guardrails) | A (EV02) | ✅ in `metrics.py` |
| FR-E3 | LLM-as-judge for tone only, 1–5 rubric, different model family, spot-check agreement rate | A (EV03), P§15 | ✅ judge = Claude Haiku (diff family) |
| FR-E4 | Metrics per run: tokens, $ cost, latency p50/p95, tool-call count, failure rate | A (EV04) | ✅ |
| FR-E5 | One command runs the whole suite and prints a scorecard | A (EV06) | ✅ `python eval/run_eval.py` |
| FR-E6 | Results log over time (CSV/markdown) so regressions are visible | A (EV06) | ✅ `results_log.csv` |
| FR-E7 | Multi-model sweep (Qwen + one proprietary) → per-model scorecard | P§15 | ⚠️ sweep depends on broken default model string (see BUG-1) |

### FR-F · Deliverables (brief §07)
| ID | Requirement | Source | Status |
|----|-------------|--------|--------|
| FR-F1 | Public repo: backend + frontend + eval | A | ✅ |
| FR-F2 | README: setup, architecture, LangGraph diagram, known limitations | A | 🔍 verify present |
| FR-F3 | Committed golden set + scorecard from latest run | A | 🔍 verify scorecard committed |
| FR-F4 | 3–5 min demo recording | A | 🔍 out of code scope |
| FR-F5 | EVALUATION.md — what eval revealed + what you'd fix | A | 🔍 verify present |

---

## 2. Non-Functional Requirements (how WELL it must work)

| ID | Requirement | Source | Status |
|----|-------------|--------|--------|
| NFR-1 | **Reliability** — the configured default model actually responds; no first-run failure | P§12 | ❌ default `qwen3.5:397b` is not a real Ollama Cloud tag → every run fails |
| NFR-2 | **Grounded-in-real-data** — no hallucinated planetary positions, ever | A, P§6 | ✅ |
| NFR-3 | **Graceful failure** — bad input/keys/tools degrade with a message, never an unhandled 500 | A (EV05) | ⚠️ missing-key path raises uncaught `ValueError` |
| NFR-4 | **Security/secrets** — API key never persisted/logged in plaintext; passed per-session | P§12 | ❌ real key committed (`.env` + `run_eval.py`) |
| NFR-5 | **Latency** — answers in reasonable time; p50/p95 tracked; no 12-tool-call blowups | A (EV04) | ⚠️ no step cap (FR-A6); no chart caching in state (FR-A4) inflates tool calls |
| NFR-6 | **Cost** — tokens/$ tracked; default avoids extended-thinking | A (EV04), P§12 | ✅ tracked in eval |
| NFR-7 | **Model-agnostic** — provider/model is config, not code (OpenAI-compatible BYOK) | P§12 | ✅ |
| NFR-8 | **Maintainability** — one responsibility/file, typed, ≤~250 lines, docstrings | P§16, AGENTS.md | ✅ |
| NFR-9 | **Reproducibility** — eval runs identically by anyone with one command | A (EV06) | ⚠️ depends on NFR-1 / committed key |
| NFR-10 | **Drift resistance** — guardrails hold over long multi-turn chats | P§14 | 🔍 re-asserted each turn via system prompt; not load-tested |
| NFR-11 | **Accuracy gate** — 2–3 charts verified vs astro-seek/AstroSage within ~1° | P§13 | 🔍 unverified |
| NFR-12 | **Honest scope** — cuts documented in README known-limitations | A, P§5 | 🔍 verify README |

---

## 3. Customer-facing feature → requirement map (for the bug audit)

| # | Customer-facing feature | Depends on | Blocking bug? |
|---|-------------------------|-----------|---------------|
| 1 | Send a message / get any reply | NFR-1, FR-A1 | **BUG-1 (critical)** |
| 2 | Birth-details form → chart | FR-C2, FR-B1, FR-A4 | BUG-4, BUG-6, BUG-7 |
| 3 | Birth chart computation (text; visual cut) | FR-B1, ~~FR-C7~~ | depends on #1 |
| 4 | Daily transits | FR-B4, FR-A4 | BUG-5 |
| 5 | Free-form Q&A grounded in chart | FR-A2, FR-A4 | depends on #1 |
| 6 | Model/provider selector (BYOK) | FR-C8, NFR-3 | BUG-2 |
| 7 | Conversation history | FR-C9 | restart-loss |
| 8 | Guardrails | FR-D1–D5 | BUG-8 (false positives) |
| 9 | Streaming | FR-C4 | BUG-3 |

See `the bug audit in the conversation / DECISIONS.md` for details on each BUG-n.
