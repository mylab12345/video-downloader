# All-in-One Universal Video Downloader 📹🚀

A powerful, universal video downloader built in Python supporting all qualities (**8K, 4K, 1080p, 720p, 480p, and Audio MP3/M4A**) from **YouTube, TikTok, Vimeo, Twitter/X, Instagram, Direct Video URLs, M3U8 streams, and 1000+ websites**.

Offers **both Command Line Interface (CLI)** and a modern **Desktop Graphical User Interface (GUI)**.

---

## Features

- 🌟 **All Qualities Supported**: Automatically extracts and lets you select any available resolution (8K, 4K, 1080p, 720p, 480p, 360p, or Audio Only).
- 🌐 **Universal Platform Support**: Works with YouTube, TikTok, Instagram, Twitter/X, Facebook, Vimeo, Reddit, Twitch clips, direct `.mp4` URLs, M3U8 HLS streams, and over 1,000 supported sites via `yt-dlp`.
- 🖥️ **Desktop GUI**: Sleek modern Tkinter application with real-time download progress bar, speed tracker, ETA display, and output directory selector.
- 💻 **CLI Mode**: Interactive or scriptable command-line interface with custom quality selection.
- ⚡ **Multi-Threaded**: Responsive UI during video fetching and downloading.
- 🎵 **Audio Extraction**: Option to download high quality audio only (MP3/M4A).

---

## Installation

1. **Clone or Navigate to Project Directory**:
   ```bash
   cd My-Video-Downloader
   ```

2. **Install Python Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Install Tkinter for Graphical GUI (Linux users)**:
   *Tkinter is required for the Desktop GUI and must be installed via apt (not pip):*
   ```bash
   sudo apt update && sudo apt install -y python3-tk
   ```

4. *(Optional but Recommended for 4K/8K merging)* **Install FFmpeg**:
   - **Linux (Ubuntu/Debian)**: `sudo apt install ffmpeg`
   - **MacOS**: `brew install ffmpeg`
   - **Windows**: Download from [FFmpeg official website](https://ffmpeg.org/download.html) and add to system PATH.


---

## Usage

### 🚀 Desktop GUI Mode
Launch the graphical interface by simply running:
```bash
python main.py
```
or directly:
```bash
python gui.py
```

**GUI Steps**:
1. Paste or enter your video URL.
2. Click **🔍 Fetch Qualities** to load metadata and available format options.
3. Select your desired resolution/quality from the dropdown.
4. (Optional) Choose a custom folder to save the video.
5. Click **⬇ Start Download**.

---

### 💻 Command Line Interface (CLI) Mode

#### 1. Interactive CLI:
```bash
python main.py "https://www.youtube.com/watch?v=EXAMPLE"
```
*(Displays video details and interactive numbered list of qualities to choose from)*

#### 2. List Available Qualities without Downloading:
```bash
python cli.py "https://www.youtube.com/watch?v=EXAMPLE" --list-formats
```

#### 3. Direct Download with Specific Quality or Output Directory:
```bash
# Download best quality into custom folder
python cli.py "https://www.youtube.com/watch?v=EXAMPLE" -o ./my_videos

# Download specific resolution (e.g. 1080p)
python cli.py "https://www.youtube.com/watch?v=EXAMPLE" -f 1080p

# Download audio only (MP3/M4A)
python cli.py "https://www.youtube.com/watch?v=EXAMPLE" --audio-only
```

---

## Project Architecture

```
My-Video-Downloader/
├── downloader.py    # Core yt-dlp wrapper and format parser
├── cli.py           # Command line interface with live progress bar
├── gui.py           # Tkinter desktop application
├── main.py          # Dual entry launcher (runs GUI or CLI)
├── requirements.txt # Project dependencies
└── README.md        # Documentation
```

---

## License
MIT License
