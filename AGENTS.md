# AGENT.md — AstroAgent Build Instructions

> **READ THIS FILE IN FULL AT THE START OF EVERY RUN, BEFORE EXECUTING ANYTHING.** It is your standing contract for this project. Re-read it if a session resumes or context is lost. Nothing happens before this file is read.

You are the **orchestrator** for building AstroAgent. This file governs how you plan, delegate, verify, checkpoint, and log.

## Source of truth

Three documents define this project. Treat them as authoritative; do not invent scope.
- **PRD** — what to build, scope (in/deferred), and the eight locked decisions.
- **Technical Implementation Document (TID)** — concrete libraries, code patterns, setup.
- **Architecture Document** — components, data flow, request lifecycle.

If anything here conflicts with those docs, the docs win for *what*; this file wins for *how to build it*.

## Prime directives (non-negotiable)

1. **MVS-first.** Build in the order: scaffold → a bare, working end-to-end frame → progressive polish. A working ugly thing beats a beautiful broken thing. Never start polish before the walking skeleton works end-to-end.
2. **Stop for the human after every phase.** Each phase ends with an automated gate *and* a manual checkpoint. Never start the next phase without explicit human approval. (See Manual Checkpoints.)
3. **Log every decision.** Maintain `DECISIONS.md`. Every deviation from the docs, every judgment call, every substantive fix gets an entry — as it happens. (See Decision Log.)
4. **Never fake chart math.** All planetary data comes from Kerykeion (sidereal/Lahiri, whole-sign houses). No hardcoded or invented positions, even as placeholders past Phase 1.
5. **Verify framework APIs; do not trust memory.** LangGraph, Kerykeion, assistant-ui, and provider packages have version-specific APIs. Confirm against the installed version before relying on any API. Honor every `[VERIFY]` item. If unsure, check docs — don't guess.
6. **Modular always.** One responsibility per file. No god-files. (See Code Structure.)
7. **Defensible.** Write code the human can understand and explain. Prefer clear over clever; brief docstrings on every module.
8. **Respect scope.** Honor the cut list under time pressure; never cut the never-cut items.

---

## Build phases

Each phase has a goal, delegable tasks, an **automated exit gate**, and a **manual checkpoint**. Both must pass before the next phase begins.

### Phase 0 — Scaffolding
Goal: the skeleton exists and runs, even if it does nothing useful.
- Repo structure, `pyproject.toml`, `langgraph.json`, env files, install deps.
- Scaffold the frontend (`create-assistant-ui -t langgraph`).
- Stub every module with typed signatures + docstrings (no logic).
- An **echo graph**: one node, no tools, fixed reply.
- **Exit gate:** `langgraph dev` boots, frontend connects, echo round-trips.

### Phase 1 — Walking skeleton (bare minimum, NOT polished)
Goal: the *thinnest* path that genuinely works end-to-end.
- `state.py` complete; `tools/chart.py` real `compute_birth_chart`; minimal agent + ToolNode + `tools_condition` loop.
- A real birth input flows: agent → chart tool → real kundli → reply.
- **Exit gate:** a real input produces a *verified* chart (±1° vs a reference) in the UI. No styling, no extra tools, no guardrails yet.

### Phase 2 — Tools & agent core
- `tools/geocode.py`, `tools/transits.py`, `tools/knowledge.py` (cut-first); router node; tool-call validation + retry.
- **Exit gate:** geocode → chart → transits chain works; malformed tool calls recover.

### Phase 3 — Guardrails & safety
- `guardrails.py`: all six rails; crisis short-circuit in the router *before* any reading; birth-data validation (impossible date / unknown time).
- **Exit gate:** each guardrail fires correctly on a probe input.

### Phase 4 — Frontend completion
- Birth-details form (+ unknown-time toggle), model/provider selector (BYOK), restyle to Aradhana's voice, streaming/tool-activity/error states.
- **Exit gate:** full user flow works in-browser, on-brand.

### Phase 5 — Evaluation harness
- `eval/`: 30-case golden set, deterministic checks + DeepEval G-Eval judge (different-family model), metrics (cost/latency/tool-count/failure), one-command runner + scorecard + results log, multi-model sweep.
- **Exit gate:** `python eval/run_eval.py` prints a scorecard; judge agreement-rate spot-checked.

### Phase 6 — Polish & delivery
- README (+ diagram), EVALUATION.md, final scorecard, demo prep.
- **Exit gate:** all five PRD deliverables present.

---

## Manual checkpoints (human approval gates)

After a phase's automated exit gate passes, **STOP. Do not begin the next phase.** Hand the product to the human and wait for explicit approval. This is a hard stop, not advisory.

At each checkpoint, present to the human:
1. **What was built** this phase (short summary).
2. **How to try it manually** — exact commands to run and/or clicks to make, so the human can verify it themselves.
3. **Gate results** — which checks passed.
4. **New decision-log entries** since the last checkpoint (deviations, fixes, judgment calls).
5. **Anything uncertain** or that you'd flag for a look.

Then wait. Proceed only on an explicit "approved" / "proceed". If the human requests changes: make them, re-run the automated gate, log any decisions, and re-present the checkpoint. Never skip a checkpoint to move faster.

---

## Decision log (`DECISIONS.md`)

Maintain an **append-only, chronological** `DECISIONS.md` at the repo root. Write entries *as decisions happen*, not retroactively. Never overwrite or delete past entries.

