# Spotify Playlist Manager

A small desktop app (Tkinter) and library to create/update Spotify playlists automatically from a genre or keyword, with deduplication and configurable popularity filters. Includes a GUI, a thin Spotipy wrapper, and unit tests for the core logic.

## Features
- OAuth authentication with Spotify (Spotipy)
- Find or create playlist by name
- Search by genre/keyword and filter by popularity
- Avoid adding duplicate tracks
- GUI with track preview, progress bars, cancel and exit controls
- Unit tests with pytest

## Demo / Screenshots


## Quickstart
1. Clone the repo and enter the project directory:
```bash
git clone https://github.com/aqilFauzi121/spotify-playlist-manager.git
cd spotify-playlist-manager
```

2. Create and activate a virtual environment (recommended):
```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Copy .env.example → .env and fill in your Spotify credentials (do not commit .env):
```bash
SPOTIFY_CLIENT_ID=your_client_id
SPOTIFY_CLIENT_SECRET=your_client_secret
SPOTIFY_REDIRECT_URI=http://127.0.0.1:8888/callback
SPOTIFY_CACHE_PATH=.cache
```

5. Run the GUI:
```bash
python main.py
```
Click Authenticate and follow the browser flow, then use the GUI to create/update playlists.

Headless example
A small headless example is available in main.py that demonstrates finding/creating a playlist and adding tracks programmatically.
```bash
python main.py
```

Running tests
Unit tests use pytest and are designed to run offline using mocks for the Spotify client.
```bash
pip install pytest
pytest -q
```

Development & Staging
Break changes into small commits. Suggested staged plan is in DEVELOPMENT.md (or see the repo issues). Use branches and PRs for each feature:
feat/core — Spotify wrapper & playlist manager
feat/gui — initial GUI
feat/gui-progress — add progress bars
chore/tests — add tests & CI

Contributing
Contributions welcome. Please open an issue first if you plan a larger change.

License
This project is licensed under the MIT License — see the LICENSE file for details.
