#!/usr/bin/env python3
"""Launcher tests — desktop GUI is skipped in headless envs, web GUI is used."""
import os
import sys
import unittest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import main as launcher


class TestLauncher(unittest.TestCase):
    def test_desktop_gui_unavailable_without_display_or_tk(self):
        ok, reason = launcher.desktop_gui_available()
        # This sandbox has neither tkinter nor DISPLAY.
        if "tkinter" in sys.modules or self._has_tk():
            # If tk is present, DISPLAY still decides.
            if not os.environ.get("DISPLAY") and not os.environ.get("WAYLAND_DISPLAY"):
                if sys.platform.startswith("linux"):
                    self.assertFalse(ok)
                    self.assertIn("DISPLAY", reason)
        else:
            self.assertFalse(ok)

    def _has_tk(self):
        try:
            import tkinter  # noqa: F401
            return True
        except ImportError:
            return False

    def test_no_args_launches_web_when_desktop_unavailable(self):
        with patch.object(launcher, "desktop_gui_available", return_value=(False, "no display")), \
             patch.object(launcher, "launch_web_gui") as web, \
             patch.object(launcher, "launch_desktop_gui") as desk, \
             patch.object(sys, "argv", ["main.py"]):
            launcher.main()
            web.assert_called_once()
            desk.assert_not_called()

    def test_web_flag(self):
        with patch.object(launcher, "launch_web_gui") as web, \
             patch.object(sys, "argv", ["main.py", "--web"]):
            launcher.main()
            web.assert_called_once()

    def test_gui_flag_falls_through_to_desktop_helper(self):
        with patch.object(launcher, "launch_desktop_gui") as desk, \
             patch.object(sys, "argv", ["main.py", "--gui"]):
            launcher.main()
            desk.assert_called_once()

    def test_url_goes_to_cli(self):
        with patch.object(launcher, "launch_cli") as cli, \
             patch.object(sys, "argv", ["main.py", "https://example.com/v.mp4"]):
            launcher.main()
            cli.assert_called_once()

    def test_cli_flag(self):
        with patch.object(launcher, "launch_cli") as cli, \
             patch.object(sys, "argv", ["main.py", "--cli", "https://example.com/v.mp4"]):
            launcher.main()
            cli.assert_called_once()

    def test_desktop_helper_falls_back_to_web(self):
        with patch.object(launcher, "desktop_gui_available", return_value=(False, "no tk")), \
             patch.object(launcher, "launch_web_gui") as web:
            launcher.launch_desktop_gui()
            web.assert_called_once()


if __name__ == "__main__":
    unittest.main(verbosity=2)
