# VideoFlow — Modern Video Downloader

A beautiful, modern desktop video downloader with **glassmorphism + minimalist** design inspired by 4K Video Downloader, JDownloader 2, and modern web apps.

Supports **4K, 8K, HDR, 1080p** + audio-only from **YouTube, TikTok, Instagram, Twitter/X, Vimeo, 1000+ sites** via yt-dlp.

![Modern UI](https://via.placeholder.com/900x520/181825/89b4fa?text=VideoFlow+Modern+Glassmorphism+UI)

---

## ✨ What's New (Modern UI Upgrade)

### Visual Aesthetic
- **Glassmorphism** design: frosted glass cards, subtle borders, layered depth
- **Catppuccin Mocha** inspired dark palette
- Clean rounded corners, soft shadows, and elegant typography (Segoe UI)
- Modern iconography (emoji + symbols) instead of plain text

### Core Layout
- **Smart Input Bar** — prominent URL field + real-time platform detection (YouTube → 🎬, TikTok → 🎵, etc.)
- **Dynamic Preview Card** — thumbnail preview (play icon), title, uploader, duration + rich quality selector
- **High Quality Options** — Best (auto), 8K, 4K HDR, 1440p, 1080p, etc.
- **Audio / Video Segmented Toggle** — instant mode switching

### Queue Management
- Beautiful drag-reorderable queue list
- Per-item mini progress bars + status badges
- "Add Current", "Start Queue", drag ordering, clear

### Interactive Feedback
- **Custom Canvas Progress Bar** — animated glass progress + live **Speed • ETA • Downloaded / Total**
- Smooth state transitions (idle → analyzing → downloading → completed)
- **Toast notifications** (non-blocking, bottom-right)
- Hover micro-interactions on all buttons and cards

### UX Enhancements
- **One-click "Paste & Download"**
- **Slide-in Settings panel** (from right)
- Keyboard shortcuts (`Ctrl+V`, `Enter`, `Esc`)
- Auto folder opening

---

## 🚀 Quick Start

```bash
# Install dependencies
pip install yt-dlp pillow requests

# Run the modern GUI
python gui.py
```

> **Note**: On Linux you may need `sudo apt install python3-tk` (or equivalent).

---

## Architecture

```
video-downloader/
├── gui.py             # ✨ Completely redesigned modern UI (this is the focus)
├── downloader.py      # Core yt-dlp logic (unchanged)
├── cli.py             # Classic CLI (still available)
├── main.py            # Launcher
└── README.md
```

---

## 📸 UI Highlights (Wireframe Logic)

```
┌──────────────────────────────────────────────────────────────┐
│  ▶ VideoFlow                 4K+ • 1000+ sites     ⚙ Settings  📁  │
├──────────────────────────────────────────────────────────────┤
│  [🔗] Paste a link from YouTube...                             │
│  ┌────────────────────────────────────────────────────┐       │
│  │ https://youtube.com/...                    [Paste] │       │
│  │                                     [Analyze] [⬇ Paste & Download] │
│  └────────────────────────────────────────────────────┘       │
├──────────────────────────────────────────────────────────────┤
│  ┌──────────────────────────────┬──────────────────────────┐ │
│  │  [▶]  Thumbnail              │ Title: ...               │ │
│  │      (glass + play icon)     │ Uploader • 3m 42s        │ │
│  │                              │                          │ │
│  │                              │ [🎬 Video+Audio] [🎵 Audio] │ │
│  │                              │ Quality:  [4K 60fps ... ▼] │ │
│  └──────────────────────────────┴──────────────────────────┘ │
├──────────────────────────────────────────────────────────────┤
│  Download Queue                              [+ Add] [▶ Start Queue] [Clear] │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │ [Rick Astley - ...] [4K 60fps]  queued   ↑ ↓ ✕           │ │
│  │ [Viral Dance...]      [1080p]   queued   ↑ ↓ ✕           │ │
│  └──────────────────────────────────────────────────────────┘ │
├──────────────────────────────────────────────────────────────┤
│  No active download                                            │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │ ████████████████░░░░░░░░░░░░  67%   12.4 MB/s • ETA 18s   │ │
│  │                     142 MB / 211 MB                       │ │
│  └──────────────────────────────────────────────────────────┘ │
│  [⬇ Download Now]  [Cancel]                                    │
└──────────────────────────────────────────────────────────────┘
```

---

## 🛠️ Key Code Components

### 1. Modern Glassmorphic Progress Bar (`ModernProgressBar`)

See full implementation in `gui.py`:

```python
class ModernProgressBar(tk.Canvas):
    def _draw(self):
        # Outer glass frame
        self._draw_rounded_rect(...)
        # Inner track + progress fill
        # Gloss highlight layer
        # Live overlay text: percent + speed + ETA
```

### 2. Smart Input + Platform Detection

```python
def _detect_platform(self, url):
    if "youtube" in url: return "🎬 YouTube", ...
    ...
```

### 3. Dynamic Preview Card

Rendered with a canvas-based glass thumbnail + rich metadata.

### 4. Queue with Drag-Reorder (simple)

Uses `QueueItem` widgets + list reordering.

### 5. Toast Notifications

```python
class Toast(tk.Toplevel):
    # Auto-positioned, auto-dismiss, colored accent bar
```

### 6. Slide-in Settings

```python
def _toggle_settings(self):
    if not visible:
        self.settings_panel.pack(side="right", fill="y")
```

---

## 🎨 Styling Tips (Glassmorphism + Neumorphism)

### CSS / Tkinter equivalents

**Glassmorphism** (applied via colors + layered frames):
```css
/* Equivalent for web port */
.card {
  background: rgba(49, 50, 68, 0.85);
  border: 1px solid rgba(69, 71, 90, 0.6);
  backdrop-filter: blur(20px);
  border-radius: 16px;
  box-shadow: 0 8px 32px rgba(0,0,0,0.4);
}
```

**Tkinter implementation** (used in this app):
- Rounded rectangles via `create_rectangle` + `create_arc`
- Layered `SURFACE` colors with subtle borders (`#45475a`)
- Gloss overlay using `stipple="gray50"` + white rectangle
- Hover states via `.bind("<Enter>")` + color swap

**Color Palette** (Catppuccin Mocha):
- `#181825` — Deep background
- `#313244` — Glass surface
- `#89b4fa` — Accent (blue)
- `#a6e3a1` — Success

**Micro-interactions**:
- Buttons use `style.map` for `active` / `pressed`
- `QueueItem` hover changes background
- Progress bar redraws on every update (smooth)

**Typography**:
- Primary: `Segoe UI` (or `Helvetica` fallback)
- Weight hierarchy: 9pt muted, 10–11pt normal, 13pt bold titles

---

## Future Enhancements (Easy to Add)

- Real thumbnail download using Pillow + yt-dlp thumbnail extraction
- Drag & drop support (`tkinterdnd2`)
- Dark/Light toggle
- Download history + completed tab
- Speed graph in progress bar
- Web version (React + Tailwind + shadcn/ui glass components)

---

## Legacy Support

The original `gui.py` behavior is preserved in spirit. You can still run the classic version by reverting or using `cli.py`.

---

**Built with ❤️ as a Senior UI/UX + Frontend exercise on top of the existing yt-dlp core.**

Run `python gui.py` and enjoy the modern experience!
