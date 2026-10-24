import { api, ApiError, profile } from "./api.js";
import { diagram, diagramLabel } from "./diagrams.js";
import { Recorder } from "./recorder.js";
import { icon, kili, setKili } from "./ui.js";

const main = document.getElementById("main");
const nav = document.getElementById("nav");
const LANG = { "ta-IN": { name: "Tamil", native: "தமிழ்" }, "hi-IN": { name: "Hindi", native: "हिन्दी" } };

const state = { me: null, targets: null, levelNames: {}, health: null, session: null };

// ---------- helpers ----------

const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

function highlight(text, letter) {
  // Wrap the whole syllable (letter + its vowel signs) so marks never detach.
  const re = new RegExp(`${letter}\\p{M}*`, "gu");
  return esc(text).replace(re, (m) => `<span class="hl">${m}</span>`);
}

function toast(msg, ms = 3200) {
  const t = document.getElementById("toast");
  t.textContent = msg;
  t.classList.add("show");
  clearTimeout(toast.timer);
  toast.timer = setTimeout(() => t.classList.remove("show"), ms);
}

function render(html) {
  main.innerHTML = html;
  main.focus({ preventScroll: true });
  window.scrollTo(0, 0);
}

function errorBox(e) {
  return `<div class="notice warn" role="alert">${esc(e instanceof ApiError ? e.message : "Something went wrong. Please try again.")}</div>`;
}

async function loadMe() {
  if (!profile.id) return (state.me = null);
  try {
    state.me = await api("/api/me");
  } catch (e) {
    if (e.status === 401) profile.clear();
    state.me = null;
  }
  return state.me;
}

async function loadTargets() {
  if (!state.me) return [];
  if (!state.targets || state.targets.lang !== state.me.preferred_language) {
    const data = await api(`/api/targets?language=${state.me.preferred_language}`);
    state.targets = { lang: state.me.preferred_language, list: data.targets };
    state.levelNames = data.level_names;
  }
  return state.targets.list;
}
const targetById = (id) => state.targets?.list.find((t) => t.id === id);

async function loadHealth() {
  try { state.health = await api("/api/health"); } catch { state.health = null; }
  return state.health;
}

function engineChips() {
  const h = state.health;
  if (!h) return `<span class="chip bad"><i class="dot"></i>Server offline</span>`;
  const s = h.engines.sarvam.configured;
  const p = h.engines.phonemes.status;
  const pLabel = { ready: "Sound model ready", loading: "Sound model loading…", unavailable: "Sound model unavailable", off: "Sound model off", not_loaded: "Sound model starting" }[p] || p;
  return `<span class="chip ${s ? "ok" : "warn"}"><i class="dot"></i>${s ? "Sarvam speech-to-text connected" : "Sarvam key not set"}</span>
    <span class="chip ${p === "ready" ? "ok" : p === "loading" ? "" : "warn"}"><i class="dot"></i>${pLabel}</span>
    ${state.me?.is_demo ? `<span class="chip" style="background:var(--wash-grape);color:var(--grape-deep);border-color:var(--grape-deep)">Demo profile</span>` : ""}`;
}

// Five levels as stepping stones joined by a path: done, current, still ahead.
function stones(level, mastered = false) {
  const parts = [];
  for (let l = 1; l <= 5; l++) {
    const cls = mastered || l < level ? "done" : l === level ? "current" : "";
    if (l > 1) parts.push(`<span class="path ${mastered || l <= level ? "done" : ""}"></span>`);
    parts.push(`<span class="stone ${cls}">${cls === "done" ? icon("check") : l}</span>`);
  }
  return `<div class="stones" role="img" aria-label="Level ${level} of 5">${parts.join("")}</div>`;
}

function analysisReady() {
  const h = state.health;
  return h && (h.engines.sarvam.configured || h.engines.phonemes.status === "ready");
}

function setNav(route) {
  if (!state.me) { nav.innerHTML = ""; return; }
  const links = [["#/home", "Home"], ["#/practice", "Practice"], ["#/progress", "Progress"], ["#/settings", "Settings"]];
  nav.innerHTML = links.map(([href, label]) => `<a href="${href}" ${route === href ? 'aria-current="page"' : ""}>${label}</a>`).join("");
}

const MIC_ICON = icon("mic");
const STOP_ICON = icon("stop");

// Live voice waveform: bars scroll left as the microphone level arrives.
function waveform(canvas) {
  const ctx = canvas.getContext("2d");
  const N = 40;
  const levels = new Array(N).fill(0);
  let live = false, raf = 0;
  function size() {
    const r = canvas.getBoundingClientRect();
    const dpr = window.devicePixelRatio || 1;
    canvas.width = Math.max(1, r.width * dpr); canvas.height = Math.max(1, r.height * dpr);
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  }
  function draw() {
    const w = canvas.clientWidth, h = canvas.clientHeight;
    ctx.clearRect(0, 0, w, h);
    const gap = 3, bw = (w - gap * (N - 1)) / N;
    const styles = getComputedStyle(document.documentElement);
    const ink = styles.getPropertyValue("--ink").trim(), fill = styles.getPropertyValue(live ? "--coral" : "--grape").trim();
    levels.forEach((v, i) => {
      const bh = Math.max(6, Math.min(h - 4, (live ? v : 0) * h * 1.8));
      const x = i * (bw + gap), y = (h - bh) / 2;
      ctx.fillStyle = fill; ctx.strokeStyle = ink; ctx.lineWidth = 1.5;
      ctx.beginPath(); ctx.roundRect(x, y, bw, bh, bw / 2); ctx.fill(); ctx.stroke();
    });
    if (live) raf = requestAnimationFrame(draw);
  }
  size(); draw();
  return {
    push(v) { levels.shift(); levels.push(v); },
    start() { live = true; size(); cancelAnimationFrame(raf); draw(); },
    stop() { live = false; cancelAnimationFrame(raf); levels.fill(0); draw(); },
  };
}

// ---------- reference audio ----------

