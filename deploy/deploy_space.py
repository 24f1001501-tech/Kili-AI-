"""Create/update the Kili AI Hugging Face Space. Run it yourself: it asks for your
Hugging Face token and Sarvam key with hidden input and never prints them."""
import getpass
import os
from pathlib import Path

from huggingface_hub import HfApi, get_token, login

SPACE_DIR = Path(__file__).resolve().parent / "space"
SPACE_NAME = "kili-ai"

if not get_token():
    print("Create a token with WRITE access at https://huggingface.co/settings/tokens, then paste it below.")
    login(add_to_git_credential=False)

api = HfApi()
user = api.whoami()["name"]
repo_id = f"{user}/{SPACE_NAME}"
api.create_repo(repo_id, repo_type="space", space_sdk="docker", exist_ok=True)
print(f"Uploading {sum(1 for p in SPACE_DIR.rglob('*') if p.is_file())} files to {repo_id} ...")
api.upload_folder(folder_path=str(SPACE_DIR), repo_id=repo_id, repo_type="space",
                  commit_message="Deploy Kili AI backend")

key = os.environ.get("SARVAM_API_KEY", "").strip() or getpass.getpass("Paste your Sarvam API key (hidden; press Enter to skip): ").strip()
if key:
    api.add_space_secret(repo_id, "SARVAM_API_KEY", key)
    print("Saved SARVAM_API_KEY as a Space secret.")

host = f"{user}-{SPACE_NAME}".lower().replace("_", "-") + ".hf.space"
print(f"\nSpace page : https://huggingface.co/spaces/{repo_id}")
print(f"API host   : https://{host}")
(Path(__file__).resolve().parent / "space_host.txt").write_text(host, encoding="utf-8")
print("Done. The Space now builds (about 10 minutes the first time).")
