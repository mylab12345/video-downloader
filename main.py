#!/usr/bin/env python3
"""
VideoFlow launcher.

  python main.py                 → desktop GUI if available, otherwise web GUI
  python main.py --web           → web GUI (browser)
  python main.py --gui           → desktop (tkinter) GUI
  python main.py --cli [args]    → CLI
  python main.py <url> [opts]    → CLI with a URL
"""
import os
import sys


WEB_FLAGS = {"--web", "-w", "--web-gui"}
GUI_FLAGS = {"--gui", "--desktop", "--tk"}
CLI_FLAGS = {"--cli"}


def check_tkinter():
    try:
        import tkinter  # noqa: F401
        return True, ""
    except ImportError as e:
        return False, str(e)


def desktop_gui_available():
    has_tk, err = check_tkinter()
    if not has_tk:
        return False, err
    if sys.platform.startswith("linux") and not os.environ.get("DISPLAY") and not os.environ.get("WAYLAND_DISPLAY"):
        return False, "no DISPLAY / WAYLAND_DISPLAY (headless environment)"
    return True, ""


def launch_web_gui(extra_argv=None):
    """Start the Flask web GUI, bound for sandbox / reverse-proxy preview."""
    try:
        import web
    except ImportError as e:
        print("\n❌ Web GUI could not start: missing dependency ({})".format(e))
        print("   Install with:  python3 -m venv venv && ./venv/bin/pip install -r requirements.txt")
        print("   Then run:      ./venv/bin/python main.py --web\n")
        raise SystemExit(1) from e

    port = int(os.environ.get("PORT", "8000"))
    host = os.environ.get("HOST", "0.0.0.0")
    print("=" * 70)
    print("  VideoFlow web GUI")
    print("=" * 70)
    print(f"  Listening on http://{host}:{port}")
    print("  Open the live preview / that URL in your browser.")
    print("  Desktop tkinter GUI is unavailable in this environment,")
    print("  so the browser UI is used instead.")
    print("=" * 70)
    web.serve(host=host, port=port)


def launch_desktop_gui():
    ok, reason = desktop_gui_available()
    if not ok:
        print(f"\n⚠️  Desktop GUI unavailable ({reason}).")
        print("    Launching web GUI instead...\n")
        launch_web_gui()
        return
    try:
        import gui
        gui.main()
    except Exception as e:
        print(f"\n❌ Error starting desktop GUI: {e}")
        print("    Launching web GUI instead...\n")
        launch_web_gui()


def launch_cli(argv):
    # Strip our own mode flags so argparse in cli.py only sees its options.
    cleaned = [a for a in argv if a not in WEB_FLAGS | GUI_FLAGS | CLI_FLAGS]
    sys.argv = [sys.argv[0]] + cleaned
    import cli
    cli.main()


def main():
    argv = sys.argv[1:]
    flags = set(argv)

    if flags & WEB_FLAGS:
        launch_web_gui()
        return
    if flags & GUI_FLAGS:
        launch_desktop_gui()
        return
    if flags & CLI_FLAGS:
        launch_cli(argv)
        return

    # Any remaining args (a URL, -l, -f, …) mean CLI mode.
    if argv:
        launch_cli(argv)
        return

    # No args: prefer a real GUI. Desktop if we can, otherwise the web UI
    # — never drop the user into a blocking CLI prompt.
    ok, _reason = desktop_gui_available()
    if ok:
        launch_desktop_gui()
    else:
        launch_web_gui()


if __name__ == "__main__":
    main()
