#!/usr/bin/env python3
import sys
import os

def check_tkinter():
    try:
        import tkinter
        return True, ""
    except ImportError as e:
        return False, str(e)

def main():
    if len(sys.argv) > 1:
        # Arguments provided, launch CLI mode directly
        import cli
        cli.main()
    else:
        # No arguments provided, attempt to launch Desktop GUI
        has_tk, err = check_tkinter()
        if not has_tk:
            print("\n" + "=" * 70)
            print(" ⚠️  DESKTOP GUI REQUIREMENT MISSING IN THIS PYTHON ENVIRONMENT")
            print("=" * 70)
            print(" python3-tk is installed on your Linux system for Ubuntu Python 3.12,")
            print(" but this venv was created using a Python build without Tkinter bindings.")
            print("\n 🔧 QUICK FIX: Run the setup script to link system Python 3.12:")
            print("     bash setup_venv.sh")
            print("\n Then start the app:")
            print("     ./venv/bin/python main.py\n")
            print(" Falling back to CLI mode for now...\n" + "=" * 70 + "\n")
            import cli
            cli.main()
            return


        # Check for X11 / Wayland DISPLAY on Linux
        if sys.platform.startswith("linux") and not os.environ.get("DISPLAY") and not os.environ.get("WAYLAND_DISPLAY"):
            print("\n⚠️  No graphical DISPLAY detected (headless/SSH environment).")
            print("Launching CLI mode instead...\n")
            import cli
            cli.main()
            return

        try:
            import gui
            gui.main()
        except Exception as e:
            print(f"\n❌ Error starting GUI: {e}")
            print("Falling back to CLI mode...\n")
            import cli
            cli.main()

if __name__ == "__main__":
    main()

