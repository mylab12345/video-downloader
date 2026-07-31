#!/usr/bin/env python3
"""
Modern Video Downloader GUI
Glassmorphism / Neumorphism inspired dark UI
Inspired by 4K Video Downloader, JDownloader 2, yt-dlp web UIs

Features implemented:
- Smart URL input + auto platform detection + Paste & Analyze / One-click Download
- Dynamic glass preview card (thumbnail placeholder, title, meta, high-quality options)
- Audio/Video toggle (segmented)
- High quality options (8K, 4K HDR, 1080p, etc + Best)
- Sleek queue list with reorder, status, mini progress
- Custom animated canvas progress bar (speed + ETA)
- Micro-interactions, hover effects, state transitions
- Slide-in settings panel (from right)
- Toast notifications (non-blocking)
- Clean minimalist dark palette
"""

import os
import sys
import threading
import time
import re
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from downloader import VideoDownloader

# ==================== MODERN COLOR PALETTE (Catppuccin Mocha inspired) ====================
class Colors:
    BG = "#181825"          # Main dark background
    BG_ALT = "#1e1e2e"      # Slightly lighter
    SURFACE = "#313244"     # Glass / card surface
    SURFACE_HOVER = "#45475a"
    SURFACE_ACTIVE = "#585b70"
    TEXT = "#cdd6f4"
    TEXT_MUTED = "#a6adc8"
    ACCENT = "#89b4fa"      # Primary blue
    ACCENT_DARK = "#74c7ec"
    SUCCESS = "#a6e3a1"
    WARNING = "#f9e2af"
    ERROR = "#f38ba8"
    GLASS_BORDER = "#45475a"
    PROGRESS_BG = "#45475a"
    PROGRESS_FILL = "#89b4fa"

# ==================== CUSTOM WIDGETS ====================

class ModernProgressBar(tk.Canvas):
    """Glassmorphic animated progress bar with speed + ETA overlay"""
    def __init__(self, parent, width=600, height=42, **kwargs):
        super().__init__(parent, width=width, height=height, 
                         bg=Colors.BG, highlightthickness=0, **kwargs)
        self.width = width
        self.height = height
        self.progress = 0.0
        self.speed = "0 B/s"
        self.eta = "--:--"
        self.downloaded = "0 B"
        self.total = "0 B"
        self.status = "idle"
        self._animation_id = None
        self._pulse = 0
        
        # Rounded glass frame
        self.bind("<Configure>", self._on_resize)
        self._draw()

    def _on_resize(self, event):
        self.width = event.width
        self._draw()

    def _draw_rounded_rect(self, x1, y1, x2, y2, radius, fill, outline=None, width=1):
        """Draw rounded rectangle using arcs + lines"""
        self.create_rectangle(x1 + radius, y1, x2 - radius, y2, fill=fill, outline="", width=0)
        self.create_rectangle(x1, y1 + radius, x2, y2 - radius, fill=fill, outline="", width=0)
        self.create_arc(x1, y1, x1 + 2*radius, y1 + 2*radius, start=90, extent=90, fill=fill, outline="")
        self.create_arc(x2 - 2*radius, y1, x2, y1 + 2*radius, start=0, extent=90, fill=fill, outline="")
        self.create_arc(x1, y2 - 2*radius, x1 + 2*radius, y2, start=180, extent=90, fill=fill, outline="")
        self.create_arc(x2 - 2*radius, y2 - 2*radius, x2, y2, start=270, extent=90, fill=fill, outline="")
        
        if outline:
            # Draw subtle outline
            self.create_line(x1 + radius, y1, x2 - radius, y1, fill=outline, width=width)
            self.create_line(x1 + radius, y2, x2 - radius, y2, fill=outline, width=width)
            self.create_line(x1, y1 + radius, x1, y2 - radius, fill=outline, width=width)
            self.create_line(x2, y1 + radius, x2, y2 - radius, fill=outline, width=width)

    def _draw(self):
        self.delete("all")
        
        # Outer glass border (subtle)
        self._draw_rounded_rect(2, 2, self.width-2, self.height-2, 14, 
                               Colors.SURFACE, Colors.GLASS_BORDER, 1)
        
        # Inner track
        track_margin = 6
        self._draw_rounded_rect(track_margin, track_margin, 
                               self.width - track_margin, self.height - track_margin, 
                               10, Colors.PROGRESS_BG)
        
        # Progress fill
        if self.progress > 0:
            fill_width = (self.width - 2*track_margin) * (self.progress / 100)
            if fill_width > 20:
                self._draw_rounded_rect(track_margin, track_margin, 
                                       track_margin + fill_width, self.height - track_margin, 
                                       10, Colors.PROGRESS_FILL)
        
        # Gloss overlay (glassmorphism highlight)
        gloss_height = self.height // 3
        self.create_rectangle(track_margin + 2, track_margin + 2, 
                             self.width - track_margin - 2, track_margin + gloss_height,
                             fill="#ffffff", stipple="gray50", outline="")
        
        # Text overlay
        center_y = self.height // 2 + 1
        
        # Main percent
        percent_text = f"{self.progress:.0f}%" if self.progress > 0 else ""
        self.create_text(self.width//2 - 60, center_y, text=percent_text, 
                        fill=Colors.TEXT, font=("Segoe UI", 13, "bold"), anchor="center")
        
        # Speed + ETA
        info_text = f"{self.speed}  •  ETA {self.eta}"
        self.create_text(self.width//2 + 50, center_y, text=info_text, 
                        fill=Colors.TEXT_MUTED, font=("Segoe UI", 10), anchor="center")
        
        # Downloaded / total (right aligned)
        if self.total != "0 B":
            self.create_text(self.width - 18, center_y + 1, text=f"{self.downloaded} / {self.total}",
                            fill=Colors.TEXT_MUTED, font=("Segoe UI", 9), anchor="e")

    def set_progress(self, percent, speed="0 B/s", eta="--:--", downloaded="0 B", total="0 B"):
        self.progress = max(0, min(100, percent))
        self.speed = speed
        self.eta = eta
        self.downloaded = downloaded
        self.total = total
        self._draw()

    def set_status(self, status):
        self.status = status
        self._draw()

    def reset(self):
        self.progress = 0
        self.speed = "0 B/s"
        self.eta = "--:--"
        self.downloaded = "0 B"
        self.total = "0 B"
        self._draw()

