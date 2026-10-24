"""Compare an attempt with Sarvam TTS recordings of the same item, said
correctly and with each common mix-up, in several voices.

For every voice we ask: is the attempt closer to this voice's correct
version, or to one of its mix-up versions? Comparing within one voice cancels
out who is speaking, so only the target sound decides. The voices then vote.
This does not need the recognizer to know Tamil ழ: it only needs the two
recordings to sound different.
"""
import logging
import os
import threading
from collections import Counter

import numpy as np

from .. import content, g2p
from ..audio import decode_wav, trim_silence
from . import phonemes, sarvam

log = logging.getLogger(__name__)

SPEAKERS = [s.strip() for s in os.getenv("SARVAM_TEMPLATE_SPEAKERS", "shubh,kavitha,anand,priya,rahul,shruti").split(",") if s.strip()]
# Layer 18 with best-2 scoring won on leave-one-voice-out tests (ழ 62%, श 88%; layer 12 voting: 51%, 63%).
LAYER = int(os.getenv("TEMPLATE_LAYER", "18"))
MAX_LEVEL = 3  # phrases and sentences are long; templates only for sounds, syllables and words

_bank: dict[tuple, np.ndarray] = {}
_bank_lock = threading.Lock()


def available() -> bool:
    return sarvam.available() and phonemes.available()


def labels(target: dict) -> list[str]:
    accepted = {g2p.normalize(a) for a in target.get("accept", [])}
    return ["correct"] + [g2p.normalize(c) for c in target["confusions"] if g2p.normalize(c) not in accepted]


def spoken_text(item_text: str, target: dict, label: str) -> str:
    text = g2p.normalize(item_text)
    return text if label == "correct" else text.replace(g2p.normalize(target["letter"]), label)


def supports(target: dict, item_text: str) -> bool:
    found = content.find_item(target["id"], item_text)
    return bool(found) and found[0] <= MAX_LEVEL


def _features(target: dict, item_text: str, label: str, speaker: str) -> np.ndarray:
    key = (target["id"], item_text, label, speaker, LAYER)
    with _bank_lock:
        if key in _bank:
            return _bank[key]
    wav = sarvam.reference_audio(spoken_text(item_text, target, label), target["language"], speaker)
    f = phonemes.hidden(trim_silence(decode_wav(wav)), LAYER)
    with _bank_lock:
        _bank[key] = f
    return f


def dtw(a: np.ndarray, b: np.ndarray) -> float:
    """Length-normalised DTW over cosine distance."""
    d = 1.0 - a @ b.T
    n, m = d.shape
    D = np.full((n + 1, m + 1), np.inf)
    D[0, 0] = 0.0
    for i in range(1, n + 1):
        Di, Dp, di = D[i], D[i - 1], d[i - 1]
        for j in range(1, m + 1):
            Di[j] = di[j - 1] + min(Dp[j], Di[j - 1], Dp[j - 1])
    return float(D[n, m] / (n + m))


def classify(x: np.ndarray, target: dict, item_text: str, exclude_speaker: str | None = None) -> dict:
    """Each version (correct / each mix-up) is scored by the mean distance to its
    two closest voices; the closest version wins."""
    labs = labels(target)
    f = phonemes.hidden(x, LAYER)
    dists: dict[str, list[float]] = {lab: [] for lab in labs}
    votes = Counter()
    used = 0
    for spk in SPEAKERS:
        if spk == exclude_speaker:
            continue
        try:
            d = {lab: dtw(f, _features(target, item_text, lab, spk)) for lab in labs}
        except Exception as e:  # one voice failing shouldn't sink the comparison
            log.warning("template %s/%s failed: %s", item_text, spk, e)
            continue
        used += 1
        votes[min(d, key=d.get)] += 1
        for lab, v in d.items():
            dists[lab].append(v)
    if used < 2:
        return {"verdict": "unclear", "heard_as": None, "votes": dict(votes), "reason": "not enough voices"}
    score = {lab: float(np.mean(sorted(v)[:2])) for lab, v in dists.items()}
    ranked = sorted(score, key=score.get)
    winner, margin = ranked[0], score[ranked[1]] - score[ranked[0]]
    out = {"votes": dict(votes), "voices": used, "scores": {k: round(v, 4) for k, v in score.items()}, "margin": round(margin, 4)}
    if winner == "correct":
        return out | {"verdict": "on_target", "heard_as": None}
    return out | {"verdict": "substitution", "heard_as": winner}


def warm(target: dict, item_text: str) -> None:
    """Fetch/compute every template for an item, so the first attempt isn't slow."""
    for lab in labels(target):
        for spk in SPEAKERS:
            _features(target, item_text, lab, spk)
