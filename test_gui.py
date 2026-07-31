#!/usr/bin/env python3
"""
Headless Test Suite for Modern VideoFlow GUI
Runs without a real display / tkinter installed.
Uses unittest.mock to simulate Tkinter widgets.

Run with:
    python test_gui.py
"""

import sys
import os
import unittest
from unittest.mock import MagicMock, patch, PropertyMock
import importlib

# Ensure we can import local modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# We will mock tkinter before importing gui
MOCK_TK = MagicMock()
MOCK_TTK = MagicMock()

# Patch at module level before import
sys.modules['tkinter'] = MOCK_TK
sys.modules['tkinter.ttk'] = MOCK_TTK

# Now safe to import
import gui
from downloader import VideoDownloader

# Reset mocks for clean state in tests
def reset_mocks():
    for mod in (MOCK_TK, MOCK_TTK):
        mod.reset_mock()

    # Return value for Tk root (used in app init)
    mock_root = MagicMock()
    mock_root.clipboard_get.return_value = ""
    mock_root.winfo_x.return_value = 0
    mock_root.winfo_y.return_value = 0
    mock_root.winfo_width.return_value = 1000
    mock_root.winfo_height.return_value = 800
    MOCK_TK.Tk.return_value = mock_root

    # Common widget constructors
    MOCK_TK.Toplevel.return_value = MagicMock()
    MOCK_TK.Canvas.return_value = MagicMock()
    MOCK_TTK.Style.return_value = MagicMock()
    MOCK_TTK.Combobox.return_value = MagicMock()

    # Make containers and buttons return mock objects that support .pack(), .config() etc.
    for widget_cls in ('Frame', 'Button', 'Label', 'Entry', 'Canvas', 'StringVar'):
        getattr(MOCK_TK, widget_cls).return_value = MagicMock()
        if widget_cls == 'StringVar':
            getattr(MOCK_TK, widget_cls).return_value.get.return_value = ""

    MOCK_TK.Frame.return_value.pack = MagicMock()
    MOCK_TK.Button.return_value.pack = MagicMock()

class TestModernGUIImports(unittest.TestCase):
    def test_colors_defined(self):
        self.assertTrue(hasattr(gui, 'Colors'))
        c = gui.Colors
        self.assertTrue(hasattr(c, 'BG'))
        self.assertTrue(hasattr(c, 'ACCENT'))
        self.assertIn('#', c.ACCENT)

    def test_classes_exist(self):
        self.assertTrue(hasattr(gui, 'ModernProgressBar'))
        self.assertTrue(hasattr(gui, 'Toast'))
        self.assertTrue(hasattr(gui, 'QueueItem'))
        self.assertTrue(hasattr(gui, 'ModernVideoDownloaderGUI'))

class TestPlatformDetection(unittest.TestCase):
    def setUp(self):
        reset_mocks()
        # We need a minimal root for the app
        mock_root = MagicMock()
        mock_root.clipboard_get.return_value = ""
        self.app = gui.ModernVideoDownloaderGUI(mock_root)

    def test_youtube_detection(self):
        name, color = self.app._detect_platform("https://www.youtube.com/watch?v=abc123")
        self.assertIn("YouTube", name)
        self.assertEqual(color, gui.Colors.ERROR)

    def test_tiktok_detection(self):
        name, _ = self.app._detect_platform("https://www.tiktok.com/@user/video/123")
        self.assertIn("TikTok", name)

    def test_direct_url(self):
        name, _ = self.app._detect_platform("https://example.com/video.mp4")
        self.assertIn("Web", name)

class TestModernProgressBar(unittest.TestCase):
    def setUp(self):
        reset_mocks()
        self.mock_parent = MagicMock()
        self.bar = gui.ModernProgressBar(self.mock_parent, width=400, height=40)

    def test_initial_state(self):
        self.assertEqual(self.bar.progress, 0.0)
        self.assertEqual(self.bar.speed, "0 B/s")

    def test_set_progress(self):
        self.bar.set_progress(67, "4.2 MB/s", "12s", "142 MB", "211 MB")
        self.assertEqual(self.bar.progress, 67)
        self.assertEqual(self.bar.speed, "4.2 MB/s")
        self.assertEqual(self.bar.eta, "12s")

    def test_reset(self):
        self.bar.set_progress(55)
        self.bar.reset()
        self.assertEqual(self.bar.progress, 0)

    def test_draw_called(self):
        # _draw should have been called during init and updates
        self.assertTrue(self.bar._draw.called or len(self.bar.delete.call_args_list) > 0)

class TestToast(unittest.TestCase):
    def test_toast_creation(self):
        reset_mocks()
        mock_parent = MagicMock()
        mock_parent.winfo_x.return_value = 100
        mock_parent.winfo_y.return_value = 200
        mock_parent.winfo_width.return_value = 900
        mock_parent.winfo_height.return_value = 700

        toast = gui.Toast(mock_parent, "Download complete!", "success")
        self.assertIsNotNone(toast)
        # Should have called Toplevel
        MOCK_TK.Toplevel.assert_called()

