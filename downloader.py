#!/usr/bin/env python3
"""
Core Video Downloader.

Wraps yt-dlp with a robust, web-friendly configuration:

  * Streams-safe defaults (chunk size / retries / timeouts).
  * Container-safe merging (prefers MKV, falls back to MP4).
  * Auth-aware error messages (bot check, private/removed, 403).
  * Optional aria2c external downloader when installed.
  * Deterministic on-disk filenames (`restrictfilenames=True`) so the
    resulting file is safe to hand to a browser as a download.
"""

import os
import shutil
import subprocess
import sys
import yt_dlp


# --- ffmpeg discovery -------------------------------------------------------
# yt-dlp needs ffmpeg to merge separate video+audio streams (which is how
# every 1080p / 4K / 8K YouTube download works).  In many sandboxes ffmpeg
# isn't on $PATH so we fall back to the static binary shipped by the
# `imageio-ffmpeg` wheel.
def _resolve_ffmpeg() -> str | None:
    path = shutil.which("ffmpeg")
    if path:
        return path
    try:
        import imageio_ffmpeg  # type: ignore

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return None


FFMPEG_PATH = _resolve_ffmpeg()


class VideoDownloader:
    """yt-dlp powered downloader with sane defaults for a web frontend."""

    def __init__(
        self,
        cookie_file: str | None = None,
        use_cookies_from_browser: bool = False,
        browser_name: str = "chrome",
    ):
        self.cookie_file = cookie_file
        self.use_cookies_from_browser = use_cookies_from_browser
        self.browser_name = browser_name

    # ------------------------------------------------------------------ opts
    def _get_base_opts(self) -> dict:
        """Shared yt-dlp options for both info fetch and download."""
        opts: dict = {
            "quiet": True,
            "no_warnings": True,
            "socket_timeout": 30,
            "retries": 10,
            "fragment_retries": 10,
            "file_access_retries": 5,
            "extractor_retries": 5,
            # Fixes a class of "certificate verify failed" errors seen when
            # yt-dlp fetches info behind corporate proxies / sandboxes.
            "nocheckcertificate": True,
            # Try to bypass a few common restrictions.
            "geo_bypass": True,
            "extractor_args": {
                "youtube": {
                    # Multiple player clients works around the "Sign in to
                    # confirm you're not a bot" errors on many videos.
                    "player_client": ["ios", "android", "web"],
                }
            },
        }

        if FFMPEG_PATH:
            opts["ffmpeg_location"] = FFMPEG_PATH

        if self.cookie_file and os.path.exists(self.cookie_file):
            opts["cookiefile"] = self.cookie_file
        elif self.use_cookies_from_browser:
            try:
                opts["cookiesfrombrowser"] = (self.browser_name,)
            except Exception:
                pass

        return opts

    # ------------------------------------------------------------------ info
    def fetch_video_info(self, url: str) -> dict:
        """Fetch metadata + formats without downloading."""
        ydl_opts = self._get_base_opts()
        ydl_opts.update(
            {
                "skip_download": True,
                "extract_flat": False,
                "playlistend": 1,
            }
        )

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                return ydl.extract_info(url, download=False)
        except yt_dlp.utils.DownloadError as e:
            raise Exception(self._friendly_error(str(e), url)) from e

    # --------------------------------------------------------------- formats
    def parse_formats(self, info: dict) -> list:
        """Turn yt-dlp's raw format list into UI-friendly entries."""
        formats = info.get("formats", [])
        parsed: list[dict] = []

        parsed.append(
            {
                "format_id": "bestvideo*+bestaudio/best",
                "label": "Best Quality (Auto Merge Best Video & Audio)",
                "resolution": "Best Auto",
                "ext": "mp4/mkv",
                "filesize_str": "Dynamic",
            }
        )
        parsed.append(
            {
                "format_id": "bestaudio/best",
                "label": "Best Audio Only (Extract MP3/M4A)",
                "resolution": "Audio Only",
                "ext": "mp3/m4a",
                "filesize_str": "Dynamic",
            }
        )

        seen = set()
        for f in reversed(formats):
            vcodec = f.get("vcodec", "none")
            acodec = f.get("acodec", "none")
            height = f.get("height")
            width = f.get("width")
            ext = f.get("ext", "mp4")
            fid = f.get("format_id")
            filesize = f.get("filesize") or f.get("filesize_approx")

            if height:
                res_str = f"{height}p"
            elif width:
                res_str = f"{width}w"
            else:
                res_str = "Audio Only" if vcodec == "none" else "Unknown"

            filesize_str = (
                f"{round(filesize / (1024 * 1024), 1)} MB"
                if filesize
                else "Unknown size"
            )
            fps = f.get("fps")
            fps_str = f" {fps}fps" if fps and fps > 30 else ""
            note = f.get("format_note", "")

            if vcodec != "none" and acodec != "none":
                type_str = "Video+Audio"
            elif vcodec != "none":
                type_str = "Video Only"
            else:
                type_str = "Audio Only"

            label = f"{res_str}{fps_str} [{ext.upper()}] ({type_str}) - {filesize_str}"
            if note:
                label += f" ({note})"

            if label in seen or not fid:
                continue
            seen.add(label)

            target = (
                f"{fid}+bestaudio/best"
                if vcodec != "none" and acodec == "none"
                else fid
            )
            parsed.append(
                {
                    "format_id": target,
                    "raw_fid": fid,
                    "label": label,
                    "resolution": res_str,
                    "ext": ext,
                    "filesize_str": filesize_str,
                }
            )

        return parsed

    # ------------------------------------------------------------- download
    def download(
        self,
        url: str,
        format_id: str | None = None,
        output_path: str = ".",
        progress_hook=None,
    ) -> str:
        """
        Download a video to ``output_path``.

        Returns the absolute path of the resulting file on disk.  The
        filename is restricted to ASCII-safe characters so it can be sent
        back to a browser via ``Content-Disposition`` without escaping
        surprises.
        """
        os.makedirs(output_path, exist_ok=True)
        # `restrictfilenames` keeps names ASCII / path-safe.
        out_tmpl = os.path.join(output_path, "%(title).150B [%(id)s].%(ext)s")

        target_format = format_id or "bestvideo*+bestaudio/best"

        ydl_opts = self._get_base_opts()
        ydl_opts.update(
            {
                "format": target_format,
                "outtmpl": out_tmpl,
                "restrictfilenames": True,
                "windowsfilenames": True,
                "noprogress": True,
                "concurrent_fragment_downloads": 4,
                # 1 MiB chunks: large enough for throughput, small enough
                # that a broken connection retries fast.  10 MiB (previous
                # value) frequently tripped server-side range limits and
                # led to stalled downloads over flaky links.
                "http_chunk_size": 1048576,
                # MKV is the safe universal merge container — it accepts
                # any codec combination yt-dlp might produce (VP9+Opus,
                # AV1+Opus, HEVC+AAC, …).  When the streams happen to be
                # H.264+AAC ffmpeg's remuxer still produces an MP4 anyway.
                "merge_output_format": "mkv",
                "postprocessor_args": {
                    "ffmpeg": ["-movflags", "+faststart"],
                },
            }
        )

        # Optional aria2c external downloader.
        if shutil.which("aria2c"):
            ydl_opts["external_downloader"] = {"http": "aria2c", "https": "aria2c"}
            ydl_opts["external_downloader_args"] = {
                "aria2c": [
                    "--max-connection-per-server=4",
                    "--min-split-size=1M",
                    "--split=4",
                    "--async-dns=false",
                    "--disable-ipv6=true",
                    "--allow-overwrite=true",
                    "--auto-file-renaming=false",
                ]
            }

        if progress_hook:
            ydl_opts["progress_hooks"] = [progress_hook]

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                if not info:
                    return None

                # Playlists: use first entry.
                if info.get("_type") == "playlist" and info.get("entries"):
                    info = info["entries"][0]

                # yt-dlp's `requested_downloads` is the source of truth for
                # the actual file that ended up on disk (accounts for
                # post-processor rewrites like merge / remux).
                rd = info.get("requested_downloads") or []
                if rd and rd[0].get("filepath") and os.path.exists(rd[0]["filepath"]):
                    return os.path.abspath(rd[0]["filepath"])

                filename = ydl.prepare_filename(info)
                if os.path.exists(filename):
                    return os.path.abspath(filename)

                # Fall back to searching for any extension after merge.
                base = os.path.splitext(filename)[0]
                for ext in (".mkv", ".mp4", ".webm", ".m4a", ".mp3", ".opus", ".aac"):
                    if os.path.exists(base + ext):
                        return os.path.abspath(base + ext)

                return None
        except yt_dlp.utils.DownloadError as e:
            raise Exception(self._friendly_error(str(e), url)) from e

    # --------------------------------------------------------------- errors
    @staticmethod
    def _friendly_error(error_msg: str, url: str) -> str:
        low = error_msg.lower()
        if "sign in to confirm" in low or "confirm you" in low or "not a bot" in low:
            return (
                "This site requires authentication (bot check). Export "
                "browser cookies to a Netscape cookies.txt file and pass "
                "it via VideoDownloader(cookie_file='cookies.txt')."
            )
        if "unavailable" in low or "private" in low or "removed" in low:
            return f"Video is unavailable, private, or has been removed: {url}"
        if "403" in low or "forbidden" in low:
            return (
                f"Access forbidden (HTTP 403). The URL may need auth or the "
                f"source rate-limited us: {url}"
            )
        if "ffmpeg" in low and ("not" in low or "install" in low):
            return (
                "ffmpeg is required to merge separate video+audio streams "
                "(needed for 1080p / 4K / 8K). Install ffmpeg or the "
                "`imageio-ffmpeg` Python package."
            )
        return f"Download failed: {error_msg}"
