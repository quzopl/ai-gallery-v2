"""Generowanie i cache WebP miniatur."""
from __future__ import annotations

from pathlib import Path

import subprocess

from PIL import Image

VIDEO_EXTS = {".mp4", ".webm", ".mov", ".mkv", ".m4v"}


def _video_frame(src: Path, out: Path, *, max_size: int, quality: int) -> None:
    """One frame ~1 s in (or the first one for very short clips) → WebP."""
    for seek in ("1", "0"):
        subprocess.run(
            ["ffmpeg", "-v", "error", "-y", "-ss", seek, "-i", str(src), "-frames:v", "1",
             "-vf", f"scale='min({max_size},iw)':-2", "-quality", str(quality), str(out)],
            capture_output=True, timeout=60)
        if out.exists() and out.stat().st_size > 0:
            return
    raise RuntimeError(f"no frame decoded: {src}")


def get_or_generate(
    src: Path, *, sha1: str, cache_dir: Path, max_size: int = 512, quality: int = 80
) -> Path:
    """Zwróć ścieżkę do cache'owanej miniatury. Generuj jeśli brak."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    out = cache_dir / f"{sha1}.webp"
    if out.exists():
        return out
    if src.suffix.lower() in VIDEO_EXTS:
        _video_frame(src, out, max_size=max_size, quality=quality)
        return out
    with Image.open(src) as img:
        img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
        if img.mode not in ("RGB", "RGBA"):
            img = img.convert("RGB")
        img.save(out, "WEBP", quality=quality, method=4)
    return out


def sweep(cache_dir: Path, *, known_sha1s: set[str]) -> int:
    """Usuń pliki .webp których nazwa (sha1) nie jest w known_sha1s. Zwróć liczbę usuniętych."""
    if not cache_dir.exists():
        return 0
    removed = 0
    for p in cache_dir.iterdir():
        if not p.is_file() or p.suffix != ".webp":
            continue
        if p.stem not in known_sha1s:
            p.unlink()
            removed += 1
    return removed