let refAudio = null;
async function playReference(targetId, text, lang) {
  try {
    refAudio?.pause();
    const res = await fetch(`/api/reference?target_id=${encodeURIComponent(targetId)}&text=${encodeURIComponent(text)}`);
    if (res.ok) {
      refAudio = new Audio(URL.createObjectURL(await res.blob()));
      await refAudio.play();
      return;
    }
  } catch { /* fall through to the browser voice */ }
  const voices = speechSynthesis?.getVoices?.() || [];
  const voice = voices.find((v) => v.lang?.toLowerCase().startsWith(lang.slice(0, 2)));
  if (voice) {
    const u = new SpeechSynthesisUtterance(text);
    u.voice = voice; u.lang = voice.lang; u.rate = 0.8;
    speechSynthesis.cancel();
    speechSynthesis.speak(u);
  } else {
    toast(`Reference audio needs a Sarvam API key (or a ${LANG[lang].name} voice installed on this device).`, 5000);
  }
}

// ---------- recorder widget ----------

function recorderWidget(container, { onSubmit, submitLabel = "Check my attempt", onState = () => {} }) {
  let blob = null;
  let url = null;
  const supported = Recorder.supported();
  container.innerHTML = `
    <div class="recorder">
      <button class="rec-btn" type="button" aria-label="Start recording" ${supported ? "" : "disabled"}>${MIC_ICON}</button>
      <canvas class="wave" aria-hidden="true"></canvas>
      <div class="rec-status" aria-live="polite">${supported ? "Tap the microphone and say the word" : "Recording isn't supported in this browser. You can upload a WAV file instead."}</div>
      <div class="btn-row rec-after" hidden>
        <button class="btn btn-secondary" data-act="play" type="button">${icon("play")} Play back</button>
        <button class="btn btn-primary" data-act="submit" type="button">${submitLabel}</button>
      </div>
      <label class="small muted" style="cursor:pointer">or <u>upload a WAV recording</u><input type="file" accept="audio/wav,.wav" class="sr-only"></label>
    </div>`;
  const btn = container.querySelector(".rec-btn");
  const wave = waveform(container.querySelector(".wave"));
  const status = container.querySelector(".rec-status");
  const after = container.querySelector(".rec-after");
  const file = container.querySelector("input[type=file]");

  const rec = new Recorder({
    onLevel: (p) => wave.push(p),
    onTick: (s) => { status.textContent = `Recording… ${s.toFixed(1)}s — tap to stop`; },
    onAutoStop: () => stop(),
  });

  async function start() {
    try {
      await rec.start();
      blob = null; after.hidden = true;
      wave.start(); onState("listening");
      btn.classList.add("recording"); btn.innerHTML = STOP_ICON; btn.setAttribute("aria-label", "Stop recording");
      status.textContent = "Recording… tap to stop";
    } catch (e) {
      status.textContent = e.name === "NotAllowedError"
        ? "Microphone access was blocked. Allow the microphone in your browser's site settings, then try again."
        : e.name === "NotFoundError" ? "No microphone was found. Connect one, or upload a WAV file." : "Couldn't start the microphone.";
    }
  }
  async function stop() {
    const b = await rec.stop();
    btn.classList.remove("recording"); btn.innerHTML = MIC_ICON; btn.setAttribute("aria-label", "Record again");
    wave.stop(); onState("idle");
    if (!b) return;
    setBlob(b, "Got it. Play it back, or check your attempt.");
  }
  function setBlob(b, msg) {
    blob = b;
    if (url) URL.revokeObjectURL(url);
    url = URL.createObjectURL(b);
    after.hidden = false;
    status.textContent = msg;
  }
  btn.addEventListener("click", () => (rec.recording ? stop() : start()));
  file.addEventListener("change", () => {
    const f = file.files[0];
    if (!f) return;
    if (!/\.wav$/i.test(f.name) && f.type !== "audio/wav") { status.textContent = "Please choose a .wav file."; return; }
    setBlob(f, `Loaded ${f.name}.`);
    file.value = "";
  });
  after.addEventListener("click", async (e) => {
    const act = e.target.closest("button")?.dataset.act;
    if (act === "play" && url) new Audio(url).play();
    if (act === "submit" && blob) {
      after.querySelectorAll("button").forEach((b) => (b.disabled = true));
      btn.disabled = true;
      status.innerHTML = `<span class="spinner"></span> Listening carefully…`;
      onState("thinking");
      try {
        await onSubmit(blob, url);
      } finally {
        after.querySelectorAll("button").forEach((b) => (b.disabled = false));
        btn.disabled = !supported;
      }
    }
  });
  return { cancel: () => rec.cancel() };
}

// ---------- views ----------

async function viewLanding() {
  let profiles = [];
  try { profiles = await api("/api/profiles"); } catch { /* server down shows below */ }
  // Hosted sites don't list profiles; still offer the one this browser remembers.
  if (!profiles.length && state.me) profiles = [state.me];
  render(`
    <section class="hero">
      <div>
        <div class="eyebrow">Tamil &amp; Hindi speech practice</div>
        <h1>Practice speech. Build confidence. <span class="squiggle">One sound at a time.</span></h1>
        <p class="lede">SayBetter listens to how you say a sound, shows how the tongue and lips should move, and plans your next exercise from your own results.</p>
        <div class="sticker-row" style="margin:-4px 0 22px" aria-label="Sounds you can practise">
          <span class="sticker s1">ழ</span><span class="sticker s2">ள</span><span class="sticker s3">ர</span>
          <span class="sticker s2">श</span><span class="sticker s1">ख</span><span class="sticker s3">र</span>
        </div>
        <div class="btn-row">
          <a class="btn btn-primary" href="#/start">Start your first practice</a>
          <button class="btn btn-secondary" data-demo="ta-IN">Try a demo (Tamil)</button>
          <button class="btn btn-secondary" data-demo="hi-IN">Try a demo (Hindi)</button>
        </div>
        ${profiles.length ? `<div class="profile-row"><span class="small muted">Continue as</span>${profiles.slice(-4).reverse().map((p) => `<button class="profile-chip" data-pid="${esc(p.api_key)}">${esc(p.display_name)} <span class="lang">${LANG[p.preferred_language].native}${p.is_demo ? " · demo" : ""}</span></button>`).join("")}</div>` : ""}
      </div>
      <div class="hero-stage">
        <div class="hero-bubble">
          ${diagram("retroflex_approximant", { title: "How to say ழ (zha)" })}
          <p class="caption small muted"><strong style="font-family:var(--font-native);color:var(--ink)">ழ (zha)</strong> — ${esc(diagramLabel("retroflex_approximant"))}</p>
        </div>
        <div class="hero-kili">${kili("happy", { size: 112, label: "Kili the parrot, SayBetter's practice buddy" })}
          <p class="small muted" style="margin:0 0 18px">Hi, I'm <strong style="color:var(--ink)">Kili</strong> — <em>kili</em> is Tamil for parrot. I'll listen while you practise.</p></div>
      </div>
    </section>
    <section class="steps3">
      <div class="card"><div class="step-num">1</div><h3>Practice</h3><p class="muted">Say a short word, phrase or sentence built around one sound you want to improve.</p></div>
      <div class="card"><div class="step-num">2</div><h3>Get feedback</h3><p class="muted">We check that sound on its own, tell you which sound we heard, and give one specific tip.</p></div>
      <div class="card"><div class="step-num">3</div><h3>Improve</h3><p class="muted">Your plan moves up, steps back, or repeats a level based on your saved results.</p></div>
    </section>
    <div class="grid grid-2">
      <div class="notice"><strong>Privacy.</strong> Recordings are analysed and then discarded unless you choose to keep them. Everything is stored on this computer, and you can delete it at any time.</div>
      <div class="notice"><strong>Not a diagnosis.</strong> SayBetter supports practice. It doesn't assess or diagnose speech disorders, and it doesn't replace a qualified speech-language therapist.</div>
    </div>`);
  main.querySelectorAll("[data-demo]").forEach((b) => b.addEventListener("click", async () => {
    const u = await api(`/api/profiles/demo?language=${b.dataset.demo}`, { method: "POST" });
    profile.set(u.api_key);
    location.hash = "#/baseline";
  }));
  main.querySelectorAll("[data-pid]").forEach((b) => b.addEventListener("click", () => {
    profile.set(b.dataset.pid);
    location.hash = "#/home";
  }));
}

