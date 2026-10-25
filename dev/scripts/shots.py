"""Drive headless Edge over CDP through every SayBetter feature and save screenshots."""
import asyncio
import base64
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import httpx
import websockets

EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
BASE = "http://localhost:8000"
OUT = Path(sys.argv[1])
PORT = 9333
LOG = []


class Page:
    def __init__(self, ws):
        self.ws, self.n = ws, 0

    async def send(self, method, params=None):
        self.n += 1
        mid = self.n
        await self.ws.send(json.dumps({"id": mid, "method": method, "params": params or {}}))
        while True:
            msg = json.loads(await self.ws.recv())
            if msg.get("id") == mid:
                if "error" in msg:
                    raise RuntimeError(f"{method}: {msg['error']}")
                return msg.get("result", {})

    async def js(self, code):
        r = await self.send("Runtime.evaluate", {"expression": f"(async () => {{ {code} }})()", "awaitPromise": True, "returnByValue": True})
        if r.get("exceptionDetails"):
            raise RuntimeError(r["exceptionDetails"].get("exception", {}).get("description", str(r["exceptionDetails"])))
        return r.get("result", {}).get("value")

    async def viewport(self, w, h, dsf=1.5, mobile=False):
        await self.send("Emulation.setDeviceMetricsOverride", {"width": w, "height": h, "deviceScaleFactor": dsf, "mobile": mobile})

    async def go(self, hash_, settle=1.3):
        await self.js(f"location.hash = {json.dumps(hash_)}; return 1;")
        await asyncio.sleep(settle)
        await self.js("await document.fonts.ready; window.scrollTo(0,0); return 1;")
        await asyncio.sleep(0.4)

    async def shot(self, name, selector=None, full=False, pad=16):
        # hide anything the browser injects outside the app (e.g. an Edge assistant button)
        await self.js("""document.querySelectorAll('body > *').forEach(e => {
            if (!e.matches('.topbar, main, .toast, .skip, script')) e.style.setProperty('display', 'none', 'important'); });
            document.querySelectorAll('html > *:not(head):not(body)').forEach(e => e.style.setProperty('display', 'none', 'important'));
            return 1;""")
        if selector:
            rect = await self.js(f"""const el = document.querySelector({json.dumps(selector)});
                window.scrollTo(0, el.getBoundingClientRect().top + scrollY - 110);
                await new Promise(r => setTimeout(r, 450)); const b = el.getBoundingClientRect();
                return {{x: b.left + scrollX, y: b.top + scrollY, w: b.width, h: b.height}};""")
            clip = {"x": max(0, rect["x"] - pad), "y": max(0, rect["y"] - pad), "width": rect["w"] + 2 * pad, "height": rect["h"] + 2 * pad, "scale": 1}
            params = {"format": "png", "clip": clip, "captureBeyondViewport": True}
        elif full:
            m = await self.send("Page.getLayoutMetrics")
            cs = m["cssContentSize"]
            params = {"format": "png", "captureBeyondViewport": True,
                      "clip": {"x": 0, "y": 0, "width": cs["width"], "height": cs["height"], "scale": 1}}
        else:
            params = {"format": "png"}
        data = (await self.send("Page.captureScreenshot", params))["data"]
        (OUT / f"{name}.png").write_bytes(base64.b64decode(data))
        LOG.append(name)
        print("shot", name, flush=True)

    async def upload(self, spoken):
        """Put a clip into the recorder's file input and submit it."""
        return await self.js(f"""
            const idx = await (await fetch('/static/_shots/index.json')).json();
            const blob = await (await fetch('/static/_shots/' + idx[{json.dumps(spoken)}])).blob();
            const inp = document.querySelector('.recorder input[type=file]');
            const dt = new DataTransfer(); dt.items.add(new File([blob], 'attempt.wav', {{type: 'audio/wav'}}));
            inp.files = dt.files; inp.dispatchEvent(new Event('change'));
            await new Promise(r => setTimeout(r, 150));
            document.querySelector('[data-act=submit]').click();
            return 1;""")


async def wait_for(page, cond, timeout=60):
    t0 = time.time()
    while time.time() - t0 < timeout:
        if await page.js(f"return !!({cond});"):
            return True
        await asyncio.sleep(0.4)
    raise TimeoutError(cond)


TA_MIX = {"மழை": "மளை", "பழம்": "பலம்", "ழா": "ளா", "ழி": "ளி", "ஏழு": "ஏளு", "கோழி": "கோளி"}
HI_MIX = {"शा": "सा", "शी": "सी", "शेर": "सेर", "खाना": "काना"}


