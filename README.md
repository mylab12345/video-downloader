# VideoFlow — Modern Video Downloader

A beautiful, modern desktop video downloader with **glassmorphism + minimalist** design inspired by 4K Video Downloader, JDownloader 2, and modern web apps.

Supports **4K, 8K, HDR, 1080p** + audio-only from **YouTube, TikTok, Instagram, Twitter/X, Vimeo, 1000+ sites** via yt-dlp.

**✨ Optimized for fast downloads** with concurrent fragment downloading and aria2c integration.

---

## 🚀 Installation on Linux Mint

### Option 1: Install from .deb Package (Recommended)

A `.deb` package is included in this repository for easy installation:

```bash
# Navigate to the directory containing the .deb file
cd /path/to/video-downloader

# Install the package
sudo dpkg -i video-downloader_1.0.0_all.deb

# If there are dependency issues, fix them with:
sudo apt-get install -f -y
```

This will automatically:
- Install all system dependencies (python3, ffmpeg, aria2, etc.)
- Create a virtual environment with Python packages (yt-dlp, requests, pillow)
- Add a menu entry for the GUI application (find it in Applications > Audio & Video)
- Install command-line tools (`video-downloader` and `video-downloader-cli`)

**After installation:**
- **GUI**: Run `video-downloader` from terminal or click the icon in the application menu
- **CLI**: Run `video-downloader-cli <URL>` from terminal

---

### Option 2: Manual Installation

If you prefer to install manually without the .deb package:

#### Step 1: Install System Dependencies

Open a terminal and run:

```bash
# Update package list
sudo apt update

# Install Python 3, pip, tkinter (for GUI), git, ffmpeg, and aria2c (for faster downloads)
sudo apt install -y python3 python3-pip python3-tk git ffmpeg aria2
```

#### Step 2: Clone or Download the Project

If you have the project as a zip file, extract it. Or clone from git:

```bash
cd ~
git clone <repository-url> video-downloader
cd video-downloader
```

#### Step 3: Create Virtual Environment (Recommended)

```bash
# Create virtual environment
python3 -m venv venv

# Activate it
source venv/bin/activate
```

#### Step 4: Install Python Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

---

## 📋 Quick Start

### Launch the GUI

**If installed via .deb package:**
```bash
video-downloader
```
Or find "Video Downloader" in your application menu (Applications > Audio & Video).

**If manually installed:**
```bash
# Make sure you're in the project directory and venv is activated
python main.py
```

Or directly:
```bash
python gui.py
```

### Use the CLI

**If installed via .deb package:**
```bash
# Basic download (best quality)
video-downloader-cli https://youtube.com/watch?v=VIDEO_ID

# List available formats
video-downloader-cli -l https://youtube.com/watch?v=VIDEO_ID

# Download specific quality (e.g., 1080p)
video-downloader-cli -f 1080p https://youtube.com/watch?v=VIDEO_ID

# Download audio only
video-downloader-cli -a https://youtube.com/watch?v=VIDEO_ID

# Download to specific folder
video-downloader-cli -o ~/Videos https://youtube.com/watch?v=VIDEO_ID
```

**If manually installed:**
```bash
# Basic download (best quality)
python cli.py https://youtube.com/watch?v=VIDEO_ID

# List available formats
python cli.py -l https://youtube.com/watch?v=VIDEO_ID

# Download specific quality (e.g., 1080p)
python cli.py -f 1080p https://youtube.com/watch?v=VIDEO_ID

# Download audio only
python cli.py -a https://youtube.com/watch?v=VIDEO_ID

# Download to specific folder
python cli.py -o ~/Videos https://youtube.com/watch?v=VIDEO_ID
```

---

## ⚡ Maximizing Download Speed

The downloader is optimized for speed with these built-in features:

- **Concurrent fragment downloads** (4 parallel connections by default)
- **aria2c integration** for maximum throughput (auto-detected)
- Smart retry logic with exponential backoff
- Optimized HTTP chunk sizes (10MB) for better network utilization

### Additional Tips:

1. **Ensure aria2c is installed** (already included in Step 1 above)
2. **Use wired Ethernet** for more stable high-speed downloads
3. **Close bandwidth-heavy apps** during large downloads

### Advanced: Increase Concurrent Connections

For very fast internet connections, edit `downloader.py`:

```python
'concurrent_fragment_downloads': 8,  # Increase from 4 to 8 or 16
'http_chunk_size': 20971520,  # 20MB chunks (from 10MB)
```

And aria2c args:

```python
'--max-connection-per-server=8',  # Increase from 4
'--split=8',  # Increase from 4
```

⚠️ **Note**: Too many connections may trigger rate limiting on some sites like YouTube.

---

## 🛠️ Troubleshooting on Linux Mint

### Issue: `tkinter` not found
```bash
sudo apt install python3-tk
```

### Issue: `ffmpeg` not found (needed for merging video+audio)
```bash
sudo apt install ffmpeg
```

### Issue: Permission errors when installing packages
Use a virtual environment or:
```bash
pip install --user -r requirements.txt
```

### Issue: No DISPLAY / GUI won't start
This happens in SSH or headless environments. Use CLI mode:
```bash
python cli.py <URL>
```

---

## Architecture

```
video-downloader/
├── gui.py              # Modern glassmorphic UI
├── downloader.py       # Core yt-dlp logic with speed optimizations
├── cli.py              # Command-line interface
├── main.py             # Smart launcher (GUI or CLI)
├── requirements.txt    # Python dependencies
└── README.md           # This file
```

---

## 🎯 Supported Sites

Via yt-dlp, this tool supports **1000+ websites** including:

- YouTube (4K, 8K, HDR, 60fps)
- TikTok
- Instagram (Reels, Stories, Posts)
- Twitter / X
- Vimeo
- Facebook
- Twitch clips
- Dailymotion
- And many more!

Full list: https://github.com/yt-dlp/yt-dlp/blob/master/supportedsites.md

---

## Features

### Visual Aesthetic
- **Glassmorphism** design with frosted glass cards
- **Catppuccin Mocha** inspired dark palette
- Clean rounded corners and elegant typography

### Core Functionality
- Smart URL input with platform detection
- Dynamic preview card with metadata
- Quality selection (8K, 4K, 1080p, etc.)
- Audio/Video mode toggle
- Download queue management
- Real-time progress with speed & ETA
- Toast notifications

---

**Built with ❤️ for Linux Mint and other Linux distributions.**

Run `python gui.py` and enjoy the modern experience!
