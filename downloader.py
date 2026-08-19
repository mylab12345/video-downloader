#!/usr/bin/env python3
import os
import sys
import yt_dlp

class VideoDownloader:
    """
    Core Video Downloader utilizing yt-dlp to support 1000+ websites and direct video URLs.
    Handles format extraction, metadata parsing, and downloading with progress tracking.
    Optimized for fast downloads with concurrent fragments and smart retry logic.
    """

    def fetch_video_info(self, url: str) -> dict:
        """
        Fetches metadata and available formats for a given video URL without downloading.
        """
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'skip_download': True,
            'extract_flat': False,
            'socket_timeout': 30,
            'retries': 3,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return info

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
        """
        os.makedirs(output_path, exist_ok=True)
        out_tmpl = os.path.join(output_path, '%(title)s.%(ext)s')

        target_format = format_id if format_id else 'bestvideo+bestaudio/best'

        ydl_opts = {
            'format': target_format,
            'outtmpl': out_tmpl,
            'quiet': True,
            'no_warnings': True,
            'nocheckcertificate': True,
            # Speed optimization settings
            'concurrent_fragment_downloads': 4,  # Download 4 fragments concurrently
            'fragment_retries': 3,
            'retries': 3,
            'socket_timeout': 30,
            'http_chunk_size': 10485760,  # 10MB chunks for better throughput
            # Use aria2c if available for even faster downloads
            'external_downloader': 'aria2c',
            'external_downloader_args': {
                'aria2c': [
                    '--max-connection-per-server=4',
                    '--min-split-size=1M',
                    '--split=4',
                    '--async-dns=false',
                    '--disable-ipv6=true',
                ]
            },
            # Post-processing options
            'merge_output_format': 'mp4',  # Auto-merge to mp4
            'postprocessor_args': ['-movflags', '+faststart'],  # Optimize for streaming
        }

        # Fallback to default downloader if aria2c is not available
        try:
            import subprocess
            result = subprocess.run(['aria2c', '--version'], capture_output=True, timeout=2)
            if result.returncode != 0:
                # aria2c not available, remove external downloader settings
                del ydl_opts['external_downloader']
                del ydl_opts['external_downloader_args']
        except (subprocess.SubprocessError, FileNotFoundError):
            # aria2c not installed, use built-in downloader
            del ydl_opts['external_downloader']
            del ydl_opts['external_downloader_args']

        if progress_hook:
            ydl_opts['progress_hooks'] = [progress_hook]

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            return filename
