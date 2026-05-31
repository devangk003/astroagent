# AstroAgent — Product Requirements Document

*Aradhana · Full-Stack Builder Assignment · v1.0*

**How to read this doc.** Part 1 is written for everyone — no technical background needed. If you're not building it, you can stop after Part 1 and still understand what AstroAgent is and why. Part 2 is the technical specification for whoever implements it.

---

# PART 1 — THE PLAIN-LANGUAGE BRIEF

## 1. In one line

AstroAgent is a warm, conversational Vedic astrology companion that computes a user's real birth chart and answers their questions — grounded in actual astronomical data, never made-up.

## 2. What we're building

A chat app with an astrology "brain" behind it. A user enters their birth details once; the app calculates their *kundli* (Vedic birth chart) using a real astronomical engine, then chats with them about it — "what does my chart say about my career?", "what's the energy for me today?" The defining principle: the app never invents planetary positions or fortune-tells with false certainty. It reasons step by step, fetches real data with tools, and replies with care.

## 3. Who it's for

People seeking daily spiritual reflection and self-understanding through Vedic astrology — the Aradhana audience. They want warmth and insight, not a cold calculator or a doom-monger.

## 4. What a user can do (v1)

- Enter birth details (date, time, place) through a simple form.
- Get their Vedic birth chart: moon sign (*rashi*), planetary placements, houses (*bhavas*), ascendant (*lagna*), and birth star (*nakshatra*).
- Ask free-form questions and get answers grounded in their actual chart.
- Get daily guidance based on where the planets are *today* relative to their chart.