async def main():
    prof = Path(os.environ["LOCALAPPDATA"]) / "SayBetter" / "edge-prof"
    proc = subprocess.Popen([EDGE, "--headless=new", f"--remote-debugging-port={PORT}", f"--user-data-dir={prof}",
                             "--use-fake-ui-for-media-stream", "--use-fake-device-for-media-stream", "--hide-scrollbars",
                             "--window-size=1366,900", "--no-first-run", "about:blank"])
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
            await p.send("Runtime.enable")
            await p.viewport(1366, 900)
            await p.send("Page.navigate", {"url": BASE + "/"})
            await asyncio.sleep(2.5)
            await p.js("try { localStorage.clear(); } catch {} return 1;")
            await p.send("Page.reload")
            await asyncio.sleep(2.5)
            await p.js("await document.fonts.ready; return 1;")
            await asyncio.sleep(0.8)
            await p.shot("01_landing", full=True)

            # Onboarding
            await p.go("#/start")
            await p.js("""const f = document.querySelector('#f');
                f.display_name.value = 'Priya'; f.goal.value = 'Say ழ clearly when I talk at school';
                f.querySelector('input[value="encouraging"]').checked = true; return 1;""")
            await p.shot("02_onboarding", full=True)
            await p.js("document.querySelector('#f button[type=submit]').click(); return 1;")
            await wait_for(p, "document.querySelector('.recorder')")
            await asyncio.sleep(1.0)
            await p.shot("03_baseline", full=True)

            # Baseline: mix up the two ழ words, say the rest correctly
            for _ in range(6):
                word = await p.js("return document.querySelector('.target-word').textContent;")
                await p.upload(TA_MIX.get(word, word))
                await wait_for(p, f"!document.querySelector('.target-word') || document.querySelector('.target-word').textContent !== {json.dumps(word)} || document.querySelector('#res').textContent", 90)
                await asyncio.sleep(0.6)
            await wait_for(p, "document.body.textContent.includes('Your plan is ready')", 60)
            await asyncio.sleep(1.0)
            await p.shot("04_plan_ready", selector="#box")

            # Practice ழ
            await p.js("await fetch('/api/plan/active', {method:'PUT', headers:{'X-Profile-Id': localStorage.getItem('saybetter.profileId'), 'Content-Type':'application/json'}, body: JSON.stringify({speech_target_id:'ta-zha'})}); return 1;")
            await p.go("#/practice", settle=2.0)
            await p.shot("05_practice", full=True)
            await p.js("document.querySelector('.rec-btn').click(); return 1;")
            await asyncio.sleep(2.2)
            await p.shot("06_recording", selector=".practice-layout > .card")
            await p.js("document.querySelector('.rec-btn').click(); return 1;")
            await asyncio.sleep(1.0)
            word = await p.js("return document.querySelector('.target-word').textContent;")
            await p.upload(TA_MIX.get(word, word))
            await wait_for(p, "document.querySelector('.feedback')", 120)
            await asyncio.sleep(1.2)
            await p.shot("07_feedback_tamil", selector=".feedback")
            await p.js("document.querySelector('[data-act=retry]').click(); return 1;")
            await asyncio.sleep(1.0)
            word = await p.js("return document.querySelector('.target-word').textContent;")
            await p.upload(word)
            await wait_for(p, "document.querySelector('.feedback')", 120)
            await asyncio.sleep(1.2)
            await p.shot("08_feedback_tamil_retry", selector=".feedback")

            await p.go("#/learn/ta-zha", settle=1.5)
            await p.shot("09_sound_guide", full=True)
            await p.go("#/home", settle=1.8)
            await p.shot("10_dashboard", full=True)
            await p.go("#/progress", settle=1.8)
            await p.shot("11_progress", full=True)
            await p.go("#/settings", settle=2.5)
            await p.js("document.querySelectorAll('details').forEach(d => d.open = true); return 1;")
            await asyncio.sleep(0.5)
            await p.shot("12_settings_accuracy", full=True)

            # Hindi learner: श
            await p.js("""const u = await (await fetch('/api/profiles', {method:'POST', headers:{'Content-Type':'application/json'},
                body: JSON.stringify({display_name:'Arjun', preferred_language:'hi-IN', practice_goal:'Clear श in presentations', feedback_style:'step_by_step'})})).json();
                localStorage.setItem('saybetter.profileId', u.id);
                await fetch('/api/plan/active', {method:'PUT', headers:{'X-Profile-Id': String(u.id), 'Content-Type':'application/json'}, body: JSON.stringify({speech_target_id:'hi-sha'})});
                return u.id;""")
            await p.go("#/practice", settle=2.0)
            word = await p.js("return document.querySelector('.target-word').textContent;")
            await p.upload(HI_MIX.get(word, word))
            await wait_for(p, "document.querySelector('.feedback')", 120)
            await asyncio.sleep(1.2)
            await p.shot("13_feedback_hindi_mixup", selector=".feedback")
            await p.js("document.querySelector('[data-act=retry]').click(); return 1;")
            await asyncio.sleep(1.0)
            word = await p.js("return document.querySelector('.target-word').textContent;")
            await p.upload(word)
            await wait_for(p, "document.querySelector('.feedback')", 120)
            await asyncio.sleep(1.2)
            await p.shot("14_feedback_hindi_correct", selector=".feedback")

            # Mobile
            await p.viewport(390, 844, dsf=2, mobile=True)
            await p.go("#/progress", settle=1.0)
            await p.go("#/practice", settle=2.0)
            await p.shot("15_mobile_practice")
            await p.go("#/home", settle=1.8)
            await p.shot("16_mobile_dashboard")
            await p.js("try { localStorage.clear(); } catch {} return 1;")
            await p.go("#/", settle=1.8)
            await p.shot("17_mobile_landing")
    finally:
        proc.terminate()
    print(json.dumps(LOG))


if __name__ == "__main__":
    asyncio.run(main())
