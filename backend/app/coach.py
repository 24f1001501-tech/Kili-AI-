"""Turn an analysis result into one focused, pre-written practice tip.

Every sentence the learner sees comes from the content library or the
templates below; nothing here invents clinical advice.
"""

PRAISE = {
    "brief": "That sounded like {letter}.",
    "step_by_step": "That sounded like {letter}. Keep the same tongue position and try the next one.",
    "encouraging": "Nice work — that sounded like {letter}! Keep that same feeling in your mouth.",
}


def feedback(analysis: dict, target: dict, feedback_style: str, attempt_no: int) -> dict:
    status = analysis["status"]
    letter = target["letter"]
    steps = target["steps"]

    if status == "audio_unusable":
        issues = (analysis.get("quality") or {}).get("issues") or ["We couldn't use that recording."]
        return {"feedback_type": "audio_issue", "guidance_text": issues[0], "next_action": "retry", "diagram": None}
    if status == "analysis_unavailable":
        return {"feedback_type": "analysis_unavailable",
                "guidance_text": "Speech analysis isn't set up yet, so we can't check this attempt. You can still listen and practise with the guide.",
                "next_action": "retry", "diagram": None}
    if status == "analysis_failed":
        return {"feedback_type": "analysis_failed",
                "guidance_text": "Something went wrong while checking your attempt. Please try again in a moment.",
                "next_action": "retry", "diagram": None}

    outcome = analysis["outcome"]
    if outcome == "on_target":
        text = PRAISE.get(feedback_style, PRAISE["step_by_step"]).format(letter=letter)
        return {"feedback_type": "reinforce", "guidance_text": text, "next_action": "continue", "diagram": target["diagram"]}

    if outcome == "substitution" and analysis.get("heard_as") in target["confusions"]:
        conf = target["confusions"][analysis["heard_as"]]
        return {"feedback_type": "correct_substitution", "guidance_text": conf["tip"], "next_action": "retry",
                "diagram": target["diagram"], "heard_diagram": conf["diagram"], "heard_as": analysis["heard_as"]}

    # Uncertain: no specific corrective claim, just one articulation step to focus on.
    step = steps[attempt_no % len(steps)]
    return {"feedback_type": "uncertain",
            "guidance_text": f"We couldn't tell clearly how the {letter} sound came out. Listen to the reference once, then try slowly. Focus on this: {step}",
            "next_action": "retry", "diagram": target["diagram"]}
