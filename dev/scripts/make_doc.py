"""Build the SayBetter AI summary as a Word document."""
import sys

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

OUT = sys.argv[1]
NAVY = RGBColor(0x14, 0x21, 0x3D)
TEAL = RGBColor(0x0F, 0x76, 0x6E)
GREY = RGBColor(0x4A, 0x55, 0x68)

doc = Document()
sec = doc.sections[0]
sec.page_width, sec.page_height = Cm(21.0), Cm(29.7)  # A4
for side in ("left_margin", "right_margin"):
    setattr(sec, side, Cm(2.2))
sec.top_margin = sec.bottom_margin = Cm(2.0)

st = doc.styles
st["Normal"].font.name = "Calibri"
st["Normal"].font.size = Pt(10.5)
st["Normal"].font.color.rgb = NAVY
# Nirmala UI renders Tamil and Devanagari on Windows
st["Normal"].element.rPr.rFonts.set(qn("w:cs"), "Nirmala UI")
st["Normal"].paragraph_format.space_after = Pt(4)
for name, size in (("Title", 26), ("Heading 1", 16), ("Heading 2", 12.5)):
    s = st[name]
    s.font.name = "Calibri"
    s.font.size = Pt(size)
    s.font.bold = True
    s.font.color.rgb = TEAL if name != "Title" else NAVY
    s.element.rPr.rFonts.set(qn("w:cs"), "Nirmala UI")
st["Heading 1"].paragraph_format.space_before = Pt(16)
st["Heading 2"].paragraph_format.space_before = Pt(10)


def shade(cell, hex_fill):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), hex_fill)
    tcPr.append(shd)


def para(text="", bold_prefix=None, italic=False, color=None, size=None, align=None):
    p = doc.add_paragraph()
    if bold_prefix:
        r = p.add_run(bold_prefix)
        r.bold = True
    r = p.add_run(text)
    r.italic = italic
    if color:
        r.font.color.rgb = color
    if size:
        r.font.size = Pt(size)
    if align:
        p.alignment = align
    return p


def bullets(items, style="List Bullet"):
    for it in items:
        p = doc.add_paragraph(style=style)
        if isinstance(it, tuple):
            p.add_run(it[0]).bold = True
            p.add_run(it[1])
        else:
            p.add_run(it)


def table(headers, rows, widths):
    t = doc.add_table(rows=1, cols=len(headers))
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, h in enumerate(headers):
        c = t.rows[0].cells[i]
        c.text = ""
        r = c.paragraphs[0].add_run(h)
        r.bold = True
        r.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
        shade(c, "0F766E")
    for k, row in enumerate(rows):
        cells = t.add_row().cells
        for i, val in enumerate(row):
            cells[i].text = ""
            cells[i].paragraphs[0].add_run(str(val))
            if k % 2:
                shade(cells[i], "F3F0EB")
    for row in t.rows:
        for i, w in enumerate(widths):
            row.cells[i].width = Cm(w)
            for p in row.cells[i].paragraphs:
                p.paragraph_format.space_after = Pt(1)
                for r in p.runs:
                    r.font.size = Pt(9.5)
    doc.add_paragraph()
    return t


def code(lines):
    for ln in lines:
        p = doc.add_paragraph()
        p.paragraph_format.space_after = Pt(0)
        p.paragraph_format.left_indent = Cm(0.4)
        r = p.add_run(ln)
        r.font.name = "Consolas"
        r.font.size = Pt(8.5)
        r.element.rPr.rFonts.set(qn("w:cs"), "Nirmala UI")
        pPr = p._p.get_or_add_pPr()
        shd = OxmlElement("w:shd")
        shd.set(qn("w:val"), "clear")
        shd.set(qn("w:fill"), "F3F0EB")
        pPr.append(shd)
    doc.add_paragraph()


# ---------- title ----------
doc.add_paragraph("SayBetter AI", style="Title")
para("Personalised speech-sound practice for Tamil and Hindi — MVP v0.1", color=TEAL, size=13)
para("Project summary and how the app works  ·  24 October 2026", color=GREY, size=10)
p = para("Practice-support tool. It does not diagnose speech disorders or replace a qualified speech-language therapist.",
         italic=True, color=GREY, size=9.5)

