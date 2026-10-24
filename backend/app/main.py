import json
import logging
import threading
import time
import uuid
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from typing import Literal

from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, Request, Response, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import analysis, calibration, coach, content, planner
from .config import ALLOW_PROFILE_LIST, AUDIO_DIR, FRONTEND_DIR, MAX_UPLOAD_BYTES, RATE_LIMIT_PER_MIN
from .db import init_db, new_key, now, row, rows, tx
from .engines import phonemes, sarvam, templates

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


@asynccontextmanager
async def lifespan(_app):
    init_db()
    phonemes.start_loading()
    yield


app = FastAPI(title="SayBetter AI", version="0.1.0", lifespan=lifespan)

Language = Literal["ta-IN", "hi-IN"]
FeedbackStyle = Literal["brief", "step_by_step", "encouraging"]


# ---------- profiles (local MVP: no passwords; see README) ----------

class ProfileIn(BaseModel):
    display_name: str = Field(min_length=1, max_length=60)
    preferred_language: Language
    practice_goal: str = Field(default="", max_length=300)
    feedback_style: FeedbackStyle = "step_by_step"
    keep_audio: bool = False


class ProfilePatch(BaseModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=60)
    practice_goal: str | None = Field(default=None, max_length=300)
    feedback_style: FeedbackStyle | None = None
    keep_audio: bool | None = None


def current_user(x_profile_key: str | None = Header(default=None)) -> dict:
    if not x_profile_key:
        raise HTTPException(401, "No profile selected")
    with tx() as conn:
        user = row(conn.execute("SELECT * FROM users WHERE api_key = ?", (x_profile_key,)).fetchone())
    if not user:
        raise HTTPException(401, "Profile not found")
    return user


_hits: dict[str, deque] = defaultdict(deque)
_hits_lock = threading.Lock()


def rate_limited(request: Request) -> None:
    """Simple per-visitor limit for endpoints that spend Sarvam credit or create data."""
    ip = (request.headers.get("x-forwarded-for") or (request.client.host if request.client else "?")).split(",")[0].strip()
    t = time.monotonic()
    with _hits_lock:
        q = _hits[ip]
        while q and t - q[0] > 60:
            q.popleft()
        if len(q) >= RATE_LIMIT_PER_MIN:
            raise HTTPException(429, "Too many requests. Please wait a minute and try again.")
        q.append(t)


@app.get("/api/health")
def health():
    cal = calibration.load()
    return {"ok": True, "engines": {"sarvam": {"configured": sarvam.available()}, "phonemes": phonemes.status()},
            "calibration": {"available": bool(cal), "generated_at": cal and cal["generated_at"], "clips": cal and cal["clips"]}}


@app.get("/api/accuracy")
def accuracy():
    """Measured accuracy per sound and engine (from tools/calibrate.py)."""
    s = calibration.summary()
    if not s:
        raise HTTPException(404, "No accuracy measurements yet. Run: python -m tools.calibrate")
    names = {t["id"]: t["name"] for t in content.targets()}
    return s | {"names": names}


@app.get("/api/languages")
def languages():
    return list(content.LANGUAGES.values())


@app.get("/api/profiles")
def list_profiles():
    """Local convenience only: lets someone on this computer switch profiles."""
    if not ALLOW_PROFILE_LIST:
        return []
    with tx() as conn:
        return rows(conn.execute("SELECT id, display_name, preferred_language, is_demo, api_key FROM users ORDER BY id"))


@app.post("/api/profiles", status_code=201, dependencies=[Depends(rate_limited)])
def create_profile(body: ProfileIn):
    with tx() as conn:
        cur = conn.execute(
            "INSERT INTO users (display_name, preferred_language, practice_goal, feedback_style, consent_settings, api_key, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (body.display_name.strip(), body.preferred_language, body.practice_goal.strip(), body.feedback_style,
             json.dumps({"keep_audio": body.keep_audio}), new_key(), now()))
        user = row(conn.execute("SELECT * FROM users WHERE id = ?", (cur.lastrowid,)).fetchone())
        planner.ensure_plans(conn, user)
    return user


