"""Deterministic, explainable practice planning.

Rules (only attempts that were analysed with enough confidence count):
  * 3 of the last 4 attempts on target at this level  -> move up a level
  * 3 of the last 4 attempts with a substitution       -> move down a level
  * 6 substitutions in a row at level 1                -> suggest seeing a therapist
  * otherwise                                           -> stay at this level
"""
import sqlite3

from . import content
from .db import now, row, rows

COUNTED = ("analysis_completed", "demo_result")
WINDOW = 4
NEEDED = 3


def ensure_plans(conn: sqlite3.Connection, user: dict) -> None:
    ts = now()
    for i, t in enumerate(content.targets(user["preferred_language"])):
        conn.execute(
            "INSERT OR IGNORE INTO learning_plans (user_id, speech_target_id, current_level, status, priority, created_at, updated_at) "
            "VALUES (?, ?, 1, 'queued', ?, ?, ?)", (user["id"], t["id"], -i, ts, ts))


def plans(conn, user_id: int) -> list[dict]:
    return rows(conn.execute("SELECT * FROM learning_plans WHERE user_id = ? ORDER BY status = 'active' DESC, priority DESC", (user_id,)))


def active_plan(conn, user_id: int) -> dict | None:
    return row(conn.execute("SELECT * FROM learning_plans WHERE user_id = ? AND status = 'active'", (user_id,)).fetchone())


def set_active(conn, user_id: int, target_id: str) -> None:
    conn.execute("UPDATE learning_plans SET status = 'queued' WHERE user_id = ? AND status = 'active'", (user_id,))
    conn.execute("UPDATE learning_plans SET status = 'active', updated_at = ? WHERE user_id = ? AND speech_target_id = ?",
                 (now(), user_id, target_id))


def _log(conn, user_id, target_id, metric, value, note):
    conn.execute("INSERT INTO progress_records (user_id, speech_target_id, metric, value, note, recorded_at) VALUES (?, ?, ?, ?, ?, ?)",
                 (user_id, target_id, metric, value, note, now()))


def apply_baseline(conn, user: dict, session_id: int) -> dict:
    """Rank targets by baseline results and activate the one needing most practice."""
    ensure_plans(conn, user)
    results = rows(conn.execute(
        "SELECT speech_target_id, status, outcome FROM practice_attempts WHERE session_id = ? AND user_id = ?",
        (session_id, user["id"])))
    summary = {}
    for t in content.targets(user["preferred_language"]):
        rs = [r for r in results if r["speech_target_id"] == t["id"]]
        subs = sum(r["outcome"] == "substitution" and r["status"] in COUNTED for r in rs)
        ok = sum(r["outcome"] == "on_target" and r["status"] in COUNTED for r in rs)
        unclear = len(rs) - subs - ok
        summary[t["id"]] = {"substitutions": subs, "on_target": ok, "unclear": unclear, "attempts": len(rs)}

    ranked = sorted(summary, key=lambda k: (summary[k]["substitutions"] * 2 + summary[k]["unclear"], -summary[k]["on_target"]), reverse=True)
    ts = now()
    for rank, tid in enumerate(ranked):
        s = summary[tid]
        clear = s["attempts"] > 0 and s["on_target"] == s["attempts"]
        level = 1 if s["substitutions"] >= 2 else 2 if not clear else 3
        status = "not_needed" if clear and rank > 0 else "queued"
        conn.execute("UPDATE learning_plans SET current_level = ?, status = ?, priority = ?, updated_at = ? WHERE user_id = ? AND speech_target_id = ?",
                     (level, status, len(ranked) - rank, ts, user["id"], tid))
        s.update(start_level=level, plan_status=status)
    set_active(conn, user["id"], ranked[0])
    summary[ranked[0]]["plan_status"] = "active"
    _log(conn, user["id"], ranked[0], "level", summary[ranked[0]]["start_level"], "Starting level from baseline")
    conn.execute("UPDATE users SET baseline_done = 1 WHERE id = ?", (user["id"],))
    return {"ranked": ranked, "summary": summary}