function viewOnboarding() {
  render(`
    <div style="max-width:680px;margin:0 auto">
      <div class="eyebrow">Getting started</div>
      <h1 style="font-size:2rem">Tell us about your practice</h1>
      <p class="muted">This takes about a minute. You can change everything later.</p>
      <form id="f" class="card" novalidate>
        <label class="field"><span>What should we call you?</span><input type="text" name="display_name" maxlength="60" required autocomplete="nickname"></label>
        <fieldset><legend>Which language do you want to practise?</legend>
          <div class="choice-grid">
            <label class="choice"><input type="radio" name="lang" value="ta-IN" checked><span class="native">தமிழ்</span><strong>Tamil</strong><span class="small muted">ழ, ள, ர</span></label>
            <label class="choice"><input type="radio" name="lang" value="hi-IN"><span class="native">हिन्दी</span><strong>Hindi</strong><span class="small muted">र, श, ख</span></label>
          </div>
        </fieldset>
        <label class="field"><span>What would you like to work on? <span class="muted small">(optional)</span></span>
          <textarea name="goal" rows="2" maxlength="300" placeholder="e.g. I want to say ழ clearly when I talk at work"></textarea></label>
        <fieldset><legend>How would you like feedback?</legend>
          <div class="choice-grid">
            <label class="choice"><input type="radio" name="style" value="brief"><strong>Brief</strong><span class="small muted">Just the key point</span></label>
            <label class="choice"><input type="radio" name="style" value="step_by_step" checked><strong>Step by step</strong><span class="small muted">What to do next</span></label>
            <label class="choice"><input type="radio" name="style" value="encouraging"><strong>Encouraging</strong><span class="small muted">Extra motivation</span></label>
          </div>
        </fieldset>
        <label class="check field"><input type="checkbox" name="keep_audio"><span>Keep my recordings so I can review them later. <span class="muted small">Off by default; we only keep the results.</span></span></label>
        <div class="notice" style="margin-bottom:18px">
          <strong>Before you start:</strong> SayBetter checks a small set of sounds. Its results are estimates and can be wrong, especially with background noise. It does not diagnose anything. We'll ask for microphone access only when you press record.
        </div>
        <div id="err"></div>
        <button class="btn btn-primary" type="submit">Continue to a 2-minute check</button>
      </form>
    </div>`);
  const f = main.querySelector("#f");
  f.addEventListener("submit", async (e) => {
    e.preventDefault();
    const fd = new FormData(f);
    const name = (fd.get("display_name") || "").trim();
    if (!name) { f.querySelector("#err").innerHTML = `<div class="notice warn" style="margin-bottom:12px">Please enter a name.</div>`; f.display_name.focus(); return; }
    try {
      const u = await api("/api/profiles", { method: "POST", body: {
        display_name: name, preferred_language: fd.get("lang"), practice_goal: fd.get("goal") || "",
        feedback_style: fd.get("style"), keep_audio: fd.get("keep_audio") === "on",
      } });
      profile.set(u.api_key);
      location.hash = "#/baseline";
    } catch (err) { f.querySelector("#err").innerHTML = errorBox(err); }
  });
}