**Log an entry for any of:**
- A deviation from the PRD / TID / Architecture (and why).
- A judgment call made where the docs were silent or ambiguous.
- A substantive bug fix (what broke, root cause, fix).
- A library/API substitution or a resolution of a `[VERIFY]` item.
- A scope cut (and where it's noted in the README's known limitations).
- Any decision the human makes at a checkpoint.

**Entry format:**
```
## [YYYY-MM-DD HH:MM] — Phase N — <TYPE: deviation | decision | fix | verify | scope-cut>
What:   <one line>
Why:    <reason>
Impact: <what it affects; any follow-up needed>
Files:  <files touched>
Decided-by: <human | orchestrator>
```

At every manual checkpoint, surface the new entries to the human. The log feeds the README "known limitations" and EVALUATION.md, and keeps the build honest and auditable.

---

## Orchestration model (multi-agent swarm)

You delegate to sub-agents to parallelize, but you own integration and correctness. This protocol prevents deadlocks and file corruption — follow it exactly.

### Roles
- **Orchestrator (you):** plan each phase, define interfaces first, partition work, assign file ownership, dispatch sub-agent prompts, integrate, run gates, checkpoint, log.
- **Sub-agents:** implement one well-scoped task against a fixed interface, touching only their assigned files.

### The single rule that prevents corruption
**At most one agent writes to any given file at any time.** Everything below enforces this.

1. **Define interfaces before parallelizing.** You write the shared contracts first (the `state.py` schema, each tool's signature/docstring stub). Sub-agents implement *against* frozen stubs so independent work composes cleanly.
2. **You own the seams; sub-agents own the leaves.** Orchestrator-only files (never delegate): `graph.py`, every `__init__.py`, `langgraph.json`, `pyproject.toml`/`package.json`, shared config, `state.py`, and `DECISIONS.md`. Sub-agents only edit leaf modules.
3. **Parallelize only independent leaves.** Within a phase, dispatch in parallel only tasks whose files don't overlap and have no ordering dependency. Dependent work is sequenced. (Phases 0–1 are largely sequential — that's expected.)
4. **Integrate-and-gate between batches.** After a parallel batch returns, *you* wire it into the seams, run the gate, and only then dispatch the next batch. Never stack a batch on un-integrated work.
5. **No circular waits.** Strict ownership partition + centralized seams = no two agents can wait on each other → no deadlock by construction.

### Sub-agent dispatch template
```
TASK: <one specific thing>
OWN THESE FILES (edit only these): <explicit list>
INTERFACE CONTRACT (must satisfy, do not change): <signatures/types>
ACCEPTANCE CHECK: <how you'll verify it>
CONSTRAINT: Do not create or edit any file outside OWN THESE FILES.
            If you need a change to a shared file, STOP and report back.
```

### Example partition (Phase 2)
Sub-agent A → `tools/geocode.py` · B → `tools/transits.py` · C → `tools/knowledge.py` (independent → parallel). Orchestrator → `tools/__init__.py`, `graph.py`, gate, log, checkpoint.

---

## Test gates (automated)

Run a gate after **every substantial set of changes** (each completed task and each phase boundary). A gate is pass/fail; do not advance on red.

- [ ] Server boots (`langgraph dev`) and frontend builds — no import/syntax errors.
- [ ] The new unit does its job (a targeted test in `tests/`).
- [ ] All prior tests still pass — **no regressions**.
- [ ] Type-check / lint clean (if configured).
- [ ] Chart-touching changes: reference-chart tolerance check still passes.

Write a minimal test in `tests/` alongside each module as you build — repeatable gates, and it seeds the eval. If a gate fails, fix before proceeding. The automated gate precedes the manual checkpoint at every phase boundary.

---

## Code structure & conventions

```
backend/
  pyproject.toml
  langgraph.json                # orchestrator-owned
  .env
  src/agent/
    state.py                    # orchestrator-owned (shared contract)
    model.py                    # BYOK factory (provider-specific clients)
    guardrails.py
    graph.py                    # orchestrator-owned (the seam)
    tools/
      __init__.py               # orchestrator-owned
      geocode.py  chart.py  transits.py  knowledge.py
    knowledge/                  # reference notes (RAG corpus)
  tests/
    test_chart.py  test_geocode.py  test_guardrails.py ...
eval/
  golden_set.jsonl  metrics.py  run_eval.py
frontend/                       # scaffolded; edit form, selector, components, env
DECISIONS.md                    # orchestrator-owned, append-only
```

Conventions:
- **One responsibility per file**; soft cap ~250 lines — split if larger.
- **snake_case** modules, descriptive names (`compute_birth_chart`, not `util2`).
- **Type hints + a one-line docstring** on every public function.
- **No business logic in `graph.py`** beyond wiring; no tool logic in `state.py`.
- Small, single-purpose functions; prefer pure functions for tools.

---

## Scope discipline

- **Cut list (drop in this order under time pressure):** stretch goals → `knowledge_lookup` → conversation persistence → styling.
- **Never cut:** chart accuracy · the eval harness · the certainty + crisis guardrails.
- Anything cut is recorded in `DECISIONS.md` and the README's "known limitations".

## Verification checklist (confirm against installed versions)
- Kerykeion nakshatra field vs. derive-from-moon-longitude fallback.
- Whole-sign house identifier code.
- Kerykeion attribute names (`.sign` / `.position` / `.abs_pos` / house access).
- Exact Qwen 3.6 model strings on OpenRouter vs. Ollama Cloud.
- Ollama Cloud base_url + auth.
- `langgraph dev` requires `langgraph-cli[inmem]`.
- assistant-ui `useLangGraphRuntime` API against current docs.
