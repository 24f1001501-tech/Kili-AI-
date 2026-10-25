# Kili AI (SayBetter) — Project handoff

Everything needed to continue this project in a new Claude session (any account) or by hand.
Last updated: **25 October 2026**.

> **To resume with Claude:** open a new session in the project folder (see §2) and paste the prompt in §12.

---

## 1. What this is

**SayBetter AI** (mascot **Kili the parrot**; *kili* = parrot in Tamil) is a speech-sound practice app for
**Tamil and Hindi**. A learner says a word; the app checks the **one target sound**, says which sound it actually heard
(e.g. “We heard स instead of श”), shows animated side-view mouth diagrams of the target vs. the heard sound, gives one
specific tip, and moves a 5-level practice plan up or down from saved results.

Positioning: **practice support, not diagnosis** — it doesn’t replace a speech-language therapist (SLP).
Built for an entrepreneurship case competition (sustainability / social impact / well-being track), with the goal of a
real public launch.

**Status (25 Oct 2026)**

| Area | Status |
|---|---|
| App (local) | ✅ Working end to end: onboarding, 2-minute baseline, practice, feedback, plan, progress, settings |
| Accuracy | ✅ Measured on 1,218 Sarvam-voice clips (§6). Hindi strong, Tamil ழ/ள weak (app says “not sure”) |
| UI | ✅ Candy-pop redesign, Kili mascot, subtle motion, mobile-ready |
| Docs | ✅ Feature showcase, project summary, market research (Word), accuracy report, 17 screenshots |
| GitHub | ✅ https://github.com/24f1001501-tech/Kili-AI- (public, branch `main`) |
| Backend hosting | ⏳ Google Cloud Run — project `kili-ai-542225` created, **waiting for a billing account** |
| Frontend hosting | ⏳ Vercel — not imported yet; `vercel.json` still has placeholder `HF_SPACE_HOST` |
| Real-user validation | ❌ Not done — needs native-speaker recordings and SLP content review |

---

## 2. Where everything is

