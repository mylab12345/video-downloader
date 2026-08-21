#!/usr/bin/env python3
"""
Web frontend for the VideoFlow downloader.

This is the missing piece that lets users download videos *over the web*:
a small Flask app that

  * serves a single-page UI at ``/``
  * exposes ``POST /api/info``  → JSON metadata + format list
  * exposes ``POST /api/download`` → starts a background job, returns job_id
  * exposes ``GET  /api/progress/<job_id>`` → live progress (poll)
  * exposes ``GET  /api/file/<job_id>`` → streams the finished file to
    the browser with a proper ``Content-Disposition`` header, using
    chunked transfer + HTTP Range support so multi-GB / 4K / 8K files
    can be downloaded without buffering into memory.

The design decisions here are the actual fixes for the reported
"video downloads don't work over the web" bug:

  * Downloads run in a background thread — the HTTP request that starts
    a download returns immediately, so browsers, load balancers, and
    reverse proxies never hit their idle-timeout on large files.
  * Files are streamed from disk in 1 MiB chunks with `wsgi.file_wrapper`
    when available, avoiding OOM on 4K/8K MKVs (tens of GB).
  * HTTP Range is honoured so browsers can pause/resume, and download
    managers can parallelise.
  * CORS headers + trust-all-hosts config so the app works behind the
    e2b sandbox preview proxy on `https://{port}-{id}.e2b.app`.
"""

from __future__ import annotations

import mimetypes
import os
import re
import tempfile
import threading
import time
import traceback
import uuid
from pathlib import Path
from typing import Dict

from flask import (
    Flask,
    Response,
    jsonify,
    render_template_string,
    request,
    send_from_directory,
)
from werkzeug.middleware.proxy_fix import ProxyFix

from downloader import VideoDownloader, FFMPEG_PATH


# ---------------------------------------------------------------------------
# App + job registry
# ---------------------------------------------------------------------------
app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # request bodies only
# Preview is served on https://{port}-{sandbox}.e2b.app — never reject Host.
app.config["TRUSTED_HOSTS"] = None
app.config["PREFERRED_URL_SCHEME"] = "https"
# Behind the Arena / e2b reverse proxy (TLS + Host rewrite).
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

# Where finished files are stored. Keep it outside the source tree.
DOWNLOAD_ROOT = Path(os.environ.get("VIDEOFLOW_DOWNLOAD_DIR", tempfile.gettempdir())) / "videoflow"
DOWNLOAD_ROOT.mkdir(parents=True, exist_ok=True)

# In-memory job registry — fine for a single-process sandbox.
_JOBS: Dict[str, dict] = {}
_JOBS_LOCK = threading.Lock()


def _new_job() -> str:
    jid = uuid.uuid4().hex[:12]
    with _JOBS_LOCK:
        _JOBS[jid] = {
            "id": jid,
            "status": "queued",  # queued | downloading | finished | error
            "percent": 0.0,
            "downloaded": 0,
            "total": 0,
            "speed": 0,
            "eta": 0,
            "error": None,
            "file": None,
            "filename": None,
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


# ---------------------------------------------------------------------------
# Download worker
# ---------------------------------------------------------------------------
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
            total=os.path.getsize(out),
            downloaded=os.path.getsize(out),
        )
    except Exception as e:
        traceback.print_exc()
        _update_job(jid, status="error", error=str(e))


# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------
@app.after_request
def _cors(resp):
    resp.headers["Access-Control-Allow-Origin"] = "*"
    resp.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    resp.headers["Access-Control-Allow-Headers"] = "Content-Type"
    # Live preview is shown inside an iframe on the Arena UI.
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
    if not url:
        return jsonify({"error": "missing url"}), 400
    jid = _new_job()
    threading.Thread(target=_run_download, args=(jid, url, format_id), daemon=True).start()
    return jsonify({"job_id": jid})


@app.get("/api/progress/<jid>")
def api_progress(jid):
    j = _get_job(jid)
    if not j:
        return jsonify({"error": "unknown job"}), 404
    # Don't leak absolute server paths to the browser.
    j.pop("file", None)
    return jsonify(j)


# ---------------------------------------------------------------------------
# File streaming with Range support
# ---------------------------------------------------------------------------
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


