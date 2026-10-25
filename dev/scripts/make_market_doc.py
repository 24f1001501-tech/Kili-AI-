"""SayBetter AI — market research document (Word)."""
import sys

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.opc.constants import RELATIONSHIP_TYPE as RT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

OUT = sys.argv[1]
NAVY = RGBColor(0x14, 0x21, 0x3D)
TEAL = RGBColor(0x0F, 0x76, 0x6E)
GREY = RGBColor(0x4A, 0x55, 0x68)

doc = Document()
sec = doc.sections[0]
sec.page_width, sec.page_height = Cm(21.0), Cm(29.7)
sec.left_margin = sec.right_margin = Cm(2.2)
sec.top_margin = sec.bottom_margin = Cm(2.0)

st = doc.styles
st["Normal"].font.name = "Calibri"
st["Normal"].font.size = Pt(10.5)
st["Normal"].font.color.rgb = NAVY
st["Normal"].element.rPr.rFonts.set(qn("w:cs"), "Nirmala UI")
st["Normal"].paragraph_format.space_after = Pt(4)
for name, size in (("Title", 28), ("Heading 1", 16), ("Heading 2", 12.5), ("Heading 3", 11)):
    s = st[name]
    s.font.name = "Calibri"
    s.font.size = Pt(size)
    s.font.bold = True
    s.font.color.rgb = NAVY if name == "Title" else TEAL
    s.element.rPr.rFonts.set(qn("w:cs"), "Nirmala UI")
st["Heading 1"].paragraph_format.space_before = Pt(18)
st["Heading 2"].paragraph_format.space_before = Pt(10)


def shade(cell, fill):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), fill)
    tcPr.append(shd)


def para(text="", bold_prefix=None, italic=False, color=None, size=None, align=None, bold=False):
    p = doc.add_paragraph()
    if bold_prefix:
        p.add_run(bold_prefix).bold = True
    r = p.add_run(text)
    r.italic, r.bold = italic, bold
    if color:
        r.font.color.rgb = color
    if size:
        r.font.size = Pt(size)
    if align is not None:
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


def table(headers, rows, widths, highlight_last=False, font=9.2):
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
        # keep the header row on the same page as the first data row
        c.paragraphs[0].paragraph_format.keep_with_next = True
    trPr = t.rows[0]._tr.get_or_add_trPr()
    hdr = OxmlElement("w:tblHeader")
    hdr.set(qn("w:val"), "true")
    trPr.append(hdr)
    for k, row in enumerate(rows):
        cells = t.add_row().cells
        last = highlight_last and k == len(rows) - 1
        for i, val in enumerate(row):
            cells[i].text = ""
            run = cells[i].paragraphs[0].add_run(str(val))
            if last:
                run.bold = True
                shade(cells[i], "E3F2EF")
            elif k % 2:
                shade(cells[i], "F3F0EB")
    for row in t.rows:
        for i, w in enumerate(widths):
            row.cells[i].width = Cm(w)
            for p in row.cells[i].paragraphs:
                p.paragraph_format.space_after = Pt(1)
                for r in p.runs:
                    r.font.size = Pt(font)
    doc.add_paragraph()


def callout(title, text, fill="E3F2EF"):
    t = doc.add_table(rows=1, cols=1)
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    c = t.rows[0].cells[0]
    c.width = Cm(16.6)
    shade(c, fill)
    c.text = ""
    p = c.paragraphs[0]
    if title:
        p.add_run(title + "  ").bold = True
    p.add_run(text)
    for r in p.runs:
        r.font.size = Pt(10)
    doc.add_paragraph()


def link(paragraph, url, text):
    rid = paragraph.part.relate_to(url, RT.HYPERLINK, is_external=True)
    h = OxmlElement("w:hyperlink")
    h.set(qn("r:id"), rid)
    r = OxmlElement("w:r")
    rPr = OxmlElement("w:rPr")
    c = OxmlElement("w:color")
    c.set(qn("w:val"), "0F766E")
    u = OxmlElement("w:u")
    u.set(qn("w:val"), "single")
    sz = OxmlElement("w:sz")
    sz.set(qn("w:val"), "17")
    rPr.extend([c, u, sz])
    r.append(rPr)
    t = OxmlElement("w:t")
    t.text = text
    r.append(t)
    h.append(r)
    paragraph._p.append(h)


def page_break():
    doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)


# =====================================================================
# Title page
# =====================================================================
for _ in range(5):
    doc.add_paragraph()
doc.add_paragraph("SayBetter AI", style="Title")
para("Market Research Report", color=TEAL, size=18, bold=True)
para("AI speech-practice coach for Tamil and Hindi — population need, therapy costs, market size, positioning, "
     "usability, social impact and sustainability", color=GREY, size=12)
