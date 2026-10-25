"""Is it TTS or STT that 'fixes' mix-ups? Try STT models/modes and the phoneme model on the same clips."""
import sys
import time
sys.path.insert(0, sys.argv[1])
import httpx

from app.audio import decode_wav, encode_wav, trim_silence
from app.config import SARVAM_API_KEY
from app.engines import phonemes, sarvam

phonemes.start_loading()
while phonemes.status()["status"] in ("loading", "not_loaded"):
    time.sleep(0.5)

CONFIGS = [("saaras:v3", "verbatim"), ("saaras:v3", "transcribe"), ("saaras:v3", "translit"), ("saaras:v4", None), ("saarika:v2.5", None)]
clips = [("ta-IN", "மழை"), ("ta-IN", "மளை"), ("ta-IN", "மலை"), ("ta-IN", "பழம்"), ("ta-IN", "பளம்"),
         ("hi-IN", "शेर"), ("hi-IN", "सेर"), ("hi-IN", "खाना"), ("hi-IN", "काना")]
for lang, text in clips:
    wav = encode_wav(trim_silence(decode_wav(sarvam.reference_audio(text, lang, "shubh"))))
    ipa = " ".join(t["symbol"] for t in phonemes.recognize(decode_wav(wav)))
    outs = []
    for model, mode in CONFIGS:
        data = {"model": model, "language_code": lang}
        if mode:
            data["mode"] = mode
        r = httpx.post("https://api.sarvam.ai/speech-to-text", headers={"api-subscription-key": SARVAM_API_KEY},
                       data=data, files={"file": ("a.wav", wav, "audio/wav")}, timeout=60)
        outs.append(f"{model}/{mode}: {r.json().get('transcript') if r.status_code == 200 else r.status_code}")
    print(f"SAID {text:8} | phonemes: {ipa:14} | " + " | ".join(outs))
