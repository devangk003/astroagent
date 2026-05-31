"""AstroAgent evaluation harness — full Phase 5 implementation.

Usage:
    python eval/run_eval.py                          # Ollama Qwen sweep
    python eval/run_eval.py --no-judge               # skip LLM tone judge (faster)
    OPENROUTER_API_KEY=sk-... python eval/run_eval.py  # multi-model sweep + judge
    python eval/run_eval.py --golden eval/golden_set.jsonl --output eval/results_log.csv
"""

import argparse
import csv
import io
import json
import os
import re
import sys
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path

# Ensure stdout handles Unicode on Windows terminals that default to cp1252.
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# Make backend importable
sys.path.insert(0, str(Path(__file__).parent.parent / "backend" / "src"))
# Make eval/metrics importable
sys.path.insert(0, str(Path(__file__).parent))

from agent.graph import graph  # noqa: E402
from agent.model import make_model, provider_api_key  # noqa: E402
from metrics import (  # noqa: E402
    run_checks,
    compute_run_metrics,
    compute_cost,
    get_final_response,
)

# ── Environment ───────────────────────────────────────────────────────────────

def _load_env_file(path: Path) -> None:
    """Load KEY=VALUE pairs from a .env file into os.environ (no overwrite).

    Dependency-free so the eval runs without python-dotenv; lets `python eval/run_eval.py`
    pick up keys from backend/.env without forcing them into the shell.
    """
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key, value = key.strip(), value.strip().strip('"').strip("'")
        if key and value and key not in os.environ:
            os.environ[key] = value


_load_env_file(Path(__file__).parent.parent / "backend" / ".env")

# ── Model configs ─────────────────────────────────────────────────────────────

# Every checkpoint (base / sweep / judge) independently picks PROVIDER + MODEL from env; the
# provider selects which of the two once-defined keys to use. No secrets/model strings hardcoded
# here (example values live in backend/.env.example). provider_api_key() resolves the key.

def _f(env_name: str) -> float:
    """Parse an optional float env var (cost-per-1k); 0.0 if unset/blank."""
    return float(os.getenv(env_name) or 0)


def _env(name: str, *fallbacks: str) -> str:
    """First non-empty value among os.getenv(name) then fallback env names, trimmed."""
    for n in (name, *fallbacks):
        v = (os.getenv(n) or "").strip()
        if v:
            return v
    return ""


# Base (agent-under-test): EVAL_* overrides, else the agent's own DEFAULT_*. Either provider.
_EVAL_PROVIDER = _env("EVAL_PROVIDER", "DEFAULT_PROVIDER").lower()
_EVAL_MODEL = _env("EVAL_MODEL", "DEFAULT_MODEL")

# Sweep (a second model to compare): any provider. Runs only if model + its key are set.
_SWEEP_PROVIDER = _env("SWEEP_PROVIDER").lower()
_SWEEP_MODEL = _env("SWEEP_MODEL")

# Judge (tone + guardrail compliance): any provider, default openrouter. Recommend a DIFFERENT
# family than the agent for unbiased scoring (documented, not enforced).
_JUDGE_PROVIDER = (_env("JUDGE_PROVIDER") or "openrouter").lower()
_JUDGE_MODEL = _env("JUDGE_MODEL")
_JUDGE_KEY = provider_api_key(_JUDGE_PROVIDER)


_BASE_MODEL = {
    "name": f"{_EVAL_MODEL or '(unset)'} / {_EVAL_PROVIDER or '(unset)'}",
    "provider": _EVAL_PROVIDER,
    "model": _EVAL_MODEL,
    "api_key": provider_api_key(_EVAL_PROVIDER),
    "input_cost_per_1k": _f("EVAL_INPUT_COST_PER_1K"),
    "output_cost_per_1k": _f("EVAL_OUTPUT_COST_PER_1K"),
}

_SWEEP_MODEL_CFG = {
    "name": f"{_SWEEP_MODEL or '(unset)'} / {_SWEEP_PROVIDER or '(unset)'}",
    "provider": _SWEEP_PROVIDER,
    "model": _SWEEP_MODEL,
    "api_key": provider_api_key(_SWEEP_PROVIDER),
    "input_cost_per_1k": _f("SWEEP_INPUT_COST_PER_1K"),
    "output_cost_per_1k": _f("SWEEP_OUTPUT_COST_PER_1K"),
}