async function viewBaseline() {
  await loadMe(); if (!state.me) return (location.hash = "#/");
  await Promise.all([loadTargets(), loadHealth()]);
  const { items } = await api("/api/baseline");
  render(`
    <div style="max-width:720px;margin:0 auto">
      <div class="eyebrow">Quick check · about 2 minutes</div>
      <h1 style="font-size:2rem">Let's find your starting point</h1>
      <p class="muted">You'll say ${items.length} short ${LANG[state.me.preferred_language].name} words. We use them to pick the sound to focus on first. There's no score — this just sets up your plan.</p>
      ${analysisReady() ? "" : `<div class="notice ${state.me.is_demo ? "demo" : "warn"}" style="margin-bottom:16px">${state.me.is_demo
        ? "Demo profile: speech analysis isn't set up on this computer, so results will be <strong>simulated and clearly labelled</strong>."
        : "Speech analysis isn't set up yet (no Sarvam key and the sound model isn't ready), so we can't check these words. Your plan will start at the first sound."}</div>`}
      <div class="card" id="box"></div>
    </div>`);
  const box = main.querySelector("#box");
  const session = await api("/api/sessions", { method: "POST", body: { kind: "baseline" } });
  let i = 0;
  const results = [];

  function showItem() {
    const it = items[i];
    const t = targetById(it.speech_target_id);
    box.innerHTML = `
      <div class="progress-steps">${items.map((_, k) => `<span class="${k < i ? "done" : ""}"></span>`).join("")}</div>
      <p class="small muted">Word ${i + 1} of ${items.length}</p>
      <div class="word-stage">
        ${kili("idle", { size: 92 })}
        <div class="word-bubble">
          <div class="target-word">${highlight(it.text, t.letter)}</div>
          <div class="roman">${esc(it.roman)}</div><div class="meaning">“${esc(it.meaning)}”</div>
        </div>
      </div>
      <div class="btn-row" style="margin-top:12px"><button class="btn btn-secondary" id="ref">${icon("speaker")} Hear it</button></div>
      <div id="rec"></div><div id="res" style="margin-top:14px"></div>`;
    box.querySelector("#ref").addEventListener("click", () => playReference(t.id, it.text, t.language));
    recorderWidget(box.querySelector("#rec"), {
      onState: (s) => setKili(box, s),
      submitLabel: "Save and continue",
      onSubmit: async (blob) => {
        const form = new FormData();
        form.append("session_id", session.id); form.append("speech_target_id", t.id); form.append("item_text", it.text);
        form.append("audio", blob, "attempt.wav");
        try {
          const r = await api("/api/attempts", { method: "POST", form });
          if (r.analysis.status === "audio_unusable") {
            box.querySelector("#res").innerHTML = `<div class="notice warn">${esc(r.feedback.guidance_text)}</div>`;
            return;
          }
          results.push(r);
          i += 1;
          if (i < items.length) showItem(); else finish();
        } catch (e) { box.querySelector("#res").innerHTML = errorBox(e); }
      },
    });
  }

  async function finish() {
    box.innerHTML = `<p><span class="spinner"></span> Building your plan…</p>`;
    const { baseline } = await api(`/api/sessions/${session.id}/complete`, { method: "POST" });
    const first = targetById(baseline.ranked[0]);
    const demo = results.some((r) => r.analysis.status === "demo_result");
    box.innerHTML = `
      <div class="word-stage" style="align-items:center;margin:0 0 10px">${kili("happy", { size: 88 })}
        <div><div class="eyebrow">Your plan is ready</div>
        <h2 style="margin:0">First focus: <span style="font-family:var(--font-native);color:var(--coral-deep)">${esc(first.name)}</span></h2></div></div>
      ${demo ? `<div class="notice demo" style="margin-bottom:12px">These baseline results were simulated for the demo.</div>` : ""}
      <div>${baseline.ranked.map((id) => {
        const t = targetById(id); const s = baseline.summary[id];
        const label = s.plan_status === "active" ? `<span class="chip ok">Focus now · level ${s.start_level}</span>`
          : s.plan_status === "not_needed" ? `<span class="chip">Sounded clear</span>` : `<span class="chip">Later · level ${s.start_level}</span>`;
        return `<div class="target-row"><div class="letter">${esc(t.letter)}</div><div class="grow"><strong>${esc(t.name)}</strong><div class="small muted">${s.on_target} clear · ${s.substitutions} mixed up · ${s.unclear} unsure</div></div>${label}</div>`;
      }).join("")}</div>
      <p class="small muted" style="margin-top:12px">This only reflects ${items.length} words. It isn't an assessment — your plan keeps adjusting as you practise.</p>
      <div class="btn-row"><a class="btn btn-primary" href="#/practice">Start practising ${esc(first.letter)}</a><a class="btn btn-secondary" href="#/home">Go to my dashboard</a></div>`;
  }
  showItem();
}

async function viewHome() {
  await loadMe(); if (!state.me) return (location.hash = "#/");
  const [, , plan, attempts] = await Promise.all([loadTargets(), loadHealth(), api("/api/plan"), api("/api/attempts?limit=12")]);
  const a = plan.active;
  const t = a && targetById(a.speech_target_id);
  const recentDots = attempts.slice().reverse().map((x) => `<i class="${x.outcome === "on_target" && ["analysis_completed", "demo_result"].includes(x.status) ? "ok" : x.outcome === "substitution" ? "sub" : ""}" title="${esc(x.item_text)}: ${esc(x.outcome || x.status)}"></i>`).join("");
  render(`
    <div class="btn-row" style="justify-content:space-between;margin-bottom:20px;align-items:flex-end">
      <div class="word-stage" style="margin:0;align-items:center">${kili("idle", { size: 84 })}
        <div><div class="eyebrow">Welcome back</div><h1 style="font-size:2.3rem;margin:0">Hi ${esc(state.me.display_name)}</h1>
        ${state.me.practice_goal ? `<p class="muted" style="margin:4px 0 0">Your goal: ${esc(state.me.practice_goal)}</p>` : ""}</div></div>
      <div class="engine-status">${engineChips()}</div>
    </div>
    ${!plan.baseline_done ? `<div class="notice info" style="margin-bottom:16px">Take the 2-minute check so we can pick your first sound. <a href="#/baseline">Start the check</a></div>` : ""}
    ${t ? `
    <div class="card">
      <div class="focus">
        <div class="big-letter" aria-hidden="true">${esc(t.letter)}</div>
        <div>
          <div class="eyebrow">Current focus</div>
          <h2 style="margin-bottom:4px">${esc(t.name)}</h2>
          ${stones(a.current_level)}
          <p class="small muted">Level ${a.current_level} of 5 · ${esc(plan.level_names[a.current_level])}</p>
          ${plan.next_item ? `<p style="margin:8px 0 14px">Next: <strong style="font-family:var(--font-native);font-size:1.35rem">${highlight(plan.next_item.text, t.letter)}</strong> <span class="muted">(${esc(plan.next_item.roman)})</span></p>` : ""}
          <div class="btn-row"><a class="btn btn-primary" href="#/practice">${icon("mic")} Resume practice</a><a class="btn btn-secondary" href="#/learn/${t.id}">${icon("book")} How to say ${esc(t.letter)}</a></div>
        </div>
      </div>
    </div>` : ""}
    <div class="grid grid-2" style="margin-top:16px">
      <div class="card">
        <h3>Your sounds</h3>
        ${plan.plans.map((p) => {
          const tt = targetById(p.speech_target_id);
          const chip = { active: `<span class="chip ok">Focus</span>`, mastered: `<span class="chip ok">Completed</span>`, not_needed: `<span class="chip">Sounded clear</span>`, queued: `<span class="chip">Level ${p.current_level}</span>` }[p.status];
          return `<div class="target-row"><div class="letter">${esc(tt.letter)}</div><div class="grow"><strong>${esc(tt.name)}</strong><div class="small muted">${esc(tt.summary.split(".")[0])}.</div></div>${chip}${p.status !== "active" ? `<button class="btn btn-ghost small" data-focus="${tt.id}">Focus</button>` : ""}</div>`;
        }).join("")}
      </div>
      <div class="card">
        <h3>Recent attempts</h3>
        ${attempts.length ? `<div class="dots" style="margin-bottom:12px" aria-label="Recent results">${recentDots}</div>
          <ul class="attempt-list">${attempts.slice(0, 6).map((x) => `<li><span class="w">${esc(x.item_text)}</span><span class="small muted">${esc(outcomeLabel(x))}</span></li>`).join("")}</ul>
          <p class="small muted dots" style="margin-top:12px;align-items:center;gap:8px"><i class="ok"></i> on target <i class="sub"></i> mixed up <i></i> unsure</p>`
        : `<p class="muted">No attempts yet. Your practice history will appear here.</p>`}
      </div>
    </div>`);
  main.querySelectorAll("[data-focus]").forEach((b) => b.addEventListener("click", async () => {
    await api("/api/plan/active", { method: "PUT", body: { speech_target_id: b.dataset.focus } });
    viewHome();
  }));
}