# ---------- 1 ----------
doc.add_heading("1. What it is", level=1)
para("SayBetter AI is a speech-practice app for Tamil and Hindi. A learner says a word, and the app checks one target "
     "sound in it. It tells the learner what it heard (for example “We heard ள instead of ழ”), shows animated side-view "
     "mouth diagrams of the correct sound next to the one it heard, and gives one specific tip. It also adjusts the next "
     "exercise based on the learner’s saved results.")
para("It follows a speech therapist’s practice routine: assess, focus on one sound, give feedback, practise, move up "
     "or step back. Clinical decisions stay with a speech-language therapist.")

# ---------- 2 ----------
doc.add_heading("2. What the learner sees", level=1)
table(["Page", "What happens"], [
    ["Landing", "Explains Practice → Feedback → Improve. Shows a live animated diagram of the tongue for ழ, demo profiles, and privacy and “not a diagnosis” notes."],
    ["Onboarding", "Name, language (Tamil/Hindi), goal, feedback style (brief / step by step / encouraging), and whether to keep recordings (off by default)."],
    ["2-minute check (baseline)", "The learner says 6 short words (2 per sound). The app ranks which sound needs the most work, sets a starting level, and marks sounds that already sound fine as “Sounded clear”."],
    ["Dashboard", "Current sound, level x of 5, the next word, all sounds with their status, recent results as coloured dots, and which checks are running."],
    ["Practice room", "The target word with its sound highlighted, romanisation and meaning; a “Hear reference” button (a Sarvam voice); a recorder with level meter, playback and WAV upload; an animated diagram and steps."],
    ["Feedback card", "Verdict, confidence with a “Why this confidence?” explanation, what each check heard, one tip, diagrams of the correct sound vs the one heard. Buttons: Hear reference, Hear my attempt, Try again, Continue. A notice appears when the level changes."],
    ["Sound guide", "How to make the sound, common mix-ups with comparison diagrams and tips, and all 5 levels."],
    ["Progress", "Sessions, days practised, recordings made. Per sound: level, % on target, a daily chart and level history, labelled as app estimates, not clinical results."],
    ["Settings", "Edit profile, a measured-accuracy table, switch profile, and delete all my data."],
], [4.0, 12.6])

# ---------- 3 ----------
doc.add_heading("3. Practice content", level=1)
bullets([
    ("Tamil: ", "ழ (zha), ள (La), ர (ra)"),
    ("Hindi: ", "र (ra), श (sha), ख (kha)"),
    ("Each sound includes: ", "a plain-language explanation, 4 articulation steps, a diagram, and its common mix-ups, each with its own tip and diagram (ழ has three: ழ→ள, ழ→ல, ழ→ய)."),
    ("5 levels: ", "sound on its own → short words → different positions in a word → phrases → everyday sentences."),
    ("Draft content: ", "everything is in backend/app/data/targets.json and must be reviewed by a speech-language therapist before real users rely on it."),
])

