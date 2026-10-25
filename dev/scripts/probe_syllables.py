"""Does Sarvam STT transcribe isolated syllables faithfully (no word to autocorrect toward)?"""
import sys
import time
sys.path.insert(0, sys.argv[1])
from app.audio import decode_wav, encode_wav, trim_silence
from app.engines import sarvam

def call(fn, *a):
    for i in range(6):
        try:
            return fn(*a)
        except sarvam.SarvamError as e:
            if "rate_limit" in str(e):
                time.sleep(2 + 2 ** i)
                continue
            raise

sets = [("ta-IN", ["ழை", "ளை", "லை", "யை"]), ("ta-IN", ["ழா", "ளா", "லா", "யா"]), ("ta-IN", ["ழம்", "ளம்", "லம்"]),
        ("ta-IN", ["ரா", "லா", "யா"]), ("hi-IN", ["शे", "से"]), ("hi-IN", ["खा", "का"]), ("hi-IN", ["रे", "ले"])]
ok = n = 0
for lang, sylls in sets:
    row = []
    for s in sylls:
        for spk in ("shubh", "kavitha"):
            wav = encode_wav(trim_silence(decode_wav(call(sarvam.reference_audio, s, lang, spk))))
            tr = call(sarvam.transcribe, wav, lang)["transcript"]
            hit = s[0] in tr[:2]
            ok += hit; n += 1
            row.append(f"{s}/{spk[:2]}→{tr!r}{'' if hit else ' ✗'}")
            time.sleep(0.6)
    print(" | ".join(row))
print(f"first letter right: {ok}/{n}")