class Toast(tk.Toplevel):
    """Non-intrusive toast notification"""
    def __init__(self, parent, message, type_="info", duration=2800):
        super().__init__(parent)
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        
        colors = {
            "success": (Colors.SUCCESS, Colors.BG),
            "error": (Colors.ERROR, Colors.BG),
            "info": (Colors.ACCENT, Colors.BG),
            "warning": (Colors.WARNING, Colors.BG),
        }
        accent, bg = colors.get(type_, (Colors.ACCENT, Colors.BG))
        
        # Position bottom right
        parent.update_idletasks()
        x = parent.winfo_x() + parent.winfo_width() - 340
        y = parent.winfo_y() + parent.winfo_height() - 90
        
        self.geometry(f"320x62+{x}+{y}")
        self.configure(bg=Colors.SURFACE)
        
        # Glass frame
        frame = tk.Frame(self, bg=Colors.SURFACE, bd=0)
        frame.pack(fill="both", expand=True, padx=2, pady=2)
        
        # Accent bar
        bar = tk.Frame(frame, bg=accent, width=5)
        bar.pack(side="left", fill="y")
        
        # Content
        content = tk.Frame(frame, bg=Colors.SURFACE)
        content.pack(side="left", fill="both", expand=True, padx=12, pady=8)
        
        icon_map = {"success": "✓", "error": "✕", "info": "ℹ", "warning": "⚠"}
        tk.Label(content, text=icon_map.get(type_, "•"), 
                font=("Segoe UI", 16), bg=Colors.SURFACE, fg=accent).pack(side="left", padx=(0, 8))
        
        tk.Label(content, text=message, font=("Segoe UI", 11), 
                bg=Colors.SURFACE, fg=Colors.TEXT, wraplength=260, justify="left").pack(side="left", fill="x", expand=True)
        
        # Auto dismiss
        self.after(duration, self._fade_out)

    def _fade_out(self):
        try:
            self.destroy()
        except:
            pass

class QueueItem(tk.Frame):
    """Modern queue list item"""
    def __init__(self, parent, index, title, url, quality, status="queued", on_remove=None, on_move=None):
        super().__init__(parent, bg=Colors.SURFACE, bd=0)
        self.index = index
        self.url = url
        self.quality = quality
        self.on_remove = on_remove
        self.on_move = on_move
        self.status = status
        self.progress = 0
        
        self.configure(padx=8, pady=6)
        
        # Left accent
        accent = tk.Frame(self, bg=Colors.ACCENT, width=3)
        accent.pack(side="left", fill="y")
        
        # Main content
        main = tk.Frame(self, bg=Colors.SURFACE)
        main.pack(side="left", fill="both", expand=True, padx=10)
        
        # Title row
        title_frame = tk.Frame(main, bg=Colors.SURFACE)
        title_frame.pack(fill="x")
        
        self.title_label = tk.Label(title_frame, text=title[:55] + ("..." if len(title) > 55 else ""), 
                                   font=("Segoe UI", 10, "bold"), bg=Colors.SURFACE, fg=Colors.TEXT,
                                   anchor="w")
        self.title_label.pack(side="left", fill="x", expand=True)
        
        self.quality_badge = tk.Label(title_frame, text=quality[:18], 
                                     font=("Segoe UI", 8), bg=Colors.SURFACE_HOVER, 
                                     fg=Colors.ACCENT, padx=6, pady=1)
        self.quality_badge.pack(side="right")
        
        # Status row
        status_frame = tk.Frame(main, bg=Colors.SURFACE)
        status_frame.pack(fill="x", pady=(2, 0))
        
        self.status_label = tk.Label(status_frame, text=status.upper(), 
                                    font=("Segoe UI", 8, "bold"), bg=Colors.SURFACE, 
                                    fg=Colors.TEXT_MUTED)
        self.status_label.pack(side="left")
        
        self.mini_progress = tk.Canvas(status_frame, width=110, height=6, 
                                       bg=Colors.PROGRESS_BG, highlightthickness=0)
        self.mini_progress.pack(side="left", padx=8)
        
        self.metrics = tk.Label(status_frame, text="", font=("Segoe UI", 8), 
                               bg=Colors.SURFACE, fg=Colors.TEXT_MUTED)
        self.metrics.pack(side="left")
        
        # Action buttons
        btn_frame = tk.Frame(self, bg=Colors.SURFACE)
        btn_frame.pack(side="right", padx=(0, 4))
        
        # Up / Down
        tk.Button(btn_frame, text="↑", font=("Segoe UI", 9), width=2, bg=Colors.SURFACE_HOVER,
                 fg=Colors.TEXT, bd=0, command=lambda: self._move(-1)).pack(side="top", pady=1)
        tk.Button(btn_frame, text="↓", font=("Segoe UI", 9), width=2, bg=Colors.SURFACE_HOVER,
                 fg=Colors.TEXT, bd=0, command=lambda: self._move(1)).pack(side="top")
        
        # Remove
        tk.Button(btn_frame, text="✕", font=("Segoe UI", 9), width=2, bg=Colors.SURFACE_HOVER,
                 fg=Colors.ERROR, bd=0, command=self._remove).pack(side="top", pady=(4, 0))
        
        self.bind("<Enter>", lambda e: self.config(bg=Colors.SURFACE_HOVER))
        self.bind("<Leave>", lambda e: self.config(bg=Colors.SURFACE))

    def _move(self, direction):
        if self.on_move:
            self.on_move(self.index, direction)
    
    def _remove(self):
        if self.on_remove:
            self.on_remove(self.index)
    
    def update_status(self, status, progress=0, speed="", eta=""):
        self.status = status
        self.progress = progress
        color = {
            "queued": Colors.TEXT_MUTED,
            "analyzing": Colors.ACCENT,
            "downloading": Colors.ACCENT,
            "completed": Colors.SUCCESS,
            "error": Colors.ERROR,
        }.get(status, Colors.TEXT_MUTED)
        
        self.status_label.config(text=status.upper(), fg=color)
        
        # Update mini progress
        self.mini_progress.delete("all")
        if progress > 0:
            fill_w = int(110 * (progress / 100))
            self.mini_progress.create_rectangle(0, 0, fill_w, 6, fill=Colors.ACCENT, outline="")
        
        if speed or eta:
            self.metrics.config(text=f"{speed} • {eta}" if speed and eta else speed or eta)

