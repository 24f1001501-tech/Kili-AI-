"""Make 16 kHz WAV clips with Sarvam TTS for the screenshot run (correct + mixed-up words)."""
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, sys.argv[1])
from app.audio import decode_wav, encode_wav, trim_silence
from app.engines import sarvam

OUT = Path(sys.argv[2])
OUT.mkdir(exist_ok=True)
TEXTS = {
    "ta-IN": ["மழை", "மளை", "பழம்", "பலம்", "பள்ளி", "வாள்", "மரம்", "ஊர்", "ழா", "ளா", "ழி", "ளி",
              "ஏழு", "ஏளு", "கோழி", "கோளி"],
    "hi-IN": ["शा", "सा", "शी", "सी", "शेर", "सेर", "रेल", "घर", "खाना", "काना", "खेल", "शाम"],
}
index = {}
for lang, texts in TEXTS.items():
    for t in texts:
        name = hashlib.sha1(t.encode()).hexdigest()[:10] + ".wav"
        x = trim_silence(decode_wav(sarvam.reference_audio(t, lang, "kavitha")))
        (OUT / name).write_bytes(encode_wav(x))
        index[t] = name
(OUT / "index.json").write_text(json.dumps(index, ensure_ascii=False), encoding="utf-8")
print(len(index), "clips")
