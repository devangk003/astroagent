# AstroAgent — Architecture Document

*The system map: how the whole thing fits together. Companion to the PRD (what & why) and the Technical Implementation Document (the build manual). Part 1 needs no technical background; Part 2 is the engineering view.*

---

# PART 1 — THE PLAIN-LANGUAGE ARCHITECTURE

## 1. The whole thing in one picture

Imagine a careful, warm astrologer giving a consultation. They **listen** to you, they **look up your exact star positions in a real almanac** (they don't guess), they **think step by step and check their reference books**, and they **speak with care** — never predicting doom or pretending to be a doctor. Behind the scenes, a **quality inspector** quietly tests that astrologer with the same set of tricky questions every day to make sure they keep behaving well.

AstroAgent is that, built in software:

```
   YOU                  THE ASTROLOGER (the "agent")            ITS INSTRUMENTS
 ┌───────┐   asks      ┌─────────────────────────┐  looks up   ┌──────────────────┐
 │ chat  │ ──────────▶ │  thinks, decides what    │ ──────────▶ │ • birthplace map │
 │ screen│ ◀────────── │  to look up, then replies │ ◀────────── │ • star almanac   │
 └───────┘   answers   └─────────────────────────┘   results   │ • reference books│
                                  ▲                              └──────────────────┘
                                  │ keeps it safe & warm
                         ┌────────────────────┐         ┌─────────────────────────┐
                         │  professional ethics│         │ QUALITY INSPECTOR (eval) │
                         │  (the guardrails)   │         │ runs a fixed exam daily  │
                         └────────────────────┘         └─────────────────────────┘
```

## 2. The parts, in plain English

- **The chat screen** — where you type and read replies, and where you first enter your birth details. It also lets you choose which "brain" powers the astrologer.
- **The astrologer (the agent)** — the decision-maker. It reads your question, figures out what it needs to look up, fetches it, and writes the reply. It never makes up star positions.
- **Its instruments (the tools)** — a *map* that turns "Mumbai" into exact coordinates, a *star almanac* that computes your real birth chart, and *reference books* it consults so its interpretations stay consistent.
- **The brain (the AI model)** — the language-and-reasoning engine. A deliberate design choice: you can swap which brain is used (you bring your own), so the app isn't locked to one company.
- **The professional ethics (guardrails)** — rules baked in: it won't give medical/legal/financial certainty, won't fear-monger, reminds you it's an AI not a real guru, and if you seem to be struggling it sets the reading aside and points you toward real support.
- **The quality inspector (evaluation)** — a separate testing system that runs the astrologer through a fixed set of questions — normal ones and tricky ones — and produces a scorecard, so quality is *proven*, not assumed.

## 3. What happens when you ask a question

1. You enter your birth details and ask something like *"what's my moon sign?"*
2. The system first checks: is this person in distress? If so, it responds with care instead of a reading. Otherwise it continues.
3. The astrologer realizes it needs your chart, so it uses the **map** (Mumbai → coordinates) and the **almanac** (coordinates + birth time → your real chart), and remembers the chart so it never recomputes it.
4. It writes a warm, grounded answer and sends it back to your screen, appearing word by word as it's written.
5. Ask a follow-up and it reuses the chart it already has.

## 4. The principles that shaped this design

- **Grounded, never guessed** — real astronomical data for the math, reference books for the meaning.
- **Not locked to one vendor** — the brain is swappable.
- **Safety is built into the structure**, not bolted on — the distress check happens *before* any reading.
- **Quality is testable** — the inspector is wired in from day one, separate from the app so it can run on its own.

---
---

# ⎯⎯ PART 2 — TECHNICAL ARCHITECTURE ⎯⎯
*(Non-technical readers can stop above.)*

## 5. System context

Three tiers plus two external services. The frontend is scaffolded; the Python agent holds all the graded logic; the eval runs as its own process.

```
┌───────────────────────────── BROWSER ──────────────────────────────┐
│  React + assistant-ui                                                │
│   • Birth-details form (date / time-or-unknown / place)              │
│   • Chat thread — streaming + visible tool activity                  │
│   • Model/provider selector (BYOK)                                   │
└───────────────────────────────┬─────────────────────────────────────┘
                                │  LangGraph SDK (HTTP)
                                ▼
┌────────────────────── PYTHON · LangGraph server (:2024) ────────────┐
│                                                                      │
│   START → router → agent ⇄ tools → END                               │
│              │ crisis short-circuit   │ tool-call validation+retry   │
│              ▼                         ▼                              │
│        guardrails (system prompt + checks, drift-resistant)          │
│                                                                      │
│   tools: geocode_place · compute_birth_chart ·                       │
│          get_daily_transits · knowledge_lookup                       │
│                                                                      │
│   model: BYOK factory → ChatOpenRouter | ChatOllama (.bind_tools)    │
└──────────┬───────────────────────────────────┬──────────────────────┘
          │                                   │
          ▼ (place name)                      ▼ (prompt + chart context)
   ┌──────────────┐                   ┌────────────────────────────┐
   │ Nominatim     │                   │ LLM provider                │
   │ (geocoding)   │                   │ OpenRouter / Ollama Cloud    │
   └──────────────┘                   └────────────────────────────┘

      ┌─────────────────── eval/ (separate process) ──────────────────┐
      │  imports the compiled `graph` directly — no server, no UI      │
      └────────────────────────────────────────────────────────────────┘
```

## 6. Component responsibilities

| Component | Responsibility | Tech |
|---|---|---|
| Frontend | Capture birth details; render streaming chat + tool activity; model selection | React, assistant-ui LangGraph runtime |
| LangGraph server | Host the compiled graph; expose the streaming API | `langgraph dev` (LangGraph v1.0) |
| Router node | Intent classify; **crisis short-circuit before any reading** | Python + cheap classifier |
| Agent node | Reason, decide tool calls, compose replies | LLM via BYOK factory, tools bound |
| Tool node | Execute geocode / chart / transits / knowledge lookup | LangChain `ToolNode` |
| Model factory | Return the right provider client per user selection | `langchain-openrouter`, `langchain-ollama` |
| Chart engine | Sidereal/Lahiri kundli, whole-sign houses, nakshatra | Kerykeion (Swiss Ephemeris) |
| Guardrails | Certainty reframing, anti-fatalism, injection resistance, drift re-assertion | System prompt + input/output checks |
| Eval harness | Score the agent against the golden set | Pure Python + DeepEval G-Eval |

## 7. The agent graph (internal)

```
        ┌────────┐
START ─▶ │ router │ ── crisis? ──▶ care reply ──▶ END
        └───┬────┘
            │ (normal)
            ▼
        ┌────────┐   tool calls?   ┌────────┐
        │ agent  │ ───── yes ─────▶ │ tools  │
        │ (LLM)  │ ◀──────────────  │        │
        └───┬────┘   tool results   └────────┘
            │ no tool calls
            ▼
           END  ──▶ stream reply to frontend
```

- **State** carries `messages` (required by the runtime), `birth_details`, and a cached `chart` so it's computed once.
- **The loop** (`agent ⇄ tools`, gated by `tools_condition`) is the ReAct pattern: reason → act → observe → repeat.
- **Tool-call validation/retry** wraps the agent's output: malformed tool calls (the ~6% open models get wrong) trigger a corrective re-invoke rather than a crash.

## 8. Request lifecycle (a single turn)

```
User → Frontend : submit "moon sign?" (+ birth_details from form)
Frontend → Server : start run (LangGraph SDK), state seeded
Server : router → not crisis → agent
agent → LLM : reason; emits tool_calls[geocode_place]
agent → tools : geocode_place("Mumbai") → {lat,lng,tz}
tools → agent : observation
agent → tools : compute_birth_chart(...) → kundli  (cached in state.chart)
tools → agent : observation
agent → LLM : compose grounded reply (no more tool calls)
Server → Frontend : stream tokens + tool-activity events
Frontend → User : warm answer, rendered live
```

Follow-up turns skip steps 4–7 by reusing `state.chart`.

## 9. The model layer (BYOK)

The agent depends on an *interface* (`a chat model that supports .bind_tools()`), not a concrete vendor. A small factory resolves the user's selection to the correct provider-specific client — `ChatOpenRouter` or `ChatOllama` — rather than a generic OpenAI client, because tool-calling is unreliable over a raw `base_url`. This keeps the graph vendor-agnostic and makes the multi-model eval sweep a config loop rather than a code change. The user's key flows in per-session and is never logged or persisted.

## 10. Evaluation architecture

```
golden_set.jsonl ─▶ run_eval.py ─▶ for each case:
                                     ├─ graph.invoke(case.input)        (imports graph directly)
                                     ├─ deterministic checks  (pure Python: right tool? chart in
                                     │     tolerance? guardrail fired? schema valid? step budget?)
                                     └─ G-Eval judge          (DeepEval, different-family model,
                                           tone/warmth only — validated by spot-check agreement)
                                  ▼
                        scorecard table + results_log.csv
                                  ▼
                        multi-model sweep: re-run with a different agent model
```

Architecturally key: the harness imports the compiled `graph` object, so evaluation is **fully decoupled** from the server and the UI — it can run in CI, offline, and across models without touching the frontend.

## 11. Trust & security boundaries

- **User API key** — entered in the frontend, passed per-session to the backend, used only by the model factory. Never logged, never persisted in plaintext. In production it sits behind a server-side proxy so it never reaches the browser bundle.
- **User messages are untrusted** — handled by the input classifier (injection/crisis) and a strict instruction hierarchy (system prompt wins). Tool outputs are treated as data, never as instructions.
- **Birth data is sensitive PII** — minimal handling, held in session state, not retained long-term unless persistence is explicitly enabled.
- **Outbound data** — only the place name goes to Nominatim; the conversation + chart context goes to the chosen LLM provider. Both are disclosed in the privacy note.

## 12. Deployment topology

- **Development:** two local processes — `langgraph dev` (:2024) and the Next.js app (:3000) — connected directly; no key proxy needed.
- **Production (future):** LangGraph server hosted (LangGraph Platform or self-hosted); frontend on Vercel/Node; the `langgraph-nextjs-api-passthrough` route injects the key server-side so it stays off the client.

## 13. Failure modes & resilience

| Failure | Handling |
|---|---|
| Model emits a malformed tool call | Validation + corrective retry in the agent node |
| Place not found | `geocode_place` returns `{error}`; agent asks the user to clarify |
| Unknown birth time | Chart returns rashi + nakshatra only; lagna/houses omitted with explanation |
| Distress / crisis input | Router short-circuits to a care response before any reading |
| Prompt injection | Input check + instruction hierarchy; tool outputs never executed as instructions |
| Long-session guardrail drift | Key safety lines re-asserted into context each turn |
| Geocoder rate limit | Results cached; ~1 req/sec respected |

## 14. Architectural decisions & tradeoffs

| Decision | Why | Tradeoff accepted |
|---|---|---|
| Custom LangGraph `StateGraph` (not prebuilt) | Need a router, tool-call retry, and guardrail control | More code than `create_react_agent` |
| Provider-specific model clients via a factory | Reliable tool-calling; vendor-agnostic | One small factory to maintain |
| Chart computed once, cached in state | Latency + cost on follow-ups | Must invalidate if birth details change |
| Eval decoupled (imports `graph`) | Runs in CI, offline, across models | Doesn't exercise the HTTP/UI path |
| Crisis check in the router (pre-reading) | Safety must precede the feature | A small latency cost on every turn |
| Hand-rolled guardrails (not NeMo) | Defensible and fast to build in 7 days | Less out-of-the-box coverage than a framework |

## 15. Tech stack at a glance

**Backend:** Python · LangGraph v1.0 · Kerykeion (sidereal/Lahiri, whole-sign) · Nominatim + timezonefinder · sentence-transformers (RAG) · provider clients (`langchain-openrouter`, `langchain-ollama`).
**Frontend:** React · assistant-ui LangGraph runtime (scaffolded).
**Models:** BYOK via OpenRouter / Ollama Cloud; default Qwen 3.6.
**Eval:** pure-Python harness + DeepEval G-Eval judge.
**Run:** `langgraph dev` (:2024) + Next.js (:3000).
