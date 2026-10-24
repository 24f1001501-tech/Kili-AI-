"""WAV decoding and recording-quality checks (no ffmpeg needed)."""
import io
import wave
from dataclasses import dataclass, field

import numpy as np

from .config import MAX_SECONDS, MIN_SECONDS

TARGET_RATE = 16000


class AudioError(ValueError):
    pass


@dataclass
class Quality:
    status: str  # ok | noisy | too_quiet | clipped | too_short | too_long | no_speech
    usable: bool
    duration: float
    level_db: float
    snr_db: float
    clipped_ratio: float
    issues: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "status": self.status, "usable": self.usable, "duration": round(self.duration, 2),
            "level_db": round(self.level_db, 1), "snr_db": round(self.snr_db, 1),
            "clipped_ratio": round(self.clipped_ratio, 4), "issues": self.issues,
        }


def decode_wav(data: bytes) -> np.ndarray:
    """Return mono float32 samples at 16 kHz."""
    try:
        with wave.open(io.BytesIO(data)) as w:
            channels, width, rate, n = w.getnchannels(), w.getsampwidth(), w.getframerate(), w.getnframes()
            raw = w.readframes(n)
    except (wave.Error, EOFError) as e:
        raise AudioError("The recording is not a readable WAV file.") from e

    if width == 2:
        x = np.frombuffer(raw, dtype="<i2").astype(np.float32) / 32768.0
    elif width == 4:
        x = np.frombuffer(raw, dtype="<i4").astype(np.float32) / 2147483648.0
    elif width == 1:
        x = (np.frombuffer(raw, dtype=np.uint8).astype(np.float32) - 128.0) / 128.0
    else:
        raise AudioError(f"Unsupported sample width: {width * 8} bits.")
    if channels > 1:
        x = x.reshape(-1, channels).mean(axis=1)
    if rate != TARGET_RATE and len(x):
        n_out = int(round(len(x) * TARGET_RATE / rate))
        x = np.interp(np.linspace(0, len(x) - 1, n_out), np.arange(len(x)), x).astype(np.float32)
    return x


def encode_wav(x: np.ndarray, rate: int = TARGET_RATE) -> bytes:
    pcm = (np.clip(x, -1, 1) * 32767).astype("<i2").tobytes()
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(pcm)
    return buf.getvalue()


def assess(x: np.ndarray) -> Quality:
    duration = len(x) / TARGET_RATE
    if duration < MIN_SECONDS:
        return Quality("too_short", False, duration, -120, 0, 0, ["The recording is too short. Hold the button and say the whole word."])
    if duration > MAX_SECONDS:
        return Quality("too_long", False, duration, -120, 0, 0, [f"Please keep recordings under {int(MAX_SECONDS)} seconds."])

    frame = 320  # 20 ms
    n = len(x) // frame
    frames = x[: n * frame].reshape(n, frame)
    energy = np.sqrt((frames ** 2).mean(axis=1) + 1e-12)
    db = 20 * np.log10(energy + 1e-12)
    noise_floor = float(np.percentile(db, 10))
    speech_level = float(np.percentile(db, 95))
    snr = speech_level - noise_floor
    clipped = float((np.abs(x) > 0.985).mean())

    issues = []
    if speech_level < -45:
        return Quality("too_quiet", False, duration, speech_level, snr, clipped,
                       ["We could barely hear you. Move closer to the microphone or speak a little louder."])
    if snr < 6:
        return Quality("no_speech", False, duration, speech_level, snr, clipped,
                       ["We could not find clear speech in this recording. Try again in a quieter place."])
    status = "ok"
    if clipped > 0.01:
        status = "clipped"
        issues.append("The recording is distorted (too loud). Move slightly away from the microphone.")
    elif snr < 15:
        status = "noisy"
        issues.append("There is background noise, so the result may be less reliable.")
    return Quality(status, True, duration, speech_level, snr, clipped, issues)


def trim_silence(x: np.ndarray, pad: float = 0.15) -> np.ndarray:
    frame = 320
    n = len(x) // frame
    if n < 3:
        return x
    energy = np.sqrt((x[: n * frame].reshape(n, frame) ** 2).mean(axis=1) + 1e-12)
    db = 20 * np.log10(energy)
    thresh = max(np.percentile(db, 10) + 10, db.max() - 40)
    voiced = np.where(db > thresh)[0]
    if not len(voiced):
        return x
    p = int(pad * TARGET_RATE)
    return x[max(0, voiced[0] * frame - p): min(len(x), (voiced[-1] + 1) * frame + p)]