@app.post("/api/profiles/demo", status_code=201, dependencies=[Depends(rate_limited)])
def create_demo_profile(language: Language = "ta-IN"):
    """A separate, clearly marked profile. Falls back to scripted results only
    when real analysis is unavailable, and every such result is labelled."""
    with tx() as conn:
        cur = conn.execute(
            "INSERT INTO users (display_name, preferred_language, practice_goal, feedback_style, is_demo, api_key, created_at) "
            "VALUES (?, ?, ?, 'encouraging', 1, ?, ?)",
            ("Demo learner", language, "Try out SayBetter", new_key(), now()))
        user = row(conn.execute("SELECT * FROM users WHERE id = ?", (cur.lastrowid,)).fetchone())
        planner.ensure_plans(conn, user)
    return user


@app.get("/api/me")
def me(user=Depends(current_user)):
    return user


@app.patch("/api/me")
def update_me(body: ProfilePatch, user=Depends(current_user)):
    consent = dict(user["consent_settings"])
    if body.keep_audio is not None:
        consent["keep_audio"] = body.keep_audio
    with tx() as conn:
        conn.execute("UPDATE users SET display_name = COALESCE(?, display_name), practice_goal = COALESCE(?, practice_goal), "
                     "feedback_style = COALESCE(?, feedback_style), consent_settings = ? WHERE id = ?",
                     (body.display_name, body.practice_goal, body.feedback_style, json.dumps(consent), user["id"]))
        return row(conn.execute("SELECT * FROM users WHERE id = ?", (user["id"],)).fetchone())


@app.delete("/api/me", status_code=204)
def delete_me(user=Depends(current_user)):
    with tx() as conn:
        paths = [r[0] for r in conn.execute("SELECT audio_path FROM practice_attempts WHERE user_id = ? AND audio_path IS NOT NULL", (user["id"],))]
        conn.execute("DELETE FROM users WHERE id = ?", (user["id"],))
    for p in paths:
        (AUDIO_DIR / p).unlink(missing_ok=True)
    return Response(status_code=204)


# ---------- content ----------

def _public_target(t: dict) -> dict:
    return {k: t[k] for k in ("id", "language", "letter", "roman", "ipa", "name", "diagram", "summary", "steps")} | {
        "confusions": {k: {"diagram": v["diagram"], "tip": v["tip"]} for k, v in t["confusions"].items()},
        "levels": {int(k): v for k, v in t["items"].items()},
    }


@app.get("/api/targets")
def list_targets(language: Language | None = None):
    return {"level_names": content.level_names(), "targets": [_public_target(t) for t in content.targets(language)]}


@app.get("/api/targets/{target_id}")
def get_target(target_id: str):
    t = content.target(target_id)
    if not t:
        raise HTTPException(404, "Unknown target")
    return _public_target(t) | {"level_names": content.level_names()}


@app.get("/api/reference", dependencies=[Depends(rate_limited)])
def reference(target_id: str, text: str):
    t = content.target(target_id)
    if not t or not content.find_item(target_id, text):
        raise HTTPException(404, "Unknown item")
    if not sarvam.available():
        raise HTTPException(503, "Reference audio needs a Sarvam API key")
    try:
        audio = sarvam.reference_audio(text, t["language"])
    except Exception as e:
        raise HTTPException(502, f"Reference audio failed: {e}")
    return Response(audio, media_type="audio/wav", headers={"Cache-Control": "max-age=86400"})


# ---------- sessions, attempts, plan ----------

class SessionIn(BaseModel):
    kind: Literal["baseline", "practice"]


@app.get("/api/baseline")
def baseline_items(user=Depends(current_user)):
    return {"items": content.baseline_items(user["preferred_language"])}


@app.post("/api/sessions", status_code=201)
def start_session(body: SessionIn, user=Depends(current_user)):
    with tx() as conn:
        plan = planner.active_plan(conn, user["id"])
        cur = conn.execute("INSERT INTO practice_sessions (user_id, learning_plan_id, kind, started_at) VALUES (?, ?, ?, ?)",
                           (user["id"], plan["id"] if plan and body.kind == "practice" else None, body.kind, now()))
        return {"id": cur.lastrowid, "kind": body.kind}


def _own_session(conn, session_id: int, user_id: int) -> dict:
    s = row(conn.execute("SELECT * FROM practice_sessions WHERE id = ? AND user_id = ?", (session_id, user_id)).fetchone())
    if not s:
        raise HTTPException(404, "Session not found")
    return s


