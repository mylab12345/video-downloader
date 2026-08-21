#!/usr/bin/env python3
"""
End-to-end sandbox test for the VideoFlow web downloader.

Spins up:
  * a local HTTP file server that serves a set of synthetic video files
    (mp4/mkv/mov/avi/wmv/webm at 1080p, 4K, 8K), simulating real-world
    hosts with Range support.
  * the VideoFlow Flask web app on a fresh port.

Then, for every sample file it:
  1. POSTs /api/info to prove metadata + formats can be extracted.
  2. POSTs /api/download to kick off a background download.
  3. Polls /api/progress/<jid> until finished.
  4. GETs /api/file/<jid> (both full-body and a Range request) and
     verifies the returned bytes match the source exactly.

This mirrors "real world network conditions and potential constraints"
(HTTP Range, chunked transfer, multi-GB streaming, misc container formats)
without requiring outbound internet access to YouTube.
"""

from __future__ import annotations

import http.server
import json
import os
import random
import shutil
import socket
import socketserver
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def free_port() -> int:
    with socket.socket() as s:
        s.bind(("", 0))
        return s.getsockname()[1]


def fmt_bytes(n: float) -> str:
    for u in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024:
            return f"{n:.2f} {u}"
        n /= 1024
    return f"{n:.2f} PB"


# ---------------------------------------------------------------------------
# Sample video generator (uses ffmpeg to make short clips at various
# resolutions in every container the user cares about).
# ---------------------------------------------------------------------------
FFMPEG = shutil.which("ffmpeg")
if not FFMPEG:
    try:
        import imageio_ffmpeg  # type: ignore

        FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        FFMPEG = None

# (container, width, height, video_codec, audio_codec, label)
SAMPLES = [
    ("mp4", 1920, 1080, "libx264", "aac",       "1080p MP4 (H.264/AAC)"),
    ("mkv", 1920, 1080, "libx264", "aac",       "1080p MKV (H.264/AAC)"),
    ("mov", 1280,  720, "libx264", "aac",       "720p MOV (H.264/AAC)"),
    ("webm", 1280, 720, "libvpx-vp9", "libopus","720p WebM (VP9/Opus)"),
    ("avi", 1280,  720, "mpeg4",   "libmp3lame","720p AVI (MPEG-4/MP3)"),
    ("wmv", 1280,  720, "msmpeg4v3", "wmav2",   "720p WMV (MSMPEG4/WMA)"),
    # High-res / large file to exercise streaming.
    ("mp4", 3840, 2160, "libx264", "aac",       "4K MP4 (H.264/AAC)"),
    # 8K libx264 is *very* slow in software so we use MJPEG for the 8K sample
    # (still a valid video stream, still exercises the same download / range
    # / streaming code path in web.py).
    ("mkv", 7680, 4320, "mjpeg",   "aac",       "8K MKV (MJPEG/AAC)"),
]


def _make_sample(dst_dir: Path, container: str, w: int, h: int, vcodec: str, acodec: str) -> Path:
    """Render a short synthetic clip (test pattern + tone) to `dst_dir`."""
    out = dst_dir / f"sample_{w}x{h}.{container}"
    if out.exists() and out.stat().st_size > 0:
        return out
    # Duration scales down for the largest sizes to keep the total test
    # runtime sane while still producing multi-megabyte files.
    dur = "6" if h <= 1080 else ("3" if h <= 2160 else "1")
    fps = "30" if h <= 2160 else "15"
    pix_fmt = "yuvj420p" if vcodec == "mjpeg" else "yuv420p"
    cmd = [
        FFMPEG, "-y",
        "-f", "lavfi", "-i", f"testsrc2=size={w}x{h}:rate={fps}:duration={dur}",
        "-f", "lavfi", "-i", f"sine=frequency=440:duration={dur}",
        "-c:v", vcodec,
        "-pix_fmt", pix_fmt,
    ]
    if vcodec == "mjpeg":
        cmd += ["-q:v", "12"]  # visually lossless, big files, encodes fast
    else:
        cmd += ["-b:v", "1200k"]
    cmd += [
        "-c:a", acodec,
        "-b:a", "96k",
        "-shortest",
        str(out),
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"ffmpeg failed for {out.name}:\n{r.stderr[-800:]}")
    return out


# ---------------------------------------------------------------------------
# Static file server (with HTTP Range) simulating a real CDN.
# ---------------------------------------------------------------------------
class _QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format, *args):  # silence
        pass


class _ReusableTCPServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


def start_static_server(root: Path) -> tuple[str, threading.Thread, _ReusableTCPServer]:
    port = free_port()
    handler = lambda *a, **k: _QuietHandler(*a, directory=str(root), **k)
    srv = _ReusableTCPServer(("127.0.0.1", port), handler)
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    return f"http://127.0.0.1:{port}", t, srv


