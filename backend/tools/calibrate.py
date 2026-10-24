"""Measure how accurate each check is, per target sound.

For every practice item (levels 1-3) Sarvam TTS voices say:
  * the item correctly                                -> label "correct"
  * the item with the target letter swapped for each
    common mix-up (மழை -> மளை, शेर -> सेर)           -> label "mixup:<letter>"
Each clip then goes through the same checks a learner's attempt does. The
voice comparison never compares a clip with its own voice (leave-one-voice-out).
Results: var/calibration.json (used for confidence), var/calibration_report.md.

Run from the backend folder:
    python -m tools.calibrate --dry-run       # clip count and estimated cost
    python -m tools.calibrate
Synthetic speech is cleaner than real learners: treat the numbers as best case
until they are checked against real recordings.
"""
import argparse
import json
import sys
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

from app import analysis, calibration, content, g2p
from app.audio import decode_wav, trim_silence
from app.calibration import CALIBRATION_PATH
from app.config import DATA_DIR, SARVAM_STT_MODEL, SARVAM_TTS_MODEL
from app.engines import phonemes, sarvam, templates

ENGINES = ("transcript", "phonemes", "templates")


def build_clips(target_ids, levels, speakers, stt_speakers):
    clips = []
    for t in content.targets():
        if target_ids and t["id"] not in target_ids:
            continue
        for lvl in levels:
            for it in content.items(t["id"], lvl):
                for lab in templates.labels(t):
                    for spk in speakers:
                        clips.append({"target": t["id"], "level": lvl, "item": it["text"], "label": lab, "speaker": spk,
                                      "spoken": templates.spoken_text(it["text"], t, lab), "language": t["language"],
                                      "stt": spk in stt_speakers})
    return clips


def run_clip(clip):
    t = content.target(clip["target"])
    out = dict(clip)
    try:
        x = trim_silence(decode_wav(sarvam.reference_audio(clip["spoken"], clip["language"], clip["speaker"])))
    except Exception as e:
        return out | {"error": f"tts: {e}"}
    engines = ENGINES if clip["stt"] else ("phonemes", "templates")
    views, extras, errors = analysis.run_engines(x, clip["item"], t, exclude_speaker=clip["speaker"], engines=engines)
    out["views"] = {eng: {"verdict": v["verdict"], "heard_as": v.get("heard_as")} for eng, v in views.items()}
    out["transcript"] = extras.get("transcript")
    out["ipa"] = extras.get("phonemes")
    if errors:
        out["engine_errors"] = errors
    return out


def tally(results):
    blank = lambda: {"correct": {"on_target": 0, "substitution": 0, "unclear": 0},
                     "mixup": {"on_target": 0, "substitution_right": 0, "substitution_other": 0, "unclear": 0}}
    counts = defaultdict(lambda: defaultdict(blank))
    for r in results:
        if "error" in r:
            continue
        truth = "correct" if r["label"] == "correct" else r["label"]
        for eng, v in r.get("views", {}).items():
            c = counts[r["target"]][eng]
            if truth == "correct":
                c["correct"][v["verdict"]] += 1
            elif v["verdict"] == "substitution":
                c["mixup"]["substitution_right" if g2p.normalize(v["heard_as"] or "") == truth else "substitution_other"] += 1
            else:
                c["mixup"][v["verdict"]] += 1
    return {t: dict(e) for t, e in counts.items()}


def fused_accuracy(results):
    """Accuracy of the final combined verdict, using the freshly measured precisions."""
    acc = defaultdict(lambda: {"right": 0, "wrong": 0, "unsure": 0})
    for r in results:
        if "error" in r or not r.get("views"):
            continue
        f = analysis.fuse(r["views"], "ok", r["target"])
        truth = ("on_target", None) if r["label"] == "correct" else ("substitution", r["label"])
        a = acc[r["target"]]
        if f["outcome"] == "unclear":
            a["unsure"] += 1
        elif (f["outcome"], g2p.normalize(f["heard_as"]) if f["heard_as"] else None) == truth:
            a["right"] += 1
        else:
            a["wrong"] += 1
    return dict(acc)


