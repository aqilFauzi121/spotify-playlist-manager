# gui.py
"""
Tkinter GUI with:
 - genre autosuggest dropdown (editable Combobox)
 - separate determinate progress bars for Search and Add phases (with percentages)
 - track preview list
 - Cancel support, Exit button for safe shutdown
 - copy/open playlist link, validation
"""
import tkinter as tk
from tkinter import ttk, messagebox
import threading
import logging
import webbrowser
from typing import Optional

from spotify_client import SpotifyClient
from playlist_manager import PlaylistManager
from config import get_config

logger = logging.getLogger(__name__)

POPULAR_GENRES = [
    "pop", "rock", "hip-hop", "electronic", "dance", "jazz", "classical",
    "r&b", "indie", "metal", "country", "reggae", "latin", "punk", "blues",
    "lo-fi", "soul", "folk", "house", "techno"
]


class SpotifyGUI:
    def __init__(self, root: tk.Tk):
        self.root = root
        root.title("Spotify Playlist Manager")
        root.geometry("900x600")

        cfg = get_config()
        self.client = SpotifyClient(
            cfg["SPOTIFY_CLIENT_ID"],
            cfg["SPOTIFY_CLIENT_SECRET"],
            cfg["SPOTIFY_REDIRECT_URI"],
            cache_path=cfg.get("SPOTIFY_CACHE_PATH", ".cache"),
        )
        self.pm: Optional[PlaylistManager] = None
        self.user_id: Optional[str] = None

        self._cancel_event: Optional[threading.Event] = None
        self._job_thread: Optional[threading.Thread] = None

        # search/add progress counters
        self._search_found = 0
        self._search_target = 1
        self._add_done = 0
        self._add_target = 1

        self._build_widgets()

    def _build_widgets(self):
        pad = {"padx": 8, "pady": 6}
        top = ttk.Frame(self.root, padding=10)
        top.pack(fill=tk.X)

        # Left form
        form = ttk.Frame(top)
        form.pack(side=tk.LEFT, fill=tk.Y)

        ttk.Label(form, text="Playlist name:").grid(row=0, column=0, sticky=tk.W, **pad)
        self.playlist_entry = ttk.Entry(form, width=36)
        self.playlist_entry.grid(row=0, column=1, **pad)

        ttk.Label(form, text="Genre / Keyword:").grid(row=1, column=0, sticky=tk.W, **pad)
        self.genre_combo = ttk.Combobox(form, values=POPULAR_GENRES, width=34)
        self.genre_combo.set("pop")
        self.genre_combo.grid(row=1, column=1, **pad)

        ttk.Label(form, text="Popularity (0–100):").grid(row=2, column=0, sticky=tk.W, **pad)
        pop_frame = ttk.Frame(form)
        pop_frame.grid(row=2, column=1, sticky=tk.W, **pad)
        self.pop_min_var = tk.IntVar(value=40)
        self.pop_max_var = tk.IntVar(value=100)
        self.pop_min_spin = ttk.Spinbox(pop_frame, from_=0, to=100, width=6, textvariable=self.pop_min_var)
        self.pop_min_spin.pack(side=tk.LEFT)
        ttk.Label(pop_frame, text=" to ").pack(side=tk.LEFT, padx=4)
        self.pop_max_spin = ttk.Spinbox(pop_frame, from_=0, to=100, width=6, textvariable=self.pop_max_var)
        self.pop_max_spin.pack(side=tk.LEFT)

        ttk.Label(form, text="Max tracks to add:").grid(row=3, column=0, sticky=tk.W, **pad)
        self.limit_spin = ttk.Spinbox(form, from_=1, to=500, width=8)
        self.limit_spin.set("30")
        self.limit_spin.grid(row=3, column=1, sticky=tk.W, **pad)

        ttk.Label(form, text="Playlist visibility:").grid(row=4, column=0, sticky=tk.W, **pad)
        self.public_var = tk.BooleanVar(value=True)
        pub_frame = ttk.Frame(form)
        pub_frame.grid(row=4, column=1, sticky=tk.W)
        ttk.Radiobutton(pub_frame, text="Public", variable=self.public_var, value=True).pack(side=tk.LEFT)
        ttk.Radiobutton(pub_frame, text="Private", variable=self.public_var, value=False).pack(side=tk.LEFT, padx=8)

        btn_frame = ttk.Frame(form)
        btn_frame.grid(row=5, column=0, columnspan=2, pady=(10, 0))
        self.auth_btn = ttk.Button(btn_frame, text="Authenticate", command=self.authenticate)
        self.auth_btn.pack(side=tk.LEFT, padx=6)
        self.run_btn = ttk.Button(btn_frame, text="Create/Update Playlist", command=self.on_run)
        self.run_btn.pack(side=tk.LEFT, padx=6)
        self.run_btn.state(["disabled"])
        self.cancel_btn = ttk.Button(btn_frame, text="Cancel", command=self.cancel_job)
        self.cancel_btn.pack(side=tk.LEFT, padx=6)
        self.cancel_btn.state(["disabled"])
        # Exit button added here
        self.exit_btn = ttk.Button(btn_frame, text="Exit", command=self.on_exit)
        self.exit_btn.pack(side=tk.LEFT, padx=6)

        # Right: preview list
        right = ttk.Frame(top)
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=12)

        ttk.Label(right, text="Track preview (found):").pack(anchor=tk.W)
        self.track_listbox = tk.Listbox(right, height=20)
        self.track_listbox.pack(fill=tk.BOTH, expand=True)
        self.track_scroll = ttk.Scrollbar(right, orient=tk.VERTICAL, command=self.track_listbox.yview)
        self.track_listbox.config(yscrollcommand=self.track_scroll.set)
        self.track_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        # Bottom: two progress bars, playlist link, status
        bottom = ttk.Frame(self.root, padding=10)
        bottom.pack(fill=tk.X)

        # Search progress
        search_frame = ttk.Frame(bottom)
        search_frame.pack(fill=tk.X, pady=(0, 6))
        ttk.Label(search_frame, text="Search Progress:").pack(side=tk.LEFT)
        self.search_progress = ttk.Progressbar(search_frame, mode="determinate", maximum=1, value=0, length=400)
        self.search_progress.pack(side=tk.LEFT, padx=(8, 6), fill=tk.X, expand=True)
        self.search_percent_var = tk.StringVar(value="0%")
        self.search_percent_label = ttk.Label(search_frame, textvariable=self.search_percent_var, width=8)
        self.search_percent_label.pack(side=tk.LEFT)

        # Add progress
        add_frame = ttk.Frame(bottom)
        add_frame.pack(fill=tk.X, pady=(0, 6))
        ttk.Label(add_frame, text="Add Progress:").pack(side=tk.LEFT)
        self.add_progress = ttk.Progressbar(add_frame, mode="determinate", maximum=1, value=0, length=400)
        self.add_progress.pack(side=tk.LEFT, padx=(28, 6), fill=tk.X, expand=True)
        self.add_percent_var = tk.StringVar(value="0%")
        self.add_percent_label = ttk.Label(add_frame, textvariable=self.add_percent_var, width=8)
        self.add_percent_label.pack(side=tk.LEFT)

        # info counts
        self.counts_var = tk.StringVar(value="")
        self.counts_label = ttk.Label(bottom, textvariable=self.counts_var)
        self.counts_label.pack(anchor=tk.W, pady=(6, 0))

        # playlist link
        link_frame = ttk.Frame(bottom)
        link_frame.pack(fill=tk.X, pady=(8, 0))
        ttk.Label(link_frame, text="Playlist link:").pack(side=tk.LEFT)
        self.playlist_link_var = tk.StringVar(value="")
        self.playlist_link_entry = ttk.Entry(link_frame, textvariable=self.playlist_link_var, width=70)
        self.playlist_link_entry.pack(side=tk.LEFT, padx=(6, 6))
        self.open_link_btn = ttk.Button(link_frame, text="Open", command=self.open_playlist_link)
        self.open_link_btn.pack(side=tk.LEFT, padx=4)
        self.copy_link_btn = ttk.Button(link_frame, text="Copy Link", command=self.copy_playlist_link)
        self.copy_link_btn.pack(side=tk.LEFT, padx=4)

        # status
        ttk.Label(self.root, text="Status:").pack(anchor=tk.W, padx=12)
        self.status_text = tk.Text(self.root, height=8, wrap=tk.WORD)
        self.status_text.pack(fill=tk.BOTH, expand=True, padx=12, pady=(6, 12))
        self._log("Ready. Click Authenticate to sign in.")

    def _log(self, msg: str):
        def append():
            self.status_text.configure(state=tk.NORMAL)
            self.status_text.insert(tk.END, msg + "\n")
            self.status_text.see(tk.END)
            self.status_text.configure(state=tk.DISABLED)
        self.root.after(0, append)

    def authenticate(self):
        self._log("Starting authentication...")
        def _auth():
            try:
                self.client.authenticate()
                user = self.client.current_user()
                self.user_id = user.get("id")
                self.pm = PlaylistManager(self.client, self.user_id)
                self._log(f"Authenticated as {user.get('display_name') or self.user_id}")
                self.root.after(0, lambda: self.run_btn.state(["!disabled"]))
            except Exception as e:
                logger.exception("Failed to authenticate")
                self._log(f"Authentication failed: {e}")
        threading.Thread(target=_auth, daemon=True).start()

    def validate_inputs(self) -> Optional[dict]:
        name = self.playlist_entry.get().strip()
        if not name:
            messagebox.showwarning("Validation", "Please enter a playlist name.")
            return None
        genre = self.genre_combo.get().strip()
        if not genre:
            messagebox.showwarning("Validation", "Please enter a genre/keyword.")
            return None
        try:
            pop_min = int(self.pop_min_var.get())
            pop_max = int(self.pop_max_var.get())
        except Exception:
            messagebox.showwarning("Validation", "Popularity min/max must be integers 0-100.")
            return None
        if not (0 <= pop_min <= 100 and 0 <= pop_max <= 100 and pop_min <= pop_max):
            messagebox.showwarning("Validation", "Popularity must be 0..100 and min <= max.")
            return None
        try:
            limit = int(self.limit_spin.get())
            if limit < 1:
                raise ValueError()
        except Exception:
            messagebox.showwarning("Validation", "Max tracks must be a positive integer.")
            return None
        public = bool(self.public_var.get())
        return dict(name=name, genre=genre, pop_min=pop_min, pop_max=pop_max, limit=limit, public=public)

    # ---- progress helpers ----
    def _init_search_progress(self, limit: int):
        self._search_found = 0
        self._search_target = max(1, limit)
        self.search_progress.config(maximum=self._search_target, value=0)
        self.search_percent_var.set("0%")
        self._update_counts_label()

    def _inc_search_progress(self, amount: int = 1):
        self._search_found = min(self._search_found + amount, self._search_target)
        pct = int(100 * (self._search_found / self._search_target)) if self._search_target else 100
        def ui():
            self.search_progress['value'] = self._search_found
            self.search_percent_var.set(f"{pct}%")
            self._update_counts_label()
        self.root.after(0, ui)

    def _init_add_progress(self, add_target: int):
        self._add_done = 0
        self._add_target = max(1, add_target)
        self.add_progress.config(maximum=self._add_target, value=0)
        self.add_percent_var.set("0%")
        self._update_counts_label()

    def _inc_add_progress(self, amount: int = 1):
        self._add_done = min(self._add_done + amount, self._add_target)
        pct = int(100 * (self._add_done / self._add_target)) if self._add_target else 100
        def ui():
            self.add_progress['value'] = self._add_done
            self.add_percent_var.set(f"{pct}%")
            self._update_counts_label()
        self.root.after(0, ui)

    def _update_counts_label(self):
        self.counts_var.set(f"Found {self._search_found} / {self._search_target}  •  Added {self._add_done} / {self._add_target}")

    # ---- actions ----
    def on_run(self):
        params = self.validate_inputs()
        if not params:
            return
        if not self.pm:
            messagebox.showwarning("Not authenticated", "Please click Authenticate first.")
            return

        # prepare UI
        self.run_btn.state(["disabled"])
        self.cancel_btn.state(["!disabled"])
        self.auth_btn.state(["disabled"])
        self.track_listbox.delete(0, tk.END)
        self.playlist_link_var.set("")
        self._cancel_event = threading.Event()

        self._init_search_progress(params["limit"])
        # add progress will be initialized AFTER we know number of candidates

        def job():
            try:
                self._log(f"Starting operation for playlist '{params['name']}', genre '{params['genre']}'")
                pl = self.pm.find_or_create_playlist(params["name"], description=f"Auto playlist: {params['genre']}")
                pl_id = pl.get("id")
                pl_name = pl.get("name")
                self._update_playlist_link(pl)
                self._log(f"Using playlist: {pl_name} (id: {pl_id})")

                # SEARCH PHASE
                seen = set()
                uris = []
                queries = [f"genre:{params['genre']}", params['genre']]
                for q in queries:
                    if self._cancel_event.is_set():
                        self._log("Operation cancelled by user (during search).")
                        return
                    tracks = self.client.search_tracks(q, limit=50)
                    for t in tracks:
                        if self._cancel_event.is_set():
                            break
                        if len(uris) >= params["limit"]:
                            break
                        pop = t.get("popularity", 0) or 0
                        if params["pop_min"] <= pop <= params["pop_max"]:
                            uri = t.get("uri")
                            if uri and uri not in seen:
                                seen.add(uri)
                                uris.append(uri)
                                # UI preview
                                artists = ", ".join([a.get("name", "") for a in t.get("artists", [])])
                                title = t.get("name", "<unknown>")
                                preview = f"{artists} — {title} (pop {pop})"
                                self.root.after(0, lambda p=preview: self.track_listbox.insert(tk.END, p))
                                # update search progress
                                self._inc_search_progress(1)
                    if len(uris) >= params["limit"]:
                        break

                self._log(f"Found {len(uris)} candidate tracks.")
                if self._cancel_event.is_set():
                    self._log("Operation cancelled by user (before add).")
                    return

                # INIT add progress to number of candidates (we will try to add up to that many)
                self._init_add_progress(len(uris))

                # ADD PHASE
                added = self.pm.add_new_tracks_to_playlist(pl_id, uris)
                if added:
                    self._inc_add_progress(added)
                self._log(f"Added {added} new tracks to playlist '{pl_name}'.")

            except Exception as e:
                logger.exception("Operation failed")
                self._log(f"Operation failed: {e}")
            finally:
                self.root.after(0, self._on_job_finish)

        self._job_thread = threading.Thread(target=job, daemon=True)
        self._job_thread.start()

    def cancel_job(self):
        if self._cancel_event and not self._cancel_event.is_set():
            self._cancel_event.set()
            self._log("Cancellation requested... (will stop when current request completes)")
            self.cancel_btn.state(["disabled"])

    def _on_job_finish(self):
        self.run_btn.state(["!disabled"])
        self.cancel_btn.state(["disabled"])
        self.auth_btn.state(["!disabled"])
        self._log("Operation finished.")
        # ensure labels up-to-date
        self._update_counts_label()

    # ---- Exit handling ----
    def on_exit(self):
        """
        Called when user clicks Exit. If a job is running, ask for confirmation,
        request cancellation, then poll the thread until it finishes and exit.
        """
        if self._job_thread and self._job_thread.is_alive():
            # job in progress
            if not messagebox.askyesno("Exit", "A job is currently running. Cancel it and exit?"):
                return
            # request cancellation
            if self._cancel_event:
                self._cancel_event.set()
            self._log("Exit requested: waiting for running job to finish...")
            # disable buttons to avoid more actions
            self.run_btn.state(["disabled"])
            self.cancel_btn.state(["disabled"])
            self.auth_btn.state(["disabled"])
            self.exit_btn.state(["disabled"])
            # poll for thread completion
            self.root.after(500, self._wait_for_thread_and_exit)
        else:
            # no job running: safe to exit immediately
            self._log("Exiting application.")
            try:
                self.root.quit()
                self.root.destroy()
            except Exception:
                pass

    def _wait_for_thread_and_exit(self):
        if self._job_thread and self._job_thread.is_alive():
            # still running: check again later
            self.root.after(500, self._wait_for_thread_and_exit)
        else:
            self._log("Background job finished; closing now.")
            try:
                self.root.quit()
                self.root.destroy()
            except Exception:
                pass

    def _update_playlist_link(self, pl: dict):
        url = pl.get("external_urls", {}).get("spotify", "")
        if url:
            self.playlist_link_var.set(url)

    def open_playlist_link(self):
        url = self.playlist_link_var.get().strip()
        if url:
            webbrowser.open(url)
        else:
            messagebox.showinfo("No link", "No playlist link available yet.")

    def copy_playlist_link(self):
        url = self.playlist_link_var.get().strip()
        if url:
            self.root.clipboard_clear()
            self.root.clipboard_append(url)
            self._log("Playlist link copied to clipboard.")
        else:
            messagebox.showinfo("No link", "No playlist link available to copy.")