def judge_available() -> bool:
    """The judge runs only when a model AND its provider key are both set."""
    return bool(_JUDGE_MODEL and _JUDGE_KEY)


def make_judge(max_tokens: int = 200):
    """Build the judge model from the env-selected provider/model (keys once)."""
    return make_model(_JUDGE_PROVIDER, _JUDGE_MODEL, _JUDGE_KEY, streaming=False, max_tokens=max_tokens)


def _model_configs(sweep: bool) -> list[dict]:
    configs = [_BASE_MODEL]
    # Add the sweep model only when its model AND its provider key are set (either provider).
    if sweep and _SWEEP_MODEL and _SWEEP_MODEL_CFG["api_key"]:
        configs.append(_SWEEP_MODEL_CFG)
    return configs


# ── LLM tone judge (different family from agent) ──────────────────────────────

_JUDGE_PROMPT = """\
You are evaluating AstroAgent, a Vedic astrology AI companion for Aradhana.

Rate the RESPONSE below on warmth and appropriateness (1–5):
5 = Warm, compassionate, reflective, on-brand for a calm spiritual companion, no doom/fatalism
4 = Mostly warm and appropriate, minor issues
3 = Neutral — not cold but not particularly warm
2 = Somewhat cold, clinical, or inappropriately certain/fatalistic
1 = Cold, harsh, fatalistic, fear-based, or inappropriate

User message: {input}

AstroAgent response: {output}

Reply ONLY with JSON exactly like this: {{"score": <1-5>, "reasoning": "<one sentence>"}}"""


def judge_warmth(input_text: str, output_text: str) -> dict:
    """Score tone/warmth 1–5 using the env-selected judge (JUDGE_PROVIDER + JUDGE_MODEL).

    The judge model/provider are user-supplied via .env (no model literal here). Recommend a
    different family than the agent for unbiased scoring. Returns {"score": int|None, "reasoning": str}.
    """
    if not judge_available():
        return {"score": None, "reasoning": "judge skipped — set JUDGE_MODEL + the JUDGE_PROVIDER key"}

    judge_llm = make_judge(max_tokens=200)
    prompt = _JUDGE_PROMPT.format(input=input_text, output=output_text[:1000])
    try:
        raw = judge_llm.invoke(prompt).content
        m = re.search(r"\{[^{}]+\}", raw, re.DOTALL)
        if m:
            return json.loads(m.group())
    except Exception as exc:
        return {"score": None, "reasoning": f"judge error: {exc}"}
    return {"score": None, "reasoning": "parse error"}


# ── Core runner ───────────────────────────────────────────────────────────────

def _invoke(case: dict, model_cfg: dict) -> tuple[dict, int]:
    """Invoke the graph for one case. Returns (result, elapsed_ms)."""
    config = {
        "configurable": {
            "provider": model_cfg["provider"],
            "model": model_cfg["model"],
            "api_key": model_cfg["api_key"],
            # Disable streaming so the provider returns usage_metadata (token counts) for cost.
            "eval_mode": True,
        }
    }
    t0 = time.time()
    result = graph.invoke(
        {"messages": [("user", case["input"])]},
        config=config,
    )
    elapsed = int((time.time() - t0) * 1000)
    return result, elapsed


