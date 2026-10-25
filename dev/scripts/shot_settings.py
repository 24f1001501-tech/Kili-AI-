"""Retake only the settings screenshot with a temporary Tamil profile, then delete it."""
import asyncio
import os
import subprocess
import sys
import time
from pathlib import Path

import httpx
import websockets

sys.path.insert(0, str(Path(__file__).parent))
from shots import EDGE, PORT, Page  # noqa: E402

OUT = Path(sys.argv[1])


async def main():
    u = httpx.post("http://127.0.0.1:8000/api/profiles", json={"display_name": "Priya", "preferred_language": "ta-IN",
                   "practice_goal": "Say ழ clearly when I talk at school", "feedback_style": "encouraging"}).json()
    prof = Path(os.environ["LOCALAPPDATA"]) / "SayBetter" / "edge-prof"
    proc = subprocess.Popen([EDGE, "--headless=new", f"--remote-debugging-port={PORT}", f"--user-data-dir={prof}",
                             "--hide-scrollbars", "--no-first-run", "about:blank"])
    try:
        for _ in range(40):
            try:
                tabs = httpx.get(f"http://127.0.0.1:{PORT}/json").json()
                if tabs:
                    break
            except Exception:
                time.sleep(0.5)
        ws_url = next(t["webSocketDebuggerUrl"] for t in tabs if t["type"] == "page")
        async with websockets.connect(ws_url, max_size=50_000_000) as ws:
            p = Page(ws)
            await p.send("Page.enable")
            await p.viewport(1366, 900)
            await p.send("Page.navigate", {"url": "http://localhost:8000/"})
            await asyncio.sleep(2)
            await p.js(f"localStorage.setItem('saybetter.profileId', '{u['id']}'); return 1;")
            await p.go("#/settings", settle=2.5)
            await p.js("document.querySelectorAll('details').forEach(d => d.open = true); return 1;")
            await asyncio.sleep(0.5)
            await p.shot("12_settings_accuracy", full=True)
    finally:
        proc.terminate()
        httpx.delete("http://127.0.0.1:8000/api/me", headers={"X-Profile-Id": str(u["id"])})


asyncio.run(main())
