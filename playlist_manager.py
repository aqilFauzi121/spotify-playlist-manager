# === FILE: playlist_manager.py ===
"""
PlaylistManager - business logic that uses SpotifyClient to find/create playlists,
search tracks by criteria, deduplicate and add tracks.
"""
from typing import List, Optional
from spotify_client import SpotifyClient
import logging

logger = logging.getLogger(__name__)


class PlaylistManager:
    def __init__(self, client: SpotifyClient, user_id: str) -> None:
        self.client = client
        self.user_id = user_id

    def find_playlist_by_name(self, name: str) -> Optional[dict]:
        """Return a playlist dict if a playlist with the given name exists (case-insensitive)."""
        playlists = self.client.current_user_playlists()
        for p in playlists:
            if p.get("name", "").strip().lower() == name.strip().lower():
                return p
        return None

    def find_or_create_playlist(self, name: str, description: str = "") -> dict:
        pl = self.find_playlist_by_name(name)
        if pl:
            logger.info("Found existing playlist: %s", pl.get("id"))
            return pl
        logger.info("Creating new playlist: %s", name)
        return self.client.create_playlist(self.user_id, name, public=True, description=description)

    def get_playlist_track_uris(self, playlist_id: str) -> List[str]:
        items = self.client.playlist_items_all(playlist_id)
        uris: List[str] = []
        for it in items:
            track = it.get("track") or {}
            uri = track.get("uri")
            if uri:
                uris.append(uri)
        return uris

    def add_new_tracks_to_playlist(self, playlist_id: str, candidate_uris: List[str]) -> int:
        """Add only the URIs that do not already exist in the playlist. Returns number added."""
        existing = set(self.get_playlist_track_uris(playlist_id))
        to_add = [u for u in candidate_uris if u and u not in existing]
        if not to_add:
            logger.info("No new tracks to add.")
            return 0
        self.client.add_items_to_playlist(playlist_id, to_add)
        return len(to_add)

    def search_tracks_by_genre_and_popularity(self, genre: str, pop_min: int = 0, pop_max: int = 100, limit: int = 25) -> List[str]:
        """Search tracks by genre keyword and filter by popularity. Returns list of URIs up to `limit`.

        Note: Spotify's `genre:` query only works reliably against artists, not all tracks. This function
        performs a few searches and filters results.
        """
        found: List[str] = []
        queries = [f"genre:{genre}", genre]
        for q in queries:
            if len(found) >= limit:
                break
            tracks = self.client.search_tracks(q, limit=50)
            for t in tracks:
                if len(found) >= limit:
                    break
                pop = t.get("popularity", 0) or 0
                uri = t.get("uri")
                if uri and pop_min <= pop <= pop_max and uri not in found:
                    found.append(uri)
        return found[:limit]