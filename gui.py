#!/usr/bin/env python3
import os
import sys
import threading
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from downloader import VideoDownloader

class VideoDownloaderGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("All-in-One Video Downloader")
        self.root.geometry("780x620")
        self.root.minsize(700, 550)

        self.downloader = VideoDownloader()
        self.parsed_formats = []
        self.current_info = None

        self.setup_styles()
        self.build_ui()

    def setup_styles(self):
        self.style = ttk.Style()
        self.style.theme_use('clam')

        # Color Palette
        self.bg_color = "#1e1e2e"
        self.fg_color = "#cdd6f4"
        self.card_bg = "#313244"
        self.accent_color = "#89b4fa"
        self.success_color = "#a6e3a1"
        self.btn_bg = "#45475a"
        self.btn_active = "#585b70"

        self.root.configure(bg=self.bg_color)

        self.style.configure(".", background=self.bg_color, foreground=self.fg_color, font=("Helvetica", 10))
        self.style.configure("Header.TLabel", font=("Helvetica", 18, "bold"), foreground=self.accent_color, background=self.bg_color)
        self.style.configure("SubHeader.TLabel", font=("Helvetica", 10, "italic"), foreground="#a6adc8", background=self.bg_color)
        self.style.configure("Card.TFrame", background=self.card_bg)
        self.style.configure("Card.TLabel", background=self.card_bg, foreground=self.fg_color)
        self.style.configure("TButton", font=("Helvetica", 10, "bold"), background=self.btn_bg, foreground=self.fg_color, padding=6)
        self.style.map("TButton", background=[("active", self.btn_active)])
        
        self.style.configure("Accent.TButton", font=("Helvetica", 10, "bold"), background=self.accent_color, foreground="#11111b", padding=6)
        self.style.map("Accent.TButton", background=[("active", "#b4befe")])

        self.style.configure("Horizontal.TProgressbar", thickness=18, troughcolor="#45475a", background=self.accent_color)

    def build_ui(self):
        # Header
        header_frame = ttk.Frame(self.root, padding=(20, 15))
        header_frame.pack(fill="x")

        title_label = ttk.Label(header_frame, text="⚡ Universal Video Downloader", style="Header.TLabel")
        title_label.pack(anchor="w")

        subtitle_label = ttk.Label(
            header_frame,
            text="Download videos in all qualities from YouTube, TikTok, Vimeo, Twitter/X, Direct URLs & 1000+ sites",
            style="SubHeader.TLabel"
        )
        subtitle_label.pack(anchor="w", pady=(2, 0))

        # Main Scrollable / Card Frame
        main_frame = ttk.Frame(self.root, padding=20)
        main_frame.pack(fill="both", expand=True)

        # 1. URL Section Card
        url_card = ttk.Frame(main_frame, style="Card.TFrame", padding=15)
        url_card.pack(fill="x", pady=(0, 12))

        url_label = ttk.Label(url_card, text="Video URL:", style="Card.TLabel", font=("Helvetica", 11, "bold"))
        url_label.pack(anchor="w", pady=(0, 5))

        url_input_frame = ttk.Frame(url_card, style="Card.TFrame")
        url_input_frame.pack(fill="x")

        self.url_entry = ttk.Entry(url_input_frame, font=("Helvetica", 11))
        self.url_entry.pack(side="left", fill="x", expand=True, ipady=4)
        self.url_entry.focus()

        paste_btn = ttk.Button(url_input_frame, text="📋 Paste", command=self.paste_url)
        paste_btn.pack(side="left", padx=(8, 0))

        self.fetch_btn = ttk.Button(url_input_frame, text="🔍 Fetch Qualities", style="Accent.TButton", command=self.on_fetch_qualities)
        self.fetch_btn.pack(side="left", padx=(8, 0))

        # 2. Video Info & Quality Selection Card
        self.info_card = ttk.Frame(main_frame, style="Card.TFrame", padding=15)
        self.info_card.pack(fill="x", pady=(0, 12))

        self.title_val_label = ttk.Label(self.info_card, text="Title: Enter a video URL and click 'Fetch Qualities'", style="Card.TLabel", font=("Helvetica", 10, "bold"), wraplength=700)
        self.title_val_label.pack(anchor="w", pady=(0, 6))

        self.meta_val_label = ttk.Label(self.info_card, text="Uploader: - | Duration: -", style="Card.TLabel", font=("Helvetica", 9), foreground="#a6adc8")
        self.meta_val_label.pack(anchor="w", pady=(0, 10))

        quality_label = ttk.Label(self.info_card, text="Select Video Quality / Format:", style="Card.TLabel", font=("Helvetica", 10, "bold"))
        quality_label.pack(anchor="w", pady=(0, 4))

        self.quality_combo = ttk.Combobox(self.info_card, state="disabled", font=("Helvetica", 10))
        self.quality_combo.pack(fill="x", ipady=3)

        # 3. Output Folder Card
        out_card = ttk.Frame(main_frame, style="Card.TFrame", padding=15)
        out_card.pack(fill="x", pady=(0, 12))

        out_label = ttk.Label(out_card, text="Save Folder:", style="Card.TLabel", font=("Helvetica", 10, "bold"))
        out_label.pack(anchor="w", pady=(0, 4))

        out_input_frame = ttk.Frame(out_card, style="Card.TFrame")
        out_input_frame.pack(fill="x")

        self.out_dir_var = tk.StringVar(value=os.path.abspath("downloads"))
        self.out_entry = ttk.Entry(out_input_frame, textvariable=self.out_dir_var, font=("Helvetica", 10))
        self.out_entry.pack(side="left", fill="x", expand=True, ipady=3)

        browse_btn = ttk.Button(out_input_frame, text="📁 Browse...", command=self.browse_folder)
        browse_btn.pack(side="left", padx=(8, 0))

        # 4. Progress & Action Card
        action_card = ttk.Frame(main_frame, style="Card.TFrame", padding=15)
        action_card.pack(fill="both", expand=True)

        self.download_btn = ttk.Button(action_card, text="⬇ Start Download", style="Accent.TButton", state="disabled", command=self.on_start_download)
        self.download_btn.pack(fill="x", ipady=5, pady=(0, 10))

        self.progress_bar = ttk.Progressbar(action_card, orient="horizontal", mode="determinate", style="Horizontal.TProgressbar")
        self.progress_bar.pack(fill="x", pady=(0, 6))

        self.status_label = ttk.Label(action_card, text="Status: Ready", style="Card.TLabel", font=("Helvetica", 9, "bold"))
        self.status_label.pack(anchor="w")

        self.metrics_label = ttk.Label(action_card, text="Speed: 0 B/s | Downloaded: 0 B | ETA: --", style="Card.TLabel", font=("Helvetica", 9), foreground="#a6adc8")
        self.metrics_label.pack(anchor="w")

    def paste_url(self):
        try:
            clipboard_text = self.root.clipboard_get().strip()
            self.url_entry.delete(0, tk.END)
            self.url_entry.insert(0, clipboard_text)
        except Exception:
            pass

    def browse_folder(self):
        selected = filedialog.askdirectory(initialdir=self.out_dir_var.get())
        if selected:
            self.out_dir_var.set(selected)

    def on_fetch_qualities(self):
        url = self.url_entry.get().strip()
        if not url:
            messagebox.showwarning("Input Required", "Please enter or paste a video URL.")
            return

        self.fetch_btn.config(state="disabled")
        self.download_btn.config(state="disabled")
        self.status_label.config(text="Status: 🔍 Fetching video qualities...")
        self.title_val_label.config(text="Title: Fetching metadata...")

        # Run fetch in background thread
        threading.Thread(target=self._async_fetch, args=(url,), daemon=True).start()

    def _async_fetch(self, url):
        try:
            info = self.downloader.fetch_video_info(url)
            parsed_formats = self.downloader.parse_formats(info)
            self.root.after(0, self._on_fetch_success, info, parsed_formats)
        except Exception as e:
            self.root.after(0, self._on_fetch_error, str(e))

    def _on_fetch_success(self, info, parsed_formats):
        self.current_info = info
        self.parsed_formats = parsed_formats

        title = info.get('title', 'Unknown Title')
        uploader = info.get('uploader', 'Unknown Uploader')
        duration = info.get('duration', 0)
        
        mins, secs = divmod(duration, 60)
        hrs, mins = divmod(mins, 60)
        dur_str = f"{hrs}h {mins}m {secs}s" if hrs else f"{mins}m {secs}s" if duration else "Live/Unknown"

        self.title_val_label.config(text=f"Title: {title}")
        self.meta_val_label.config(text=f"Uploader: {uploader} | Duration: {dur_str}")

        combo_values = [fmt['label'] for fmt in self.parsed_formats]
        self.quality_combo.config(values=combo_values, state="readonly")
        if combo_values:
            self.quality_combo.current(0)

        self.fetch_btn.config(state="normal")
        self.download_btn.config(state="normal")
        self.status_label.config(text="Status: Qualities loaded! Ready to download.")

    def _on_fetch_error(self, err_msg):
        self.fetch_btn.config(state="normal")
        self.status_label.config(text="Status: ❌ Error fetching qualities")
        self.title_val_label.config(text="Title: Could not fetch video metadata.")
        messagebox.showerror("Fetch Error", f"Failed to fetch video details:\n{err_msg}")

    def on_start_download(self):
        url = self.url_entry.get().strip()
        selected_idx = self.quality_combo.current()

        if selected_idx < 0 or selected_idx >= len(self.parsed_formats):
            format_id = 'bestvideo+bestaudio/best'
        else:
            format_id = self.parsed_formats[selected_idx]['format_id']

        out_path = self.out_dir_var.get().strip() or "."

        self.fetch_btn.config(state="disabled")
        self.download_btn.config(state="disabled")
        self.quality_combo.config(state="disabled")
        self.progress_bar['value'] = 0
        self.status_label.config(text="Status: 🚀 Downloading...")

        threading.Thread(target=self._async_download, args=(url, format_id, out_path), daemon=True).start()

    def _async_download(self, url, format_id, out_path):
        try:
            saved_path = self.downloader.download(
                url,
                format_id=format_id,
                output_path=out_path,
                progress_hook=self._progress_hook
            )
            self.root.after(0, self._on_download_success, saved_path)
        except Exception as e:
            self.root.after(0, self._on_download_error, str(e))

    def _progress_hook(self, d):
        if d.get('status') == 'downloading':
            total = d.get('total_bytes') or d.get('total_bytes_estimate') or 0
            downloaded = d.get('downloaded_bytes', 0)
            speed = d.get('speed', 0) or 0
            eta = d.get('eta', 0) or 0

            percent = (downloaded / total * 100) if total > 0 else 0
            speed_str = self._format_bytes(speed) + "/s"
            downloaded_str = self._format_bytes(downloaded)
            total_str = self._format_bytes(total)
            eta_str = f"{eta}s" if eta else "--"

            self.root.after(0, self._update_progress_ui, percent, speed_str, downloaded_str, total_str, eta_str)

    def _format_bytes(self, bytes_num):
        if not bytes_num:
            return "0 B"
        for unit in ['B', 'KB', 'MB', 'GB']:
            if bytes_num < 1024.0:
                return f"{bytes_num:.2f} {unit}"
            bytes_num /= 1024.0
        return f"{bytes_num:.2f} GB"

    def _update_progress_ui(self, percent, speed_str, downloaded_str, total_str, eta_str):
        self.progress_bar['value'] = percent
        self.status_label.config(text=f"Status: 🚀 Downloading ({percent:.1f}%)")
        self.metrics_label.config(text=f"Speed: {speed_str} | Downloaded: {downloaded_str} / {total_str} | ETA: {eta_str}")

    def _on_download_success(self, saved_path):
        self.progress_bar['value'] = 100
        self.status_label.config(text="Status: 🎉 Download Complete!")
        self.metrics_label.config(text=f"Saved file to: {saved_path}")
        self.fetch_btn.config(state="normal")
        self.download_btn.config(state="normal")
        self.quality_combo.config(state="readonly")
        messagebox.showinfo("Success", f"Video successfully downloaded to:\n{saved_path}")

    def _on_download_error(self, err_msg):
        self.fetch_btn.config(state="normal")
        self.download_btn.config(state="normal")
        self.quality_combo.config(state="readonly")
        self.status_label.config(text="Status: ❌ Download Failed")
        messagebox.showerror("Download Error", f"An error occurred during download:\n{err_msg}")

def main():
    root = tk.Tk()
    app = VideoDownloaderGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()
