"""Prototype: classify correct vs mix-up by comparing against Sarvam-TTS templates (leave-one-voice-out)."""
import sys
import time
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
BLANK = phonemes._blank
SPEAKERS = ["shubh", "kavitha", "anand", "priya"]


def feats(x):
    inp = extractor(x, sampling_rate=16000, return_tensors="pt")
    with torch.inference_mode():
        out = model(inp.input_values, output_hidden_states=True)
    post = torch.softmax(out.logits[0], -1).numpy()
    keep = post[:, BLANK] < 0.7
    if keep.sum() < 3:
        keep[:] = True
    h = {L: out.hidden_states[L][0].numpy() for L in (12, 18)}
    return {"post": post[keep], **{f"h{L}": v / np.linalg.norm(v, axis=1, keepdims=True) for L, v in h.items()}}


def dtw(a, b, kind):
    if kind == "post":
        d = -np.log(np.clip(a @ b.T, 1e-6, None))
    else:
        d = 1 - a @ b.T
    n, m = d.shape
    D = np.full((n + 1, m + 1), np.inf)
    D[0, 0] = 0
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            D[i, j] = d[i - 1, j - 1] + min(D[i - 1, j], D[i, j - 1], D[i - 1, j - 1])
    return D[n, m] / (n + m)


tests = [("ta-zha", ["மழை", "பழம்", "கோழி", "ஏழு"]), ("ta-La", ["பள்ளி", "குளம்", "வாள்"]),
         ("hi-sha", ["शेर", "शाम", "देश"]), ("hi-kha", ["खाना", "खेल", "सुख"]), ("hi-ra", ["रेल", "घर", "रोटी"])]
for tid, words in tests:
    t = content.target(tid)
    letter = g2p.normalize(t["letter"])
    labels = ["correct"] + [g2p.normalize(c) for c in t["confusions"]]
    stats = {k: [0, 0] for k in ("post", "h12", "h18")}
    for w in words:
        w = g2p.normalize(w)
        bank = {}
        for lab in labels:
            spoken = w if lab == "correct" else w.replace(letter, lab)
            for spk in SPEAKERS:
                try:
                    bank[(lab, spk)] = feats(trim_silence(decode_wav(sarvam.reference_audio(spoken, t["language"], spk))))
                except Exception as e:
                    print("  tts fail", spk, e)
        for (lab, spk), f in bank.items():
            for kind in stats:
                scores = {}
                for (lab2, spk2), g in bank.items():
                    if spk2 == spk:
                        continue
                    scores.setdefault(lab2, []).append(dtw(f[kind], g[kind], kind))
                pred = min(scores, key=lambda k: np.mean(sorted(scores[k])[:2]))
                stats[kind][0] += pred == lab
                stats[kind][1] += 1
    print(tid, {k: f"{a}/{n} ({100 * a // n}%)" for k, (a, n) in stats.items()}, "chance", f"{100 // len(labels)}%")
