// Microphone capture straight to 16 kHz mono 16-bit WAV, so the backend
// needs no ffmpeg and every engine gets the same clean PCM.

const RATE = 16000;
const MAX_SECONDS = 15;

export class Recorder {
  constructor({ onLevel, onTick, onAutoStop } = {}) {
    this.onLevel = onLevel || (() => {});
    this.onTick = onTick || (() => {});
    this.onAutoStop = onAutoStop || (() => {});
    this.stream = null;
    this.ctx = null;
    this.chunks = [];
    this.recording = false;
  }

  static supported() {
    return !!(navigator.mediaDevices && navigator.mediaDevices.getUserMedia && (window.AudioContext || window.webkitAudioContext));
  }

  async start() {
    if (this.recording) return;
    this.stream = await navigator.mediaDevices.getUserMedia({
      audio: { channelCount: 1, echoCancellation: true, noiseSuppression: false, autoGainControl: true },
    });
    const Ctx = window.AudioContext || window.webkitAudioContext;
    this.ctx = new Ctx();
    const src = this.ctx.createMediaStreamSource(this.stream);
    const proc = this.ctx.createScriptProcessor(4096, 1, 1);
    this.chunks = [];
    this.inputRate = this.ctx.sampleRate;
    this.startedAt = performance.now();
    proc.onaudioprocess = (e) => {
      if (!this.recording) return;
      const data = e.inputBuffer.getChannelData(0);
      this.chunks.push(new Float32Array(data));
      let peak = 0;
      for (let i = 0; i < data.length; i += 8) peak = Math.max(peak, Math.abs(data[i]));
      this.onLevel(peak);
      const secs = (performance.now() - this.startedAt) / 1000;
      this.onTick(secs);
      if (secs >= MAX_SECONDS) this.onAutoStop();
    };
    src.connect(proc);
    proc.connect(this.ctx.destination);
    this.proc = proc;
    this.recording = true;
  }

  async stop() {
    if (!this.recording) return null;
    this.recording = false;
    this.proc.disconnect();
    this.stream.getTracks().forEach((t) => t.stop());
    await this.ctx.close();
    const total = this.chunks.reduce((n, c) => n + c.length, 0);
    const all = new Float32Array(total);
    let off = 0;
    for (const c of this.chunks) { all.set(c, off); off += c.length; }
    return encodeWav(resample(all, this.inputRate, RATE), RATE);
  }

  cancel() {
    if (!this.recording) return;
    this.recording = false;
    this.proc?.disconnect();
    this.stream?.getTracks().forEach((t) => t.stop());
    this.ctx?.close();
  }
}

function resample(input, from, to) {
  if (from === to) return input;
  const ratio = from / to;
  const out = new Float32Array(Math.floor(input.length / ratio));
  // average over each source window (cheap low-pass) when downsampling
  for (let i = 0; i < out.length; i++) {
    const start = Math.floor(i * ratio);
    const end = Math.min(input.length, Math.floor((i + 1) * ratio));
    let sum = 0;
    for (let j = start; j < end; j++) sum += input[j];
    out[i] = sum / Math.max(1, end - start);
  }
  return out;
}

function encodeWav(samples, rate) {
  const buf = new ArrayBuffer(44 + samples.length * 2);
  const v = new DataView(buf);
  const str = (o, s) => [...s].forEach((c, i) => v.setUint8(o + i, c.charCodeAt(0)));
  str(0, "RIFF"); v.setUint32(4, 36 + samples.length * 2, true); str(8, "WAVE");
  str(12, "fmt "); v.setUint32(16, 16, true); v.setUint16(20, 1, true); v.setUint16(22, 1, true);
  v.setUint32(24, rate, true); v.setUint32(28, rate * 2, true); v.setUint16(32, 2, true); v.setUint16(34, 16, true);
  str(36, "data"); v.setUint32(40, samples.length * 2, true);
  for (let i = 0; i < samples.length; i++) {
    const s = Math.max(-1, Math.min(1, samples[i]));
    v.setInt16(44 + i * 2, s < 0 ? s * 0x8000 : s * 0x7fff, true);
  }
  return new Blob([buf], { type: "audio/wav" });
}
