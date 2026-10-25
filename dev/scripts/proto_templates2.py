"""Template matching v2: paired same-voice contrast + voting; compare feature layers. Leave-one-voice-out."""
import sys
import time
from collections import Counter
sys.path.insert(0, sys.argv[1])
import numpy as np
import torch

from app import content, g2p
from app.audio import decode_wav, trim_silence
from app.engines import phonemes, sarvam

phonemes.start_loading()
while phonemes.status()["status"] in ("loading", "not_loaded"):
    time.sleep(0.5)
model, extractor = phonemes._model, phonemes._extractor
SPEAKERS = ["shubh", "kavitha", "anand", "priya", "rahul", "shruti"]
LAYERS = (8, 12, 15, 18)


def tts(text, lang, spk):
    for i in range(7):
        try:
            return sarvam.reference_audio(text, lang, spk)
        except sarvam.SarvamError as e:
            if "rate_limit" in str(e):
                time.sleep(2 + 2 ** i)
                continue
            raise


def feats(x):
    inp = extractor(x, sampling_rate=16000, return_tensors="pt")
    with torch.inference_mode():
        out = model(inp.input_values, output_hidden_states=True)
    res = {}
    for L in LAYERS:
        v = out.hidden_states[L][0].numpy()
        v = v - v.mean(0, keepdims=True)  # per-utterance mean removal (speaker/channel)
        res[L] = v / (np.linalg.norm(v, axis=1, keepdims=True) + 1e-8)
    return res


def dtw(a, b):
    d = 1 - a @ b.T
    n, m = d.shape
    D = np.full((n + 1, m + 1), np.inf)
    D[0, 0] = 0
    for i in range(1, n + 1):
        Di, Dp, di = D[i], D[i - 1], d[i - 1]
        for j in range(1, m + 1):
            Di[j] = di[j - 1] + min(Dp[j], Di[j - 1], Dp[j - 1])
    return D[n, m] / (n + m)


tests = [("ta-zha", ["மழை", "பழம்", "கோழி", "ஏழு"]), ("ta-La", ["பள்ளி", "குளம்", "வாள்"]), ("ta-ra", ["மரம்", "அரிசி", "கரை"]),
         ("hi-sha", ["शेर", "शाम", "देश"]), ("hi-kha", ["खाना", "खेल", "सुख"]), ("hi-ra", ["रेल", "घर", "रोटी"])]
for tid, words in tests:
    t = content.target(tid)
    letter = g2p.normalize(t["letter"])
    labels = ["correct"] + [g2p.normalize(c) for c in t["confusions"] if c not in t.get("accept", [])]
    res = {(L, m): [0, 0] for L in LAYERS for m in ("best2", "paired")}
    for w in words:
        w = g2p.normalize(w)
        bank = {}
        for lab in labels:
            spoken = w if lab == "correct" else w.replace(letter, lab)
            for spk in SPEAKERS:
                bank[(lab, spk)] = feats(trim_silence(decode_wav(tts(spoken, t["language"], spk))))
        for (lab, spk), f in bank.items():
            for L in LAYERS:
                d = {(l2, s2): dtw(f[L], g[L]) for (l2, s2), g in bank.items() if s2 != spk}
                per_lab = {l2: np.mean(sorted(v for (l, s), v in d.items() if l == l2)[:2]) for l2 in labels}
                p1 = min(per_lab, key=per_lab.get)
                votes = Counter(min(labels, key=lambda l2: d[(l2, s2)]) for s2 in SPEAKERS if s2 != spk)
                p2 = votes.most_common(1)[0][0]
                for m_, p in (("best2", p1), ("paired", p2)):
                    res[(L, m_)][0] += p == lab
                    res[(L, m_)][1] += 1
    total = next(iter(res.values()))[1]
    print(tid, f"chance {100 // len(labels)}%", " ".join(f"L{L}/{m}:{100 * a // c}%" for (L, m), (a, c) in res.items()), f"n={total}", flush=True)
