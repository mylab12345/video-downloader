#!/usr/bin/env python3
"""
VideoFlow desktop app backend.

Flask serves a native-feeling desktop shell (templates/index.html) plus
the download API. Bound on 0.0.0.0 so the Arena preview proxy can reach it.
"""

from __future__ import annotations

import mimetypes
import os
import re
import subprocess
import tempfile
import threading
import time
import traceback
import uuid
from pathlib import Path
from typing import Dict

from flask import Flask, Response, jsonify, request, send_from_directory
from werkzeug.middleware.proxy_fix import ProxyFix

from downloader import VideoDownloader, FFMPEG_PATH

ROOT = Path(__file__).resolve().parent

app = Flask(__name__, static_folder=str(ROOT / "static"), static_url_path="/static")
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024
app.config["TRUSTED_HOSTS"] = None
app.config["PREFERRED_URL_SCHEME"] = "https"
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

DOWNLOAD_ROOT = Path(os.environ.get("VIDEOFLOW_DOWNLOAD_DIR", tempfile.gettempdir())) / "videoflow"
DOWNLOAD_ROOT.mkdir(parents=True, exist_ok=True)

_JOBS: Dict[str, dict] = {}
_JOBS_LOCK = threading.Lock()
_VIDEO_EXTS = {".mp4", ".mkv", ".webm", ".mov", ".avi", ".wmv", ".m4a", ".mp3", ".opus", ".aac"}


def _new_job(url: str = "", format_id: str | None = None, title: str | None = None) -> str:
    jid = uuid.uuid4().hex[:12]
    with _JOBS_LOCK:
        _JOBS[jid] = {
            "id": jid,
            "status": "queued",
            "percent": 0.0,
            "downloaded": 0,
            "total": 0,
            "speed": 0,
            "eta": 0,
            "error": None,
            "file": None,
            "filename": None,
            "url": url,
            "format_id": format_id,
            "title": title or url or jid,
            "started": time.time(),
        }
    return jid


def _update_job(jid: str, **fields) -> None:
    with _JOBS_LOCK:
        if jid in _JOBS:
            _JOBS[jid].update(fields)


def _get_job(jid: str) -> dict | None:
    with _JOBS_LOCK:
        j = _JOBS.get(jid)
        return dict(j) if j else None


def _run_download(jid: str, url: str, format_id: str | None) -> None:
    job_dir = DOWNLOAD_ROOT / jid
    job_dir.mkdir(parents=True, exist_ok=True)
    dl = VideoDownloader()

    def hook(d):
        status = d.get("status")
        if status == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
            done = d.get("downloaded_bytes", 0)
            _update_job(
                jid,
                status="downloading",
                percent=(done / total * 100.0) if total else 0.0,
                downloaded=done,
                total=total,
                speed=d.get("speed") or 0,
                eta=d.get("eta") or 0,
            )
        elif status == "finished":
            _update_job(jid, status="processing", percent=99.0)

    try:
        _update_job(jid, status="downloading")
        out = dl.download(url, format_id=format_id, output_path=str(job_dir), progress_hook=hook)
        if not out or not os.path.exists(out):
            raise RuntimeError("downloader returned no file")
        _update_job(
            jid,
            status="finished",
            percent=100.0,
            file=out,
            filename=os.path.basename(out),
            title=_JOBS.get(jid, {}).get("title") or os.path.basename(out),
            total=os.path.getsize(out),
            downloaded=os.path.getsize(out),
        )
    except Exception as e:
        traceback.print_exc()
        _update_job(jid, status="error", error=str(e))


@app.after_request
def _cors(resp):
    resp.headers["Access-Control-Allow-Origin"] = "*"
    resp.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    resp.headers["Access-Control-Allow-Headers"] = "Content-Type"
    resp.headers.pop("X-Frame-Options", None)
    resp.headers["Content-Security-Policy"] = "frame-ancestors *"
    return resp


@app.get("/api/health")
def health():
    return jsonify(
        {
            "ok": True,
            "ffmpeg": FFMPEG_PATH,
            "download_root": str(DOWNLOAD_ROOT),
            "jobs": len(_JOBS),
        }
    )


@app.post("/api/info")
def api_info():
    data = request.get_json(force=True, silent=True) or {}
    url = (data.get("url") or "").strip()
    if not url:
        return jsonify({"error": "missing url"}), 400
    try:
        info = VideoDownloader().fetch_video_info(url)
    except Exception as e:
        return jsonify({"error": str(e)}), 400

    formats = VideoDownloader().parse_formats(info)
    return jsonify(
        {
            "title": info.get("title"),
            "uploader": info.get("uploader"),
            "duration": info.get("duration"),
            "thumbnail": info.get("thumbnail"),
            "webpage_url": info.get("webpage_url") or url,
            "formats": formats,
        }
    )


