"""Adaptive plan test: on-target attempts at the plan's own items should level up; misses should level down."""
import sys
from pathlib import Path

import httpx

WAV = Path(sys.argv[1])
GOOD = {"शा": "shah", "शी": "shee", "शू": "shoo", "शेर": "shehr", "शाम": "shahm", "देश": "desh", "शहर": "shahar",
        "आशा": "aasha", "पशु": "pashoo", "निशान": "nishahn"}
BAD = {"शा": "sah", "शी": "see", "शू": "soo", "शेर": "sehr", "शाम": "sahm", "देश": "dess", "शहर": "sahar",
       "आशा": "aasa", "पशु": "pasoo", "निशान": "nisahn"}
c = httpx.Client(base_url="http://127.0.0.1:8000", timeout=60)
u = c.post("/api/profiles", json={"display_name": "Plan test", "preferred_language": "hi-IN"}).json()
H = {"X-Profile-Id": str(u["id"])}
c.put("/api/plan/active", headers=H, json={"speech_target_id": "hi-sha"})
s = c.post("/api/sessions", headers=H, json={"kind": "practice"}).json()


def attempt(good: bool):
    plan = c.get("/api/plan?advance=true", headers=H).json()
    item = plan["next_item"]
    clip = (GOOD if good else BAD)[item["text"]] + ".wav"
    r = c.post("/api/attempts", headers=H, data={"session_id": s["id"], "speech_target_id": "hi-sha", "item_text": item["text"]},
               files={"audio": (clip, (WAV / clip).read_bytes(), "audio/wav")}).json()
    a, pu = r["analysis"], r["plan_update"]
    print(f"L{plan['active']['current_level']} {item['text']:<5} {clip:11} -> {a['status']:<18} {a['outcome']:<12} heard={a['heard_as']} "
          f"ipa={a['phonemes']:<10} | {pu and pu['action']} {pu and pu['message'] or ''}")


for good in [True] * 6 + [False] * 4:
    attempt(good)
c.delete("/api/me", headers=H)
