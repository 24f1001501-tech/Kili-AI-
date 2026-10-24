"""Sarvam AI speech-to-text and text-to-speech (https://docs.sarvam.ai)."""
import base64
import hashlib
import json
import time

import httpx

from ..config import REFERENCE_DIR, SARVAM_API_KEY, SARVAM_STT_MODEL, SARVAM_TTS_MODEL, SARVAM_TTS_SPEAKER

STT_URL = "https://api.sarvam.ai/speech-to-text"
TTS_URL = "https://api.sarvam.ai/text-to-speech"


class SarvamError(RuntimeError):
    pass


def available() -> bool:
    return bool(SARVAM_API_KEY)


def _headers() -> dict:
    return {"api-subscription-key": SARVAM_API_KEY}


def _post(url: str, **kwargs) -> httpx.Response:
    """POST with backoff on rate limits and transient gateway errors."""
    for attempt in range(6):
        with httpx.Client(timeout=45) as client:
            resp = client.post(url, headers=_headers(), **kwargs)
        if resp.status_code not in (429, 502, 503, 504) or attempt == 5:
            return resp
        time.sleep(min(20, 1.5 * 2 ** attempt))
    return resp


def _raise_for(resp: httpx.Response) -> None:
    if resp.status_code == 200:
        return
    try:
        err = resp.json().get("error", {})
        msg = f"{err.get('code', resp.status_code)}: {err.get('message', '')}"
    except (json.JSONDecodeError, AttributeError):
        msg = f"HTTP {resp.status_code}"
    raise SarvamError(msg)


def transcribe(wav: bytes, language: str, keyterms: list[str] | None = None) -> dict:
    """Verbatim transcript in native script.

    saaras:v3 with mode=verbatim is preferred: it does less 'autocorrecting' of
    mispronounced words than the default transcribe mode, which matters here.
    """
    data = {"model": SARVAM_STT_MODEL, "language_code": language}
    if SARVAM_STT_MODEL == "saaras:v3":
        data["mode"] = "verbatim"
    if keyterms and SARVAM_STT_MODEL == "saaras:v4":
        data["keyterms"] = json.dumps(keyterms[:50], ensure_ascii=False)
    files = {"file": ("attempt.wav", wav, "audio/wav")}
    resp = _post(STT_URL, data=data, files=files)
    _raise_for(resp)
    body = resp.json()
    return {"transcript": body.get("transcript", ""), "language_code": body.get("language_code"),
            "model": SARVAM_STT_MODEL}


def reference_audio(text: str, language: str, speaker: str | None = None) -> bytes:
    """TTS recording, cached on disk so each phrase is paid for once."""
    speaker = SARVAM_TTS_SPEAKER if speaker is None else speaker
    key = hashlib.sha1(f"{SARVAM_TTS_MODEL}|{speaker}|{language}|{text}".encode()).hexdigest()
    path = REFERENCE_DIR / f"{key}.wav"
    if path.exists():
        return path.read_bytes()
    payload = {"text": text, "language_code": language, "model": SARVAM_TTS_MODEL, "pace": 0.8,
               "speech_sample_rate": 22050}
    if speaker:
        payload["speaker"] = speaker
    resp = _post(TTS_URL, json=payload)
    _raise_for(resp)
    audio = base64.b64decode(resp.json()["audios"][0])
    path.write_bytes(audio)
    return audio