doc.add_paragraph()
para("Prepared for: Entrepreneurship case competition (sustainability, social impact & well-being track)", size=10.5)
para("Date: 24 October 2026", size=10.5)
para("Status: desk research from published sources + our own calculations. Figures marked “our estimate” are "
     "derived from the cited sources using the assumptions shown, and should be validated with primary research "
     "(Section 13) before final submission.", italic=True, color=GREY, size=9.5)
page_break()

# =====================================================================
# Executive summary
# =====================================================================
doc.add_heading("Executive summary", level=1)
para("SayBetter AI helps children and adults practise specific speech sounds in Tamil and Hindi at home. It shows how "
     "the tongue and lips should move, tells the learner which sound it actually heard (for example “ள instead of ழ”), "
     "and adapts the next exercise from their saved results — positioned as practice support between (or in the "
     "absence of) speech-therapy sessions, not as a diagnosis or a replacement for a therapist.")
table(["Question", "Key finding"], [
    ["How many people are affected?", "≈ 33 lakh Indians with a speech/language disability on the strict NSS definition; "
     "≈ 5.8 crore with some communication disorder on a broader 4% estimate. About 1.3 crore children may have a speech "
     "disorder (our estimate) [1–5]."],
    ["Is there a supply gap?", "Yes. Only about 2,500–3,500+ registered speech-language pathologists and audiologists serve "
     "1.44 billion people — roughly 1 professional per 32,000 people who need one — concentrated in cities [6–8]."],
    ["What does therapy cost today?", "₹600–2,500 per session in the private and online sector (₹3,000–6,000 at specialist "
     "centres). A typical 12-week course of ~24 sessions costs ₹14,000–60,000, mostly out of pocket [9–11, 16]."],
    ["How big is the market?", "India speech-therapy services: US$1.33 bn (2023) → US$2.56 bn (2030), 9.8% CAGR [12]. "
     "Our serviceable market (children with speech disorders, Hindi/Tamil speaking, online): ≈ 40 lakh children, "
     "≈ ₹400 crore a year at ₹999/year (our estimate)."],
    ["Where do we fit?", "No product combines Indian-language speech sounds, sound-level AI feedback and visual articulation "
     "guidance at app prices. Competitors are English-first, stuttering-only, or human teletherapy at ₹600+ per session."],
    ["Is it usable?", "MVP built with one action per screen, native script + romanisation + audio, a 2-minute check, honest "
     "“not sure” results. Next: SUS testing (target ≥ 75), Tamil/Hindi interface, low-end Android."],
    ["Is it sustainable?", "Low running cost (≈ ₹10–15 per active user per month, our estimate) supports a freemium + "
     "family plan + clinic/school/CSR model with ~90% gross margin."],
    ["Social impact", "Directly serves SDG 3 (health & well-being), SDG 4 (education) and SDG 10 (reduced inequalities) by "
     "bringing daily, affordable practice to families who cannot reach or afford a therapist."],
], [4.3, 12.3])
page_break()

# =====================================================================
# 1. Problem and population
# =====================================================================
doc.add_heading("1. The problem: who struggles to speak clearly", level=1)
para("Speech-sound (articulation) difficulties mean a person consistently says one sound in place of another — for "
     "example a Tamil child saying வாலைப்பலம் for வாழைப்பழம் (ழ → ல), or a Hindi speaker saying सेर for शेर (श → स). "
     "Left unaddressed in childhood, they affect intelligibility, reading, classroom participation and confidence; in adults, "
     "speech difficulties after a stroke (aphasia, dysarthria) affect work and independence.")
doc.add_heading("1.1 Population affected in India", level=2)
table(["Group", "Figure", "Basis", "Src"], [
    ["People with speech disability (Census 2011)", "19.98 lakh", "Strict census definition; known undercount", "[1]"],
    ["People with speech & language disability (NSS 76th round, 2018)", "≈ 33 lakh (our estimate)", "228 per 1,00,000 persons × 144 crore population", "[2, 3]"],
    ["People with any communication disorder", "≈ 5.8 crore (our estimate)", "≈ 4% of population, the assumption used in Indian workforce planning", "[6]"],
    ["School children with a communication disorder", "11.5% of children screened", "School screening, Mysuru (2,010 children); speech disorder alone 3.8%", "[4]"],
    ["Rural Tamil Nadu school children with hearing, speech or language disorders", "≈ 9% (130 of 1,453)", "Longitudinal rural school study", "[5]"],
    ["Children (0–14) with a speech disorder, India", "≈ 1.3 crore (our estimate)", "3.8% × ≈ 34.6 crore children (24% of 144 crore)", "[4, 17]"],
    ["People who stutter", "≈ 1.4 crore (our estimate)", "≈ 1% worldwide; 1.68% in a Karnataka school study", "[13]"],
    ["New stroke cases per year", "≈ 15–22 lakh (our estimate)", "105–152 per 1,00,000 persons per year", "[14]"],
    ["New post-stroke aphasia cases per year", "≈ 3–8 lakh (our estimate)", "21–38% of stroke patients", "[14]"],
], [5.6, 3.4, 6.2, 1.4])
callout("Why the numbers vary.", "Indian estimates differ by up to 10× because the Census counts only severe disability, "
        "while school screenings count every child who needs help. For the business case we use the conservative child "
        "estimate (3.8%), not the broad 4–11% screening figures.")