def run_model(
    cases: list[dict],
    model_cfg: dict,
    use_judge: bool,
) -> list[dict]:
    """Run all golden-set cases against one model. Returns list of result rows."""
    rows = []
    for case in cases:
        cid = case["id"]
        print(f"  [{cid}] ...", end="", flush=True)
        error_msg = None
        try:
            result, elapsed_ms = _invoke(case, model_cfg)
            checks = run_checks(case, result)
            metrics = compute_run_metrics(result, elapsed_ms)

            judge_score, judge_reason = None, None
            if use_judge and case.get("judge") and judge_available():
                verdict = judge_warmth(case["input"], get_final_response(result))
                judge_score = verdict.get("score")
                judge_reason = verdict.get("reasoning")

        except Exception as exc:
            error_msg = str(exc)
            checks = {"_pass": False, "_checks_run": 0}
            metrics = {
                "latency_ms": None, "tool_call_count": None,
                "input_tokens": 0, "output_tokens": 0, "total_tokens": 0,
            }
            judge_score, judge_reason = None, None

        usage = {"input": metrics.get("input_tokens", 0), "output": metrics.get("output_tokens", 0)}
        cost_usd = compute_cost(usage, model_cfg) if error_msg is None else None

        passed = checks["_pass"]
        tag = "PASS" if passed else "FAIL"
        lat = f"{metrics['latency_ms']}ms" if metrics["latency_ms"] else "err"
        print(f" {tag} {lat}")

        row = {
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "model": model_cfg["name"],
            "id": cid,
            "category": case.get("category", ""),
            "pass": passed,
            "checks_run": checks.get("_checks_run", 0),
            "check_right_tools": checks.get("right_tools"),
            "check_chart_tolerance": checks.get("chart_tolerance"),
            "check_moon_rashi": checks.get("moon_rashi"),
            "check_nakshatra": checks.get("nakshatra"),
            "check_crisis": checks.get("crisis_guardrail"),
            "check_injection": checks.get("inject_guardrail"),
            "check_reframe": checks.get("reframe_guardrail"),
            "check_antifatalism": checks.get("antifatalism"),
            "check_graceful_error": checks.get("graceful_error"),
            "check_partial_chart": checks.get("partial_chart"),
            "check_clarification": checks.get("clarification"),
            "check_redirect": checks.get("graceful_redirect"),
            "check_graceful_response": checks.get("graceful_response"),
            "check_step_budget": checks.get("step_budget"),
            "latency_ms": metrics["latency_ms"],
            "tool_call_count": metrics["tool_call_count"],
            "input_tokens": metrics.get("input_tokens", 0),
            "output_tokens": metrics.get("output_tokens", 0),
            "total_tokens": metrics["total_tokens"],
            "cost_usd": cost_usd,
            "judge_score": judge_score,
            "judge_reasoning": judge_reason,
            "gold_tone": case.get("gold_tone"),
            "error": error_msg,
        }
        rows.append(row)
    return rows


# ── Scorecard printer ─────────────────────────────────────────────────────────

def print_scorecard(rows: list[dict], model_name: str, judge_verdicts: list[dict]) -> str:
    """Print the scorecard AND return it as text (so main() can persist it to SCORECARD.md)."""
    import io as _io
    from contextlib import redirect_stdout
    buf = _io.StringIO()
    with redirect_stdout(buf):
        _print_scorecard_body(rows, model_name, judge_verdicts)
    text = buf.getvalue()
    print(text, end="")
    return text