function outcomeLabel(x) {
  const t = targetById(x.speech_target_id);
  if (x.status === "audio_unusable") return "recording unclear";
  if (x.status === "analysis_unavailable") return "not analysed";
  if (x.status === "analysis_failed") return "analysis failed";
  if (x.status === "low_confidence") return "unsure";
  const demo = x.status === "demo_result" ? " (demo)" : "";
  if (x.outcome === "on_target") return `sounded like ${t?.letter ?? "target"}${demo}`;
  if (x.outcome === "substitution") return `heard ${x.heard_as}${demo}`;
  return "unsure";
}

async function viewPractice() {
  await loadMe(); if (!state.me) return (location.hash = "#/");
  await Promise.all([loadTargets(), loadHealth()]);
  let plan = await api("/api/plan");
  if (!plan.active) {
    render(`<div class="card"><h2>Choose a sound first</h2><p class="muted">Take the 2-minute check, or pick a sound from your dashboard.</p><div class="btn-row"><a class="btn btn-primary" href="#/baseline">Take the check</a><a class="btn btn-secondary" href="#/home">Dashboard</a></div></div>`);
    return;
  }
  // A session belongs to one profile; start a fresh one after switching profiles.
  const newSession = async () => ({ ...(await api("/api/sessions", { method: "POST", body: { kind: "practice" } })), profileId: state.me.id });
  if (!state.session || state.session.profileId !== state.me.id) state.session = await newSession();
  let count = 0;

  function show(item, feedbackHtml = "") {
    const a = plan.active;
    const t = targetById(a.speech_target_id);
    render(`
      ${analysisReady() ? "" : `<div class="notice ${state.me.is_demo ? "demo" : "warn"}" style="margin-bottom:14px">${state.me.is_demo ? "Demo profile: results are <strong>simulated</strong> because speech analysis isn't set up on this computer." : "Speech analysis isn't set up yet, so attempts can't be checked. Add a Sarvam key or wait for the sound model to load."}</div>`}
      <div class="practice-layout">
        <div class="card">
          <div class="btn-row" style="justify-content:space-between">
            <span class="chip ok">${esc(t.name)} · Level ${a.current_level}: ${esc(plan.level_names[a.current_level])}</span>
            <span class="small muted">${count} attempt${count === 1 ? "" : "s"} this session</span>
          </div>
          <div class="word-stage" id="stage">
            ${kili("idle", { size: 96 })}
            <div class="word-bubble">
              <div class="target-word">${highlight(item.text, t.letter)}</div>
              <div class="roman">${esc(item.roman)}</div>
              <div class="meaning">“${esc(item.meaning)}”</div>
            </div>
          </div>
          ${item.reason ? `<p class="small muted" style="margin:10px 0 0">${esc(item.reason)}</p>` : ""}
          <div class="btn-row" style="margin-top:12px"><button class="btn btn-secondary" id="ref">${icon("speaker")} Hear reference</button></div>
          <div id="rec"></div>
        </div>
        <div class="card">
          <h3>How to say ${esc(t.letter)}</h3>
          ${diagram(t.diagram, { title: `How to say ${t.name}`, compact: true })}
          <p class="small muted" style="text-align:center">${esc(diagramLabel(t.diagram))}</p>
          <ol class="guide-steps">${t.steps.map((s) => `<li>${esc(s)}</li>`).join("")}</ol>
          <a class="small" href="#/learn/${t.id}">Full guide and common mix-ups</a>
        </div>
      </div>
      <div id="fb" style="margin-top:20px">${feedbackHtml}</div>
      <div class="btn-row" style="margin-top:20px;justify-content:flex-end"><button class="btn btn-ghost" id="end">Finish session</button></div>`);
    main.querySelector("#ref").addEventListener("click", () => playReference(t.id, item.text, t.language));
    main.querySelector("#end").addEventListener("click", async () => {
      await api(`/api/sessions/${state.session.id}/complete`, { method: "POST" });
      state.session = null;
      toast(`Session saved: ${count} attempt${count === 1 ? "" : "s"}.`);
      location.hash = "#/home";
    });
    recorderWidget(main.querySelector("#rec"), {
      onState: (s) => setKili(main.querySelector("#stage"), s),
      onSubmit: async (blob, localUrl) => {
        const send = () => {
          const form = new FormData();
          form.append("session_id", state.session.id); form.append("speech_target_id", t.id); form.append("item_text", item.text);
          form.append("audio", blob, "attempt.wav");
          return api("/api/attempts", { method: "POST", form });
        };
        try {
          let r;
          try {
            r = await send();
          } catch (e) {
            if (e.status !== 404 || !/session/i.test(e.message)) throw e;
            state.session = await newSession();
            r = await send();
          }
          count += 1;
          const fbBox = main.querySelector("#fb");
          fbBox.innerHTML = feedbackCard(r, t, item);
          setKili(main.querySelector("#stage"), kiliMood(r.analysis));
          fbBox.scrollIntoView({ behavior: "smooth", block: "start" });
          wireFeedback(fbBox, r, t, item, localUrl);
        } catch (e) { main.querySelector("#fb").innerHTML = errorBox(e); }
      },
    });
  }

  function wireFeedback(box, r, t, item, localUrl) {
    box.querySelector("[data-act=ref]")?.addEventListener("click", () => playReference(t.id, item.text, t.language));
    box.querySelector("[data-act=mine]")?.addEventListener("click", () => new Audio(localUrl).play());
    box.querySelector("[data-act=retry]")?.addEventListener("click", () => show(item));
    box.querySelector("[data-act=next]")?.addEventListener("click", async () => {
      plan = await api("/api/plan?advance=true");
      if (!plan.active) return (location.hash = "#/home");
      show(plan.next_item);
    });
  }

  show(plan.next_item);
}