doc.add_heading("1.2 Global context", level=2)
bullets([
    ("United States: ", "nearly 1 in 12 children aged 3–17 (7.7%) had a voice, speech, language or swallowing disorder in "
     "the past year; speech problems were most common (5.0%). Only about 55% received any treatment [15]."),
    ("Stuttering: ", "about 1% of people worldwide [13]."),
    ("Implication: ", "even in a country with ~200,000 therapists, almost half of affected children go untreated — in India, "
     "with ~3,000, the treatment gap is far larger."),
])
doc.add_heading("1.3 Languages: our beachhead", level=2)
table(["Language", "First-language speakers (Census 2011)", "Share of India", "Src"], [
    ["Hindi", "52.8 crore (≈ 69 crore incl. second/third language)", "43.6%", "[18]"],
    ["Tamil", "6.9 crore (≈ 7.7 crore incl. second/third language)", "5.7%", "[18]"],
    ["Hindi + Tamil", "≈ 59.7 crore first-language speakers", "≈ 49.3%", "[18]"],
], [3.2, 8.2, 3.6, 1.6])
para("Almost every speech-therapy app is built for English sounds. Tamil sounds such as ழ, ள and the retroflex consonants, "
     "and Hindi contrasts such as श/स and aspirated ख/क, are not covered — even though roughly half of India speaks one of "
     "these two languages as a first language.")

# =====================================================================
# 2. Supply gap
# =====================================================================
doc.add_heading("2. The supply gap: too few therapists", level=1)
table(["Indicator", "Figure", "Src"], [
    ["Registered speech-language pathologists & audiologists", "≈ 1,854 (ISHA directory) to 3,500+ (later estimates)", "[6, 7]"],
    ["Supply-to-need ratio", "≈ 1 professional per 32,000 people with communication disorders", "[6]"],
    ["New BASLP graduates per year", "≈ 2,500; India produces about one-tenth of the audiologists it needs", "[7]"],
    ["Training institutions", "≈ 45–50 offer a bachelor’s degree; ≈ 10 a master’s", "[6]"],
    ["Brain drain", "Graduates migrate to North America, Western Europe and the Gulf", "[6]"],
    ["Geography", "Services are skewed to cities; rural and semi-urban needs are largely unmet", "[8]"],
], [6.0, 9.0, 1.6])
para("Even with the right referral, families wait for appointments, travel long distances and can rarely afford the "
     "2–3 sessions a week the evidence recommends. Therapists, in turn, cannot see what happens between sessions — and home "
     "practice is where most of the repetition must happen.")
callout("The core insight.", "Improvement in speech-sound disorders comes from many correct repetitions (evidence suggests "
        "50–100+ practice trials per session, at least twice a week) [10]. A therapist’s time is the bottleneck; guided, "
        "checked home practice is where an app can multiply each therapist’s reach.")

# =====================================================================
# 3. Cost
# =====================================================================
doc.add_heading("3. What therapy costs families today", level=1)
doc.add_heading("3.1 Price per session", level=2)
table(["Setting", "Typical price per session", "Src"], [
    ["Government hospital", "₹150–500 (long waits, few centres)", "[9, 11]"],
    ["Online teletherapy", "₹600–1,500 (30–45 min)", "[9]"],
    ["Private clinic, metro", "₹1,000–2,500", "[9, 11]"],
    ["Specialist centre", "₹3,000–6,000", "[11]"],
    ["Initial assessment (one-time)", "₹500–3,000", "[11]"],
], [6.0, 9.0, 1.6])
doc.add_heading("3.2 Cost of a full course", level=2)
para("Typical evidence-based pattern for speech-sound disorders: about 2 sessions a week, 30–60 minutes, for 12–18 weeks "
     "(average ≈ 19 sessions in phonological studies) [10]. We assume 24 sessions over 12 weeks.")