@app.post("/api/sessions/{session_id}/complete")
def complete_session(session_id: int, user=Depends(current_user)):
    with tx() as conn:
        s = _own_session(conn, session_id, user["id"])
        conn.execute("UPDATE practice_sessions SET completed_at = ? WHERE id = ?", (now(), session_id))
        if s["kind"] == "baseline":
            return {"baseline": planner.apply_baseline(conn, user, session_id)}
        n = conn.execute("SELECT COUNT(*) FROM practice_attempts WHERE session_id = ?", (session_id,)).fetchone()[0]
        return {"attempts": n}


@app.post("/api/attempts", status_code=201, dependencies=[Depends(rate_limited)])
async def submit_attempt(session_id: int = Form(...), speech_target_id: str = Form(...), item_text: str = Form(...),
                         audio: UploadFile = File(...), user=Depends(current_user)):
    target = content.target(speech_target_id)
    found = content.find_item(speech_target_id, item_text)
    if not target or not found or target["language"] != user["preferred_language"]:
        raise HTTPException(422, "Unknown practice item for this profile")
    level, _item = found
    data = await audio.read(MAX_UPLOAD_BYTES + 1)
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, "Recording is too large")
    if not data:
        raise HTTPException(422, "Empty recording")

    with tx() as conn:
        session = _own_session(conn, session_id, user["id"])
        prior = conn.execute("SELECT COUNT(*) FROM practice_attempts WHERE user_id = ? AND speech_target_id = ?",
                             (user["id"], speech_target_id)).fetchone()[0]

    # Slow network/model work happens outside the DB transaction.
    result = analysis.analyze(data, item_text, target, allow_demo=bool(user["is_demo"]), demo_attempt_no=prior)
    fb = coach.feedback(result, target, user["feedback_style"], prior)

    audio_path = None
    if user["consent_settings"].get("keep_audio") and result["status"] != "audio_unusable":
        audio_path = f"{user['id']}_{uuid.uuid4().hex}.wav"
        (AUDIO_DIR / audio_path).write_bytes(data)

    with tx() as conn:
        cur = conn.execute(
            "INSERT INTO practice_attempts (session_id, user_id, speech_target_id, level, item_text, status, outcome, heard_as, "
            "transcript, phonemes, analysis_result, confidence, method, audio_quality_status, audio_path, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (session_id, user["id"], speech_target_id, level, item_text, result["status"], result["outcome"], result["heard_as"],
             result["transcript"], result["phonemes"], json.dumps(result, ensure_ascii=False), result["confidence"],
             "+".join(result["method"]) or "none", (result["quality"] or {}).get("status", "invalid"), audio_path, now()))
        attempt_id = cur.lastrowid
        conn.execute("INSERT INTO feedback_records (attempt_id, feedback_type, guidance_text, next_action, created_at) VALUES (?, ?, ?, ?, ?)",
                     (attempt_id, fb["feedback_type"], fb["guidance_text"], fb["next_action"], now()))
        if result["status"] in planner.COUNTED:
            conn.execute("INSERT INTO progress_records (user_id, speech_target_id, metric, value, note, recorded_at) VALUES (?, ?, 'on_target', ?, ?, ?)",
                         (user["id"], speech_target_id, 1.0 if result["outcome"] == "on_target" else 0.0, item_text, now()))

        decision = None
        plan = row(conn.execute("SELECT * FROM learning_plans WHERE user_id = ? AND speech_target_id = ?",
                                (user["id"], speech_target_id)).fetchone())
        if session["kind"] == "practice" and plan and result["status"] in planner.COUNTED:
            decision = planner.after_attempt(conn, plan)
        if decision and decision["action"] in ("level_up", "level_down", "mastered"):
            fb["next_action"] = "continue"
    return {"attempt_id": attempt_id, "level": level, "item_text": item_text, "analysis": result, "feedback": fb, "plan_update": decision}


def _warm_templates(target_id: str, text: str) -> None:
    """Prepare the Sarvam voice templates for the next item while the learner reads it."""
    t = content.target(target_id)
    if t and templates.available() and templates.supports(t, text):
        threading.Thread(target=lambda: _safe_warm(t, text), daemon=True).start()


def _safe_warm(t: dict, text: str) -> None:
    try:
        templates.warm(t, text)
    except Exception as e:
        logging.getLogger(__name__).warning("Template warm-up failed for %s: %s", text, e)


