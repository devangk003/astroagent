"""Tune per-rail similarity thresholds for the semantic guardrail layer.

    python eval/tune_semantic.py

Loads eval/semantic_tune_set.jsonl (labeled, SEPARATE from the held-out guardrail_set.jsonl so the
eval stays honest), splits it dev/test, and for each rail sweeps the cosine-similarity threshold to
trade off misses (FNR) vs. false alarms (FPR). Picks a threshold per rail by an explicit objective,
prints dev + held-out-test metrics, and writes eval/semantic_thresholds.json (loaded by
agent.semantic_guard at runtime). This is the "tune it for fewer misses AND fewer false alarms" step.
"""
import io
import json
import os
import random
import sys
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

sys.path.insert(0, str(Path(__file__).parent.parent / "backend" / "src"))
os.environ["ASTRO_SEMANTIC_GUARD"] = "1"  # ensure scoring is enabled while tuning

from agent.semantic_guard import rail_scores, _ANCHORS, _THRESHOLDS_PATH  # noqa: E402
from agent.embedder import _MODEL_NAME  # noqa: E402  (the embedder these thresholds are tuned for)

RAILS = list(_ANCHORS.keys())
# Never-cut rails: favor recall (a miss is worse than a mild false alarm), subject to an FPR cap.
# medical/legal/financial stay balanced (Youden) to avoid over-blocking money/health/legal-adjacent chat.
SAFETY_RAILS = ("crisis", "injection", "fatalism")
FPR_CAP = 0.15
GRID = [round(0.20 + 0.02 * i, 2) for i in range(21)]  # 0.20 → 0.60


def _confusion(pairs, tau):
    """pairs: list of (score, is_positive). Predict positive if score >= tau."""
    tp = fp = fn = tn = 0
    for score, pos in pairs:
        pred = score >= tau
        if pos and pred:
            tp += 1
        elif pos and not pred:
            fn += 1
        elif not pos and pred:
            fp += 1
        else:
            tn += 1
    P, N = tp + fn, fp + tn
    recall = tp / P if P else 0.0
    fpr = fp / N if N else 0.0
    prec = tp / (tp + fp) if (tp + fp) else 0.0
    f1 = (2 * prec * recall / (prec + recall)) if (prec + recall) else 0.0
    return {"recall": recall, "fnr": 1 - recall, "fpr": fpr, "precision": prec, "f1": f1,
            "tp": tp, "fp": fp, "fn": fn, "tn": tn}


def _pick_threshold(rail, dev_pairs):
    """Choose tau per the rail's objective. Returns (tau, dev_metrics)."""
    scored = [(tau, _confusion(dev_pairs, tau)) for tau in GRID]
    if rail in SAFETY_RAILS:
        # Max recall subject to FPR <= cap; tie-break on higher tau (fewer false alarms).
        ok = [(t, m) for t, m in scored if m["fpr"] <= FPR_CAP]
        pool = ok or scored
        best = max(pool, key=lambda tm: (tm[1]["recall"], tm[0]))
    else:
        # Balance: maximize Youden's J = recall - FPR; tie-break on higher tau.
        best = max(scored, key=lambda tm: (tm[1]["recall"] - tm[1]["fpr"], tm[0]))
    return best[0], best[1]


def _meta_block() -> dict:
    """Provenance for the thresholds: the embedder + library they were tuned against.

    The cosine-similarity scale (hence every tau) is embedder-specific, so recording the model name
    and sentence-transformers version makes a silent model swap detectable. Loaded-but-ignored at
    runtime (semantic_guard._thresholds skips "_"-prefixed keys).
    """
    try:
        import sentence_transformers
        st_version = sentence_transformers.__version__
    except Exception:
        st_version = "unknown"
    return {
        "embedder_model": _MODEL_NAME,
        "sentence_transformers_version": st_version,
        "note": (
            "Thresholds are calibrated to this embedder's similarity scale. If the embedder model "
            "changes, these numbers are no longer valid — re-run `python eval/tune_semantic.py` to "
            "retune. (Regenerated on every tune; `_`-prefixed keys are ignored by the runtime loader.)"
        ),
    }


def main():
    path = Path("eval/semantic_tune_set.jsonl")
    items = [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]

    rng = random.Random(0)
    rng.shuffle(items)
    mid = len(items) // 2
    dev, test = items[:mid], items[mid:]

    # Precompute scores once per text (rail_scores is cached too).
    def pairs_for(rail, subset):
        out = []
        for it in subset:
            s = rail_scores(it["text"]).get(rail, 0.0)
            pos = (it.get("rail") == rail and it.get("label") == "harmful")
            out.append((s, pos))
        return out

    print(f"\nSemantic threshold tuning — {len(items)} cases (dev {len(dev)} / test {len(test)})")
    print(f"  {'Rail':<11} {'tau':>5} {'dev_recall':>10} {'dev_fpr':>8} {'test_recall':>11} {'test_fnr':>9} {'test_fpr':>9} {'test_f1':>8}")
    print(f"  {'-' * 78}")
    chosen = {}
    for rail in RAILS:
        tau, dev_m = _pick_threshold(rail, pairs_for(rail, dev))
        test_m = _confusion(pairs_for(rail, test), tau)
        chosen[rail] = tau
        print(f"  {rail:<11} {tau:>5.2f} {dev_m['recall']*100:>9.0f}% {dev_m['fpr']*100:>7.0f}% "
              f"{test_m['recall']*100:>10.0f}% {test_m['fnr']*100:>8.0f}% {test_m['fpr']*100:>8.0f}% {test_m['f1']:>8.2f}")

    # Record which embedder these thresholds were tuned against, so a future model swap is detectable
    # (the similarity scale — and thus every tau above — is embedder-specific). Regenerated each tune.
    chosen["_meta"] = _meta_block()
    _THRESHOLDS_PATH.write_text(json.dumps(chosen, indent=2) + "\n", encoding="utf-8")
    print(f"\n  Wrote thresholds → {_THRESHOLDS_PATH}")
    print(f"  {chosen}\n")
    print("  Note: test_* columns are the HELD-OUT half (not used to pick tau). Add anchors for high-FNR")
    print("  rails, add benign look-alikes for high-FPR rails, then re-run.\n")


if __name__ == "__main__":
    main()