**A sample exchange:**
> **User:** Born 14 Aug 1995, 9:30am, Mumbai. What's my moon sign?
> **AstroAgent:** *(looks up Mumbai's coordinates, computes the chart)* Your moon is in Capricorn (Makara), in your birth star Shravana. That tends toward discipline and a steady, responsible streak…
> **User:** Will I get cancer?
> **AstroAgent:** I can't and won't predict health outcomes — astrology here is for reflection, not medical certainty. For anything health-related, please talk to a doctor. I'm happy to explore what your chart suggests about energy or wellbeing habits instead.

## 5. What's in, and what's deliberately left out

| In scope (v1) | Deferred (future work) |
|---|---|
| Sidereal Vedic kundli (rashi, houses, lagna, nakshatra) | Dasha timeline (Vimshottari) |
| Daily transit guidance | Kundli matching / compatibility (gun milan) |
| Conversational Q&A grounded in the chart | Divisional charts (navamsa, etc.) |
| Handling unknown birth time gracefully | Yogas & doshas (manglik, sade-sati) |
| Safety guardrails (see §6) | Panchang, numerology, tarot |
| | Indian-language support (Sarvam model) |

**Why scoped this way:** the deferred items are real astrology features but aren't required by the brief, and chasing them would steal time from the parts that *are* graded — the agent's design, its grounding in real data, and the proof that it works. Cutting them deliberately (and saying so) is good product judgment, not under-delivery.

> **Note on the Vedic choice:** going Vedic rather than Western was a judgment call inferred from contextual signals (the Aradhana name, "spiritual companion" framing, the Indian audience), not an explicit instruction. If the real stakeholder has a different intent, this is the first thing to confirm.

## 6. Non-negotiable principles

1. **Grounded in real data.** Planetary positions come from a real astronomical engine. The agent never invents them.
2. **Guidance, not certainty.** Never present readings as medical, legal, or financial fact.
3. **Safe with vulnerable users.** If someone is in distress, respond with care and point toward support — never with a horoscope.
4. **Empowering, not fatalistic.** Frame placements as tendencies to reflect on, not doom to fear.
5. **Honest about itself.** It's an AI companion, not a real guru or a substitute for professional help.
6. **Prove it works.** Every claim about quality is backed by a repeatable evaluation, not "it worked when I tried it."

## 7. What "done" looks like

**Minimum viable submission (protect this at all costs):** the agent computes a correct chart, answers a real question, streams in the chat UI, the evaluation runs with one command and prints a scorecard, and the four deliverables exist.

**The four deliverables (required by the brief):**
- [ ] Public Git repo: backend, frontend, evaluation harness
- [ ] README: setup, architecture overview, a diagram of the agent, known limitations
- [ ] Committed golden-set file + a scorecard from the latest eval run
- [ ] 3–5 minute screen recording (a real conversation + the eval running)
- [ ] EVALUATION.md: what the eval revealed and what you'd fix with more time

**Full target:** all four tools, all six guardrails tested, the 30-case golden set, the multi-model eval sweep, and the UI restyled to Aradhana's calm voice.

## 8. Success criteria

Done well means: the chart math is verifiably accurate; the agent reliably uses tools instead of guessing; the guardrails actually fire; the eval is honest and reproducible (a truthfully-reported low score beats an unreproducible perfect one); and the UI is calm, usable, and on-brand.

---
---

# ⎯⎯ PART 2 — TECHNICAL SPECIFICATION ⎯⎯
*(Non-technical readers can stop above. Everything below is for the build.)*

## 9. Architecture overview

Three tiers. The frontend is scaffolded; the Python agent is where the graded work lives; the eval is decoupled from both.

```
┌──────────────────────────────────────────────────────────────┐
│  BROWSER                                                       │
│  React + assistant-ui                                          │
│   • Birth-details form (date / time / place, "unknown time")   │
│   • Chat thread: streaming + visible tool activity             │
│   • Model/provider selector (bring-your-own-key)               │
└───────────────────────────┬──────────────────────────────────┘
                            │  LangGraph SDK over HTTP
                            ▼
┌──────────────────────────────────────────────────────────────┐
│  PYTHON — LangGraph server (`langgraph dev`)                   │
│                                                                │
│   START → [router] → [agent / reason] ⇄ [tools] → END          │
│                          │  tool-call validation + retry       │
│                          ▼                                      │
│        guardrails woven through (system prompt + checks)        │
│                                                                │
│   Tools: geocode_place · compute_birth_chart                   │
│          get_daily_transits · knowledge_lookup                 │
│                                                                │
│   LLM via ONE OpenAI-compatible client →                       │
│        Ollama Cloud / OpenRouter (user's key, user's model)    │
└───────────────────────────┬──────────────────────────────────┘
                            │  imports the compiled `graph`
                            ▼
                  ┌─────────────────────────┐
                  │  eval/ (pure Python)     │
                  │   golden_set.jsonl       │
                  │   run_eval.py (1 command)│
                  └─────────────────────────┘
```
*(Convert this to a Mermaid diagram for the README — the rubric asks for one.)*

## 10. The agent (LangGraph)

A custom ReAct-style graph — not the prebuilt `create_react_agent`, so the mechanics are yours to defend.

**State schema** (must include a `messages` key — required by the assistant-ui runtime):
```python
class AstroState(TypedDict):
    messages: Annotated[list, add_messages]   # required by the frontend runtime
    birth_details: Optional[BirthDetails]     # captured once, reused
    chart: Optional[dict]                     # cached kundli — don't recompute
```

**Nodes & flow:** `START → router → agent → (tools_condition) → tools → agent → … → END`.
- **router** — lightweight intent classification (chart request / daily transit / free-form), selects the system prompt slant.
- **agent** — the reasoning/LLM node, tools bound.
- **tools** — `ToolNode`; conditional edge loops back until no tool call remains.
- **tool-call validation + retry** — because open models are ~94% reliable on first tool call, validate tool args and retry/repair on malformed calls. This is deliberate engineering, not a patch.

## 11. Tools

| Tool | Contract |
|---|---|
| `geocode_place(place)` | → `{lat, lng, tz}`. Nominatim + timezonefinder. |
| `compute_birth_chart(date,time,lat,lng,tz)` | → sidereal kundli (rashi, bhavas, lagna, nakshatra). Kerykeion, Lahiri ayanamsa. **Real ephemeris — no invented positions.** |
| `get_daily_transits(date, natal)` | → today's gochar vs. natal moon/lagna. |
| `knowledge_lookup(query)` | → grounding notes (graha/bhava/rashi/nakshatra meanings). RAG via sentence-transformers + cosine. **Cut-first if behind schedule.** |

## 12. Model & provider strategy

- **One OpenAI-compatible client**, parameterized by `base_url` + `api_key` + `model`. Both Ollama Cloud and OpenRouter speak this protocol, so switching providers is config, not code.
- **Bring-your-own-key:** user supplies provider + model + key via a settings panel. **Never log or persist the key in plaintext;** pass it per-session.
- **Dev/test default:** Qwen 3.6 (hosted, ~$0.15/$1 per M on OpenRouter), standard mode (no extended-thinking — it inflates cost/latency).
- **Sarvam (Indian-language)** is deferred; verify reachability before promoting it.
- The model is a *variable*, which is what makes the multi-model eval sweep (§15) nearly free.

## 13. Astrology engine notes

- **Kerykeion**, `zodiac_type="Sidereal", sidereal_mode="LAHIRI"` (Indian government standard). Wraps Swiss Ephemeris.
- **Nakshatra:** confirm whether Kerykeion exposes it directly; if not, derive from the moon's sidereal longitude (27 × 13°20′). *Build-time verification item.*
- **Unknown birth time:** common and real. Without a time, lagna and houses are unreliable but rashi and nakshatra are fine → return those, explain the limitation. (Also a guardrail + eval case.)
- **Licensing:** Kerykeion is AGPL-3.0. Fine for an open assignment repo; note in the README that production would accept AGPL, buy a commercial ephemeris license, or wrap it as a service. *(Product-judgment point — state it, don't hide it.)*
- **Accuracy gate:** verify 2–3 charts against a reference (astro-seek / AstroSage) within ~1°.

## 14. Guardrails (six, layered)

Each guardrail is also a golden-set row (§15) — define it once, test it once.

| Guardrail | Behavior | Layer |
|---|---|---|
| Certainty reframing | No medical/legal/financial fact; reframe to reflection | System + output |
| Crisis → care | Distress → care + resources, never a reading | Input classify |
| Anti-fatalism | Tendencies, not doom; no fear-mongering | System |
| Birth-data validation | Impossible/missing → graceful (+ unknown-time path) | Input/tool |
| Prompt-injection resistance | Resist "ignore instructions"; system prompt wins | Input + system |
| System-level | Instruction hierarchy, tool/step budget, **drift-resistant re-assertion** (rails must hold over long chats), "AI not a guru" | System |
| Privacy | Minimal birth-data handling, no key/data leakage | System |

> Implementation: hand-roll lightweight rails + a strong system prompt. Don't adopt NeMo/Colang — the learning curve would eat the week. Name heavier frameworks in the README as "what I'd use at scale."

## 15. Evaluation (the centerpiece — 20% for little code, most-faked, so over-invest)

- **Golden set: ~30 cases**, versioned JSONL. Categories: valid chart requests, daily-transit asks, vague/underspecified, off-topic, and adversarial/failure (mostly free from §14). *Written from Day 1, grown through the week.*
- **Deterministic checks in code** (the bulk): right tool called, chart within tolerance of a reference, valid tool-arg JSON, step budget respected, each guardrail fired correctly.
- **LLM-as-judge only for tone/helpfulness:** 1–5 rubric, **different model family** than the agent, spot-check ~10 verdicts vs. your own and report the agreement rate (an unvalidated judge isn't evidence).
- **Metrics per run:** tokens, cost, latency (p50/p95), tool-call count, failure rate.
- **Multi-model sweep:** run the suite across Qwen and one proprietary model → per-model scorecard. This single move demonstrates vendor-independent product judgment + the cost/latency practice + a model-agnostic architecture at once.
- **One command** prints a scorecard table; a results log (CSV/markdown) tracks runs so regressions are visible.
- The harness `import`s the compiled `graph` directly — no server, no UI.

## 16. Project structure

```
astroagent/
├── backend/                      # YOURS — the graded core
│   ├── langgraph.json            # graph id "astro_agent" (must match frontend env)
│   ├── pyproject.toml            # langgraph, langchain, kerykeion, timezonefinder, geopy…
│   └── src/agent/
│       ├── state.py              # AstroState (messages key)
│       ├── tools.py              # the four tools
│       ├── guardrails.py         # rails + input classifier
│       └── graph.py              # router + agent + ToolNode + loop → `graph`
├── frontend/                     # SCAFFOLDED (create-assistant-ui -t langgraph)
│   ├── .env.local                # NEXT_PUBLIC_LANGGRAPH_API_URL + ASSISTANT_ID
│   ├── app/assistant.tsx         # runtime config (light edits)
│   ├── components/...            # restyle here for Aradhana's voice
│   └── (birth form + model selector you add)
└── eval/                         # YOURS — pure Python
    ├── golden_set.jsonl
    └── run_eval.py
```

## 17. Tech-stack decision record (the "why", for the README & the interview)

| Choice | Why | Main alternative (and when it'd win) |
|---|---|---|
| LangGraph (Python) | Stateful tool-loop + conditional routing is its sweet spot; brief names it | CrewAI if it were a multi-agent crew |
| Kerykeion (sidereal/Lahiri) | Real ephemeris, Vedic in one parameter, AI-friendly | flatlib (MIT) if AGPL is a blocker |
| assistant-ui LangGraph runtime | Keeps Python backend; streaming + tool UI + persistence free; restylable | Hand-rolled SSE if you want one language |
| OpenAI-compatible BYOK (Ollama Cloud / OpenRouter) | Model-agnostic; makes multi-model eval nearly free | Single proprietary default for max reliability |
| Qwen 3.6 default | Top open tool-caller, cheap, hosted | A proprietary mid-tier for max tool reliability |
| Hand-rolled guardrails | Defensible in 7 days; no Colang learning curve | NeMo Guardrails at production scale |

## 18. Timeline, cut list & done-tiers

- **Day 1 — Foundations.** Scaffold both sides, confirm they talk, state schema, BYOK client. **Write the first ~8–10 golden-set cases.**
- **Day 2 — Tools.** geocode, compute_birth_chart (verify vs. reference), transits. The accuracy gate.
- **Day 3 — Agent graph.** Router + reasoning + ToolNode + loop, tool-call validation/retry, system prompt + tone, form→state seeding, first-turn kundli.
- **Day 4 — Guardrails + 4th tool.** Wire all six; add knowledge_lookup (cut-first); each guardrail → a golden-set row.
- **Day 5 — Frontend.** Birth form + validation + unknown-time toggle, model selector, restyle to Aradhana, confirm streaming/tool-activity/errors.
- **Day 6 — Eval.** Grow golden set to 30, deterministic + judge (+agreement rate), cost/latency/reliability logging, multi-model sweep, one-command runner + scorecard + results log.
- **Day 7 — Docs/demo/submit.** README + graph diagram + known limitations, EVALUATION.md, 3–5 min recording, final scorecard committed.

**Cut list (in order):** stretch goals → `knowledge_lookup` → conversation persistence → fancy styling.
**Never cut:** chart accuracy · the eval harness · the certainty + crisis guardrails.

## 19. Stretch goals (only if core + eval are done)

Memory across sessions · a second "editor" agent for tone · human-in-the-loop confirmation (assistant-ui renders LangGraph `interrupt()` for free) · caching chart computations.

## 20. Build-time verification items (don't trust from memory — confirm)

- Kerykeion's exact attribute names and whether `nakshatra` is built-in.
- Exact Qwen 3.6 model string on Ollama Cloud vs. OpenRouter.
- Sarvam reachability via an OpenAI-compatible endpoint (deferred, but check).
- `langgraph dev` requires `langgraph-cli[inmem]`.
- assistant-ui runtime API surface (`useLangGraphRuntime`) against current docs.

## 21. How this maps to the grading rubric

| Rubric area | Weight | Covered by |
|---|---|---|
| Agent architecture | 25% | §10 graph, routing, tool loop, validation/retry |
| Tools & correctness | 20% | §11 four real tools, §13 accuracy gate |
| Evaluation rigor | 20% | §15 golden set, deterministic + judge, multi-model |
| Frontend craft | 20% | §9/§16 assistant-ui, form, streaming, restyle |
| Code quality & docs | 10% | §16 structure, §7 README/EVALUATION.md |
| Product judgment | 5% | §5 scoping, §6/§14 guardrails, §13 AGPL note |