table(["Option", "24-session course (our estimate)", "Plus hidden costs"], [
    ["Private clinic, metro", "₹24,000–60,000", "Travel, a parent’s lost workday per visit"],
    ["Online teletherapy", "₹14,400–36,000", "Data, a free adult at fixed times"],
    ["Government hospital", "₹3,600–12,000", "Long travel and waiting; limited availability"],
    ["SayBetter + therapist (hybrid, proposed)", "≈ ₹7,000 (6 therapist sessions + 1 year of the app)", "Daily practice at home, any time"],
    ["SayBetter alone (proposed)", "₹999 per year", "For mild needs or where no therapist is reachable"],
], [5.4, 5.6, 5.6], highlight_last=True)
para("Out-of-pocket spending is still 39.4% of India’s total health expenditure (2021-22) [16], and speech therapy is "
     "rarely insured — so the course cost above usually comes straight from the family budget. A hybrid model could cut a "
     "family’s cost by roughly 70–85% while increasing practice from 2 sessions a week to daily (to be validated in a pilot).",
     italic=False)

# =====================================================================
# 4. Market size
# =====================================================================
doc.add_heading("4. Market size", level=1)
doc.add_heading("4.1 Top-down", level=2)
bullets([
    ("India speech-therapy services: ", "US$1,332.7 million (2023), projected US$2,558.7 million by 2030, 9.8% CAGR [12]."),
    ("Global speech-therapy apps for kids: ", "≈ US$2.8 bn (2025) → US$7.6 bn (2034), 11.7% CAGR; subscriptions already "
     "over 61% of app revenue (single commercial source, treat as directional) [19]."),
])
doc.add_heading("4.2 Bottom-up: TAM, SAM, SOM (our estimates)", level=2)
table(["Level", "Who", "Calculation", "People", "Value at ₹999/yr"], [
    ["TAM", "All Indians with a communication disorder", "144 crore × 4%", "≈ 5.8 crore", "≈ ₹5,750 crore (≈ US$680 m)"],
    ["SAM", "Children (0–14) with a speech disorder, Hindi/Tamil-speaking, online",
     "34.6 crore × 3.8% × 49.3% × 61.5% internet reach", "≈ 40 lakh", "≈ ₹400 crore (≈ US$47 m)"],
    ["SOM (year 3)", "1% of SAM as paying families + institutional seats", "40 lakh × 1%", "≈ 40,000", "≈ ₹4 crore ARR"],
], [1.9, 4.5, 4.6, 2.4, 3.2], font=8.8)
para("Internet reach: 886 million active internet users in 2024 (55% rural), and 98% of users access content in Indic "
     "languages [20]. Expansion beyond the SAM — adults who stutter (≈ 1.4 crore), post-stroke aphasia (≈ 3–8 lakh new cases "
     "a year), other Indian languages, and English pronunciation — is upside not counted here.", size=10)

# =====================================================================
# 5. Customers
# =====================================================================
doc.add_heading("5. Target customers", level=1)
table(["Persona", "Situation", "Need", "Who pays"], [
    ["Parent in a Tier-2/3 town (primary)", "Child aged 5–10 says ல for ழ or ர; nearest therapist is hours away or ₹1,500/session",
     "Affordable daily practice, knowing whether the child is improving", "Family (₹999/yr) or school/CSR seat"],
    ["Speech therapist in a city clinic", "Sees 30–40 clients a week; home practice is rarely done or checked",
     "Assign targets, see practice data, keep clients motivated", "Clinic licence"],
    ["Government early-intervention therapist (DEIC/DDRC)", "Large caseload; families travel long distances",
     "A tool families can use between visits", "Government / NHM"],
    ["Adult learner", "Wants clearer speech for work or after stroke rehabilitation",
     "Private, judgement-free practice", "Self"],
], [3.6, 5.0, 4.4, 3.6])

