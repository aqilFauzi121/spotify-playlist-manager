# === FILE: spotify_client.py ===
"""
SpotifyClient - thin Spotipy wrapper handling authentication and common Spotify API tasks.
"""
from typing import Optional, List, Dict, Any
import logging
import spotipy
from spotipy.oauth2 import SpotifyOAuth

logger = logging.getLogger(__name__)


class SpotifyClient:
    """A small wrapper around Spotipy to centralize auth and common helper methods.

    Usage:
        client = SpotifyClient(client_id, client_secret, redirect_uri, cache_path)
        client.authenticate()
        user = client.current_user()
    """

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        redirect_uri: str,
        cache_path: str = ".cache",
        scope: Optional[str] = None,
    ) -> None:
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.cache_path = cache_path
        # sensible default scopes for playlist creation/reading
        self.scope = scope or (
            "playlist-modify-public playlist-modify-private playlist-read-private user-library-read"
        )
        self.sp: Optional[spotipy.Spotify] = None

    def authenticate(self) -> None:
        """Authenticate and set up the spotipy.Spotify instance.
        This will open a browser for the OAuth flow on first run (Spotipy behavior).
        """
        auth_manager = SpotifyOAuth(
            client_id=self.client_id,
            client_secret=self.client_secret,
            redirect_uri=self.redirect_uri,
            scope=self.scope,
            cache_path=self.cache_path,
        )
        self.sp = spotipy.Spotify(auth_manager=auth_manager)
        logger.info("Spotify authenticated (cache: %s)", self.cache_path)

    def current_user(self) -> Dict[str, Any]:
        assert self.sp is not None, "Spotify client not authenticated"
        return self.sp.current_user()

    # --- Helper wrappers with pagination ---
    def current_user_playlists(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Return user's playlists (all) as a list of playlist dicts."""
        assert self.sp is not None
        items: List[Dict[str, Any]] = []
        results = self.sp.current_user_playlists(limit=limit)
        while results:
            items.extend(results.get("items", []))
            if results.get("next"):
                results = self.sp.next(results)
            else:
                break
        return items

    def create_playlist(self, user_id: str, name: str, public: bool = True, description: str = "") -> Dict[str, Any]:
        assert self.sp is not None
        return self.sp.user_playlist_create(user=user_id, name=name, public=public, description=description)

    def playlist_items_all(self, playlist_id: str) -> List[Dict[str, Any]]:
        """Return all playlist item objects for the given playlist id."""
        assert self.sp is not None
        items: List[Dict[str, Any]] = []
        results = self.sp.playlist_items(playlist_id, limit=100)
        while results:
            items.extend(results.get("items", []))
            if results.get("next"):
                results = self.sp.next(results)
            else:
                break
        return items

    def add_items_to_playlist(self, playlist_id: str, uris: List[str]) -> None:
        """Add items to a playlist in batches (100 max per request)."""
        assert self.sp is not None
        if not uris:
            return
        batch = 100
        for i in range(0, len(uris), batch):
            chunk = uris[i : i + batch]
            logger.info("Adding %d tracks to playlist %s", len(chunk), playlist_id)
            self.sp.playlist_add_items(playlist_id, chunk)

    def search_tracks(self, query: str, limit: int = 50, market: Optional[str] = None) -> List[Dict[str, Any]]:
        """Search tracks with Spotipy and return track objects list."""
        assert self.sp is not None
        r = self.sp.search(q=query, type="track", limit=min(limit, 50), market=market)
        return r.get("tracks", {}).get("items", [])