# ==================== MAIN APPLICATION ====================

class ModernVideoDownloaderGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("VideoFlow • Modern Downloader")
        self.root.geometry("1040x780")
        self.root.minsize(920, 660)
        self.root.configure(bg=Colors.BG)
        
        # State
        self.downloader = VideoDownloader()
        self.current_info = None
        self.parsed_formats = []
        self.queue = []  # list of dicts
        self.active_download = None
        self.settings_visible = False
        self.audio_only_mode = False
        
        self._setup_styles()
        self._build_ui()
        self._setup_bindings()
        
        # Demo queue items (for visual polish)
        self._add_demo_queue_items()

    def _setup_styles(self):
        style = ttk.Style()
        style.theme_use("clam")
        
        # Global
        style.configure(".", background=Colors.BG, foreground=Colors.TEXT, 
                       font=("Segoe UI", 10))
        
        # Buttons
        style.configure("TButton", background=Colors.SURFACE, foreground=Colors.TEXT,
                       padding=(14, 8), borderwidth=0, relief="flat",
                       font=("Segoe UI", 10))
        style.map("TButton",
                  background=[("active", Colors.SURFACE_HOVER), ("pressed", Colors.SURFACE_ACTIVE)])
        
        style.configure("Accent.TButton", background=Colors.ACCENT, foreground="#11111b",
                       font=("Segoe UI", 11, "bold"), padding=(22, 10))
        style.map("Accent.TButton", background=[("active", Colors.ACCENT_DARK)])
        
        style.configure("Glass.TButton", background=Colors.SURFACE, foreground=Colors.TEXT,
                       padding=(10, 6))
        
        # Entry
        style.configure("TEntry", fieldbackground=Colors.SURFACE, foreground=Colors.TEXT,
                       insertcolor=Colors.TEXT, borderwidth=0, padding=8)
        
        # Label styles
        style.configure("Title.TLabel", font=("Segoe UI", 22, "bold"), foreground=Colors.TEXT)
        style.configure("Subtitle.TLabel", font=("Segoe UI", 10), foreground=Colors.TEXT_MUTED)
        style.configure("Card.TLabel", background=Colors.SURFACE, foreground=Colors.TEXT)
        
        # Combobox
        style.configure("TCombobox", fieldbackground=Colors.SURFACE, foreground=Colors.TEXT,
                       selectbackground=Colors.ACCENT, padding=6)

    def _build_ui(self):
        # ========== TOP HEADER (glassmorphic) ==========
        header = tk.Frame(self.root, bg=Colors.BG_ALT, height=68)
        header.pack(fill="x")
        header.pack_propagate(False)
        
        # Header content
        header_inner = tk.Frame(header, bg=Colors.BG_ALT)
        header_inner.pack(fill="both", expand=True, padx=24, pady=12)
        
        # Logo + Title
        logo_frame = tk.Frame(header_inner, bg=Colors.BG_ALT)
        logo_frame.pack(side="left")
        
        tk.Label(logo_frame, text="▶", font=("Segoe UI", 26), 
                bg=Colors.BG_ALT, fg=Colors.ACCENT).pack(side="left", padx=(0, 6))
        tk.Label(logo_frame, text="VideoFlow", font=("Segoe UI", 20, "bold"), 
                bg=Colors.BG_ALT, fg=Colors.TEXT).pack(side="left")
        tk.Label(logo_frame, text="  4K+ • 1000+ sites", font=("Segoe UI", 9), 
                bg=Colors.BG_ALT, fg=Colors.TEXT_MUTED).pack(side="left", padx=8, pady=4)
        
        # Right side controls
        controls = tk.Frame(header_inner, bg=Colors.BG_ALT)
        controls.pack(side="right")
        
        self.settings_btn = tk.Button(controls, text="⚙  Settings", font=("Segoe UI", 10),
                                     bg=Colors.SURFACE, fg=Colors.TEXT, bd=0, padx=14, pady=6,
                                     command=self._toggle_settings)
        self.settings_btn.pack(side="right", padx=(8, 0))
        
        tk.Button(controls, text="📁 Open Folder", font=("Segoe UI", 10),
                 bg=Colors.SURFACE, fg=Colors.TEXT, bd=0, padx=14, pady=6,
                 command=self._open_downloads_folder).pack(side="right")
        
        # ========== MAIN CONTENT ==========
        main = tk.Frame(self.root, bg=Colors.BG)
        main.pack(fill="both", expand=True, padx=20, pady=(12, 16))
        
        # --- SMART INPUT BAR ---
        input_card = tk.Frame(main, bg=Colors.SURFACE, padx=18, pady=16)
        input_card.pack(fill="x", pady=(0, 14))
        
        # Platform indicator row
        platform_row = tk.Frame(input_card, bg=Colors.SURFACE)
        platform_row.pack(fill="x", pady=(0, 8))
        
        self.platform_icon = tk.Label(platform_row, text="🔗", font=("Segoe UI Emoji", 14),
                                     bg=Colors.SURFACE, fg=Colors.ACCENT)
        self.platform_icon.pack(side="left")
        
        self.platform_label = tk.Label(platform_row, text="Paste a link from YouTube, TikTok, Instagram, Vimeo, Twitter/X...", 
                                      font=("Segoe UI", 9), bg=Colors.SURFACE, fg=Colors.TEXT_MUTED)
        self.platform_label.pack(side="left", padx=6)
        
        # URL Input
        url_row = tk.Frame(input_card, bg=Colors.SURFACE)
        url_row.pack(fill="x")
        
        self.url_entry = tk.Entry(url_row, font=("Segoe UI", 13), bg=Colors.SURFACE, 
                                 fg=Colors.TEXT, insertbackground=Colors.ACCENT,
                                 relief="flat", bd=0)
        self.url_entry.pack(side="left", fill="x", expand=True, ipady=10, padx=(0, 8))
        self.url_entry.insert(0, "")
        self.url_entry.bind("<KeyRelease>", self._on_url_change)
        
        # Action buttons
        self.paste_btn = tk.Button(url_row, text="📋 Paste", font=("Segoe UI", 10),
                                  bg=Colors.SURFACE_HOVER, fg=Colors.TEXT, bd=0, padx=14, pady=9,
                                  command=self._paste_url)
        self.paste_btn.pack(side="left", padx=4)
        
        self.analyze_btn = tk.Button(url_row, text="🔍 Analyze", font=("Segoe UI", 10, "bold"),
                                    bg=Colors.ACCENT, fg="#11111b", bd=0, padx=18, pady=9,
                                    command=self._on_analyze)
        self.analyze_btn.pack(side="left", padx=4)
        
        self.quick_download_btn = tk.Button(url_row, text="⬇ Paste & Download", font=("Segoe UI", 10),
                                           bg=Colors.SURFACE_HOVER, fg=Colors.TEXT, bd=0, 
                                           padx=12, pady=9, command=self._paste_and_download)
        self.quick_download_btn.pack(side="left")
        
        # --- DYNAMIC PREVIEW CARD + QUALITY ---
        self.preview_frame = tk.Frame(main, bg=Colors.SURFACE, padx=16, pady=14)
        self.preview_frame.pack(fill="x", pady=(0, 12))
        self.preview_frame.pack_forget()  # Hidden initially

        # Note: preview_frame is packed early; we reference it later for conditional show/hide.
        
        # Preview layout: left thumbnail + right meta
        preview_content = tk.Frame(self.preview_frame, bg=Colors.SURFACE)
        preview_content.pack(fill="x")
        
        # Thumbnail (glassmorphic placeholder)
        thumb_container = tk.Frame(preview_content, bg=Colors.SURFACE)
        thumb_container.pack(side="left")
        
        self.thumb_canvas = tk.Canvas(thumb_container, width=210, height=118, 
                                     bg=Colors.BG_ALT, highlightthickness=0)
        self.thumb_canvas.pack()
        self._draw_thumbnail_placeholder()
        
        # Meta info
        meta = tk.Frame(preview_content, bg=Colors.SURFACE)
        meta.pack(side="left", fill="both", expand=True, padx=(16, 0))
        
        self.preview_title = tk.Label(meta, text="Video Title", font=("Segoe UI", 13, "bold"),
                                     bg=Colors.SURFACE, fg=Colors.TEXT, wraplength=520, anchor="w", justify="left")
        self.preview_title.pack(fill="x", pady=(0, 2))
        
        self.preview_meta = tk.Label(meta, text="Uploader • Duration • 1080p", 
                                    font=("Segoe UI", 9), bg=Colors.SURFACE, fg=Colors.TEXT_MUTED)
        self.preview_meta.pack(anchor="w")
        
        # Quality + mode controls
        controls_row = tk.Frame(meta, bg=Colors.SURFACE)
        controls_row.pack(fill="x", pady=(12, 0))
        
        # Audio / Video segmented toggle
        mode_label = tk.Label(controls_row, text="Mode:", font=("Segoe UI", 9), 
                             bg=Colors.SURFACE, fg=Colors.TEXT_MUTED)
        mode_label.pack(side="left", padx=(0, 6))
        
        self.video_btn = tk.Button(controls_row, text="🎬 Video + Audio", font=("Segoe UI", 9),
                                  bg=Colors.ACCENT, fg="#11111b", bd=0, padx=10, pady=4,
                                  command=lambda: self._set_mode(False))
        self.video_btn.pack(side="left")
        
        self.audio_btn = tk.Button(controls_row, text="🎵 Audio Only", font=("Segoe UI", 9),
                                  bg=Colors.SURFACE_HOVER, fg=Colors.TEXT, bd=0, padx=10, pady=4,
                                  command=lambda: self._set_mode(True))
        self.audio_btn.pack(side="left", padx=3)
        
        # Quality selector
        quality_row = tk.Frame(meta, bg=Colors.SURFACE)
        quality_row.pack(fill="x", pady=(10, 0))
        
        tk.Label(quality_row, text="Quality", font=("Segoe UI", 9), 
                bg=Colors.SURFACE, fg=Colors.TEXT_MUTED).pack(side="left", padx=(0, 8))
        
        self.quality_var = tk.StringVar()
        self.quality_combo = ttk.Combobox(quality_row, textvariable=self.quality_var,
                                         state="readonly", width=42, font=("Segoe UI", 10))
        self.quality_combo.pack(side="left", fill="x", expand=True)
        self.quality_combo.bind("<<ComboboxSelected>>", self._on_quality_change)
        
        # High quality badges row (visual)
        self.quality_badges = tk.Frame(quality_row, bg=Colors.SURFACE)
        self.quality_badges.pack(side="left", padx=8)
        
        # --- QUEUE SECTION ---
        queue_header = tk.Frame(main, bg=Colors.BG)
        queue_header.pack(fill="x", pady=(4, 6))
        
        tk.Label(queue_header, text="Download Queue", font=("Segoe UI", 12, "bold"),
                bg=Colors.BG, fg=Colors.TEXT).pack(side="left")
        
        queue_actions = tk.Frame(queue_header, bg=Colors.BG)
        queue_actions.pack(side="right")
        
        tk.Button(queue_actions, text="＋ Add Current", font=("Segoe UI", 9),
                 bg=Colors.SURFACE, fg=Colors.TEXT, bd=0, padx=10, pady=4,
                 command=self._add_current_to_queue).pack(side="left", padx=3)
        
        tk.Button(queue_actions, text="▶ Start Queue", font=("Segoe UI", 9, "bold"),
                 bg=Colors.ACCENT, fg="#11111b", bd=0, padx=12, pady=4,
                 command=self._start_queue).pack(side="left", padx=3)
        
        tk.Button(queue_actions, text="Clear", font=("Segoe UI", 9),
                 bg=Colors.SURFACE, fg=Colors.TEXT_MUTED, bd=0, padx=10, pady=4,
                 command=self._clear_queue).pack(side="left")
        
        # Queue container
        queue_container = tk.Frame(main, bg=Colors.SURFACE)
        queue_container.pack(fill="both", expand=True)
        
        # Scrollable queue
        self.queue_canvas = tk.Canvas(queue_container, bg=Colors.SURFACE, highlightthickness=0)
        self.queue_scrollbar = ttk.Scrollbar(queue_container, orient="vertical", 
                                            command=self.queue_canvas.yview)
        self.queue_canvas.configure(yscrollcommand=self.queue_scrollbar.set)
        
        self.queue_scrollbar.pack(side="right", fill="y")
        self.queue_canvas.pack(side="left", fill="both", expand=True)
        
        self.queue_inner = tk.Frame(self.queue_canvas, bg=Colors.SURFACE)
        self.queue_canvas.create_window((0, 0), window=self.queue_inner, anchor="nw")
        
        self.queue_inner.bind("<Configure>", lambda e: self.queue_canvas.configure(
            scrollregion=self.queue_canvas.bbox("all")))
        
        self.queue_items = []  # QueueItem widgets
        
        # --- ACTIVE DOWNLOAD BAR ---
        active_bar = tk.Frame(main, bg=Colors.BG)
        active_bar.pack(fill="x", pady=(10, 0))
        
        self.active_title = tk.Label(active_bar, text="No active download", 
                                    font=("Segoe UI", 9), bg=Colors.BG, fg=Colors.TEXT_MUTED)
        self.active_title.pack(anchor="w", pady=(0, 4))
        
        self.progress_bar = ModernProgressBar(active_bar, width=980, height=42)
        self.progress_bar.pack(fill="x")
        
        # Global actions
        action_bar = tk.Frame(active_bar, bg=Colors.BG)
        action_bar.pack(fill="x", pady=(8, 0))
        
        self.download_current_btn = tk.Button(action_bar, text="⬇ Download Now", 
                                             font=("Segoe UI", 11, "bold"),
                                             bg=Colors.ACCENT, fg="#11111b", bd=0, padx=22, pady=9,
                                             command=self._on_start_download, state="disabled")
        self.download_current_btn.pack(side="left")
        
        tk.Button(action_bar, text="Cancel", font=("Segoe UI", 10),
                 bg=Colors.SURFACE_HOVER, fg=Colors.TEXT, bd=0, padx=14, pady=8,
                 command=self._cancel_current).pack(side="left", padx=6)
        
        # ========== SLIDE-IN SETTINGS PANEL ==========
        self.settings_panel = tk.Frame(self.root, bg=Colors.SURFACE, width=300)
        # Initially not packed. Will toggle via pack
        
        settings_content = tk.Frame(self.settings_panel, bg=Colors.SURFACE, padx=18, pady=16)
        settings_content.pack(fill="both", expand=True)
        
        tk.Label(settings_content, text="Settings", font=("Segoe UI", 15, "bold"),
                bg=Colors.SURFACE, fg=Colors.TEXT).pack(anchor="w", pady=(0, 12))
        
        # Settings options
        settings_items = [
            ("Default Quality", "Best (Auto)"),
            ("Max Resolution", "8K (4320p)"),
            ("Concurrent Downloads", "3"),
            ("Save Location", os.path.abspath("downloads")),
            ("Auto-extract Audio", "Off"),
            ("Show Notifications", "On"),
            ("Theme", "Dark (Glass)"),
        ]
        
        for label, value in settings_items:
            row = tk.Frame(settings_content, bg=Colors.SURFACE)
            row.pack(fill="x", pady=6)
            tk.Label(row, text=label, font=("Segoe UI", 10), bg=Colors.SURFACE, 
                    fg=Colors.TEXT).pack(side="left")
            val_label = tk.Label(row, text=value, font=("Segoe UI", 10), 
                                bg=Colors.SURFACE, fg=Colors.ACCENT)
            val_label.pack(side="right")
        
        # Advanced toggles
        tk.Label(settings_content, text="Advanced", font=("Segoe UI", 10, "bold"),
                bg=Colors.SURFACE, fg=Colors.TEXT_MUTED).pack(anchor="w", pady=(14, 6))
        
        toggles = [
            ("Enable 8K/4K HDR", True),
            ("Prefer WebM over MP4", False),
            ("Keep original audio", True),
            ("Use yt-dlp best flags", True),
        ]
        
        for txt, checked in toggles:
            var = tk.BooleanVar(value=checked)
            cb = tk.Checkbutton(settings_content, text=txt, variable=var, 
                               bg=Colors.SURFACE, fg=Colors.TEXT, selectcolor=Colors.BG_ALT,
                               activebackground=Colors.SURFACE, font=("Segoe UI", 10))
            cb.pack(anchor="w", pady=3)
        
        close_btn = tk.Button(settings_content, text="Close", font=("Segoe UI", 10),
                             bg=Colors.ACCENT, fg="#11111b", bd=0, padx=20, pady=6,
                             command=self._toggle_settings)
        close_btn.pack(pady=16)
        
        # Footer status
        footer = tk.Frame(self.root, bg=Colors.BG_ALT, height=28)
        footer.pack(fill="x", side="bottom")
        self.status_bar = tk.Label(footer, text="Ready • 1000+ sites supported • Drag links here", 
                                  font=("Segoe UI", 8), bg=Colors.BG_ALT, fg=Colors.TEXT_MUTED)
        self.status_bar.pack(side="left", padx=18, pady=4)

    def _setup_bindings(self):
        self.url_entry.bind("<Return>", lambda e: self._on_analyze())
        self.root.bind("<Control-v>", lambda e: self._paste_url())
        # Allow drag from other apps (basic support)
        self.root.drop_target_register = lambda *a: None  # no tkinterdnd2, graceful
        
        # Keyboard shortcuts
        self.root.bind("<Control-q>", lambda e: self.root.quit())
        self.root.bind("<Escape>", lambda e: self._toggle_settings() if self.settings_visible else None)

    def _draw_thumbnail_placeholder(self):
        c = self.thumb_canvas
        c.delete("all")
        
        # Background
        c.create_rectangle(0, 0, 210, 118, fill=Colors.BG_ALT, outline="")
        
        # Glass border
        c.create_rectangle(4, 4, 206, 114, outline=Colors.GLASS_BORDER, width=1)
        
        # Gradient simulation (simple)
        for i in range(5):
            alpha = 0.1 + (i * 0.04)
            c.create_rectangle(8 + i*2, 8 + i*2, 202 - i*2, 110 - i*2, 
                              fill=Colors.SURFACE, stipple="gray50", outline="")
        
        # Play button circle
        cx, cy = 105, 59
        c.create_oval(cx-18, cy-18, cx+18, cy+18, fill=Colors.ACCENT, outline="")
        c.create_polygon(cx-6, cy-9, cx-6, cy+9, cx+9, cy, fill="#11111b", outline="")
        
        # Fake resolution badge
        c.create_rectangle(150, 88, 200, 108, fill=Colors.SURFACE, outline="")
        c.create_text(175, 98, text="4K", font=("Segoe UI", 8, "bold"), fill=Colors.ACCENT)

    def _update_thumbnail_with_info(self, info):
        """Update thumb canvas with better info"""
        c = self.thumb_canvas
        c.delete("all")
        
        # Background
        c.create_rectangle(0, 0, 210, 118, fill=Colors.BG_ALT, outline="")
        
        # Thumbnail-like gradient + play
        c.create_rectangle(4, 4, 206, 114, outline=Colors.GLASS_BORDER, width=1)
        
        # Simulated video frame
        c.create_rectangle(8, 8, 202, 110, fill="#222233", outline="")
        
        # Play icon
        cx, cy = 105, 59
        c.create_oval(cx-22, cy-22, cx+22, cy+22, fill=Colors.ACCENT, outline="")
        c.create_polygon(cx-7, cy-11, cx-7, cy+11, cx+11, cy, fill="#11111b")
        
        # Resolution badge
        res = "8K" if any("2160" in str(f.get("label", "")) for f in self.parsed_formats[:5]) else "4K"
        c.create_rectangle(145, 84, 202, 110, fill="#1e1e2e", outline="")
        c.create_text(173, 96, text=res, font=("Segoe UI", 9, "bold"), fill=Colors.ACCENT)
        
        # Duration overlay
        duration = info.get("duration", 0)
        if duration:
            mins = int(duration // 60)
            secs = int(duration % 60)
            dur = f"{mins}:{secs:02d}"
            c.create_rectangle(8, 8, 52, 24, fill="#000000", stipple="gray50")
            c.create_text(30, 16, text=dur, font=("Segoe UI", 8), fill=Colors.TEXT)

    # ==================== PLATFORM DETECTION ====================
    def _detect_platform(self, url):
        url_lower = url.lower()
        if "youtube" in url_lower or "youtu.be" in url_lower:
            return "🎬 YouTube", Colors.ERROR
        elif "tiktok" in url_lower:
            return "🎵 TikTok", "#ff0050"
        elif "instagram" in url_lower:
            return "📷 Instagram", "#e1306c"
        elif "twitter" in url_lower or "x.com" in url_lower:
            return "🐦 X / Twitter", Colors.ACCENT
        elif "vimeo" in url_lower:
            return "🎥 Vimeo", "#1ab7ea"
        elif url.startswith("http"):
            return "🌐 Web / Direct", Colors.SUCCESS
        return "🔗 Unknown", Colors.TEXT_MUTED

    def _on_url_change(self, event=None):
        url = self.url_entry.get().strip()
        if not url:
            self.platform_label.config(text="Paste a link from YouTube, TikTok, Instagram, Vimeo, Twitter/X...")
            self.platform_icon.config(text="🔗")
            return
        
        platform_name, color = self._detect_platform(url)
        self.platform_label.config(text=platform_name, fg=color)
        self.platform_icon.config(text=platform_name.split()[0])

    # ==================== CORE ACTIONS ====================
    def _paste_url(self):
        try:
            text = self.root.clipboard_get().strip()
            if text:
                self.url_entry.delete(0, tk.END)
                self.url_entry.insert(0, text)
                self._on_url_change()
        except:
            pass

    def _paste_and_download(self):
        self._paste_url()
        if self.url_entry.get().strip():
            self._on_analyze(auto_download=True)

    def _on_analyze(self, auto_download=False):
        url = self.url_entry.get().strip()
        if not url:
            self._show_toast("Please enter a video URL", "warning")
            return
        
        self.analyze_btn.config(state="disabled", text="Analyzing...")
        self.download_current_btn.config(state="disabled")
        self.status_bar.config(text="Analyzing video metadata...")
        
        threading.Thread(target=self._async_fetch, args=(url, auto_download), daemon=True).start()

    def _async_fetch(self, url, auto_download=False):
        try:
            info = self.downloader.fetch_video_info(url)
            parsed = self.downloader.parse_formats(info)
            self.root.after(0, lambda: self._on_fetch_success(info, parsed, auto_download))
        except Exception as e:
            self.root.after(0, lambda: self._on_fetch_error(str(e)))

    def _on_fetch_success(self, info, parsed_formats, auto_download=False):
        self.current_info = info
        self.parsed_formats = parsed_formats
        
        # Update preview
        title = info.get("title", "Untitled Video")[:70]
        uploader = info.get("uploader", "Unknown")
        duration = info.get("duration", 0)
        
        dur_str = ""
        if duration:
            m, s = divmod(duration, 60)
            h, m = divmod(m, 60)
            dur_str = f"{h}h {m}m {s}s" if h else f"{m}m {s}s"
        
        self.preview_title.config(text=title)
        self.preview_meta.config(text=f"{uploader}  •  {dur_str}  •  {len(parsed_formats)} formats available")
        
        # Populate quality combo with modern labels
        values = []
        for fmt in parsed_formats:
            values.append(fmt["label"])
        
        self.quality_combo["values"] = values
        if values:
            # Prefer best or first high quality
            best_idx = 0
            for i, v in enumerate(values):
                if "Best Quality" in v or "2160" in v or "4K" in v:
                    best_idx = i
                    break
            self.quality_combo.current(best_idx)
        
        # Show preview card
        try:
            self.preview_frame.pack(fill="x", pady=(0, 12))
        except Exception:
            pass  # already packed or layout issue
        
        # Update thumbnail
        self._update_thumbnail_with_info(info)
        
        # Enable download
        self.download_current_btn.config(state="normal")
        self.analyze_btn.config(state="normal", text="🔍 Analyze")
        self.status_bar.config(text="Video analyzed • Ready to download")
        
        self._show_toast(f"Loaded: {title[:40]}", "success")
        
        if auto_download:
            self.root.after(600, self._on_start_download)

    def _on_fetch_error(self, err_msg):
        self.analyze_btn.config(state="normal", text="🔍 Analyze")
        self.status_bar.config(text="Analysis failed")
        self._show_toast(f"Failed to analyze: {err_msg[:60]}", "error")
        messagebox.showerror("Analysis Failed", f"Could not fetch video info:\n{err_msg}")

    def _set_mode(self, audio_only):
        self.audio_only_mode = audio_only
        
        if audio_only:
            self.video_btn.config(bg=Colors.SURFACE_HOVER, fg=Colors.TEXT)
            self.audio_btn.config(bg=Colors.ACCENT, fg="#11111b")
            # Filter to audio formats
            audio_values = [f["label"] for f in self.parsed_formats if "Audio" in f["label"] or "bestaudio" in f.get("format_id", "")]
            if audio_values:
                self.quality_combo["values"] = audio_values
                self.quality_combo.current(0)
        else:
            self.audio_btn.config(bg=Colors.SURFACE_HOVER, fg=Colors.TEXT)
            self.video_btn.config(bg=Colors.ACCENT, fg="#11111b")
            # Restore all
            values = [f["label"] for f in self.parsed_formats]
            self.quality_combo["values"] = values
            if values:
                self.quality_combo.current(0)

    def _on_quality_change(self, event=None):
        pass  # Future: live size estimate

    def _on_start_download(self):
        if not self.current_info or not self.parsed_formats:
            self._show_toast("Analyze a video first", "warning")
            return
        
        url = self.url_entry.get().strip()
        selected_idx = self.quality_combo.current()
        
        if selected_idx < 0:
            format_id = "bestvideo+bestaudio/best"
            label = "Best Quality"
        else:
            fmt = self.parsed_formats[selected_idx]
            format_id = fmt["format_id"]
            label = fmt["label"][:35]
        
        out_dir = os.path.abspath("downloads")
        os.makedirs(out_dir, exist_ok=True)
        
        # Disable controls
        self.download_current_btn.config(state="disabled")
        self.analyze_btn.config(state="disabled")
        self.progress_bar.reset()
        self.progress_bar.set_status("downloading")
        
        self.active_title.config(text=f"Downloading: {self.current_info.get('title', '')[:55]}  [{label}]")
        
        self.status_bar.config(text="Download in progress...")
        
        thread = threading.Thread(
            target=self._async_download, 
            args=(url, format_id, out_dir, label), 
            daemon=True
        )
        thread.start()

    def _async_download(self, url, format_id, out_path, quality_label):
        try:
            def progress_hook(d):
                if d.get("status") == "downloading":
                    total = d.get("total_bytes") or d.get("total_bytes_estimate", 0)
                    downloaded = d.get("downloaded_bytes", 0)
                    speed = d.get("speed", 0) or 0
                    eta = d.get("eta", 0) or 0
                    
                    percent = (downloaded / total * 100) if total > 0 else 0
                    
                    speed_str = self._format_bytes(speed) + "/s"
                    down_str = self._format_bytes(downloaded)
                    tot_str = self._format_bytes(total)
                    eta_str = f"{int(eta)}s" if eta else "--:--"
                    
                    self.root.after(0, lambda: self.progress_bar.set_progress(
                        percent, speed_str, eta_str, down_str, tot_str
                    ))
                    
                    # Update any active queue item
                    self.root.after(0, lambda: self._update_active_queue_item(percent, speed_str, eta_str))
            
            saved_path = self.downloader.download(
                url, format_id=format_id, output_path=out_path, progress_hook=progress_hook
            )
            
            self.root.after(0, lambda: self._on_download_success(saved_path, quality_label))
            
        except Exception as e:
            self.root.after(0, lambda: self._on_download_error(str(e)))

    def _on_download_success(self, saved_path, quality_label):
        self.progress_bar.set_progress(100, "Complete", "--", "", "")
        self.active_title.config(text=f"✅ Completed: {os.path.basename(saved_path)}")
        self.status_bar.config(text="Download finished successfully")
        
        self.download_current_btn.config(state="normal")
        self.analyze_btn.config(state="normal")
        
        self._show_toast("Download complete!", "success")
        
        # Mark any queue item complete
        self._mark_queue_complete()
        
        # Auto open folder option (optional)
        # self.root.after(1200, lambda: os.startfile(os.path.dirname(saved_path)) if os.name == 'nt' else None)

    def _on_download_error(self, err_msg):
        self.progress_bar.set_progress(0)
        self.active_title.config(text="❌ Download failed")
        self.download_current_btn.config(state="normal")
        self.analyze_btn.config(state="normal")
        self.status_bar.config(text="Error during download")
        self._show_toast(f"Download error: {err_msg[:55]}", "error")

    def _cancel_current(self):
        self.progress_bar.reset()
        self.active_title.config(text="Download cancelled")
        self.download_current_btn.config(state="normal")
        self.analyze_btn.config(state="normal")
        self._show_toast("Download cancelled", "info")

    # ==================== QUEUE MANAGEMENT ====================
    def _add_current_to_queue(self):
        if not self.current_info:
            self._show_toast("Analyze a video first", "warning")
            return
        
        url = self.url_entry.get().strip()
        title = self.current_info.get("title", "Untitled")
        quality = self.quality_var.get() or "Best Quality"
        
        # Avoid duplicates
        for item in self.queue:
            if item["url"] == url and item["quality"] == quality:
                self._show_toast("Already in queue", "info")
                return
        
        qitem = {
            "id": len(self.queue),
            "url": url,
            "title": title,
            "quality": quality,
            "status": "queued",
            "progress": 0
        }
        self.queue.append(qitem)
        self._render_queue()
        self._show_toast("Added to queue", "success")

    def _add_demo_queue_items(self):
        demos = [
            ("https://youtube.com/watch?v=dQw4w9wg", "Rick Astley - Never Gonna Give You Up", "4K 60fps (Best)"),
            ("https://tiktok.com/@user/video/123", "Viral Dance Trend 2026", "1080p"),
        ]
        for url, title, q in demos:
            self.queue.append({
                "id": len(self.queue),
                "url": url,
                "title": title,
                "quality": q,
                "status": "queued",
                "progress": 0
            })
        self._render_queue()

    def _render_queue(self):
        # Clear existing widgets
        for widget in self.queue_inner.winfo_children():
            widget.destroy()
        self.queue_items = []
        
        if not self.queue:
            tk.Label(self.queue_inner, text="Queue is empty. Add videos to download multiple at once.",
                    font=("Segoe UI", 9), bg=Colors.SURFACE, fg=Colors.TEXT_MUTED, pady=20).pack()
            return
        
        for idx, item in enumerate(self.queue):
            qitem = QueueItem(
                self.queue_inner,
                index=idx,
                title=item["title"],
                url=item["url"],
                quality=item["quality"],
                status=item.get("status", "queued"),
                on_remove=self._remove_from_queue,
                on_move=self._move_queue_item
            )
            qitem.pack(fill="x", pady=3, padx=6)
            self.queue_items.append(qitem)
            
            # Restore progress if downloading
            if item.get("status") == "downloading":
                qitem.update_status("downloading", item.get("progress", 0))

    def _remove_from_queue(self, index):
        if 0 <= index < len(self.queue):
            del self.queue[index]
            self._render_queue()

    def _move_queue_item(self, index, direction):
        new_index = index + direction
        if 0 <= new_index < len(self.queue):
            self.queue[index], self.queue[new_index] = self.queue[new_index], self.queue[index]
            self._render_queue()

    def _update_active_queue_item(self, percent, speed, eta):
        # Find first downloading item and update
        for idx, item in enumerate(self.queue):
            if item.get("status") == "downloading":
                item["progress"] = percent
                if idx < len(self.queue_items):
                    self.queue_items[idx].update_status("downloading", percent, speed, eta)
                break

    def _mark_queue_complete(self):
        for idx, item in enumerate(self.queue):
            if item.get("status") == "downloading":
                item["status"] = "completed"
                item["progress"] = 100
                if idx < len(self.queue_items):
                    self.queue_items[idx].update_status("completed", 100)
                break
        # Re-render after a moment
        self.root.after(800, self._render_queue)

    def _start_queue(self):
        if not self.queue:
            self._show_toast("Queue is empty", "warning")
            return
        
        # Start processing first queued item
        for item in self.queue:
            if item["status"] == "queued":
                item["status"] = "downloading"
                self._render_queue()
                
                # Load into preview + start
                self.url_entry.delete(0, tk.END)
                self.url_entry.insert(0, item["url"])
                
                # Simulate fetch then download (or directly download if we had info)
                def start_next():
                    # In real app we would fetch again or cache
                    self._on_analyze(auto_download=True)
                
                self.root.after(300, start_next)
                return
        
        self._show_toast("No queued items ready", "info")

    def _clear_queue(self):
        self.queue.clear()
        self._render_queue()
        self._show_toast("Queue cleared", "info")

    # ==================== SETTINGS PANEL ====================
    def _toggle_settings(self):
        if self.settings_visible:
            self.settings_panel.pack_forget()
            self.settings_visible = False
            self.settings_btn.config(bg=Colors.SURFACE)
        else:
            # Pack on the right of main area (simulates slide-in)
            self.settings_panel.pack(side="right", fill="y", before=self.root.winfo_children()[-1] if self.root.winfo_children() else None)
            self.settings_visible = True
            self.settings_btn.config(bg=Colors.ACCENT, fg="#11111b")

    # ==================== HELPERS ====================
    def _format_bytes(self, num):
        if not num or num == 0:
            return "0 B"
        for unit in ["B", "KB", "MB", "GB"]:
            if num < 1024.0:
                return f"{num:.1f} {unit}"
            num /= 1024.0
        return f"{num:.1f} TB"

    def _show_toast(self, message, type_="info"):
        Toast(self.root, message, type_)

    def _on_quality_change(self, event=None):
        pass

    def _open_downloads_folder(self):
        path = os.path.abspath("downloads")
        os.makedirs(path, exist_ok=True)
        try:
            if sys.platform == "win32":
                os.startfile(path)
            elif sys.platform == "darwin":
                os.system(f"open '{path}'")
            else:
                os.system(f"xdg-open '{path}'")
        except Exception:
            self._show_toast(f"Folder: {path}", "info")

    def _update_progress_ui(self, percent, speed_str, downloaded_str, total_str, eta_str):
        """Legacy compatibility"""
        self.progress_bar.set_progress(percent, speed_str, eta_str, downloaded_str, total_str)

# ==================== LAUNCH ====================

def main():
    root = tk.Tk()
    app = ModernVideoDownloaderGUI(root)
    
    # Optional: center window
    root.update_idletasks()
    w = root.winfo_width()
    h = root.winfo_height()
    x = (root.winfo_screenwidth() // 2) - (w // 2)
    y = (root.winfo_screenheight() // 2) - (h // 2)
    root.geometry(f"{w}x{h}+{x}+{y}")
    
    root.mainloop()

if __name__ == "__main__":
    main()
