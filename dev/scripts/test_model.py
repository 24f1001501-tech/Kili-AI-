import sys
import time
sys.path.insert(0, sys.argv[1])
from pathlib import Path

from app import audio
from app.engines import phonemes

phonemes.start_loading()
t0 = time.time()
while phonemes.status()["status"] == "loading":
    time.sleep(0.5)
print("load:", phonemes.status(), f"{time.time() - t0:.1f}s")

for f in sorted(Path(sys.argv[2]).glob("*.wav")):
    x = audio.decode_wav(f.read_bytes())
    q = audio.assess(x)
    t0 = time.time()
    toks = phonemes.recognize(audio.trim_silence(x))
    print(f.name, q.status, f"{q.duration:.2f}s", "->", " ".join(t["symbol"] for t in toks), f"({time.time() - t0:.2f}s)")
