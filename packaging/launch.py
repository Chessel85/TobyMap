"""Entry point for the frozen Windows application (PyInstaller)."""
import sys

from desktop.app import main

if __name__ == "__main__":
    sys.exit(main())
