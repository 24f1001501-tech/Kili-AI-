import sys
sys.path.insert(0, sys.argv[1])
from app import g2p, compare, content

for text, lang in [("வாழைப்பழம்", "ta-IN"), ("பள்ளி", "ta-IN"), ("गरम", "hi-IN"), ("लिखना", "hi-IN"), ("शहर", "hi-IN"),
                   ("खिड़की खोलकर ताज़ी हवा आने दो", "hi-IN"), ("रखना", "hi-IN")]:
    print(text, " ".join(p for p, _ in g2p.to_ipa(text, lang)))

cases = [
    ("ta-zha", "மழை", "மழை"),      # correct
    ("ta-zha", "மழை", "மளை"),      # ழ -> ள
    ("ta-zha", "வாழைப்பழம்", "வாலைப்பலம்"),  # ழ -> ல twice
    ("ta-zha", "பழம்", "நாய்"),      # different word
    ("ta-ra", "மரம்", "மறம்"),      # ற accepted
    ("hi-sha", "शेर", "सेर"),        # श -> स
    ("hi-kha", "खाना", "काना"),      # ख -> क
    ("hi-ra", "घर", "घर"),
    ("hi-ra", "रोटी", "लोटी"),
    ("hi-ra", "रोटी", "ड़ोटी"),
]
for tid, item, heard in cases:
    r = compare.check_transcript(item, heard, content.target(tid))
    print(tid, item, "->", heard, ":", r["verdict"], r.get("heard_as"), r["similarity"], r.get("reason", ""))

t = content.target("ta-zha")
vocab = {"m", "a", "ɭ", "ɻ", "l", "j", "i", "ai"}
for seq in ("m a ɭ ai", "m a ɻ ai", "m a l ai"):
    fake = [{"symbol": s, "alts": {s: 0.7, "ɭ": 0.2}} for s in seq.split()]
    r = compare.check_phonemes("மழை", fake, t, vocab)
    print("phon", seq, ":", r["verdict"], r.get("heard_as"), r["checks"][0]["p_target"] if r["checks"] else None)
