import os
from pathlib import Path

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parent.parent
ROOT_DIR = BACKEND_DIR.parent
load_dotenv(BACKEND_DIR / ".env")

DATA_DIR = Path(os.getenv("SAYBETTER_DATA_DIR", BACKEND_DIR / "var"))
DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DATA_DIR / "saybetter.db"
AUDIO_DIR = DATA_DIR / "audio"
REFERENCE_DIR = DATA_DIR / "reference"
AUDIO_DIR.mkdir(exist_ok=True)
REFERENCE_DIR.mkdir(exist_ok=True)

FRONTEND_DIR = ROOT_DIR / "frontend"
CONTENT_PATH = Path(__file__).resolve().parent / "data" / "targets.json"

SARVAM_API_KEY = os.getenv("SARVAM_API_KEY", "").strip()
SARVAM_STT_MODEL = os.getenv("SARVAM_STT_MODEL", "saaras:v3")
SARVAM_TTS_MODEL = os.getenv("SARVAM_TTS_MODEL", "bulbul:v3")
SARVAM_TTS_SPEAKER = os.getenv("SARVAM_TTS_SPEAKER", "")

# "auto" loads the local phoneme model when torch is installed; "off" disables it.
PHONEME_ENGINE = os.getenv("PHONEME_ENGINE", "auto").lower()
PHONEME_MODEL_ID = os.getenv("PHONEME_MODEL_ID", "facebook/wav2vec2-xlsr-53-espeak-cv-ft")

# On a public deployment, never list profiles (each browser keeps its own secret profile key).
ALLOW_PROFILE_LIST = os.getenv("ALLOW_PROFILE_LIST", "1") == "1"
# Requests per minute per visitor for the endpoints that spend Sarvam credit.
RATE_LIMIT_PER_MIN = int(os.getenv("RATE_LIMIT_PER_MIN", "40"))

MAX_UPLOAD_BYTES = 5 * 1024 * 1024
MAX_SECONDS = 20.0
MIN_SECONDS = 0.3