function kiliMood(a) {
  if (["analysis_completed", "demo_result"].includes(a.status) && a.outcome === "on_target") return "happy";
  if (a.outcome === "substitution") return "encourage";
  return "thinking";
}

function feedbackCard(r, t, item) {
  const a = r.analysis, fb = r.feedback;
  const demo = a.status === "demo_result";
  let cls = "unsure", verdict;
  if (a.status === "audio_unusable") verdict = "Let's record that again";
  else if (a.status === "analysis_unavailable") verdict = "We couldn't check this attempt";
  else if (a.status === "analysis_failed") verdict = "Something went wrong";
  else if (a.status === "low_confidence" || a.outcome === "unclear") verdict = "We're not sure about this one";
  else if (a.outcome === "on_target") { cls = "ok"; verdict = `That sounded like ${t.letter}`; }
  else if (a.outcome === "substitution") { cls = "sub"; verdict = `We heard ${a.heard_as} instead of ${t.letter}`; }

  const confPct = Math.round((a.confidence || 0) * 100);
  const confLabel = demo ? "Simulated" : a.confidence >= 0.75 ? "High" : a.confidence >= 0.5 ? "Medium" : "Low";
  const engName = { transcript: "Sarvam speech-to-text", phonemes: "Sound model", templates: "Sarvam voice comparison" };
  const agreement = {
    all_agree: "All the checks that count for this sound agreed.",
    majority: "Most checks agreed; the more reliable ones outweighed the rest.",
    disagree: "The checks disagreed, so we won't guess.",
    phonemes_only: "Based on the sound model only.",
    transcript_only: "Based on Sarvam speech-to-text only.",
    templates_only: "Based on comparing your attempt with Sarvam voices only.",
    unreliable: "No check has tested reliable enough for this sound to make a call.",
    none: "No check could judge the target sound clearly.",
    demo: "Demo result — simulated, not a real analysis.",
  }[a.agreement] || "";
  const said = (e) => (e.verdict === "on_target" ? `said “correct”` : `heard ${e.heard_as}`);
  const evidence = a.evidence ? Object.entries(a.evidence).map(([eng, e]) => e.ignored
    ? `${engName[eng]} ${said(e)}, but it isn't used for ${t.letter} (tested unreliable).`
    : e.samples
      ? `${engName[eng]} ${said(e)} — right ${Math.round(e.precision * 100)}% of the time when it says that for ${t.letter} (${e.samples} test clips).`
      : `${engName[eng]} ${said(e)} — not yet measured for ${t.letter}.`).join(" ") : "";
  const ph = a.engines?.phonemes;
  const tp = a.engines?.templates;
  const q = a.quality;
  const closest = tp?.scores ? Object.entries(tp.scores).sort((x, y) => x[1] - y[1])[0][0] : null;

  const heardRows = [
    a.transcript != null ? `<dt>Speech-to-text</dt><dd>${esc(a.transcript || "(nothing recognised)")}</dd>` : "",
    ph?.expected_ipa ? `<dt>Expected sounds</dt><dd class="ipa">/${esc(ph.expected_ipa)}/</dd><dt>Sounds we heard</dt><dd class="ipa">${ph.observed_ipa ? `/${esc(ph.observed_ipa)}/` : "no clear speech sounds"}</dd>` : "",
    closest ? `<dt>Closest Sarvam voice</dt><dd>${closest === "correct" ? `the correct ${esc(t.letter)}` : `the mix-up with ${esc(closest)}`} <span style="font-family:var(--font-body)" class="muted">(${tp.voices} voices compared)</span></dd>` : "",
    a.status !== "audio_unusable" && q && q.status !== "ok" && q.issues?.length ? `<dt>Recording</dt><dd style="font-family:var(--font-body)">${esc(q.issues[0])}</dd>` : "",
  ].join("");

  const compare = fb.heard_diagram ? `
    <div class="compare">
      <figure>${diagram(fb.diagram, { compact: true, title: `Target ${t.letter}` })}<figcaption>Aim for: ${esc(t.letter)}</figcaption></figure>
      <figure>${diagram(fb.heard_diagram, { compact: true, title: `What ${fb.heard_as} looks like` })}<figcaption>What we heard: ${esc(fb.heard_as)}</figcaption></figure>
    </div>` : "";

  const pu = r.plan_update;
  const planMsg = pu?.message ? `<div class="notice ${pu.suggest_therapist ? "warn" : "info"} plan-update">${esc(pu.message)}</div>` : "";
  const primaryNext = fb.next_action === "continue";

  return `
    <div class="card feedback ${cls}" aria-live="polite">
      ${demo ? `<div class="notice demo" style="margin-bottom:12px"><strong>Demo result:</strong> simulated, not a real analysis of your recording.</div>` : ""}
      <div class="feedback-head">${kili(kiliMood(a), { size: 64, label: "Kili" })}<p class="verdict">${cls === "ok" ? icon("check") : ""}${esc(verdict)}</p></div>
      ${["analysis_completed", "low_confidence", "demo_result"].includes(a.status) ? `<div class="conf"><span>Confidence: <strong>${confLabel}</strong></span><span class="conf-bar"><i style="width:${demo ? 0 : confPct}%"></i></span></div><p class="small muted" style="margin:6px 0 0">${esc(agreement)}</p>${evidence ? `<details class="small" style="margin-top:6px"><summary>Why this confidence?</summary><p class="muted" style="margin:6px 0 0">${esc(evidence)}${a.calibrated ? " Measured on Sarvam's synthetic voices, so real-world accuracy may be lower." : ""}</p></details>` : ""}` : ""}
      ${heardRows ? `<dl class="heard">${heardRows}</dl>` : ""}
      <div class="tip"><strong>Your practice tip</strong>${esc(fb.guidance_text)}</div>
      ${compare}
      ${planMsg}
      <div class="btn-row" style="margin-top:14px">
        <button class="btn btn-secondary" data-act="ref" type="button">${icon("speaker")} Hear reference</button>
        <button class="btn btn-secondary" data-act="mine" type="button">${icon("play")} Hear my attempt</button>
        <button class="btn ${primaryNext ? "btn-secondary" : "btn-primary"}" data-act="retry" type="button">${icon("retry")} Try again</button>
        <button class="btn ${primaryNext ? "btn-primary" : "btn-secondary"}" data-act="next" type="button">Continue ${icon("arrow")}</button>
      </div>
    </div>`;
}