# ---------- 4 ----------
doc.add_heading("4. How an attempt is checked", level=1)
code([
    "Browser mic ─► 16 kHz WAV ─► POST /api/attempts",
    "   1. Recording quality: too short / quiet / no speech / distorted → “record again”",
    "   2. Three checks run on the same recording:",
    "      a. Sarvam speech-to-text (saaras:v3, verbatim) → which letter was heard?",
    "      b. Sound model on the PC (wav2vec2, writes IPA)  → which sound was heard?",
    "      c. Sarvam voice comparison: 6 Sarvam voices say the word correctly and with",
    "         each mix-up; the attempt is matched against all of them; closest version wins",
    "   3. Look only at the target sound’s position in the word",
    "   4. Combine: each check’s measured track record for this sound adds evidence",
    "      when it agrees and subtracts when it disagrees",
    "   5. Verdict + confidence (below 55% → “not sure”, no claim)",
    "   6. Tip for that exact mix-up → plan update → saved",
])
doc.add_heading("Why three checks", level=2)
para("Each check has a blind spot, found in testing with the Sarvam key:")
bullets([
    ("Sarvam speech-to-text ", "knows Indian languages well, but “autocorrects” a mix-up into the real word: it wrote down सेर (a mix-up) as शेर, and மளை as மழை. It only catches mix-ups that form another real word, such as மலை (“mountain”)."),
    ("The sound model ", "has no dictionary, so it doesn’t autocorrect. It is good for Hindi श/स but weak for Tamil ழ."),
    ("Sarvam voice comparison ", "doesn’t need any model to “know” ழ; it only needs the correct and mix-up recordings to sound different."),
])
para("First test of the voice comparison (it never saw the voice being tested):", bold_prefix=None)
table(["Sound", "Random guessing", "Voice comparison"], [
    ["श (sha)", "50%", "88%"], ["ख (kha)", "33%", "72%"], ["र (ra, Hindi)", "25%", "68%"],
    ["ழ (zha)", "25%", "62%"], ["ர (ra, Tamil)", "25%", "59%"], ["ள (La)", "33%", "48%"],
], [5.5, 5.5, 5.6])
doc.add_heading("How confidence is calculated", level=2)
bullets([
    "The calibration test (section 6) records how often each check was right for each sound.",
    "Each check’s track record then counts for or against the verdict.",
    "A check that is right less than 60% of the time for a sound is ignored for that sound.",
    "Confidence is capped at 95% because the tests used synthetic voices; background noise lowers it.",
    "Every verdict carries a plain-language explanation, e.g. “Sarvam voice comparison heard ள — right 87% of the time when it says that for ழ (40 test clips)”.",
])

# ---------- 5 ----------
doc.add_heading("5. Adaptive plan (fixed, transparent rules)", level=1)
table(["Rule", "Condition"], [
    ["Move up a level", "3 of the last 4 confident attempts were on target"],
    ["Step back a level", "3 of the last 4 confident attempts were a mix-up"],
    ["Suggest a therapist", "6 mix-ups in a row at level 1"],
    ["Stay", "Anything else"],
    ["Next word", "After a miss, retry the same word; otherwise the least-practised word at that level. “Continue” always moves to a new word."],
    ["No false progress", "“Not sure” attempts never move the level"],
], [4.5, 12.1])

# ---------- 6 ----------
doc.add_heading("6. Calibration test (the accuracy measurement)", level=1)
para("Command: python -m tools.calibrate (run from the backend folder). It works in two steps:")
bullets([
    "Sarvam text-to-speech generates 1,218 clips: every word at levels 1–3, said correctly and with each mix-up, in 6 voices (shubh, kavitha, anand, priya, rahul, shruti). Cost ≈ ₹18; clips are saved so each is paid for once.",
    "The clips go through the same 3 checks a learner’s attempt does. The voice comparison never compares a clip against its own voice.",
], style="List Number")
para("Outputs:")
bullets([
    "var/calibration.json — used by the confidence calculation",
    "var/calibration_report.md — accuracy of the final verdict and of each check",
    "The accuracy table in Settings",
])
para("Status when this document was written: the calibration was running (still generating clips); final numbers were not yet available.",
     italic=True, color=GREY)

