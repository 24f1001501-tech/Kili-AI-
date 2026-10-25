"""Profile keys, hidden listing and rate limits, against a throwaway database."""
import os
import sys
import tempfile

os.environ["SAYBETTER_DATA_DIR"] = tempfile.mkdtemp()
os.environ["ALLOW_PROFILE_LIST"] = "0"
os.environ["RATE_LIMIT_PER_MIN"] = "5"
os.environ["PHONEME_ENGINE"] = "off"
sys.path.insert(0, sys.argv[1])

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

with TestClient(app) as c:
    u = c.post("/api/profiles", json={"display_name": "A", "preferred_language": "ta-IN"}).json()
    print("key length", len(u["api_key"]), "id", u["id"])
    print("me with key ->", c.get("/api/me", headers={"X-Profile-Key": u["api_key"]}).status_code)
    print("me with id as key ->", c.get("/api/me", headers={"X-Profile-Key": str(u["id"])}).status_code)
    print("old id header ->", c.get("/api/me", headers={"X-Profile-Id": str(u["id"])}).status_code)
    print("listing ->", c.get("/api/profiles").json())
    codes = [c.post("/api/profiles", json={"display_name": "B", "preferred_language": "hi-IN"}).status_code for _ in range(6)]
    print("profile creation codes", codes)
    print("plan ->", c.get("/api/plan", headers={"X-Profile-Key": u["api_key"]}).status_code)