async function viewLearn(id) {
  await loadMe(); if (!state.me) return (location.hash = "#/");
  await loadTargets();
  const t = targetById(id);
  if (!t) return render(`<div class="card"><p>Sound not found.</p><a href="#/home">Back</a></div>`);
  render(`
    <a href="#/home" class="small">Back to dashboard</a>
    <div class="practice-layout" style="margin-top:12px">
      <div class="card">
        <div class="eyebrow">Sound guide</div>
        <h1 style="font-size:2.2rem"><span style="font-family:var(--font-native)">${esc(t.letter)}</span> ${esc(t.roman)}</h1>
        <p>${esc(t.summary)}</p>
        <ol class="guide-steps">${t.steps.map((s) => `<li>${esc(s)}</li>`).join("")}</ol>
      </div>
      <div class="card">${diagram(t.diagram, { title: `How to say ${t.name}` })}<p class="small muted" style="text-align:center">${esc(diagramLabel(t.diagram))}</p></div>
    </div>
    <h2 style="margin-top:28px">Common mix-ups</h2>
    <div class="grid grid-2">${Object.entries(t.confusions).map(([letter, c]) => `
      <div class="card">
        <h3><span style="font-family:var(--font-native)">${esc(letter)}</span> instead of <span style="font-family:var(--font-native)">${esc(t.letter)}</span></h3>
        <div class="compare"><figure>${diagram(t.diagram, { compact: true, animate: false })}<figcaption>${esc(t.letter)}</figcaption></figure><figure>${diagram(c.diagram, { compact: true, animate: false })}<figcaption>${esc(letter)}</figcaption></figure></div>
        <p class="small" style="margin-top:10px">${esc(c.tip)}</p>
      </div>`).join("")}</div>
    <h2 style="margin-top:28px">Practice levels</h2>
    <div class="card">${Object.entries(t.levels).map(([lvl, its]) => `
      <div class="target-row"><span class="chip">${lvl}</span><div class="grow"><strong>${esc(state.levelNames[lvl])}</strong><div style="font-family:var(--font-native)">${its.map((i) => esc(i.text)).join(" · ")}</div></div></div>`).join("")}
      <div class="btn-row" style="margin-top:12px"><button class="btn btn-primary" id="focus">Practise this sound</button></div>
    </div>
    <p class="foot-note">Guidance is draft practice content and should be reviewed by a speech-language therapist. Diagrams are simplified side views; real tongue shapes vary between people.</p>`);
  main.querySelector("#focus").addEventListener("click", async () => {
    await api("/api/plan/active", { method: "PUT", body: { speech_target_id: t.id } });
    location.hash = "#/practice";
  });
}

async function viewProgress() {
  await loadMe(); if (!state.me) return (location.hash = "#/");
  await loadTargets();
  const p = await api("/api/progress");
  const byTarget = Object.fromEntries(p.per_target.map((r) => [r.speech_target_id, r]));
  render(`
    <div class="eyebrow">Progress</div>
    <h1 style="font-size:2rem">Your practice so far</h1>
    <div class="grid grid-3">
      <div class="card"><div class="stat">${p.sessions_completed}</div><div class="muted">practice sessions finished</div></div>
      <div class="card"><div class="stat">${p.days_practised}</div><div class="muted">days practised</div></div>
      <div class="card"><div class="stat">${p.per_target.reduce((n, r) => n + r.attempts, 0)}</div><div class="muted">recordings made</div></div>
    </div>
    <div class="grid grid-2" style="margin-top:16px">${p.plans.map((pl) => {
      const t = targetById(pl.speech_target_id); const s = byTarget[pl.speech_target_id];
      const days = p.daily.filter((d) => d.speech_target_id === pl.speech_target_id).slice(-10);
      const lv = p.levels.filter((l) => l.speech_target_id === pl.speech_target_id).slice(-4);
      return `<div class="card">
        <div class="btn-row" style="justify-content:space-between"><h3 style="margin:0"><span style="font-family:var(--font-native)">${esc(t.letter)}</span> ${esc(t.roman)}</h3><span class="chip ${pl.status === "active" ? "ok" : ""}">${pl.status === "not_needed" ? "sounded clear" : pl.status}</span></div>
        ${stones(pl.current_level, pl.status === "mastered")}
        <p class="small muted">Level ${pl.current_level}: ${esc(state.levelNames[pl.current_level])}</p>
        ${s ? `<p>${s.analysed ? `<strong>${Math.round((s.on_target / s.analysed) * 100)}%</strong> of ${s.analysed} checked attempts sounded on target` : "No checked attempts yet"} <span class="small muted">(${s.attempts} recordings)</span></p>` : `<p class="muted">Not practised yet.</p>`}
        ${days.length ? `<div class="bars" aria-label="On-target share by day">${days.map((d, i) => { const pct = d.analysed ? Math.round((d.on_target / d.analysed) * 100) : 0; return `<div style="height:${Math.max(4, pct)}%;--i:${i}" title="${d.day}: ${pct}% of ${d.analysed} checked"><span>${d.day.slice(5)}</span></div>`; }).join("")}</div><div style="height:22px"></div>` : ""}
        ${lv.length ? `<ul class="attempt-list small">${lv.map((l) => `<li><span>${esc(l.note)} → level ${l.level}</span><span class="muted">${l.recorded_at.slice(0, 10)}</span></li>`).join("")}</ul>` : ""}
      </div>`;
    }).join("")}</div>
    <p class="foot-note">“On target” is the app's estimate from its speech analysis. It measures practice performance, not clinical improvement. Demo results are counted separately only on demo profiles.</p>`);
}