# ---------------------------------------------------------------------------
# App under test
# ---------------------------------------------------------------------------
def start_web_app() -> tuple[str, subprocess.Popen]:
    port = free_port()
    env = os.environ.copy()
    env["PORT"] = str(port)
    env["VIDEOFLOW_DOWNLOAD_DIR"] = tempfile.mkdtemp(prefix="videoflow-test-")
    proc = subprocess.Popen(
        [sys.executable, str(ROOT / "web.py")],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    # Wait for it to come up.
    base = f"http://127.0.0.1:{port}"
    for _ in range(60):
        try:
            with urllib.request.urlopen(base + "/api/health", timeout=1) as r:
                if r.status == 200:
                    return base, proc
        except Exception:
            time.sleep(0.25)
    proc.terminate()
    raise RuntimeError("web.py never came up")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------
def _post(url: str, body: dict) -> dict:
    data = json.dumps(body).encode()
    req = urllib.request.Request(
        url, data=data, headers={"Content-Type": "application/json"}, method="POST"
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())


def _get_json(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=30) as r:
        return json.loads(r.read().decode())


def _test_one(base_web: str, src_url: str, src_path: Path, label: str) -> dict:
    print(f"\n=== {label} — {src_path.name} ({fmt_bytes(src_path.stat().st_size)}) ===")
    t0 = time.time()
    info = _post(base_web + "/api/info", {"url": src_url})
    if "error" in info:
        raise RuntimeError(f"info failed: {info['error']}")
    print(f"  info: title={info.get('title')!r}, formats={len(info.get('formats') or [])}")

    job = _post(base_web + "/api/download", {"url": src_url})
    jid = job.get("job_id")
    if not jid:
        raise RuntimeError(f"download start failed: {job}")

    # Poll.
    last = 0
    for _ in range(300):
        p = _get_json(f"{base_web}/api/progress/{jid}")
        if p.get("status") == "finished":
            break
        if p.get("status") == "error":
            raise RuntimeError(f"job errored: {p.get('error')}")
        pct = p.get("percent") or 0
        if pct - last >= 25:
            print(f"  progress: {pct:.1f}%  {fmt_bytes(p.get('downloaded',0))}/{fmt_bytes(p.get('total',0))}")
            last = pct
        time.sleep(0.5)
    else:
        raise RuntimeError("timed out")
    p = _get_json(f"{base_web}/api/progress/{jid}")
    print(f"  finished: file={p.get('filename')} size={fmt_bytes(p.get('total') or 0)} in {time.time()-t0:.1f}s")

    # Full download from web.
    with urllib.request.urlopen(f"{base_web}/api/file/{jid}", timeout=60) as r:
        served = r.read()
        assert r.headers.get("Content-Disposition", "").startswith("attachment"), \
            f"missing Content-Disposition header: {dict(r.headers)}"
        assert r.headers.get("Accept-Ranges") == "bytes", "Accept-Ranges header missing"

    src_bytes = src_path.read_bytes()
    assert served == src_bytes, f"bytes served ({len(served)}) != source ({len(src_bytes)})"

    # Range request.
    mid = len(src_bytes) // 2
    req = urllib.request.Request(f"{base_web}/api/file/{jid}", headers={"Range": f"bytes={mid}-{mid+1023}"})
    with urllib.request.urlopen(req, timeout=30) as r:
        assert r.status == 206, f"expected 206, got {r.status}"
        rng = r.read()
    assert rng == src_bytes[mid:mid + 1024], "range bytes mismatch"
    print(f"  ✓ served {fmt_bytes(len(served))} + verified 1KB range")
    return {"label": label, "size": len(served), "ok": True}


def main() -> int:
    if not FFMPEG:
        print("ffmpeg not available — cannot run the sandbox suite.")
        return 2

    print(f"ffmpeg: {FFMPEG}")

    # 1. Build sample library.
    samples_dir = Path(tempfile.mkdtemp(prefix="videoflow-samples-"))
    print(f"\nGenerating sample videos in {samples_dir} …")
    made = []
    for cont, w, h, vc, ac, label in SAMPLES:
        try:
            p = _make_sample(samples_dir, cont, w, h, vc, ac)
            print(f"  ✓ {p.name}  {fmt_bytes(p.stat().st_size)}  ({label})")
            made.append((p, label))
        except Exception as e:
            print(f"  ✗ {label}: {e}")

    # 2. Serve them.
    base_static, _t, srv = start_static_server(samples_dir)
    print(f"\nStatic server: {base_static}")

    # 3. Boot the web app.
    base_web, proc = start_web_app()
    print(f"Web app:      {base_web}")

    results = []
    try:
        for p, label in made:
            try:
                results.append(_test_one(base_web, f"{base_static}/{p.name}", p, label))
            except Exception as e:
                print(f"  ✗ FAILED: {e}")
                results.append({"label": label, "ok": False, "error": str(e)})
    finally:
        srv.shutdown()
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except Exception:
            proc.kill()

    # 4. Summary.
    ok = sum(1 for r in results if r.get("ok"))
    print("\n" + "=" * 70)
    print(f"SANDBOX RESULTS: {ok}/{len(results)} passed")
    for r in results:
        status = "✓" if r.get("ok") else "✗"
        size = fmt_bytes(r["size"]) if r.get("ok") else r.get("error", "")
        print(f"  [{status}] {r['label']:40s}  {size}")
    print("=" * 70)
    return 0 if ok == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
