"""One TTS + one STT call, without printing the key."""
import sys
sys.path.insert(0, sys.argv[1])
from app import compare, content
from app.audio import decode_wav, encode_wav, trim_silence
from app.config import SARVAM_API_KEY
from app.engines import sarvam

print("key set:", bool(SARVAM_API_KEY), "length:", len(SARVAM_API_KEY))
for tid, text, spoken in [("ta-zha", "மழை", "மழை"), ("ta-zha", "மழை", "மளை"), ("hi-sha", "शेर", "सेर")]:
    t = content.target(tid)
    try:
        wav = sarvam.reference_audio(spoken, t["language"], "shubh")
        x = trim_silence(decode_wav(wav))
        stt = sarvam.transcribe(encode_wav(x), t["language"])
        r = compare.check_transcript(text, stt["transcript"], t)
        print(f"{tid} said={spoken} -> transcript={stt['transcript']!r} verdict={r['verdict']} heard={r.get('heard_as')} ({len(x)/16000:.2f}s)")
    except Exception as e:
        print(f"{tid} {spoken}: ERROR {e}")
