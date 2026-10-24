"""Measured reliability of each engine, per target sound.

Produced by tools/calibrate.py from labelled clips (correct and mixed-up
pronunciations of every practice item). Confidence in analysis.py comes from
these measured precisions instead of hand-set numbers.
"""
import json
from functools import lru_cache
from pathlib import Path

# Shipped with the code so every deployment uses the same measured accuracy.
CALIBRATION_PATH = Path(__file__).resolve().parent / "data" / "calibration.json"
MIN_SAMPLES = 6


@lru_cache
def load() -> dict | None:
    if not CALIBRATION_PATH.exists():
        return None
    with open(CALIBRATION_PATH, encoding="utf-8") as f:
        return json.load(f)


def reload() -> None:
    load.cache_clear()


def stats(target_id: str, engine: str) -> dict | None:
    cal = load()
    return cal and cal["targets"].get(target_id, {}).get(engine)


def precision(target_id: str, engine: str, verdict: str) -> tuple[float, int] | None:
    """How often this engine was right when it gave this verdict for this target.

    Laplace-smoothed; None when there were too few such verdicts to say.
    """
    s = stats(target_id, engine)
    if not s:
        return None
    if verdict == "on_target":
        right, wrong = s["correct"]["on_target"], s["mixup"]["on_target"]
    elif verdict == "substitution":
        right, wrong = s["mixup"]["substitution_right"], s["correct"]["substitution"] + s["mixup"]["substitution_other"]
    else:
        return None
    n = right + wrong
    if n < MIN_SAMPLES:
        return None
    return (right + 1) / (n + 2), n


def summary() -> dict | None:
    """Plain numbers for the accuracy report page."""
    cal = load()
    if not cal:
        return None
    out = {}
    for tid, engines in cal["targets"].items():
        out[tid] = {}
        for eng, s in engines.items():
            c, m = s["correct"], s["mixup"]
            n_c, n_m = sum(c.values()), sum(m.values())
            p_ok, p_sub = precision(tid, eng, "on_target"), precision(tid, eng, "substitution")
            out[tid][eng] = {
                "correct_clips": n_c, "mixup_clips": n_m,
                "correct_recognised": c["on_target"], "mixups_caught": m["substitution_right"] + m["substitution_other"],
                "mixups_named_right": m["substitution_right"], "false_alarms": c["substitution"],
                "precision_on_target": p_ok and round(p_ok[0], 3), "precision_substitution": p_sub and round(p_sub[0], 3),
            }
    return {"generated_at": cal["generated_at"], "source": cal["source"], "clips": cal["clips"], "targets": out,
            "fused": cal.get("fused")}