def report(counts, fused, n_clips, errors, speakers):
    pct = lambda a, b: f"{a}/{b} ({round(100 * a / b) if b else 0}%)"
    names = {"transcript": "Sarvam speech-to-text", "phonemes": "Sound model", "templates": "Sarvam voice comparison"}
    lines = ["# SayBetter accuracy report", "",
             f"Generated {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC from {n_clips} synthetic clips: Sarvam {SARVAM_TTS_MODEL} "
             f"voices ({', '.join(speakers)}), speech-to-text {SARVAM_STT_MODEL}. {errors} clips failed.", "",
             "Synthetic speech is cleaner than real learners: treat these as best-case numbers.", "",
             "## Combined verdict (what the learner sees)", "",
             "| Sound | Right | Wrong | Said “not sure” | Right when it made a call |", "|---|---|---|---|---|"]
    for tid, a in fused.items():
        n = a["right"] + a["wrong"] + a["unsure"]
        lines.append(f"| {content.target(tid)['name']} | {pct(a['right'], n)} | {pct(a['wrong'], n)} | {pct(a['unsure'], n)} | "
                     f"{pct(a['right'], a['right'] + a['wrong'])} |")
    lines += ["", "## Each check on its own", "",
              "| Sound | Check | Correct judged correct | Mix-ups caught | Mix-up named right | False alarms |", "|---|---|---|---|---|---|"]
    for tid, engines in counts.items():
        for eng, c in engines.items():
            nc, nm = sum(c["correct"].values()), sum(c["mixup"].values())
            caught = c["mixup"]["substitution_right"] + c["mixup"]["substitution_other"]
            lines.append(f"| {content.target(tid)['name']} | {names[eng]} | {pct(c['correct']['on_target'], nc)} | {pct(caught, nm)} | "
                         f"{pct(c['mixup']['substitution_right'], nm)} | {pct(c['correct']['substitution'], nc)} |")
    return "\n".join(lines) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--targets", nargs="*", default=[])
    ap.add_argument("--levels", nargs="*", type=int, default=[1, 2, 3])
    ap.add_argument("--stt-voices", type=int, default=3, help="run speech-to-text on this many voices (cost control)")
    ap.add_argument("--workers", type=int, default=3)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    speakers = templates.SPEAKERS
    clips = build_clips(set(args.targets), args.levels, speakers, set(speakers[: args.stt_voices]))
    chars = sum(len(c["spoken"]) for c in clips)
    n_stt = sum(c["stt"] for c in clips)
    print(f"{len(clips)} clips ({n_stt} with speech-to-text), {chars} TTS characters "
          f"≈ ₹{chars / 1000 * 3:.0f} TTS + ≈ ₹{n_stt * 1.0 / 60 * 0.49:.0f} STT at pay-as-you-go rates (cached clips cost nothing)")
    if args.dry_run:
        return
    if not sarvam.available():
        sys.exit("SARVAM_API_KEY is not set in backend/.env")

    phonemes.start_loading()
    while phonemes.status()["status"] in ("loading", "not_loaded"):
        time.sleep(0.5)

    # Generate every clip first (rate-limited API), then analyse.
    started = time.time()
    with ThreadPoolExecutor(args.workers) as pool:
        def fetch(c):
            try:
                sarvam.reference_audio(c["spoken"], c["language"], c["speaker"])
            except Exception as e:
                return str(e)
        failed = [e for e in pool.map(fetch, clips) if e]
    print(f"TTS ready in {time.time() - started:.0f}s ({len(failed)} failed)", flush=True)

    results = []
    with ThreadPoolExecutor(args.workers) as pool:
        for i, r in enumerate(pool.map(run_clip, clips), 1):
            results.append(r)
            if i % 50 == 0 or i == len(clips):
                print(f"  analysed {i}/{len(clips)}", flush=True)

    errors = sum("error" in r for r in results)
    counts = tally(results)
    CALIBRATION_PATH.write_text(json.dumps({
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source": f"synthetic: Sarvam {SARVAM_TTS_MODEL} voices ({', '.join(speakers)}); STT {SARVAM_STT_MODEL}",
        "clips": len(results) - errors, "targets": counts,
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    calibration.reload()
    fused = fused_accuracy(results)
    with open(DATA_DIR / "calibration_clips.jsonl", "w", encoding="utf-8") as f:
        for r in results:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    data = json.loads(CALIBRATION_PATH.read_text(encoding="utf-8"))
    data["fused"] = fused
    CALIBRATION_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    text = report(counts, fused, len(results) - errors, errors, speakers)
    (DATA_DIR / "calibration_report.md").write_text(text, encoding="utf-8")
    print(text)
    if errors:
        print("first errors:", [r["error"] for r in results if "error" in r][:3])


if __name__ == "__main__":
    main()
