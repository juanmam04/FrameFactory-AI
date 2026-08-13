"""Always-on documentary bed: same sparse minor pad under every episode."""
from __future__ import annotations

import math
import os
import struct
import wave
from pathlib import Path


def documentary_bed_path() -> Path:
    if (os.getenv("VERCEL") or os.getenv("VERCEL_ENV") or "").strip():
        root = Path("/tmp/ff-audio")
    else:
        root = Path(__file__).resolve().parents[2] / "output" / "audio"
    root.mkdir(parents=True, exist_ok=True)
    dest = root / "documentary_bed.wav"
    if dest.is_file() and dest.stat().st_size > 20_000:
        return dest
    _write_pad(dest)
    return dest


def _write_pad(dest: Path, seconds: float = 16.0, sr: int = 22050) -> None:
    """Deterministic Am–F–C–G pad. Quiet, looping, no melody competing with VO."""
    n = int(seconds * sr)
    chords = (
        (110.00, 130.81, 164.81),
        (87.31, 130.81, 174.61),
        (130.81, 164.81, 196.00),
        (98.00, 146.83, 196.00),
    )
    chord_len = seconds / len(chords)
    frames = bytearray()
    for i in range(n):
        t = i / sr
        freqs = chords[int(t / chord_len) % len(chords)]
        local = t % chord_len
        env = min(1.0, local / 0.5) * min(1.0, (chord_len - local) / 0.8)
        env = max(0.0, env)
        s = 0.0
        for f in freqs:
            s += 0.20 * math.sin(2 * math.pi * f * t)
            s += 0.07 * math.sin(2 * math.pi * f * 2 * t)
        s *= env * (0.75 + 0.25 * math.sin(2 * math.pi * 0.04 * t))
        s = max(-1.0, min(1.0, s * 0.28))
        frames += struct.pack("<h", int(s * 28000))
    dest.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(dest), "w") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(bytes(frames))