# =====================================================================
# 6. Competition and positioning
# =====================================================================
doc.add_heading("6. Competitive landscape and positioning", level=1)
table(["Product / option", "Indian languages", "Sound-level AI feedback", "Shows mouth/tongue", "Price", "Gap"], [
    ["Clinic / online therapist", "Yes (human)", "Human", "Human demo", "₹600–2,500 per session", "Cost, availability, 1–2 sessions a week"],
    ["Govt. DEIC / DDRC", "Yes (human)", "Human", "Human demo", "Free / low", "Few centres, travel, capacity"],
    ["Stamurai (India)", "Partly", "Stuttering only", "No", "₹2,999/yr app; ₹6,000 for 8 therapist sessions", "Not for speech sounds"],
    ["Speech Blubs", "English-first", "No (video modelling)", "Child videos", "≈ US$60/yr", "No Indian sounds"],
    ["Articulation Station", "English", "No", "No", "≈ US$7–15/month", "Therapist tool, English only"],
    ["Speech Sounds Visualized", "English", "No", "X-ray + 3D", "≈ US$30/yr", "No scoring, iOS"],
    ["Pronunciation Coach 3D", "English", "Word-level score", "3D model", "One-time, Windows", "Desktop, English learners"],
    ["SpeechLP / Sara", "English", "Yes", "No", "Free beta / subscription", "No visuals, no Indian sounds"],
    ["SayBetter AI", "Tamil + Hindi", "Yes — 3 checks + honest confidence", "Animated diagrams", "₹999/yr (proposed)", "Accuracy to be validated on real speech"],
], [3.2, 2.1, 2.9, 2.3, 3.2, 2.9], highlight_last=True, font=8.4)
para("Sources: [21–24, 29, 30] and app-store listings reviewed in our competitor scan.", italic=True, color=GREY, size=9)
doc.add_heading("6.1 Positioning statement", level=2)
callout("", "For families and adults in India who cannot get enough speech-therapy practice, SayBetter AI is a speech-practice "
        "coach in Tamil and Hindi that shows how to make each sound, tells you which sound you actually said, and plans your "
        "next exercise — unlike English-only apps or ₹600+ teletherapy sessions, it gives daily, checked practice for less "
        "than the price of one session a year.")
doc.add_heading("6.2 Why we can win", level=2)
bullets([
    ("Indian-language sounds: ", "built around ழ, ள, ர, र, श, ख and their typical mix-ups, not English phonemes."),
    ("Says which sound you made: ", "three independent checks (Sarvam speech-to-text, a phoneme model, and comparison with "
     "Sarvam voices) and a confidence based on measured accuracy — it says “not sure” rather than guessing."),
    ("Shows the mouth: ", "animated side-view diagrams of the target sound next to the sound the learner made."),
    ("Therapist logic: ", "assessment → one target → 5 levels → move up/back on evidence; suggests a therapist when stuck."),
    ("Price: ", "about the cost of one clinic session per year."),
])

# =====================================================================
# 7. Usability
# =====================================================================
doc.add_heading("7. Ease of use", level=1)
doc.add_heading("7.1 What the MVP already does", level=2)
table(["Principle", "How SayBetter applies it"], [
    ["One action per screen", "Large record button, one target word at a time, clear Try again / Continue"],
    ["Low literacy friendly", "Native script with the target sound highlighted, romanisation, meaning and a “Hear reference” voice"],
    ["Fast start", "2-minute check of 6 words builds the plan; no long questionnaire"],
    ["Shows, not tells", "Animated mouth diagrams instead of technical terms"],
    ["Encouraging, not shaming", "Feedback style choice (brief / step by step / encouraging); “mixed up” not “wrong”"],
    ["Honest", "Shows confidence and “not sure” instead of fake scores; progress labelled as app estimates"],
    ["Private by default", "Recordings deleted after analysis unless the user opts in; one-tap delete of all data"],
    ["Works on a phone", "Responsive layout, no horizontal scrolling at 375 px; small 16 kHz recordings for low bandwidth"],
], [4.5, 12.1])
doc.add_heading("7.2 Usability gaps and plan", level=2)
bullets([
    ("Gaps today: ", "interface text is in English; needs testing on low-end Android phones and in noisy homes; no caregiver "
     "or therapist dashboard yet; no offline mode."),
    ("Test plan: ", "moderated tests with 15–20 users (parents, children 6–10, therapists) in Tamil Nadu and a Hindi-speaking "
     "state; measure task success (complete the check, practise 5 words), time on task, errors, and System Usability Scale."),
    ("Targets: ", "SUS ≥ 75 (“good”); ≥ 90% of parents complete the 2-minute check without help; ≥ 4 practice days per week "
     "in week 2."),
    ("Accessibility: ", "large text and buttons, audio prompts for every instruction, colour not used alone for meaning, "
     "keyboard and screen-reader support."),
])