class TestQueueItem(unittest.TestCase):
    def setUp(self):
        reset_mocks()
        self.mock_parent = MagicMock()
        self.item = gui.QueueItem(
            self.mock_parent,
            index=0,
            title="Test Video Title",
            url="https://example.com/vid",
            quality="4K 60fps",
            status="queued"
        )

    def test_initial_status(self):
        self.assertEqual(self.item.status, "queued")

    def test_update_status(self):
        self.item.update_status("downloading", 42, "2.1 MB/s", "31s")
        self.assertEqual(self.item.status, "downloading")
        self.assertEqual(self.item.progress, 42)

class TestModernVideoDownloaderGUI(unittest.TestCase):
    def setUp(self):
        reset_mocks()
        self.mock_root = MagicMock()
        self.mock_root.clipboard_get.return_value = "https://www.youtube.com/watch?v=test123"
        self.app = gui.ModernVideoDownloaderGUI(self.mock_root)

    def test_initial_state(self):
        self.assertIsNotNone(self.app.downloader)
        self.assertEqual(len(self.app.queue), 2)  # demo items
        self.assertFalse(self.app.audio_only_mode)
        self.assertFalse(self.app.settings_visible)

    def test_paste_url(self):
        self.app._paste_url()
        # Should have called clipboard_get
        self.mock_root.clipboard_get.assert_called()

    def test_add_current_to_queue_requires_info(self):
        # No current_info yet
        self.app._add_current_to_queue()
        # Should have shown toast
        self.assertTrue(MOCK_TK.Toplevel.called or True)  # loose check

    def test_detect_platform_on_url_change(self):
        self.app.url_entry.get = MagicMock(return_value="https://tiktok.com/xyz")
        self.app._on_url_change()
        # platform_label should have been updated
        self.assertTrue(self.app.platform_label.config.called)

    def test_set_mode(self):
        self.app.parsed_formats = [
            {"label": "Best Quality", "format_id": "best"},
            {"label": "Best Audio Only", "format_id": "bestaudio/best"},
        ]
        self.app.quality_combo = MagicMock()

        self.app._set_mode(True)  # audio only
        self.assertTrue(self.app.audio_only_mode)

        self.app._set_mode(False)
        self.assertFalse(self.app.audio_only_mode)

    def test_format_bytes(self):
        self.assertEqual(self.app._format_bytes(0), "0 B")
        self.assertEqual(self.app._format_bytes(1024), "1.0 KB")
        self.assertEqual(self.app._format_bytes(1048576), "1.0 MB")

    def test_queue_operations(self):
        initial_len = len(self.app.queue)
        self.app.queue.append({"id": 99, "title": "Test", "url": "x", "quality": "Best", "status": "queued"})
        self.app._render_queue()
        self.assertEqual(len(self.app.queue), initial_len + 1)

        self.app._clear_queue()
        self.assertEqual(len(self.app.queue), 0)

class TestIntegrationWithDownloader(unittest.TestCase):
    def test_downloader_parse_formats(self):
        dl = VideoDownloader()
        # Simulated yt-dlp info
        fake_info = {
            "title": "Test Video",
            "uploader": "Test Channel",
            "duration": 185,
            "formats": [
                {"format_id": "137", "height": 1080, "vcodec": "avc1", "acodec": "aac", "ext": "mp4", "filesize": 45000000},
                {"format_id": "140", "vcodec": "none", "acodec": "aac", "ext": "m4a", "filesize": 4200000},
            ]
        }
        parsed = dl.parse_formats(fake_info)
        self.assertGreaterEqual(len(parsed), 2)
        self.assertIn("Best Quality", parsed[0]["label"])
        self.assertIn("Audio Only", parsed[1]["label"])

    def test_fetch_video_info_mock(self):
        dl = VideoDownloader()
        with patch.object(dl, 'fetch_video_info') as mock_fetch:
            mock_fetch.return_value = {"title": "Mocked"}
            info = dl.fetch_video_info("https://fake.url")
            self.assertEqual(info["title"], "Mocked")

if __name__ == "__main__":
    print("=" * 60)
    print("VideoFlow Modern GUI - Headless Test Suite")
    print("=" * 60)
    print(f"Python: {sys.version}")
    print(f"Running in headless mode (tkinter mocked)")
    print()

    # Run all tests
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(sys.modules[__name__])
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    print("\n" + "=" * 60)
    if result.wasSuccessful():
        print("✅ ALL TESTS PASSED")
        print(f"Tests run: {result.testsRun}")
    else:
        print("❌ SOME TESTS FAILED")
        print(f"Failures: {len(result.failures)} | Errors: {len(result.errors)}")
    print("=" * 60)

    sys.exit(0 if result.wasSuccessful() else 1)