@app.post("/api/download")
def api_download():
    data = request.get_json(force=True, silent=True) or {}
    url = (data.get("url") or "").strip()
    format_id = (data.get("format_id") or "").strip() or None
    title = (data.get("title") or "").strip() or None
    if not url:
        return jsonify({"error": "missing url"}), 400
    jid = _new_job(url=url, format_id=format_id, title=title)
    threading.Thread(target=_run_download, args=(jid, url, format_id), daemon=True).start()
    return jsonify({"job_id": jid})


@app.get("/api/progress/<jid>")
def api_progress(jid):
    j = _get_job(jid)
    if not j:
        return jsonify({"error": "unknown job"}), 404
    j.pop("file", None)
    return jsonify(j)


@app.get("/api/jobs")
def api_jobs():
    with _JOBS_LOCK:
        jobs = []
        for j in _JOBS.values():
            d = dict(j)
            d.pop("file", None)
            jobs.append(d)
    jobs.sort(key=lambda x: x.get("started") or 0, reverse=True)
    return jsonify(jobs)


@app.get("/api/library")
def api_library():
    items = []
    if DOWNLOAD_ROOT.exists():
        with _JOBS_LOCK:
            known = set(_JOBS.keys())
        for p in DOWNLOAD_ROOT.rglob("*"):
            if not p.is_file() or p.suffix.lower() not in _VIDEO_EXTS:
                continue
            items.append(
                {
                    "name": p.name,
                    "size": p.stat().st_size,
                    "job_id": p.parent.name if p.parent.name in known else None,
                }
            )
    items.sort(key=lambda x: x["name"])
    return jsonify(items)


@app.post("/api/install-desktop")
def api_install_desktop():
    script = ROOT / "packaging" / "install-desktop.sh"
    if not script.exists():
        return jsonify({"ok": False, "log": "install script missing"}), 500
    r = subprocess.run(["bash", str(script)], capture_output=True, text=True)
    return jsonify({"ok": r.returncode == 0, "log": (r.stdout or "") + (r.stderr or "")})


_RANGE_RE = re.compile(r"bytes=(\d+)-(\d*)")


def _stream_file(path: str, start: int, end: int, chunk: int = 1024 * 1024):
    remaining = end - start + 1
    with open(path, "rb") as f:
        f.seek(start)
        while remaining > 0:
            data = f.read(min(chunk, remaining))
            if not data:
                break
            remaining -= len(data)
            yield data


@app.get("/api/file/<jid>")
def api_file(jid):
    j = _get_job(jid)
    if not j or j.get("status") != "finished":
        return jsonify({"error": "not ready"}), 404
    path = j.get("file") or (_JOBS.get(jid) or {}).get("file")
    if not path or not os.path.exists(path):
        return jsonify({"error": "file missing on disk"}), 410

    file_size = os.path.getsize(path)
    filename = os.path.basename(path)
    mime = mimetypes.guess_type(filename)[0] or "application/octet-stream"

    range_hdr = request.headers.get("Range", "")
    start, end = 0, file_size - 1
    status = 200
    headers = {
        "Content-Type": mime,
        "Content-Disposition": f'attachment; filename="{filename}"',
        "Accept-Ranges": "bytes",
        "Cache-Control": "no-store",
    }

    m = _RANGE_RE.match(range_hdr)
    if m:
        start = int(m.group(1))
        end = int(m.group(2)) if m.group(2) else file_size - 1
        end = min(end, file_size - 1)
        if start > end:
            return Response(status=416, headers={"Content-Range": f"bytes */{file_size}"})
        status = 206
        headers["Content-Range"] = f"bytes {start}-{end}/{file_size}"

    headers["Content-Length"] = str(end - start + 1)
    return Response(_stream_file(path, start, end), status=status, headers=headers, direct_passthrough=True)


@app.get("/")
def index():
    return send_from_directory(ROOT / "templates", "index.html")


@app.get("/icon.png")
def icon():
    return send_from_directory(ROOT / "assets", "icon.png")


@app.get("/manifest.webmanifest")
def manifest():
    return send_from_directory(ROOT / "static", "manifest.webmanifest")


def serve(host: str = "0.0.0.0", port: int | None = None) -> None:
    if port is None:
        port = int(os.environ.get("PORT", "8000"))
    app.run(host=host, port=port, threaded=True, debug=False, use_reloader=False)


if __name__ == "__main__":
    serve()