async function viewSettings() {
  await loadMe(); if (!state.me) return (location.hash = "#/");
  await loadHealth();
  const m = state.me;
  render(`
    <div style="max-width:680px;margin:0 auto">
      <h1 style="font-size:2rem">Settings</h1>
      <form id="f" class="card">
        <label class="field"><span>Name</span><input type="text" name="display_name" value="${esc(m.display_name)}" maxlength="60"></label>
        <label class="field"><span>Practice goal</span><textarea name="goal" rows="2" maxlength="300">${esc(m.practice_goal)}</textarea></label>
        <fieldset><legend>Feedback style</legend><div class="choice-grid">
          ${[["brief", "Brief"], ["step_by_step", "Step by step"], ["encouraging", "Encouraging"]].map(([v, l]) => `<label class="choice"><input type="radio" name="style" value="${v}" ${m.feedback_style === v ? "checked" : ""}><strong>${l}</strong></label>`).join("")}
        </div></fieldset>
        <label class="check field"><input type="checkbox" name="keep_audio" ${m.consent_settings.keep_audio ? "checked" : ""}><span>Keep my recordings on this computer</span></label>
        <p class="small muted">Language: ${LANG[m.preferred_language].name}. To practise another language, create a new profile.</p>
        <button class="btn btn-primary" type="submit">Save</button>
      </form>
      <div class="card"><h3>Speech analysis</h3><div class="engine-status">${engineChips()}</div>
        <p class="small muted" style="margin-top:10px">${state.health?.engines.sarvam.configured
          ? "Sarvam is connected: speech-to-text, reference audio and voice comparison are on."
          : "Add a Sarvam API key in <code>backend/.env</code> to turn on speech-to-text, reference audio and voice comparison. The local sound model needs no key."}</p>
        <div id="acc"></div></div>
      <div class="card">
        <h3>Your data</h3>
        <p class="muted small">Delete this profile, all attempts, feedback, progress and any saved recordings. This can't be undone.</p>
        <div class="btn-row"><button class="btn btn-secondary" id="switch">Switch profile</button><button class="btn btn-danger" id="del">Delete all my data</button></div>
      </div>
    </div>`);
  api("/api/accuracy").then((acc) => {
    const rows = Object.entries(acc.targets).filter(([id]) => id.startsWith(m.preferred_language.slice(0, 2)));
    const pct = (a, b) => (b ? `${Math.round((100 * a) / b)}%` : "–");
    main.querySelector("#acc").innerHTML = `
      <h3 style="margin-top:18px">Measured accuracy</h3>
      <p class="small muted">Tested on ${acc.clips} synthetic clips (${esc(acc.source)}), ${esc(acc.generated_at.slice(0, 10))}. Real learners' speech is harder, so treat these as best-case.</p>
      ${acc.fused ? `<div style="overflow-x:auto;margin-bottom:14px"><table class="acc-table"><thead><tr><th>Sound</th><th>Final verdict right</th><th>Wrong</th><th>“Not sure”</th><th>Right when it made a call</th></tr></thead><tbody>
      ${rows.filter(([id]) => acc.fused[id]).map(([id]) => { const f = acc.fused[id]; const n = f.right + f.wrong + f.unsure; return `<tr><td style="font-family:var(--font-native)">${esc(acc.names[id])}</td><td><strong>${pct(f.right, n)}</strong></td><td>${pct(f.wrong, n)}</td><td>${pct(f.unsure, n)}</td><td>${pct(f.right, f.right + f.wrong)}</td></tr>`; }).join("")}
      </tbody></table></div>` : ""}
      <details class="small"><summary>Each check on its own</summary>
      <div style="overflow-x:auto"><table class="acc-table"><thead><tr><th>Sound</th><th>Check</th><th>Correct judged correct</th><th>Mix-ups caught</th><th>Mix-up named right</th><th>False alarms</th></tr></thead><tbody>
      ${rows.flatMap(([id, engines]) => Object.entries(engines).map(([eng, s]) => `<tr><td style="font-family:var(--font-native)">${esc(acc.names[id])}</td><td>${{ transcript: "Sarvam speech-to-text", phonemes: "Sound model", templates: "Sarvam voices" }[eng]}</td>
        <td>${pct(s.correct_recognised, s.correct_clips)}</td><td>${pct(s.mixups_caught, s.mixup_clips)}</td><td>${pct(s.mixups_named_right, s.mixup_clips)}</td><td>${pct(s.false_alarms, s.correct_clips)}</td></tr>`)).join("")}
      </tbody></table></div></details>`;
  }).catch(() => { /* no calibration yet */ });
  main.querySelector("#f").addEventListener("submit", async (e) => {
    e.preventDefault();
    const fd = new FormData(e.target);
    state.me = await api("/api/me", { method: "PATCH", body: { display_name: fd.get("display_name").trim() || undefined, practice_goal: fd.get("goal"), feedback_style: fd.get("style"), keep_audio: fd.get("keep_audio") === "on" } });
    toast("Saved.");
  });
  main.querySelector("#switch").addEventListener("click", () => { profile.clear(); state.me = null; state.session = null; location.hash = "#/"; });
  main.querySelector("#del").addEventListener("click", async () => {
    if (!confirm("Delete this profile and all of its practice data? This can't be undone.")) return;
    await api("/api/me", { method: "DELETE" });
    profile.clear(); state.me = null; state.targets = null;
    toast("Your data was deleted.");
    location.hash = "#/";
  });
}

// ---------- router ----------

async function route() {
  const hash = location.hash || "#/";
  await loadMe();
  setNav(hash.split("/").slice(0, 2).join("/"));
  try {
    if (hash === "#/" || hash === "") return await viewLanding();
    if (hash === "#/start") return viewOnboarding();
    if (hash === "#/baseline") return await viewBaseline();
    if (hash === "#/home") return await viewHome();
    if (hash === "#/practice") return await viewPractice();
    if (hash === "#/progress") return await viewProgress();
    if (hash === "#/settings") return await viewSettings();
    if (hash.startsWith("#/learn/")) return await viewLearn(decodeURIComponent(hash.slice(8)));
    location.hash = "#/";
  } catch (e) {
    render(`<div class="card">${errorBox(e)}<div class="btn-row" style="margin-top:12px"><button class="btn btn-secondary" onclick="location.reload()">Reload</button></div></div>`);
  }
}

window.addEventListener("hashchange", route);
speechSynthesis?.getVoices?.();
route();