# ---------- 7 ----------
doc.add_heading("7. Technical setup", level=1)
table(["Part", "Technology", "File"], [
    ["Backend", "Python 3.12, FastAPI, SQLite", "backend/app/main.py"],
    ["Frontend", "Plain HTML/JS, no build step; animated SVG mouth diagrams", "frontend/js/app.js, diagrams.js"],
    ["Speech-to-text, reference audio, voice recordings", "Sarvam saaras:v3 + bulbul:v3, with automatic slow-down and retry on rate limits", "engines/sarvam.py"],
    ["Sound model", "facebook/wav2vec2-xlsr-53-espeak-cv-ft on CPU (~0.1 s per clip)", "engines/phonemes.py"],
    ["Voice comparison", "Layer-18 sound features, DTW alignment, scored by the 2 closest voices", "engines/templates.py"],
    ["Comparison, confidence, tips, plan", "Alignment, evidence fusion, coaching, adaptive rules", "compare.py, analysis.py, coach.py, planner.py"],
    ["Data", "users, learning_plans, practice_sessions, practice_attempts, feedback_records, progress_records. Recordings deleted after analysis unless kept by choice.", "db.py"],
], [4.2, 7.6, 4.8])
doc.add_heading("Main API endpoints", level=2)
table(["Endpoint", "Purpose"], [
    ["POST /api/attempts", "Analyse a recording; returns verdict, confidence, evidence, tip and plan update"],
    ["GET /api/plan, PUT /api/plan/active", "The learning plan and the next item; choose the focus sound"],
    ["GET /api/progress", "Practice history and level changes"],
    ["GET /api/accuracy", "Measured accuracy per sound and check"],
    ["GET /api/health", "Which checks are running"],
    ["GET /api/reference", "Sarvam reference audio for an item"],
    ["POST /api/profiles, DELETE /api/me", "Create a profile; delete all of a profile’s data"],
], [6.0, 10.6])
para("Interactive API docs: http://localhost:8000/docs")

# ---------- 8 ----------
doc.add_heading("8. What is tested and what isn’t", level=1)
table(["Area", "Status"], [
    ["Sarvam key, text-to-speech, speech-to-text", "Working"],
    ["Sarvam “autocorrect” problem", "Found and worked around (voice comparison + track-record weighting)"],
    ["Detecting श/स, ख/क, र/ल on real audio", "Working"],
    ["Level-up, next-word choice, retry after a miss", "Tested end to end"],
    ["Bad audio, other users’ data, data deletion", "Rejected / works"],
    ["Full calibration and final accuracy numbers", "Running"],
    ["Server restart with the 3-check code; feedback card in the browser", "After calibration"],
    ["Accuracy on real learners, especially Tamil ள/ழ", "Not yet — needs recordings from native speakers"],
    ["Live microphone", "Works in Chrome/Edge at localhost:8000; blocked in the app’s built-in browser panel"],
    ["Step-back rule", "Logic in place; never triggered in testing"],
], [8.3, 8.3])

# ---------- 9 ----------
doc.add_heading("9. Known limits and next steps", level=1)
bullets([
    ("Tamil ள and ழ are the weakest ", "(about 50–60% in the first test). The biggest improvement: 5–10 native speakers recording each word, correctly and with their natural mix-ups, for honest real-world accuracy and data to train on real speech."),
    ("Shortcuts to replace: ", "local profiles without passwords → Supabase login; SQLite → Postgres; plain JS → Next.js."),
    ("Interface language: ", "buttons and instructions are in English; Sarvam’s translation API could show them in Tamil and Hindi."),
    ("Content review ", "by a speech-language therapist before real users."),
    ("Security: ", "the Sarvam key was shared in chat; create a new key in the Sarvam dashboard and put it in backend/.env."),
])

# ---------- 10 ----------
doc.add_heading("10. How to run it", level=1)
code(["powershell -ExecutionPolicy Bypass -File saybetter\\run.ps1"])
para("Then open http://localhost:8000 in Chrome or Edge. The first run sets up Python 3.12 in %LOCALAPPDATA%\\SayBetter\\venv "
     "and downloads the ~1.2 GB sound model.")

# footer page numbers
fp = sec.footer.paragraphs[0]
fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
run = fp.add_run("SayBetter AI — MVP summary   ·   page ")
run.font.size = Pt(8)
run.font.color.rgb = GREY
for tag, text in (("begin", None), (None, "PAGE"), ("end", None)):
    r = fp.add_run()
    r.font.size = Pt(8)
    if tag:
        fc = OxmlElement("w:fldChar")
        fc.set(qn("w:fldCharType"), tag)
        r._r.append(fc)
    else:
        it = OxmlElement("w:instrText")
        it.set(qn("xml:space"), "preserve")
        it.text = text
        r._r.append(it)

doc.save(OUT)
print("saved", OUT)
