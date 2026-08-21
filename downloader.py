#!/usr/bin/env python3
import os
import sys
import yt_dlp
import subprocess
import tempfile

class VideoDownloader:
    """
    Core Video Downloader utilizing yt-dlp to support 1000+ websites and direct video URLs.
    Handles format extraction, metadata parsing, and downloading with progress tracking.
    Optimized for fast downloads with concurrent fragments and smart retry logic.
    """

    def __init__(self, cookie_file=None, use_cookies_from_browser=False, browser_name='chrome'):
        """
        Initialize the downloader with optional authentication.
        
        Args:
            cookie_file: Path to Netscape cookie file for authentication
            use_cookies_from_browser: Whether to extract cookies from browser
            browser_name: Browser name to extract cookies from (chrome, firefox, edge, etc.)
        """
        self.cookie_file = cookie_file
        self.use_cookies_from_browser = use_cookies_from_browser
        self.browser_name = browser_name
        
    def _get_base_opts(self):
        """Get base yt-dlp options with authentication support"""
        opts = {
            'quiet': True,
            'no_warnings': True,
            'skip_download': True,
            'extract_flat': False,
            'socket_timeout': 30,
            'retries': 5,
            'fragment_retries': 5,
            # Try to bypass some restrictions
            'extractor_args': {
                'youtube': {
                    'player_client': ['ios', 'web'],  # Use multiple player clients
                    'player_skip': ['webpage'],  # Skip webpage extraction when possible
                }
            },
        }
        
        # Add cookie support if available
        if self.cookie_file and os.path.exists(self.cookie_file):
            opts['cookiefile'] = self.cookie_file
        elif self.use_cookies_from_browser:
            try:
                # Try to auto-detect browser cookies
                opts['cookiesfrombrowser'] = (self.browser_name,)
            except:
                pass
                
        return opts

    def fetch_video_info(self, url: str) -> dict:
        """
        Fetches metadata and available formats for a given video URL without downloading.
        Enhanced with better error handling and retry logic.
        """
        ydl_opts = self._get_base_opts()
        
        # Add specific options for info extraction
        ydl_opts.update({
            'skip_download': True,
            'playlistend': 1,  # Only get first video if playlist
        })
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                return info
        except yt_dlp.utils.DownloadError as e:
            error_msg = str(e)
            
            # Check for common errors and provide helpful messages
            if 'Sign in to confirm' in error_msg or 'bot' in error_msg.lower():
                raise Exception(
                    "YouTube requires authentication. Please export cookies using:\n"
                    "  1. Install 'cookies.txt' browser extension\n"
                    "  2. Export cookies from youtube.com\n"
                    "  3. Save as 'cookies.txt' in the same directory\n"
                    "Or use: VideoDownloader(cookie_file='cookies.txt')"
                )
            elif 'unavailable' in error_msg.lower() or 'private' in error_msg.lower():
                raise Exception(f"Video is unavailable, private, or has been removed: {url}")
            elif '403' in error_msg or 'Forbidden' in error_msg:
                raise Exception(f"Access forbidden. The URL may require authentication or has restrictions: {url}")
            else:
                raise Exception(f"Failed to fetch video info: {error_msg}")

    def parse_formats(self, info: dict) -> list:
        """
        Parses yt-dlp raw format list into clean user-friendly dictionaries.
        """
        formats = info.get('formats', [])
        parsed = []
        
        # Default smart choices at top
        parsed.append({
            'format_id': 'bestvideo+bestaudio/best',
            'label': 'Best Quality (Auto Merge Best Video & Audio)',
            'resolution': 'Best Auto',
            'ext': 'mp4/mkv',
            'filesize_str': 'Dynamic'
        })
        parsed.append({
            'format_id': 'bestaudio/best',
            'label': 'Best Audio Only (Extract MP3/M4A)',
            'resolution': 'Audio Only',
            'ext': 'mp3/m4a',
            'filesize_str': 'Dynamic'
        })

        seen_labels = set()
        
        # Reverse format list to get higher qualities first
        for f in reversed(formats):
            vcodec = f.get('vcodec', 'none')
            acodec = f.get('acodec', 'none')
            height = f.get('height')
            width = f.get('width')
            ext = f.get('ext', 'mp4')
            fid = f.get('format_id')
            filesize = f.get('filesize') or f.get('filesize_approx')
            
            if height:
                res_str = f"{height}p"
            elif width:
                res_str = f"{width}w"
            else:
                res_str = "Audio Only" if vcodec == 'none' else "Unknown"

            filesize_str = f"{round(filesize / (1024 * 1024), 1)} MB" if filesize else "Unknown size"
            
            format_note = f.get('format_note', '')
            fps = f.get('fps')
            fps_str = f" {fps}fps" if fps and fps > 30 else ""
            
            type_str = "Video+Audio" if vcodec != 'none' and acodec != 'none' else ("Video Only" if vcodec != 'none' else "Audio Only")
            label = f"{res_str}{fps_str} [{ext.upper()}] ({type_str}) - {filesize_str}"
            if format_note:
                label += f" ({format_note})"
                
            if label not in seen_labels and fid:
                seen_labels.add(label)
                # If video only, pair with best audio for complete output
                target_format_id = f"{fid}+bestaudio/best" if vcodec != 'none' and acodec == 'none' else fid
                parsed.append({
                    'format_id': target_format_id,
                    'raw_fid': fid,
                    'label': label,
                    'resolution': res_str,
                    'ext': ext,
                    'filesize_str': filesize_str
                })

        return parsed

    def download(self, url: str, format_id: str = None, output_path: str = ".", progress_hook=None) -> str:
        """
        Downloads video for a given URL and format into output_path.
        Optimized for maximum download speed with concurrent fragments.
        Supports all video formats and high resolutions (4K, 8K, HDR).
        """
        os.makedirs(output_path, exist_ok=True)
        out_tmpl = os.path.join(output_path, '%(title)s.%(ext)s')

        target_format = format_id if format_id else 'bestvideo+bestaudio/best'

        ydl_opts = self._get_base_opts()
        ydl_opts.update({
            'format': target_format,
            'outtmpl': out_tmpl,
            'quiet': True,
            'no_warnings': True,
            'nocheckcertificate': True,
            # Speed optimization settings
            'concurrent_fragment_downloads': 4,  # Download 4 fragments concurrently
            'fragment_retries': 5,
            'retries': 5,
            'socket_timeout': 30,
            'http_chunk_size': 10485760,  # 10MB chunks for better throughput
            # Post-processing options
            'merge_output_format': 'mp4',  # Auto-merge to mp4
            'postprocessor_args': ['-movflags', '+faststart'],  # Optimize for streaming
        })

        # Try to use aria2c for faster downloads if available
        aria2c_available = False
        try:
            result = subprocess.run(['aria2c', '--version'], capture_output=True, timeout=2)
            if result.returncode == 0:
                aria2c_available = True
                ydl_opts['external_downloader'] = 'aria2c'
                ydl_opts['external_downloader_args'] = {
                    'aria2c': [
                        '--max-connection-per-server=4',
                        '--min-split-size=1M',
                        '--split=4',
                        '--async-dns=false',
                        '--disable-ipv6=true',
                    ]
                }
        except (subprocess.SubprocessError, FileNotFoundError):
            pass

        if progress_hook:
            ydl_opts['progress_hooks'] = [progress_hook]

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                if info:
                    filename = ydl.prepare_filename(info)
                    # Handle merged files (when video+audio are combined)
                    if not os.path.exists(filename):
                        # Try common extensions
                        for ext in ['.mp4', '.mkv', '.webm', '.m4a', '.mp3']:
                            alt_filename = os.path.splitext(filename)[0] + ext
                            if os.path.exists(alt_filename):
                                return alt_filename
                    return filename
                return None
        except yt_dlp.utils.DownloadError as e:
            error_msg = str(e)
            if 'Sign in to confirm' in error_msg or 'bot' in error_msg.lower():
                raise Exception(
                    "YouTube requires authentication. Please use cookies for authentication.\n"
                    "See: https://github.com/yt-dlp/yt-dlp/wiki/FAQ#how-do-i-pass-cookies-to-yt-dlp"
                )
            elif 'unavailable' in error_msg.lower():
                raise Exception(f"Video is unavailable or has been removed: {url}")
            else:
                raise Exception(f"Download failed: {error_msg}")
