"""Attempt analysis pipeline.

validate audio -> quality check -> three independent checks of the target sound:
    transcript  Sarvam speech-to-text, verbatim, in native script
    phonemes    local wav2vec2 phoneme recognizer (IPA)
    templates   comparison with Sarvam TTS voices saying the item correctly / with each mix-up
-> fuse: each check's measured track record for this sound adds (agrees) or
   subtracts (disagrees) evidence, giving one outcome and a confidence.
"""
import logging
import math

from . import calibration, compare
from .audio import AudioError, assess, decode_wav, encode_wav, trim_silence
from .engines import phonemes, sarvam, templates

log = logging.getLogger(__name__)

STATUSES = ("analysis_completed", "low_confidence", "audio_unusable", "analysis_unavailable", "analysis_failed", "demo_result")
TRUST_FLOOR = 0.6   # ignore a check's verdict for a sound where it was right less often than this
MIN_CONFIDENCE = 0.55
MAX_CONFIDENCE = 0.95  # calibration used clean synthetic speech; never claim near-certainty

# Used only until tools/calibrate.py has measured the real numbers.
DEFAULT_PRECISION = {
    ("transcript", "on_target"): 0.55,  # word recognizers lean toward the expected word
    ("transcript", "substitution"): 0.7,
    ("phonemes", "on_target"): 0.6, ("phonemes", "substitution"): 0.6,
    ("templates", "on_target"): 0.6, ("templates", "substitution"): 0.6,
}


def _key(v: dict) -> tuple:
    return (v["verdict"], v.get("heard_as"))


def fuse(views: dict[str, dict], quality_status: str, target_id: str) -> dict:
    decisive = {eng: v for eng, v in views.items() if v and v["verdict"] != "unclear"}
    trusted, evidence, all_measured = {}, {}, True
    for eng, v in decisive.items():
        measured = calibration.precision(target_id, eng, v["verdict"])
        if measured is None:
            all_measured = False
            p, n = DEFAULT_PRECISION[(eng, v["verdict"])], 0
        else:
            p, n = measured
        p = min(max(p, 0.5), 0.97)
        ev = {"verdict": v["verdict"], "heard_as": v.get("heard_as"), "precision": round(p, 3), "samples": n}
        if p < TRUST_FLOOR:
            ev["ignored"] = True
        else:
            trusted[eng] = p
        evidence[eng] = ev

    base = {"evidence": evidence, "calibrated": bool(decisive) and all_measured}
    if not trusted:
        return base | {"status": "low_confidence", "outcome": "unclear", "heard_as": None, "confidence": 0.25,
                       "agreement": "unreliable" if decisive else "none"}

    def logodds(candidate):
        total = 0.0
        for eng, p in trusted.items():
            w = math.log(p / (1 - p))
            total += w if _key(decisive[eng]) == candidate else -w
        return total

    candidates = {_key(decisive[e]) for e in trusted}
    best = max(candidates, key=logodds)
    conf = 1 / (1 + math.exp(-logodds(best)))
    supporters = [e for e in trusted if _key(decisive[e]) == best]
    if len(trusted) == 1:
        agreement = f"{supporters[0]}_only"
    elif len(supporters) == len(trusted):
        agreement = "all_agree"
    else:
        agreement = "majority"

    conf = min(conf, MAX_CONFIDENCE)
    if quality_status in ("noisy", "clipped"):
        conf -= 0.1
    conf = round(max(0.0, conf), 2)
    if conf < MIN_CONFIDENCE:
        return base | {"status": "low_confidence", "outcome": "unclear", "heard_as": None, "confidence": conf,
                       "agreement": "disagree" if len(candidates) > 1 else agreement}
    return base | {"status": "analysis_completed", "outcome": best[0], "heard_as": best[1], "confidence": conf,
                   "agreement": agreement, "supporters": supporters}


def demo_result(attempt_no: int, target: dict) -> dict:
    """Scripted, clearly labelled result for the demo profile only."""
    pattern = ["substitution", "on_target", "substitution", "on_target", "on_target"]
    outcome = pattern[attempt_no % len(pattern)]
    heard = next(iter(target["confusions"])) if outcome == "substitution" else None
    return {"status": "demo_result", "outcome": outcome, "heard_as": heard, "confidence": 0.0, "agreement": "demo"}


ALL_ENGINES = ("transcript", "phonemes", "templates")


def run_engines(x, item_text: str, target: dict, *, exclude_speaker: str | None = None,
                engines=ALL_ENGINES) -> tuple[dict, dict, list]:
    """Run the available checks. Returns (views, extras for display, errors)."""
    views, extras, errors = {}, {"method": []}, []
    if "transcript" in engines and sarvam.available():
        try:
            stt = sarvam.transcribe(encode_wav(x), target["language"])
            extras["transcript"] = stt["transcript"]
            views["transcript"] = compare.check_transcript(item_text, stt["transcript"], target)
            extras["method"].append(f"sarvam:{stt['model']}")
        except Exception as e:
            log.warning("Sarvam failed: %s", e)
            errors.append(f"Speech-to-text failed: {e}")
    if "phonemes" in engines and phonemes.available():
        try:
            views["phonemes"] = compare.check_phonemes(item_text, phonemes.recognize(x), target, phonemes.vocab())
            extras["phonemes"] = views["phonemes"].get("observed_ipa")
            extras["method"].append("wav2vec2-xlsr-espeak")
        except Exception as e:
            log.exception("Phoneme engine failed")
            errors.append(f"Phoneme analysis failed: {e}")
    if "templates" in engines and templates.available() and templates.supports(target, item_text):
        try:
            views["templates"] = templates.classify(x, target, item_text, exclude_speaker=exclude_speaker)
            extras["method"].append(f"sarvam-voices:{views['templates'].get('voices', 0)}")
        except Exception as e:
            log.exception("Template engine failed")
            errors.append(f"Voice comparison failed: {e}")
    return views, extras, errors


def analyze(wav_bytes: bytes, item_text: str, target: dict, *, allow_demo: bool, demo_attempt_no: int) -> dict:
    result = {"status": None, "outcome": None, "heard_as": None, "confidence": 0.0, "method": [],
              "quality": None, "transcript": None, "phonemes": None, "engines": {}, "errors": []}

    try:
        x = decode_wav(wav_bytes)
    except AudioError as e:
        result.update(status="audio_unusable", quality={"status": "invalid", "usable": False, "issues": [str(e)]})
        return result
    q = assess(x)
    result["quality"] = q.as_dict()
    if not q.usable:
        result["status"] = "audio_unusable"
        return result
    x = trim_silence(x)

    views, extras, errors = run_engines(x, item_text, target)
    result.update(engines=views, errors=errors, method=extras["method"],
                  transcript=extras.get("transcript"), phonemes=extras.get("phonemes"))

    if not views:
        if allow_demo:
            result.update(demo_result(demo_attempt_no, target))
            result["method"] = ["demo"]
        else:
            result["status"] = "analysis_failed" if errors else "analysis_unavailable"
        return result

    result.update(fuse(views, q.status, target["id"]))
    return result