# ---------------------------------------------------------------------------
# UI
# ---------------------------------------------------------------------------
INDEX_HTML = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>VideoFlow — Web Downloader</title>
<style>
  :root {
    --bg:#0f0f1a; --panel:#181825; --surface:#1e1e2e; --border:#313244;
    --text:#cdd6f4; --muted:#a6adc8; --accent:#89b4fa; --accent2:#b4befe;
    --ok:#a6e3a1; --err:#f38ba8; --warn:#f9e2af;
  }
  *{box-sizing:border-box}
  body{margin:0;background:radial-gradient(1200px 800px at 20% -10%,#1e1e3a 0,transparent 60%),
       radial-gradient(900px 600px at 110% 10%,#3a1e3a 0,transparent 60%),var(--bg);
       color:var(--text);font:15px/1.4 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;
       min-height:100vh}
  .wrap{max-width:920px;margin:0 auto;padding:40px 20px 80px}
  h1{font-size:28px;margin:0 0 4px;letter-spacing:-.02em}
  .tag{color:var(--muted);margin:0 0 28px}
  .card{background:rgba(30,30,46,.7);backdrop-filter:blur(14px);
        border:1px solid var(--border);border-radius:14px;padding:20px;margin-bottom:16px}
  .row{display:flex;gap:10px}
  input,select,button{font:inherit;color:inherit}
  input[type=text]{flex:1;background:var(--panel);border:1px solid var(--border);
                   border-radius:10px;padding:12px 14px;outline:none}
  input[type=text]:focus{border-color:var(--accent)}
  button{background:var(--accent);color:#11111b;border:none;border-radius:10px;
         padding:12px 18px;font-weight:600;cursor:pointer;transition:.15s}
  button:hover{background:var(--accent2)}
  button.secondary{background:var(--surface);color:var(--text);border:1px solid var(--border)}
  button:disabled{opacity:.5;cursor:not-allowed}
  select{width:100%;background:var(--panel);border:1px solid var(--border);
         border-radius:10px;padding:12px 14px;outline:none}
  .meta{display:flex;gap:16px;align-items:flex-start}
  .thumb{width:180px;height:100px;border-radius:8px;background:var(--panel);
         object-fit:cover;flex-shrink:0}
  .meta-info h3{margin:0 0 4px;font-size:17px}
  .meta-info p{margin:0;color:var(--muted);font-size:13px}
  .progress{height:14px;background:var(--panel);border-radius:8px;overflow:hidden;
            border:1px solid var(--border);margin:14px 0 8px}
  .fill{height:100%;background:linear-gradient(90deg,var(--accent),var(--accent2));
        width:0%;transition:width .3s}
  .pmeta{display:flex;justify-content:space-between;color:var(--muted);font-size:13px}
  .toast{position:fixed;right:20px;bottom:20px;background:var(--surface);
         border:1px solid var(--border);padding:12px 16px;border-radius:10px;
         max-width:360px;box-shadow:0 8px 24px rgba(0,0,0,.4);display:none}
  .toast.show{display:block;animation:slide .2s ease}
  .toast.err{border-color:var(--err);color:var(--err)}
  .toast.ok{border-color:var(--ok);color:var(--ok)}
  @keyframes slide{from{transform:translateY(10px);opacity:0}to{transform:translateY(0);opacity:1}}
  .muted{color:var(--muted);font-size:13px}
  a{color:var(--accent)}
  .footer{color:var(--muted);font-size:12px;text-align:center;margin-top:30px}
  code{background:var(--panel);padding:2px 6px;border-radius:4px;font-size:13px}
</style>
</head>
<body>
<div class="wrap">
  <h1>🎬 VideoFlow</h1>
  <p class="tag">Download videos from YouTube, Vimeo, direct URLs and 1000+ sites — right in your browser.</p>

  <div class="card">
    <div class="row">
      <input id="url" type="text" placeholder="Paste a video URL (YouTube, Vimeo, TikTok, direct .mp4, …)" />
      <button id="analyze">Analyze</button>
    </div>
    <p class="muted" style="margin:10px 0 0">Tip: try a direct <code>.mp4</code>, <code>.mkv</code>, <code>.mov</code>, <code>.avi</code>, or <code>.wmv</code> URL.</p>
  </div>

  <div id="preview" class="card" style="display:none">
    <div class="meta">
      <img id="thumb" class="thumb" alt="">
      <div class="meta-info">
        <h3 id="title">—</h3>
        <p id="sub">—</p>
      </div>
    </div>
    <div style="margin-top:14px">
      <label class="muted" for="fmt">Quality / format</label>
      <select id="fmt"></select>
    </div>
    <div class="row" style="margin-top:14px">
      <button id="download">⬇️ Download</button>
      <button id="reset" class="secondary">Clear</button>
    </div>
  </div>

  <div id="progress" class="card" style="display:none">
    <div style="display:flex;justify-content:space-between;align-items:center">
      <strong id="pstatus">Starting…</strong>
      <span class="muted" id="ppct">0%</span>
    </div>
    <div class="progress"><div class="fill" id="pfill"></div></div>
    <div class="pmeta">
      <span id="psize">0 / 0</span>
      <span id="pspeed">0 B/s</span>
      <span id="peta">ETA —</span>
    </div>
    <div class="row" style="margin-top:14px">
      <a id="saveLink" style="display:none"><button>💾 Save file</button></a>
    </div>
  </div>

  <p class="footer">Powered by yt-dlp + ffmpeg. Supports MP4, MKV, MOV, AVI, WMV, WebM at up to 8K.</p>
</div>

<div id="toast" class="toast"></div>

<script>
const $ = s => document.querySelector(s);
const fmt = n => {
  if (!n) return "0 B";
  const u = ["B","KB","MB","GB","TB"]; let i = 0;
  while (n >= 1024 && i < u.length-1) { n /= 1024; i++; }
  return n.toFixed(2) + " " + u[i];
};
const fmtTime = s => {
  if (!s) return "—";
  const m = Math.floor(s/60), r = s%60;
  return m ? `${m}m ${r}s` : `${r}s`;
};
function toast(msg, kind="") {
  const t = $("#toast");
  t.className = "toast show " + kind;
  t.textContent = msg;
  clearTimeout(window._tt); window._tt = setTimeout(()=>t.classList.remove("show"), 4500);
}

let currentInfo = null;
let pollTimer = null;

$("#analyze").onclick = async () => {
  const url = $("#url").value.trim();
  if (!url) return toast("Enter a URL first", "err");
  $("#analyze").disabled = true; $("#analyze").textContent = "Analyzing…";
  try {
    const r = await fetch("api/info", {method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify({url})});
    const j = await r.json();
    if (!r.ok) throw new Error(j.error || "failed");
    currentInfo = j;
    $("#preview").style.display = "block";
    $("#title").textContent = j.title || "(untitled)";
    $("#sub").textContent = [j.uploader, j.duration ? fmtTime(j.duration) : null].filter(Boolean).join(" • ");
    $("#thumb").src = j.thumbnail || "";
    const sel = $("#fmt"); sel.innerHTML = "";
    j.formats.forEach(f => {
      const o = document.createElement("option");
      o.value = f.format_id; o.textContent = f.label;
      sel.appendChild(o);
    });
    toast("Ready to download", "ok");
  } catch (e) { toast(e.message, "err"); }
  finally { $("#analyze").disabled = false; $("#analyze").textContent = "Analyze"; }
};

$("#reset").onclick = () => {
  currentInfo = null;
  $("#preview").style.display = "none";
  $("#progress").style.display = "none";
  $("#url").value = "";
  clearInterval(pollTimer);
};

$("#download").onclick = async () => {
  if (!currentInfo) return;
  const url = $("#url").value.trim();
  const format_id = $("#fmt").value;
  $("#download").disabled = true;
  try {
    const r = await fetch("api/download", {method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify({url, format_id})});
    const j = await r.json();
    if (!r.ok) throw new Error(j.error || "failed");
    startPolling(j.job_id);
  } catch (e) { toast(e.message, "err"); $("#download").disabled = false; }
};

function startPolling(jid) {
  $("#progress").style.display = "block";
  $("#pstatus").textContent = "Queued…";
  $("#saveLink").style.display = "none";
  clearInterval(pollTimer);
  pollTimer = setInterval(async () => {
    try {
      const r = await fetch("api/progress/" + jid);
      const j = await r.json();
      $("#ppct").textContent = (j.percent || 0).toFixed(1) + "%";
      $("#pfill").style.width = (j.percent || 0) + "%";
      $("#psize").textContent = fmt(j.downloaded) + " / " + fmt(j.total);
      $("#pspeed").textContent = fmt(j.speed) + "/s";
      $("#peta").textContent = "ETA " + fmtTime(j.eta);
      $("#pstatus").textContent = ({queued:"Queued…", downloading:"Downloading…", processing:"Processing…", finished:"Finished ✔", error:"Error ✖"})[j.status] || j.status;
      if (j.status === "finished") {
        clearInterval(pollTimer);
        const a = $("#saveLink");
        a.href = "api/file/" + jid;
        a.setAttribute("download", j.filename || "video");
        a.style.display = "inline-block";
        $("#download").disabled = false;
        toast("Download ready: " + (j.filename || ""), "ok");
      } else if (j.status === "error") {
        clearInterval(pollTimer);
        toast(j.error || "Download failed", "err");
        $("#download").disabled = false;
      }
    } catch (e) { /* transient */ }
  }, 800);
}
</script>
</body>
</html>
"""


@app.get("/")
def index():
    return render_template_string(INDEX_HTML)


def serve(host: str = "0.0.0.0", port: int | None = None) -> None:
    """Run the web GUI. Bound on 0.0.0.0 so the preview proxy can reach us."""
    if port is None:
        port = int(os.environ.get("PORT", "8000"))
    # Threaded so multiple downloads / range requests can be served
    # concurrently. use_reloader=False so we don't spawn a second process
    # that races the preview probe.
    app.run(host=host, port=port, threaded=True, debug=False, use_reloader=False)


if __name__ == "__main__":
    serve()
