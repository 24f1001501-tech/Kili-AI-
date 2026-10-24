# Run Kili AI (SayBetter) on another computer

The GitHub repo has all the code, practice content and accuracy data. Two things are **not** in it, on purpose:

| Not in GitHub | Why | What to do |
|---|---|---|
| Your **Sarvam API key** (`backend/.env`) | It's a secret | Create `backend/.env` (step 4) and paste your key |
| The ~1.5 GB of Python packages and speech model | Too big for Git | Downloaded automatically on the first run |

Optional: the cached Sarvam voice clips aren't in GitHub either. The app recreates them on demand, so the first
attempt at each word is a few seconds slower and uses a little Sarvam credit (fractions of a rupee).

## What the other computer needs

- **Windows 10/11** (for the one-click launcher; Mac/Linux steps are at the end)
- **Python 3.12** — https://www.python.org/downloads/ (tick **“Add python.exe to PATH”** while installing)
- **Git** — https://git-scm.com/download/win (or download the repo as a ZIP from GitHub instead)
- **Internet** for the first run (about 1.5 GB) and for Sarvam
- **8 GB RAM** recommended (the speech model uses about 2 GB)
- **Chrome or Edge** (for the microphone)

## Steps (Windows)

1. Open **Command Prompt** and go to a folder you'll keep, for example:
   ```
   cd /d D:\Projects
   ```
2. Download the code:
   ```
   git clone https://github.com/24f1001501-tech/Kili-AI-.git
   cd Kili-AI-
   ```
3. Start it once (this sets everything up — 5–15 minutes the first time):
   ```
   Start-Kili-AI.cmd
   ```
4. It creates `backend\.env`. Open it in Notepad and put your Sarvam key after `SARVAM_API_KEY=`, save, then close the
   app window and run `Start-Kili-AI.cmd` again.
   ```
   notepad backend\.env
   ```
5. The browser opens **http://localhost:8000** by itself when the app is ready. Close the black window to stop the app.

After the first time, starting is just: double-click **`Start-Kili-AI.cmd`** in the `Kili-AI-` folder
(or right-click it → *Send to* → *Desktop (create shortcut)* for a desktop icon).

## Getting the latest version later

```
cd /d D:\Projects\Kili-AI-
git pull
```

## Mac / Linux

```bash
git clone https://github.com/24f1001501-tech/Kili-AI-.git && cd Kili-AI-
python3.12 -m venv ~/.saybetter-venv
~/.saybetter-venv/bin/pip install torch --index-url https://download.pytorch.org/whl/cpu
~/.saybetter-venv/bin/pip install -r backend/requirements.txt
cp backend/.env.example backend/.env   # then add your Sarvam key
cd backend && ~/.saybetter-venv/bin/python -m uvicorn app.main:app --port 8000
```

Then open http://localhost:8000.

## If something goes wrong

| Problem | Fix |
|---|---|
| “Python 3.12 is needed” | Install Python 3.12 from python.org with “Add to PATH” ticked, open a new Command Prompt, run again |
| Page says the sound model is loading | Wait about 10 seconds after start; the first run also downloads it (1.2 GB) |
| “Sarvam key not set” chip | Add the key to `backend\.env`, restart the app |
| Microphone doesn't work | Use Chrome or Edge at http://localhost:8000 and allow the microphone |
| Port 8000 already in use | Close the other app window that's running Kili AI |
