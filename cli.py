#!/usr/bin/env python3
import sys
import os
import argparse
from downloader import VideoDownloader

def format_bytes(bytes_num):
    if not bytes_num:
        return "0 B"
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_num < 1024.0:
            return f"{bytes_num:.2f} {unit}"
        bytes_num /= 1024.0
    return f"{bytes_num:.2f} PB"

def cli_progress_hook(d):
    status = d.get('status')
    if status == 'downloading':
        total = d.get('total_bytes') or d.get('total_bytes_estimate') or 0
        downloaded = d.get('downloaded_bytes', 0)
        speed = d.get('speed', 0) or 0
        eta = d.get('eta', 0) or 0

        percent = (downloaded / total * 100) if total > 0 else 0
        percent_str = f"{percent:.1f}%"
        speed_str = f"{format_bytes(speed)}/s"
        eta_str = f"{eta}s" if eta else "N/A"
        downloaded_str = format_bytes(downloaded)
        total_str = format_bytes(total)

        bar_length = 30
        filled_length = int(bar_length * percent // 100) if total > 0 else 0
        bar = '█' * filled_length + '-' * (bar_length - filled_length)

        sys.stdout.write(f"\r[{bar}] {percent_str} | {downloaded_str}/{total_str} | Speed: {speed_str} | ETA: {eta_str}  ")
        sys.stdout.flush()

    elif status == 'finished':
        sys.stdout.write("\n✔ Download finished! Processing final file...\n")
        sys.stdout.flush()

def main():
    parser = argparse.ArgumentParser(
        description="All-in-One Universal Video Downloader CLI (YouTube, TikTok, Twitter, Vimeo, Direct URLs & 1000+ sites)"
    )
    parser.add_argument("url", nargs="?", help="URL of the video to download")
    parser.add_argument("-l", "--list-formats", action="store_true", help="List all available qualities and formats for the video")
    parser.add_argument("-f", "--format", help="Format ID to download (e.g. 1080p, bestvideo+bestaudio, or specific format ID)")
    parser.add_argument("-o", "--output", default=".", help="Output directory path (default: current directory)")
    parser.add_argument("-a", "--audio-only", action="store_true", help="Download best audio only (MP3/M4A)")

    args = parser.parse_args()

    if not args.url:
        args.url = input("Enter Video URL: ").strip()
        if not args.url:
            print("Error: No URL provided.")
            sys.exit(1)

    dl = VideoDownloader()
    print(f"\n🔍 Fetching video info for: {args.url}")

    try:
        info = dl.fetch_video_info(args.url)
        title = info.get('title', 'Unknown Title')
        duration = info.get('duration', 0)
        uploader = info.get('uploader', 'Unknown')
        
        print(f"\n🎥 Title: {title}")
        print(f"👤 Uploader: {uploader}")
        if duration:
            mins, secs = divmod(duration, 60)
            hrs, mins = divmod(mins, 60)
            dur_str = f"{hrs}h {mins}m {secs}s" if hrs else f"{mins}m {secs}s"
            print(f"⏱  Duration: {dur_str}")
        
        parsed_formats = dl.parse_formats(info)

        if args.list_formats:
            print("\n📋 Available Qualities and Formats:")
            print("-" * 75)
            for idx, fmt in enumerate(parsed_formats, 1):
                print(f" [{idx:2d}] {fmt['label']}")
            print("-" * 75)
            return

        selected_format_id = None

        if args.audio_only:
            selected_format_id = 'bestaudio/best'
        elif args.format:
            # Check if user passed a resolution string like "1080p" or index number or exact format_id
            if args.format.isdigit():
                idx = int(args.format) - 1
                if 0 <= idx < len(parsed_formats):
                    selected_format_id = parsed_formats[idx]['format_id']
                else:
                    print(f"Warning: Format index {args.format} out of range. Using default best quality.")
            else:
                # search by resolution string
                matched = [f for f in parsed_formats if args.format.lower() in f['resolution'].lower()]
                if matched:
                    selected_format_id = matched[0]['format_id']
                else:
                    selected_format_id = args.format
        else:
            # Interactive format selection if launched without specific format flag
            print("\n📋 Available Qualities:")
            print("-" * 75)
            for idx, fmt in enumerate(parsed_formats, 1):
                print(f" [{idx:2d}] {fmt['label']}")
            print("-" * 75)
            
            choice = input(f"\nSelect quality number [1-{len(parsed_formats)}] (Default: 1 - Best Quality): ").strip()
            if choice.isdigit() and 1 <= int(choice) <= len(parsed_formats):
                selected_format_id = parsed_formats[int(choice) - 1]['format_id']
            else:
                selected_format_id = parsed_formats[0]['format_id']

        print(f"\n🚀 Starting download into: {os.path.abspath(args.output)}")
        saved_file = dl.download(args.url, format_id=selected_format_id, output_path=args.output, progress_hook=cli_progress_hook)
        print(f"🎉 Saved successfully to: {saved_file}\n")

    except Exception as e:
        print(f"\n❌ Error downloading video: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