# =====================================================================
# 8. Business model
# =====================================================================
doc.add_heading("8. Business model and pricing", level=1)
table(["Plan", "Price (proposed)", "For", "Includes"], [
    ["Free", "₹0", "Anyone", "2-minute check, one sound, limited daily attempts"],
    ["Family", "₹149/month or ₹999/year", "Parents, adult learners", "All sounds and levels, progress, reference audio"],
    ["Clinic", "₹499 per therapist per month", "Private therapists", "Up to 15 clients, assign targets, see practice data (roadmap)"],
    ["Institution / CSR", "≈ ₹300 per child per year", "Schools, NGOs, DEIC/DDRC, CSR sponsors", "Bulk seats, screening reports, training"],
], [3.0, 3.8, 4.2, 5.6])
doc.add_heading("8.1 Unit economics (our estimates)", level=2)
table(["Item", "Assumption", "Cost per active user per month"], [
    ["Sarvam speech-to-text", "15 attempts/day × 25 days × ~1.5 s ≈ 9.4 min at ₹0.49/min [25]", "≈ ₹4.6"],
    ["Sarvam text-to-speech", "Reference and comparison voices generated once per word and cached (₹3 per 1,000 characters) [25]", "≈ ₹0 (one-time ≈ ₹20 for the whole library)"],
    ["Compute and hosting", "Phoneme model and voice comparison on CPU servers", "≈ ₹5–10"],
    ["Total cost to serve", "", "≈ ₹10–15"],
    ["Gross margin at ₹149/month", "", "≈ 90%"],
], [4.0, 8.4, 4.2], highlight_last=True)
para("Break-even example (our estimate): with a 3-person team at ≈ ₹2.5 lakh/month total cost, about 1,900 Family "
     "subscribers at ₹149/month — or a mix of family, clinic and CSR seats — covers operating costs.", size=10)

# =====================================================================
# 9. Social impact & sustainability
# =====================================================================
doc.add_heading("9. Social impact and sustainability", level=1)
doc.add_heading("9.1 Sustainable Development Goals", level=2)
table(["SDG", "How SayBetter contributes"], [
    ["SDG 3 — Good health and well-being", "Affordable, early support for communication disorders; confidence and mental well-being of children and adults"],
    ["SDG 4 — Quality education", "Clearer speech supports reading, classroom participation and inclusive education"],
    ["SDG 10 — Reduced inequalities", "Reaches rural, low-income and non-English-speaking families excluded by cost, distance and language"],
    ["SDG 9 — Industry, innovation and infrastructure", "Indian-language speech AI built on Indian models (Sarvam) for local needs"],
], [5.2, 11.4])
doc.add_heading("9.2 Theory of change", level=2)
table(["Inputs", "Activities", "Outputs", "Outcomes", "Impact"], [
    ["App, Indian-language content, therapist partners", "Daily guided practice with feedback; therapist oversight",
     "Practice minutes, attempts, sounds reaching higher levels", "Clearer target sounds; more confident communication",
     "More children and adults heard and understood, at school, work and home"],
], [3.1, 3.4, 3.4, 3.3, 3.4], font=8.8)
doc.add_heading("9.3 Impact metrics we will report", level=2)
bullets([
    "Learners reached, split by rural / Tier-2-3 / metro and by language",
    "Practice days per week and minutes per learner",
    "Share of learners who move up at least two levels in 8 weeks (app estimate), confirmed by therapist ratings in pilots",
    "Cost per child per course versus clinic-only care",
    "Therapist caseload served per therapist hour (hybrid model)",
    "Families referred to a therapist after the app suggests it",
])
doc.add_heading("9.4 Sustainability", level=2)
bullets([
    ("Financial: ", "high-margin subscriptions plus institutional and CSR seats (CSR rules under Schedule VII of the Companies "
     "Act cover health, education and disability), so free access for low-income families is funded by paying segments."),
    ("Government channels: ", "RBSK screens children for developmental delays and refers them to District Early Intervention "
     "Centres, which include speech therapists (Tamil Nadu alone has 34 DEICs); District Disability Rehabilitation Centres "
     "offer speech therapy under the RPwD Act framework [26–28]. SayBetter can extend these teams’ reach between visits."),
    ("Environmental: ", "fewer clinic trips for routine practice reduces travel; the analysis runs on small CPU servers, with "
     "an on-device version on the roadmap."),
    ("Ethical and legal: ", "children’s data requires verifiable parental consent under India’s Digital Personal Data "
     "Protection Act, 2023; recordings are not kept by default; no diagnostic claims, to stay outside medical-device regulation "
     "until clinically validated."),
])

# =====================================================================
# 10. Go-to-market
# =====================================================================
doc.add_heading("10. Go-to-market", level=1)
table(["Phase", "Focus", "Channels", "Goal"], [
    ["0–6 months", "Tamil Nadu pilot (Tamil)", "2–3 speech-therapy colleges and clinics in Chennai; 1 NGO; school screening camps",
     "200 learners; usability and accuracy on real speech; 5 therapist partners"],
    ["6–18 months", "Hindi launch", "NGOs and schools in one Hindi-speaking state; CSR sponsor; parent WhatsApp communities",
     "5,000 learners; first paying families and clinics"],
    ["18–36 months", "Scale", "Government DEIC/DDRC pilots; more Indian languages; therapist dashboard",
     "40,000 paying learners (SOM); institutional contracts"],
], [2.6, 3.4, 6.6, 4.0])

