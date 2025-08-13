# === FILE: main.py ===
"""
Entrypoint to run the Tkinter GUI application.
"""
import logging
import tkinter as tk
from gui import SpotifyGUI


def main():
    logging.basicConfig(level=logging.INFO)
    root = tk.Tk()
    app = SpotifyGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()