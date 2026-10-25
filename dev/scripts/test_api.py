"""End-to-end API test against a running server, using English TTS clips as stand-ins."""
import sys
from pathlib import Path

import httpx

BASE = "http://127.0.0.1:8000"
WAV = Path(sys.argv[1])
c = httpx.Client(base_url=BASE, timeout=60)

print("health", c.get("/api/health").json())
u = c.post("/api/profiles", json={"display_name": "Test Hindi", "preferred_language": "hi-IN", "practice_goal": "श", "feedback_style": "brief"}).json()
H = {"X-Profile-Id": str(u["id"])}
print("profile", u["id"], u["preferred_language"])

# unauthorised access is rejected
print("no header ->", c.get("/api/plan").status_code)

# baseline with the 6 items; answer every item with the same clip
items = c.get("/api/baseline", headers=H).json()["items"]
s = c.post("/api/sessions", headers=H, json={"kind": "baseline"}).json()
for it in items:
    clip = {"hi-sha": "sahm.wav", "hi-ra": "rail.wav", "hi-kha": "kahna.wav"}[it["speech_target_id"]]
    r = c.post("/api/attempts", headers=H, data={"session_id": s["id"], "speech_target_id": it["speech_target_id"], "item_text": it["text"]},
               files={"audio": (clip, (WAV / clip).read_bytes(), "audio/wav")}).json()
    a = r["analysis"]
    print(f"  baseline {it['speech_target_id']} {it['text']}: {a['status']} {a['outcome']} heard={a['heard_as']} ipa={a['phonemes']}")
b = c.post(f"/api/sessions/{s['id']}/complete", headers=H).json()["baseline"]
print("ranked", b["ranked"], {k: (v["plan_status"], v["start_level"]) for k, v in b["summary"].items()})

# practice श on the plan's own items
c.put("/api/plan/active", headers=H, json={"speech_target_id": "hi-sha"})
s = c.post("/api/sessions", headers=H, json={"kind": "practice"}).json()
for clip, text in [("sahm.wav", "शाम"), ("shahm.wav", "शाम"), ("shahm.wav", "शाम"), ("shehr.wav", "शेर"), ("desh.wav", "देश")]:
    r = c.post("/api/attempts", headers=H, data={"session_id": s["id"], "speech_target_id": "hi-sha", "item_text": text},
               files={"audio": (clip, (WAV / clip).read_bytes(), "audio/wav")}).json()
    a, fb, pu = r["analysis"], r["feedback"], r["plan_update"]
    print(f"  {clip:10} {text}: {a['status']} {a['outcome']} heard={a['heard_as']} conf={a['confidence']} ipa={a['phonemes']}")
    print(f"     tip: {fb['guidance_text'][:90]} | next={fb['next_action']} | plan={pu and pu['action']} {pu and pu['window']}")
plan = c.get("/api/plan", headers=H).json()
print("plan level", plan["active"]["current_level"], "next", plan["next_item"]["text"], plan["next_item"]["reason"])

# bad inputs
print("bad item ->", c.post("/api/attempts", headers=H, data={"session_id": s["id"], "speech_target_id": "hi-sha", "item_text": "hello"},
                            files={"audio": ("x.wav", b"RIFF", "audio/wav")}).status_code)
r = c.post("/api/attempts", headers=H, data={"session_id": s["id"], "speech_target_id": "hi-sha", "item_text": "शाम"},
           files={"audio": ("x.wav", b"not a wav", "audio/wav")}).json()
print("garbage audio ->", r["analysis"]["status"], "|", r["feedback"]["guidance_text"])
other = c.post("/api/profiles", json={"display_name": "Other", "preferred_language": "hi-IN"}).json()
print("other user's session ->", c.post(f"/api/sessions/{s['id']}/complete", headers={"X-Profile-Id": str(other["id"])}).status_code)
p = c.get("/api/progress", headers=H).json()
print("progress", p["per_target"], p["levels"])
print("delete ->", c.delete("/api/me", headers=H).status_code, c.get("/api/me", headers=H).status_code)
c.delete("/api/me", headers={"X-Profile-Id": str(other["id"])})