| What | Location | Notes |
|---|---|---|
| **GitHub repo (source of truth)** | https://github.com/24f1001501-tech/Kili-AI- | Everything except secrets and big downloads |
| Current working copy | `C:\Users\srik6\AppData\Local\Claude-Data\claude_pzs8sxrjxfjjc\scratch-workspaces\823d3f77-b9d0-43d1-958a-ce5e519deb2c\dfd16e65-ff19-47e5-a30e-1b9e7bd2f7a2\scratch-2026-10-24-b45a6a\saybetter` | A **temporary** folder tied to the old Claude session — it is deleted with that session. Don’t rely on it |
| **Recommended permanent copy** | `D:\SIGMA\Kili-AI-` | Create with: `git clone https://github.com/24f1001501-tech/Kili-AI-.git D:\SIGMA\Kili-AI-` |
| Sarvam API key | `backend\.env` (`SARVAM_API_KEY=...`) | **Not in GitHub.** Copy `backend\.env` from the working copy above into the permanent copy, or re-create it from `backend\.env.example` |
| Python environment | `%LOCALAPPDATA%\SayBetter\venv` | Created by `run.ps1` on first start (~1.5 GB with PyTorch) |
| Speech model cache | `%USERPROFILE%\.cache\huggingface\hub\models--facebook--wav2vec2-xlsr-53-espeak-cv-ft` | ~1.2 GB, downloaded on first start |
| Local database + cached voice clips | `backend\var\` (`saybetter.db`, `reference\*.wav`, `audio\`) | Not in GitHub; recreated automatically |
| Measured accuracy (used by the app) | `backend\app\data\calibration.json` | In GitHub |
| Practice content | `backend\app\data\targets.json` | In GitHub; **draft — needs SLP review** |
| Word docs | `docs\SayBetter_Feature_Showcase.docx`, `docs\SayBetter_AI_Summary.docx`, `docs\SayBetter_Market_Research.docx` | In GitHub |
| Screenshots | `docs\screenshots\*.png` (17) | In GitHub |
| Accuracy report | `docs\accuracy-report.md` | In GitHub |
| Google Cloud project | `kili-ai-542225` (account srik6067@gmail.com), region `asia-south1` | Billing not linked yet |
| Git | `C:\Program Files\Git\cmd\git.exe` | Installed |
| Python 3.12 | `%LOCALAPPDATA%\Python\pythoncore-3.12-64\python.exe` | Installed (Python install manager) |

> ⚠️ Quirk seen on this PC: files Claude created under `%LOCALAPPDATA%` from inside Claude’s sandbox were **invisible
> to your own terminal**. If something “should exist” there but doesn’t, just run `Start-Kili-AI.cmd` — it recreates
> the environment.

---

## 3. Start the app (no Claude needed)

```
cd /d D:\SIGMA\Kili-AI-
Start-Kili-AI.cmd
```

The browser opens **http://localhost:8000** when ready (first run: 5–15 min of downloads). Close the window to stop.
Microphone works in Chrome/Edge. Full guide for other PCs: [SETUP.md](SETUP.md).

---

## 4. Repository map

```
Kili-AI-/
├─ Start-Kili-AI.cmd        one-click launcher (Windows)
├─ run.ps1                  finds Python 3.12/3.13, builds venv, starts uvicorn, opens browser
├─ Dockerfile               backend container (CPU torch + model baked in), port 7860
├─ vercel.json              Vercel: serves frontend/, rewrites /api/* to the backend host (placeholder!)
├─ .vercelignore / .gcloudignore / .gitignore
├─ README.md  SETUP.md  PROJECT_HANDOFF.md
├─ backend/
│  ├─ requirements.txt      fastapi, uvicorn, httpx, numpy, python-dotenv, transformers (+ torch CPU)
│  ├─ .env.example          SARVAM_API_KEY, model names, PHONEME_ENGINE
│  ├─ app/
│  │  ├─ main.py            FastAPI routes, profile keys, rate limiting, serves frontend at /
│  │  ├─ config.py          env/config (DATA_DIR, Sarvam models, ALLOW_PROFILE_LIST, RATE_LIMIT_PER_MIN)
│  │  ├─ db.py              SQLite schema (users, learning_plans, practice_sessions, practice_attempts,
│  │  │                     feedback_records, progress_records) + migration adding users.api_key
│  │  ├─ content.py         loads targets.json; baseline items (2 level-2 words per sound)
│  │  ├─ audio.py           WAV decode/resample to 16 kHz, quality checks, silence trim (no ffmpeg)
│  │  ├─ g2p.py             Tamil/Devanagari script → IPA (rule-based, Hindi schwa deletion, nukta handling)
│  │  ├─ compare.py         weighted Levenshtein alignment; judges only the target-sound positions
│  │  ├─ analysis.py        pipeline + evidence fusion (log-odds of measured precision), statuses
│  │  ├─ calibration.py     loads calibration.json; precision per sound × check × verdict
│  │  ├─ coach.py           picks one pre-written tip per outcome / mix-up
│  │  ├─ planner.py         adaptive 5-level rules, baseline ranking, next-item choice
│  │  ├─ engines/sarvam.py      Sarvam STT (saaras:v3 verbatim) + TTS (bulbul:v3), retry/backoff, TTS cache
│  │  ├─ engines/phonemes.py    wav2vec2-xlsr-53-espeak-cv-ft: IPA decoding + hidden-layer features
│  │  ├─ engines/templates.py   voice comparison: DTW vs 6 Sarvam voices × (correct + each mix-up)
│  │  └─ data/targets.json, data/calibration.json
│  └─ tools/calibrate.py    regenerates calibration.json + report (~₹18 of Sarvam credit)
├─ frontend/                plain HTML/CSS/JS, no build step
│  ├─ index.html, styles.css   design tokens, sticker style, Kili poses, reduced-motion support
│  └─ js/ app.js (router + all views), api.js (fetch + profile key), recorder.js (mic → 16 kHz WAV),
│         diagrams.js (animated SVG mouth), ui.js (Kili SVG + icon set)
├─ deploy/
│  ├─ cloudrun.ps1          deploys backend to Google Cloud Run from the repo root
│  ├─ deploy_space.py       Hugging Face Space uploader (blocked: Docker Spaces now need HF PRO)
│  └─ hf-space-README.md
├─ dev/scripts/             tests, probes, screenshot tour, Word-doc generators (see §8)
└─ docs/                    Word docs, accuracy report, screenshots
```

---

## 5. Methodology — how it was built

**1. Research first.** Web research on existing apps (Speech Tutor, Speech Sounds Visualized, Pronunciation Coach 3D,
SpeechLP, Sara, Speech Blubs, Stamurai, Articulation Station, ultrasound/EPG tools). Finding: nobody combines Indian-
language speech sounds + sound-level AI feedback + visual articulation at app prices → the gap we target.

**2. Lean MVP before polish.** Decisions taken with the founder up front: Tamil + Hindi, Sarvam + local phoneme model,
local FastAPI + SQLite (no login), animated diagrams instead of video avatars. Node.js wasn’t installed, so the frontend
is plain JS served by FastAPI (no build step).

**3. Content as data.** `targets.json`: 6 target sounds (Tamil ழ ள ர; Hindi र श ख), each with plain-language steps,
diagram type, common mix-ups (each with its own tip + diagram) and 5 levels (sound → short words → positions → phrases
→ sentences). Tamil/Devanagari spell sounds almost one-to-one, so ழ/ள/ல are distinct letters — this makes letter-level
checking meaningful.

**4. Analysis pipeline (per attempt).**
1. Browser records mic → 16 kHz mono WAV (`recorder.js`) → `POST /api/attempts`.
2. Quality gate: too short / too quiet / no speech / clipped / noisy (`audio.py`).
3. Three independent checks, each producing *on_target / substitution(letter) / unclear* for the target positions only:
   - **Sarvam speech-to-text** (`saaras:v3`, `mode=verbatim`) → align letters (`compare.check_transcript`).
   - **Phoneme model** (wav2vec2 espeak IPA, greedy CTC) → align IPA vs. rule-based g2p (`compare.check_phonemes`).
   - **Sarvam voice comparison** (`templates.py`): Sarvam TTS says the item correctly and with each mix-up in 6 voices;
     layer-18 wav2vec2 features + DTW; each version scored by the mean of its 2 closest voices; closest wins.
4. **Fusion** (`analysis.fuse`): each check’s *measured* precision for that sound & verdict becomes log-odds evidence
   (+ if it agrees, − if it disagrees). Checks under 60 % precision are ignored for that sound. Confidence capped at
   95 %, −10 % for noisy audio, **below 55 % → “not sure”** (no claim).
5. Coach picks one tip; planner updates the level; everything is saved.

**5. Key findings that shaped the design**
- Sarvam STT **autocorrects** mix-ups into real words (सेर → शेर, மளை → மழை) in every model/mode; it only catches
  mix-ups that form another real word. Cutting out single syllables didn’t help either.
- The multilingual phoneme model is good for Hindi श/स but hears even correct Tamil ழ as l/r.
- → Added the **voice-comparison** check, which doesn’t need any model to “know” ழ. Best setting found by experiment:
  layer 18 + best-2 scoring (vs. layer 12 voting).

**6. Calibration.** `tools/calibrate.py`: Sarvam TTS generates every level 1–3 item correctly and with each mix-up in 6
voices = **1,218 clips**; all checks run on them (leave-one-voice-out for voice comparison); precisions saved to
`calibration.json`. ⚠️ Synthetic voices = best case, and the fused accuracy is in-sample (optimistic).

**7. Adaptive plan (transparent rules).** Baseline: 6 words → rank sounds (substitutions×2 + unclear) → start level
1–3. Then: 3 of last 4 confident attempts on target → level up; 3 of 4 mix-ups → level down; 6 mix-ups in a row at
level 1 → suggest a therapist; “not sure” never moves the level. After a miss, retry the same word.

**8. Design.** Skills used: `frontend-design`, `ui-ux-pro-max`. Candy-pop palette (coral #FF6B6B, sunshine #FFD93D,
sky #4D96FF, grape #9B5DE5, ink #2B2D42), sticker style (2.5 px ink outlines, hard offset shadows), Baloo 2 / Baloo
Thambi 2 / DM Sans, Kili with 5 moods, subtle meaningful motion, `prefers-reduced-motion` respected, 48 px tap targets,
AA contrast (text in ink or deep variants, candy colours only as fills).

**9. Security for public hosting.** Each profile has a secret `api_key` (header `X-Profile-Key`); hosted mode hides the
profile list (`ALLOW_PROFILE_LIST=0`); per-IP rate limit on credit-spending endpoints (`RATE_LIMIT_PER_MIN`, default
40); recordings deleted after analysis unless opted in; one-tap delete of all data. No secrets in Git.

**10. Testing.** Unit tests of g2p/alignment (`test_logic.py`), fusion (`test_fuse.py`), API end-to-end with TTS clips
(`test_api.py`, `test_plan.py`), security (`test_security.py`), Sarvam probes, and a headless-Edge (CDP) screenshot tour
that clicks through every feature with real Sarvam audio (`shots.py`) — also used as the UI regression check.

---

## 6. Measured accuracy (synthetic, best case)

| Sound | Final verdict right | Wrong | “Not sure” | Right when it made a call |
|---|---|---|---|---|
| श (sha) | 95 % | 5 % | 0 % | 95 % |
| र (ra, Hindi) | 80 % | 20 % | 0 % | 80 % |
| ர (ra, Tamil) | 75 % | 25 % | 1 % | 75 % |
| ख (kha) | 74 % | 23 % | 2 % | 76 % |
| ழ (zha) | 30 % | 10 % | 60 % | 76 % |
| ள (La) | 0 % | 0 % | 100 % | — |

Per-check numbers: [docs/accuracy-report.md](docs/accuracy-report.md).

---

## 7. API (FastAPI, interactive docs at `/docs`)

`POST /api/attempts` (multipart: session_id, speech_target_id, item_text, audio) · `GET /api/plan[?advance=true]` ·
`PUT /api/plan/active` · `GET /api/progress` · `GET /api/attempts` · `GET /api/accuracy` · `GET /api/health` ·
`GET /api/reference` (Sarvam TTS) · `POST /api/profiles` · `POST /api/profiles/demo` · `GET|PATCH|DELETE /api/me` ·
`GET /api/baseline` · `POST /api/sessions` · `POST /api/sessions/{id}/complete` · `GET /api/targets`.
All profile endpoints need header `X-Profile-Key`.

---

## 8. Dev scripts (`dev/scripts/`)

Run with the venv Python, e.g. `%LOCALAPPDATA%\SayBetter\venv\Scripts\python.exe -X utf8 dev\scripts\<file> <args>`.
Most take the backend folder as the first argument.

| Script | Purpose |
|---|---|
| `test_logic.py`, `test_fuse.py`, `test_security.py` | Unit-level checks (no server) |
| `test_api.py`, `test_plan.py`, `test_model.py` | End-to-end against a running server / the model |
| `smoke_sarvam.py`, `probe_sarvam.py`, `probe_syllables.py` | Sarvam STT/TTS behaviour probes |
| `proto_templates*.py` | Voice-comparison experiments (layers, scoring) |
| `gen_clips.py` + `shots.py` + `shot_settings.py` | Generate Sarvam test clips, then headless-Edge screenshot tour |
| `make_doc.py`, `make_market_doc.py`, `make_showcase.py` | Rebuild the three Word documents (need `pip install python-docx`) |

Recalibrate accuracy (from the `backend\` folder):
`%LOCALAPPDATA%\SayBetter\venv\Scripts\python.exe -X utf8 -m tools.calibrate --dry-run`, then run it again without
`--dry-run`. It rewrites `app\data\calibration.json` and `var\calibration_report.md`.

---

## 9. Finishing the deployment

**Plan:** backend on **Google Cloud Run** (Hugging Face free Docker Spaces now require PRO), frontend on **Vercel**.

1. **Billing:** create a billing account at https://console.cloud.google.com/billing/create (needs a card; Cloud Run
   free tier should cover a demo; image storage ≈ ₹20–25/month).
2. **Deploy backend:** from the repo folder, first reuse the existing project, then run the script:
   ```
   echo kili-ai-542225> deploy\gcp_project.txt
   powershell -ExecutionPolicy Bypass -File deploy\cloudrun.ps1
   ```
   (signs you in, uses the project in `deploy\gcp_project.txt` — or creates a new one if that file is missing —
   links billing, builds the Dockerfile in Google Cloud, deploys with 4 GiB RAM / 2 vCPU / max 1 instance,
   prints `Backend live at: https://…run.app` and saves it to `deploy\cloudrun_url.txt`).
   *If the old terminal tab is still waiting at “Press Enter when it’s created”, you can just press Enter there.*
3. **Point Vercel at it:** in `vercel.json` replace `HF_SPACE_HOST` with the Cloud Run host (without `https://`),
   commit and push.
4. **Vercel:** https://vercel.com/new → import `24f1001501-tech/Kili-AI-` → Framework “Other” → Deploy
   (`vercel.json` already sets output `frontend/` and the `/api` rewrite).
5. **Test live:** onboarding → baseline → practice (upload/record) → feedback → dashboard → settings accuracy table.

Hosted limits: scale-to-zero cold start ~30–60 s; SQLite resets when the instance restarts; Sarvam credit is spent by
visitors (rate-limited per IP).

---

## 10. Road to a real launch

1. **Validation:** record 5–10 native Tamil/Hindi speakers (correct + natural mix-ups), re-run calibration on real
   speech; SLP review of `targets.json` tips and diagrams; small pilot (≈30 children, 8 weeks).
2. **Accuracy:** fine-tune / swap the phoneme model on real Tamil data (AI4Bharat Indian-language models are an option);
   use real recordings as voice-comparison templates.
3. **Product:** real accounts + persistent DB (Supabase Auth + Postgres), clinic/therapist dashboard, Tamil/Hindi UI
   (Sarvam translation), more sounds and languages, offline/PWA, Android-first testing on low-end phones.
4. **Compliance:** DPDP Act 2023 — verifiable parental consent for children, privacy policy, data retention; keep
   “practice support, not diagnosis” wording to stay outside medical-device rules until validated.
5. **Business:** freemium → Family ₹149/mo or ₹999/yr, Clinic ₹499/therapist/mo, Institution/CSR ≈ ₹300/child/yr
   (see `docs/SayBetter_Market_Research.docx`); go-to-market: Tamil Nadu pilot → Hindi launch → DEIC/DDRC/CSR.
6. **Ops:** custom domain on Vercel, uptime monitoring, error logging, Sarvam usage alerts, Secret Manager for keys.

---

## 11. Secrets checklist

- **Sarvam key** lives only in `backend\.env` (local) and as a Cloud Run env var. It was pasted in an earlier chat →
  **create a new key** in the Sarvam dashboard and update both places.
- **Hugging Face token** pasted in chat earlier → **revoke it** at https://huggingface.co/settings/tokens (not needed now).
- Never commit `backend\.env`; `.gitignore` already excludes it, `backend/var/` and the deploy id files.

---

## 12. Prompt to resume in a new Claude session

> I'm continuing the **Kili AI / SayBetter** project. The code is in this folder (cloned from
> https://github.com/24f1001501-tech/Kili-AI-). First read `PROJECT_HANDOFF.md`, `README.md` and `SETUP.md`.
> Current goal: finish deployment — Google Cloud Run backend (project `kili-ai-542225`, script `deploy\cloudrun.ps1`)
> and Vercel frontend (update `vercel.json` placeholder `HF_SPACE_HOST` with the Cloud Run host), then test the live
> site end to end. Keep the security rules (profile keys, rate limits, no secrets in Git) and the honest-confidence
> behaviour. Don't print or commit my Sarvam key; it's in `backend\.env`.