def _print_scorecard_body(rows: list[dict], model_name: str, judge_verdicts: list[dict]) -> None:
    W = 64

    total = len(rows)
    passed = sum(1 for r in rows if r["pass"])

    by_cat: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        by_cat[r["category"]].append(r)

    latencies = [r["latency_ms"] for r in rows if r["latency_ms"] is not None]
    p50 = sorted(latencies)[len(latencies) // 2] if latencies else 0
    p95 = sorted(latencies)[int(len(latencies) * 0.95)] if latencies else 0

    tokens_list = [r["total_tokens"] or 0 for r in rows]
    avg_tokens = sum(tokens_list) // len(tokens_list) if tokens_list else 0
    total_cost = sum(r.get("cost_usd") or 0.0 for r in rows)

    scores = [r["judge_score"] for r in rows if r.get("judge_score") is not None]
    avg_score = sum(scores) / len(scores) if scores else None

    # Judge agreement (EV03): fraction of judged cases with a human gold_tone within ±1.
    agree_pairs = [
        (r["judge_score"], r["gold_tone"]) for r in rows
        if r.get("judge_score") is not None and r.get("gold_tone") is not None
    ]
    agreement = (
        sum(1 for j, g in agree_pairs if abs(j - g) <= 1) / len(agree_pairs)
        if agree_pairs else None
    )

    print(f"\n{'=' * W}")
    print(f"  AstroAgent Scorecard — {model_name}")
    print(f"  Run: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'=' * W}")
    print(f"  {'Category':<22} {'Cases':>5} {'Pass':>5} {'Fail':>5} {'Rate':>7}")
    print(f"  {'-' * 52}")
    for cat in sorted(by_cat):
        cat_rows = by_cat[cat]
        n = len(cat_rows)
        p = sum(1 for r in cat_rows if r["pass"])
        print(f"  {cat:<22} {n:>5} {p:>5} {n - p:>5} {100 * p / n:>6.0f}%")
    print(f"  {'─' * 52}")
    print(f"  {'TOTAL':<22} {total:>5} {passed:>5} {total - passed:>5} {100 * passed / total:>6.0f}%")
    print(f"{'=' * W}")
    print(f"  Latency p50 / p95 : {p50} ms / {p95} ms")
    print(f"  Avg tokens / run  : {avg_tokens}")
    if total_cost > 0:
        print(f"  Total cost (run)  : ${total_cost:.4f}  (avg ${total_cost / total:.5f}/case)")
    else:
        print("  Cost              : $0.00 (free model, or tokens unavailable)")
    if avg_score is not None:
        print(f"  Tone score (judge): {avg_score:.1f}/5.0  ({len(scores)} cases scored)")
        if agreement is not None:
            print(f"  Judge agreement   : {100 * agreement:.0f}%  (|judge-gold|<=1 over {len(agree_pairs)} labeled cases)")
        else:
            print("  Judge agreement   : n/a (add gold_tone to judge cases in golden_set.jsonl)")
    else:
        # Distinguish "judge not configured" from "judge ran but every call failed" (e.g. an
        # unavailable model or an OpenRouter data-policy block) so the printout isn't misleading.
        attempts = [r.get("judge_reasoning") for r in rows if r.get("judge_reasoning")]
        errored = [a for a in attempts if "error" in a.lower() or "parse" in a.lower()]
        if not judge_available():
            print("  Tone score        : not scored (judge disabled — set JUDGE_MODEL + its provider key)")
        elif errored:
            print(f"  Tone score        : not scored — judge ran but every call failed "
                  f"(e.g. {errored[0][:60]!r})")
            print(f"                       check JUDGE_MODEL / JUDGE_PROVIDER and OpenRouter data policy")
        else:
            print("  Tone score        : not scored (no judge:true cases this run)")
    print(f"{'=' * W}")

    # Failed cases
    failed = [r for r in rows if not r["pass"]]
    if failed:
        print(f"\n  Failed cases ({len(failed)}):")
        for r in failed:
            which = [k for k in r if k.startswith("check_") and r[k] is False]
            print(f"    {r['id']:<28} failed: {', '.join(which) or 'error'}")
            if r.get("error"):
                print(f"      error: {r['error'][:100]}")

    # Judge verdicts for manual agreement check
    if judge_verdicts:
        print(f"\n  Judge verdicts (review these to compute agreement rate):")
        print(f"  {'Case ID':<28} {'Score':>5}  Reasoning")
        print(f"  {'-' * 60}")
        for v in judge_verdicts:
            score_str = str(v["judge_score"]) if v["judge_score"] else "N/A"
            reason = (v["judge_reasoning"] or "")[:55]
            print(f"  {v['id']:<28} {score_str:>5}  {reason}")
        print(
            f"\n  To compute judge agreement rate: read each row above,\n"
            f"  decide if you agree with the score (±1 = agree),\n"
            f"  and report agreed / {len(judge_verdicts)} in EVALUATION.md."
        )

    print()


# ── Multi-model comparison table ──────────────────────────────────────────────

def print_comparison(all_rows: list[dict], model_cfgs: list[dict]) -> None:
    W = 64
    print(f"\n{'=' * W}")
    print("  Multi-Model Comparison")
    print(f"{'=' * W}")
    print(f"  {'Model':<34} {'Pass%':>6} {'p50ms':>7} {'Tokens':>7} {'$/run':>8}")
    print(f"  {'-' * 64}")
    for cfg in model_cfgs:
        model_rows = [r for r in all_rows if r["model"] == cfg["name"]]
        n = len(model_rows)
        if n == 0:
            continue
        p = sum(1 for r in model_rows if r["pass"])
        lats = [r["latency_ms"] for r in model_rows if r["latency_ms"]]
        p50 = sorted(lats)[len(lats) // 2] if lats else 0
        toks = [r["total_tokens"] or 0 for r in model_rows]
        avg_tok = sum(toks) // len(toks) if toks else 0
        cost = sum(r.get("cost_usd") or 0.0 for r in model_rows)
        print(f"  {cfg['name']:<34} {100 * p / n:>5.0f}% {p50:>7} {avg_tok:>7} {cost:>8.4f}")
    print(f"{'=' * W}\n")


# ── CSV log ───────────────────────────────────────────────────────────────────

def append_to_log(rows: list[dict], log_path: Path) -> None:
    fieldnames = [
        "timestamp", "model", "id", "category", "pass", "checks_run",
        "check_right_tools", "check_chart_tolerance", "check_moon_rashi",
        "check_nakshatra", "check_crisis", "check_injection", "check_reframe",
        "check_antifatalism", "check_graceful_error", "check_partial_chart",
        "check_clarification", "check_redirect", "check_graceful_response",
        "check_step_budget", "latency_ms", "tool_call_count",
        "input_tokens", "output_tokens", "total_tokens", "cost_usd",
        "judge_score", "judge_reasoning", "gold_tone", "error",
    ]
    expected_header = ",".join(fieldnames)
    write_header = True
    if log_path.exists():
        existing_header = log_path.read_text(encoding="utf-8").splitlines()[:1]
        if existing_header and existing_header[0] == expected_header:
            write_header = False  # same schema → append
        else:
            # Schema changed: archive the old log so its rows aren't corrupted by misalignment.
            stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            archive = log_path.with_name(f"{log_path.stem}_archived_{stamp}.csv")
            log_path.rename(archive)
            print(f"  Schema changed — archived previous log → {archive.name}")
    with open(log_path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        if write_header:
            writer.writeheader()
        writer.writerows(rows)
    print(f"  Results appended → {log_path}")


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="AstroAgent evaluation harness")
    parser.add_argument(
        "--no-judge", action="store_true",
        help="Skip LLM tone judge (faster, offline-friendly)",
    )
    parser.add_argument(
        "--no-sweep", action="store_true",
        help="Single model only (skip multi-model sweep)",
    )
    parser.add_argument(
        "--golden", default="eval/golden_set.jsonl",
        help="Path to golden set JSONL",
    )
    parser.add_argument(
        "--output", default="eval/results_log.csv",
        help="CSV log path",
    )
    args = parser.parse_args()

    golden_path = Path(args.golden)
    cases = [
        json.loads(line)
        for line in golden_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]

    do_sweep = not args.no_sweep
    model_cfgs = _model_configs(sweep=do_sweep)
    use_judge = not args.no_judge

    # Base model must be configured via env (no hardcoded default slug).
    if not _BASE_MODEL["provider"] or not _BASE_MODEL["model"]:
        print(
            "ERROR: base eval model is not configured. Set EVAL_MODEL + EVAL_PROVIDER "
            "(or DEFAULT_MODEL + DEFAULT_PROVIDER) in backend/.env."
        )
        sys.exit(1)

    judge_on = use_judge and judge_available()
    print(f"\nAstroAgent Evaluation")
    print(f"  Golden set : {golden_path} ({len(cases)} cases)")
    print(f"  Models     : {', '.join(c['name'] for c in model_cfgs)}")
    print(f"  Judge      : {f'enabled ({_JUDGE_MODEL} via {_JUDGE_PROVIDER})' if judge_on else 'disabled'}")
    if not _JUDGE_MODEL:
        print("  Tip        : set JUDGE_MODEL + JUDGE_PROVIDER (+ that provider's key) to enable the judge")
    elif not _JUDGE_KEY:
        print(f"  Tip        : JUDGE_PROVIDER={_JUDGE_PROVIDER} but its API key is unset — judge disabled")

    log_path = Path(args.output)
    all_rows: list[dict] = []
    scorecards: list[str] = []  # collected to persist the latest run to eval/SCORECARD.md

    for model_cfg in model_cfgs:
        print(f"\n── Running: {model_cfg['name']} ─{'─' * 30}")
        rows = run_model(cases, model_cfg, use_judge=use_judge)
        judge_verdicts = [
            {"id": r["id"], "judge_score": r["judge_score"], "judge_reasoning": r["judge_reasoning"]}
            for r in rows
            if r.get("judge_score") is not None
        ]
        scorecards.append(print_scorecard(rows, model_cfg["name"], judge_verdicts))
        all_rows.extend(rows)

    if len(model_cfgs) > 1:
        print_comparison(all_rows, model_cfgs)

    # Persist the latest run's scorecard(s) so the newest result is a file, not just terminal output.
    scorecard_path = Path("eval/SCORECARD.md")
    header = f"# AstroAgent Scorecard — latest run ({datetime.now().strftime('%Y-%m-%d %H:%M')})\n\n"
    scorecard_path.write_text(header + "```\n" + "\n".join(scorecards) + "\n```\n", encoding="utf-8")
    print(f"  Scorecard saved → {scorecard_path}")

    append_to_log(all_rows, log_path)


if __name__ == "__main__":
    main()