# =====================================================================
# 11. Risks
# =====================================================================
doc.add_heading("11. Risks and mitigation", level=1)
table(["Risk", "Mitigation"], [
    ["Accuracy on real children’s speech is lower than on synthetic voices (Tamil ள/ழ are hardest)",
     "Collect recordings from native speakers in the pilot; publish measured accuracy; app says “not sure” below a confidence threshold"],
    ["Clinical credibility", "Content reviewed by licensed speech-language pathologists; therapist-in-the-loop model; pilot with outcome measures"],
    ["Regulatory (medical device, data protection)", "Practice-support positioning, no diagnosis; parental consent and data minimisation under the DPDP Act"],
    ["Low engagement after the first week", "Short daily sessions, streaks, encouraging feedback, therapist and parent nudges"],
    ["Dependence on one AI provider (Sarvam)", "Local phoneme model already runs without Sarvam; engines are swappable"],
    ["Willingness to pay in low-income segments", "Free tier, CSR- and government-funded seats, low annual price"],
], [6.6, 10.0])

# =====================================================================
# 12. SWOT
# =====================================================================
doc.add_heading("12. SWOT", level=1)
t = doc.add_table(rows=2, cols=2)
t.style = "Table Grid"
quad = [
    ("Strengths", "Indian-language speech sounds; sound-level feedback with honest confidence; visual articulation; low cost to serve; working MVP", "E3F2EF"),
    ("Weaknesses", "Accuracy not yet proven on real learners; content needs clinical review; English interface; small team", "FDF3E2"),
    ("Opportunities", "~3,000 therapists for crores of people; 886 m internet users, 98% using Indic content; RBSK/DEIC and CSR channels; more languages", "E3F2EF"),
    ("Threats", "Global apps adding Indian languages; low willingness to pay; regulation if claims overreach; trust in AI feedback", "FDF3E2"),
]
for i, (title, text, fill) in enumerate(quad):
    c = t.rows[i // 2].cells[i % 2]
    c.width = Cm(8.3)
    shade(c, fill)
    c.text = ""
    p = c.paragraphs[0]
    p.add_run(title + "\n").bold = True
    p.add_run(text)
    for r in p.runs:
        r.font.size = Pt(9.5)
    if i < 2:
        p.paragraph_format.keep_with_next = True  # keep both SWOT rows on one page
for row in t.rows:
    cant = OxmlElement("w:cantSplit")
    cant.set(qn("w:val"), "true")
    row._tr.get_or_add_trPr().append(cant)
doc.add_paragraph()

# =====================================================================
# 13. Validation plan
# =====================================================================
doc.add_heading("13. Primary research to validate this report", level=1)
table(["Study", "Who", "What we learn"], [
    ["Parent survey (n ≥ 100)", "Parents in Tamil Nadu and one Hindi-speaking state",
     "How many children have speech-sound concerns; current spending and travel; willingness to pay; phone access"],
    ["Therapist interviews (n ≥ 10)", "Private and government speech therapists",
     "Caseloads, home-practice compliance, what data they want, whether they would recommend or license the app"],
    ["8-week pilot (n ≈ 30 children)", "Children with a confirmed speech-sound target, with a therapist",
     "Practice frequency, level progression, therapist-rated improvement, app accuracy vs therapist judgement, SUS score"],
], [4.2, 5.0, 7.4])
para("Suggested survey questions: Has anyone told you your child has difficulty with certain sounds? Have you seen a speech "
     "therapist — how far, how often, how much per session? What stopped you continuing? Would you use a phone app for "
     "10 minutes a day? What would you pay per year? Which language does your child speak at home?", size=10)

# =====================================================================
# Sources
# =====================================================================
doc.add_heading("Sources", level=1)
para("Accessed October 2026. Several figures come from secondary summaries or commercial reports; check the primary "
     "documents before final submission.", italic=True, color=GREY, size=9)
SOURCES = [
    ("Census of India 2011 — disability data (summary)", "https://www.languageinindia.com/jan2014/disabilityinindia2011data.pdf"),
    ("India’s disability estimates: limitations and way forward, PLOS ONE", "https://journals.plos.org/plosone/article?id=10.1371%2Fjournal.pone.0222159"),
    ("Economic gradient of onset of disability in India (NSS 76th round)", "https://www.ncbi.nlm.nih.gov/pmc/articles/PMC8061006/"),
    ("AIISH — school screening report on communication disorders", "https://aiishmysore.in/storage/files/full-report-school-screening.pdf"),
    ("Prevalence of speech, language and hearing impairment in rural school children (IJCMPH)", "https://www.ijcmph.com/index.php/ijcmph/article/download/6885/4327/27568"),
    ("A survey of telepractice in speech-language pathology and audiology in India (JISHA)", "https://www.ncbi.nlm.nih.gov/pmc/articles/PMC5716619/"),
    ("India needs 10 times the number of audiologists it has (Careers360)", "https://www.magzter.com/stories/education/Careers-360/INDIA-NEEDS-10-TIMES-THE-NUMBER-OF-AUDIOLOGISTS-IT-HAS"),
    ("Sri Ramachandra — tele-practice for rural speech and hearing services", "https://sriramachandra.edu/?p=9435"),
    ("Online speech therapy cost in India — 2026 pricing guide (NeuroNurture)", "https://neuronurture.com/blog/speech-therapy-cost-india-guide/"),
    ("Treatment intensity of speech intervention via telepractice (EBP brief)", "https://www.pearsonassessments.com/content/dam/school/global/clinical/us/assets/ebp-briefs/ebp-v15a3.pdf"),
    ("Average cost of speech therapy sessions in India (Sphere Speech & Hearing)", "https://spherespeechandhearingcare.com/cost-of-speech-therapy/"),
    ("India speech therapy services market outlook 2030 (Grand View Research)", "https://www.grandviewresearch.com/horizon/outlook/speech-therapy-services-market/india"),
    ("Prevalence of stuttering among school-age children, Dakshina Kannada", "https://doaj.org/article/c3f3d4bb57974aaba58bc39c298e5f5f"),
    ("Incidence & prevalence of stroke in India: a systematic review (IJMR); aphasia 21–38% cited in trial protocol NCT07496645",
     "https://ijmr.org.in/incidence-prevalence-of-stroke-in-india-a-systematic-review/"),
    ("NIDCD — nearly 1 in 12 children has a voice, speech, language or swallowing disorder", "https://www.nidcd.nih.gov/news/2015/about-1-12-children-has-disorder-related-voice-speech-language-or-swallowing"),
    ("NITI Aayog / NHA — out-of-pocket expenditure 39.4% in 2021-22", "https://health.medicaldialogues.in/health/niti-aayog-reports-drop-in-out-of-pocket-health-expenditure-to-394-in-2021-22-135488"),
    ("UNFPA 2024 — India population 144 crore, 24% aged 0–14", "https://www.pressreader.com/india/millennium-post-kolkata/20240418/281548000939227"),
    ("Languages of India — Census 2011 speaker counts", "https://en.wikipedia.org/wiki/Languages_of_India"),
    ("Speech therapy apps for kids market report (MarketIntelo)", "https://marketintelo.com/report/speech-therapy-apps-for-kids-market"),
    ("IAMAI–Kantar Internet in India 2024 (via IBEF / MediaNama)", "https://www.ibef.org/news/india-s-internet-users-to-exceed-900-million-in-2025-driven-by-indic-languages"),
    ("Stamurai — App Store listing (India) and therapy packages", "https://www.stamurai.com/personal-therapy/"),
    ("Speech Sounds Visualized — App Store", "https://apps.apple.com/us/app/speech-sounds-visualized/id1300151606"),
    ("Pronunciation Coach 3D (icSpeech)", "https://icspeech.com/pronunciation-coach-3D.html"),
    ("SpeechLP — App Store", "https://apps.apple.com/us/app/speechlp-speech-therapy-games/id6752866135"),
    ("Sarvam AI — API pricing", "https://docs.sarvam.ai/api-reference-docs/pricing"),
    ("RBSK — District Early Intervention Centre guidelines (MoHFW)", "https://nhm.hp.gov.in/storage/app/media/uploaded-files/GoI%20DEIC%20guidelines.pdf"),
    ("RBSK in Tamil Nadu (34 DEICs) — NHM Tamil Nadu", "https://www.nhm.tn.gov.in/en/nhm-programsrmncha/rashtriya-bal-swasthya-karyakram-rbsk"),
    ("Setting up of District Disability Rehabilitation Centres (scheme from April 2022)", "https://cdnbbsr.s3waas.gov.in/s3e58aea67b01fa747687f038dfde066f6/uploads/2023/12/202408142124777532.pdf"),
    ("Little Bee Speech — Articulation Station membership pricing", "https://www.littlebeespeech.com/blog/what-is-the-little-bee-hive-membership/"),
    ("Best speech therapy software 2026 (includes Speech Blubs pricing; aggregator)", "https://gitnux.org/best/speech-therapy-software/"),
]
for i, (title, url) in enumerate(SOURCES, 1):
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(2)
    r = p.add_run(f"[{i}] {title}. ")
    r.font.size = Pt(8.5)
    link(p, url, url)

# footer
fp = sec.footer.paragraphs[0]
fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
run = fp.add_run("SayBetter AI — Market research   ·   page ")
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
