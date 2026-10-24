"""Local phoneme recognizer: wav2vec2 XLSR-53 fine-tuned on espeak IPA (CommonVoice).

Outputs IPA symbols straight from the audio, without a dictionary, so it does
not 'correct' a mispronounced word into the expected one the way a word-level
recognizer can. Loaded lazily in a background thread; optional.
"""
import json
import logging
import threading

import numpy as np

from ..config import PHONEME_ENGINE, PHONEME_MODEL_ID

log = logging.getLogger(__name__)

_state = {"status": "off" if PHONEME_ENGINE == "off" else "not_loaded", "error": None}
_lock = threading.Lock()
_model = None
_extractor = None
_id2tok: dict[int, str] = {}
_tok2id: dict[str, int] = {}
_blank = 0
FRAME_SEC = 0.02


def status() -> dict:
    return {"status": _state["status"], "model": PHONEME_MODEL_ID, "error": _state["error"]}


def available() -> bool:
    return _state["status"] == "ready"


def vocab() -> set[str]:
    return set(_tok2id)


def start_loading() -> None:
    if _state["status"] != "not_loaded":
        return
    _state["status"] = "loading"
    threading.Thread(target=_load, daemon=True).start()


def _load() -> None:
    global _model, _extractor, _id2tok, _tok2id, _blank
    try:
        import torch  # noqa: F401
        from huggingface_hub import hf_hub_download
        from transformers import Wav2Vec2FeatureExtractor, Wav2Vec2ForCTC

        with open(hf_hub_download(PHONEME_MODEL_ID, "vocab.json"), encoding="utf-8") as f:
            _tok2id = json.load(f)
        _id2tok = {i: t for t, i in _tok2id.items()}
        _blank = _tok2id.get("<pad>", 0)
        _extractor = Wav2Vec2FeatureExtractor.from_pretrained(PHONEME_MODEL_ID)
        _model = Wav2Vec2ForCTC.from_pretrained(PHONEME_MODEL_ID).eval()
        _state["status"] = "ready"
        log.info("Phoneme model ready (%d symbols)", len(_tok2id))
    except ImportError as e:
        _state.update(status="unavailable", error=f"Not installed: {e.name}")
    except Exception as e:  # network, disk, model errors
        log.exception("Phoneme model failed to load")
        _state.update(status="unavailable", error=str(e)[:300])


def hidden(x: np.ndarray, layer: int) -> np.ndarray:
    """Frame embeddings from one transformer layer: mean-removed and unit-length,
    so cosine distance compares sounds rather than voices or microphones."""
    import torch

    with _lock:
        inputs = _extractor(x, sampling_rate=16000, return_tensors="pt")
        with torch.inference_mode():
            out = _model(inputs.input_values, output_hidden_states=True)
    v = out.hidden_states[layer][0].numpy()
    v = v - v.mean(axis=0, keepdims=True)
    return v / (np.linalg.norm(v, axis=1, keepdims=True) + 1e-8)


def recognize(x: np.ndarray, top_k: int = 6) -> list[dict]:
    """Greedy CTC decode. Each token carries its frame span and the average
    probability of the top competing symbols over that span."""
    import torch

    if not available():
        raise RuntimeError("Phoneme model is not loaded")
    with _lock:
        inputs = _extractor(x, sampling_rate=16000, return_tensors="pt")
        with torch.inference_mode():
            logits = _model(inputs.input_values).logits[0]
    probs = torch.softmax(logits, dim=-1).numpy()
    best = probs.argmax(axis=-1)

    tokens: list[dict] = []
    prev = -1
    for t, idx in enumerate(best):
        idx = int(idx)
        if idx != prev and idx != _blank:
            tokens.append({"symbol": _id2tok[idx], "start": t, "end": t + 1})
        elif idx == prev and idx != _blank and tokens:
            tokens[-1]["end"] = t + 1
        prev = idx

    special = {i for t, i in _tok2id.items() if t.startswith("<") or t in ("|", " ")}
    out = []
    for tok in tokens:
        if _tok2id.get(tok["symbol"]) in special:
            continue
        # widen the span by one frame each side: CTC spikes are narrow
        s, e = max(0, tok["start"] - 1), min(len(probs), tok["end"] + 1)
        span = probs[s:e].copy()
        span[:, _blank] = 0
        avg = span.mean(axis=0)
        avg = avg / max(avg.sum(), 1e-9)
        top = np.argsort(avg)[::-1][:top_k]
        out.append({
            # the multilingual vocabulary carries tone digits (e.g. "a5"); they mean nothing for Tamil/Hindi
            "symbol": tok["symbol"].rstrip("0123456789") or tok["symbol"],
            "time": round(tok["start"] * FRAME_SEC, 2),
            "alts": {_id2tok[int(i)]: round(float(avg[i]), 3) for i in top if int(i) not in special},
        })
    return out