@app.get("/api/plan")
def get_plan(advance: bool = False, user=Depends(current_user)):
    """advance=true skips the 'retry the same item' rule (learner chose Continue)."""
    with tx() as conn:
        planner.ensure_plans(conn, user)
        ps = planner.plans(conn, user["id"])
        active = next((p for p in ps if p["status"] == "active"), None)
        nxt = None
        if active and advance:
            nxt = planner.next_item(conn, user["id"], active, None)
        elif active:
            last = row(conn.execute(
                "SELECT a.item_text, a.level, f.next_action FROM practice_attempts a JOIN feedback_records f ON f.attempt_id = a.id "
                "JOIN practice_sessions s ON s.id = a.session_id WHERE a.user_id = ? AND a.speech_target_id = ? AND s.kind = 'practice' "
                "ORDER BY a.id DESC LIMIT 1", (user["id"], active["speech_target_id"])).fetchone())
            nxt = planner.next_item(conn, user["id"], active, last)
    if nxt and active:
        _warm_templates(active["speech_target_id"], nxt["text"])
    return {"baseline_done": bool(user["baseline_done"]), "active": active, "plans": ps, "next_item": nxt,
            "level_names": content.level_names()}


class ActiveIn(BaseModel):
    speech_target_id: str


@app.put("/api/plan/active")
def choose_target(body: ActiveIn, user=Depends(current_user)):
    t = content.target(body.speech_target_id)
    if not t or t["language"] != user["preferred_language"]:
        raise HTTPException(422, "Unknown target for this profile")
    with tx() as conn:
        planner.ensure_plans(conn, user)
        planner.set_active(conn, user["id"], body.speech_target_id)
    return get_plan(user)


@app.get("/api/attempts")
def attempt_history(speech_target_id: str | None = None, limit: int = 50, user=Depends(current_user)):
    q = ("SELECT a.id, a.speech_target_id, a.level, a.item_text, a.status, a.outcome, a.heard_as, a.transcript, a.phonemes, "
         "a.confidence, a.method, a.audio_quality_status, a.created_at, f.feedback_type, f.guidance_text "
         "FROM practice_attempts a LEFT JOIN feedback_records f ON f.attempt_id = a.id WHERE a.user_id = ?")
    args: list = [user["id"]]
    if speech_target_id:
        q += " AND a.speech_target_id = ?"
        args.append(speech_target_id)
    q += " ORDER BY a.id DESC LIMIT ?"
    args.append(max(1, min(limit, 200)))
    with tx() as conn:
        return rows(conn.execute(q, args))


@app.get("/api/progress")
def progress(user=Depends(current_user)):
    with tx() as conn:
        per_target = rows(conn.execute(
            "SELECT speech_target_id, COUNT(*) AS attempts, "
            "SUM(status IN ('analysis_completed', 'demo_result')) AS analysed, "
            "SUM(outcome = 'on_target' AND status IN ('analysis_completed', 'demo_result')) AS on_target, "
            "SUM(outcome = 'substitution' AND status IN ('analysis_completed', 'demo_result')) AS substitutions "
            "FROM practice_attempts WHERE user_id = ? GROUP BY speech_target_id", (user["id"],)))
        daily = rows(conn.execute(
            "SELECT speech_target_id, substr(created_at, 1, 10) AS day, COUNT(*) AS attempts, "
            "SUM(outcome = 'on_target' AND status IN ('analysis_completed', 'demo_result')) AS on_target, "
            "SUM(status IN ('analysis_completed', 'demo_result')) AS analysed "
            "FROM practice_attempts WHERE user_id = ? GROUP BY speech_target_id, day ORDER BY day", (user["id"],)))
        levels = rows(conn.execute(
            "SELECT speech_target_id, value AS level, note, recorded_at FROM progress_records WHERE user_id = ? AND metric = 'level' ORDER BY id",
            (user["id"],)))
        sessions = conn.execute("SELECT COUNT(*) FROM practice_sessions WHERE user_id = ? AND kind = 'practice' AND completed_at IS NOT NULL",
                                (user["id"],)).fetchone()[0]
        days = [r[0] for r in conn.execute("SELECT DISTINCT substr(created_at, 1, 10) FROM practice_attempts WHERE user_id = ? ORDER BY 1",
                                           (user["id"],))]
        ps = planner.plans(conn, user["id"])
    return {"per_target": per_target, "daily": daily, "levels": levels, "sessions_completed": sessions,
            "days_practised": len(days), "practice_days": days, "plans": ps}


# ---------- frontend ----------

app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")


@app.get("/", include_in_schema=False)
def index():
    return FileResponse(FRONTEND_DIR / "index.html")