def _window(conn, plan: dict) -> list[dict]:
    return rows(conn.execute(
        "SELECT a.outcome FROM practice_attempts a JOIN practice_sessions s ON s.id = a.session_id "
        "WHERE a.user_id = ? AND a.speech_target_id = ? AND a.level = ? AND s.kind = 'practice' "
        "AND a.status IN ('analysis_completed', 'demo_result') AND a.created_at >= ? ORDER BY a.id DESC LIMIT ?",
        (plan["user_id"], plan["speech_target_id"], plan["current_level"], plan["updated_at"], WINDOW)))


def after_attempt(conn, plan: dict) -> dict:
    """Apply the rules after a saved attempt; returns what changed and why."""
    recent = _window(conn, plan)
    ok = sum(r["outcome"] == "on_target" for r in recent)
    subs = sum(r["outcome"] == "substitution" for r in recent)
    level = plan["current_level"]
    tid = plan["speech_target_id"]
    names = content.level_names()
    decision = {"action": "stay", "level": level, "message": None, "suggest_therapist": False,
                "window": {"on_target": ok, "substitution": subs, "counted": len(recent)}}

    if ok >= NEEDED:
        if level < 5:
            decision.update(action="level_up", level=level + 1,
                            message=f"{ok} of your last {len(recent)} attempts were on target. Moving up to level {level + 1}: {names[level + 1]}.")
            conn.execute("UPDATE learning_plans SET current_level = ?, updated_at = ? WHERE id = ?", (level + 1, now(), plan["id"]))
            _log(conn, plan["user_id"], tid, "level", level + 1, "Level up")
        else:
            decision.update(action="mastered", message="You've completed every level for this sound. Great work!")
            conn.execute("UPDATE learning_plans SET status = 'mastered', updated_at = ? WHERE id = ?", (now(), plan["id"]))
            _log(conn, plan["user_id"], tid, "mastered", 1, "All levels completed")
            nxt = conn.execute("SELECT speech_target_id FROM learning_plans WHERE user_id = ? AND status = 'queued' ORDER BY priority DESC LIMIT 1",
                               (plan["user_id"],)).fetchone()
            if nxt:
                set_active(conn, plan["user_id"], nxt[0])
                decision["next_target"] = nxt[0]
    elif subs >= NEEDED:
        if level > 1:
            decision.update(action="level_down", level=level - 1,
                            message=f"This level is tricky right now. Let's practise level {level - 1} ({names[level - 1]}) for a bit, then come back.")
            conn.execute("UPDATE learning_plans SET current_level = ?, updated_at = ? WHERE id = ?", (level - 1, now(), plan["id"]))
            _log(conn, plan["user_id"], tid, "level", level - 1, "Simplified")
        else:
            streak = conn.execute(
                "SELECT outcome FROM practice_attempts WHERE user_id = ? AND speech_target_id = ? AND level = 1 "
                "AND status IN ('analysis_completed', 'demo_result') ORDER BY id DESC LIMIT 6", (plan["user_id"], tid)).fetchall()
            if len(streak) == 6 and all(r[0] == "substitution" for r in streak):
                decision.update(action="suggest_therapist", suggest_therapist=True,
                                message="This sound has been difficult for a while. Reviewing the guide may help, and a speech-language therapist can give hands-on help that an app can't.")
    return decision


def next_item(conn, user_id: int, plan: dict, last: dict | None = None) -> dict:
    """Retry the same item after a miss; otherwise pick the least-practised item."""
    its = content.items(plan["speech_target_id"], plan["current_level"])
    if last and last.get("next_action") == "retry" and last.get("level") == plan["current_level"]:
        it = next((i for i in its if i["text"] == last["item_text"]), None)
        if it:
            return {**it, "reason": "Let's try that one again."}
    stats = {r["item_text"]: (r["ok"], r["last_id"]) for r in rows(conn.execute(
        "SELECT item_text, SUM(outcome = 'on_target') AS ok, MAX(id) AS last_id FROM practice_attempts "
        "WHERE user_id = ? AND speech_target_id = ? AND level = ? GROUP BY item_text",
        (user_id, plan["speech_target_id"], plan["current_level"])))}
    it = min(its, key=lambda i: stats.get(i["text"], (0, 0)))
    reason = "New item at this level." if it["text"] not in stats else "Practise this one a little more."
    return {**it, "reason": reason}
