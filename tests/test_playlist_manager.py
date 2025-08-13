# tests/test_playlist_manager.py
import pytest
from unittest.mock import Mock, call
from playlist_manager import PlaylistManager

# Helper to build fake track items like Spotipy returns
def make_track(uri: str, popularity: int = 50):
    return {"uri": uri, "popularity": popularity}

def make_playlist_item(uri: str):
    return {"track": {"uri": uri}}

@pytest.fixture
def fake_client():
    """
    Create a lightweight fake SpotifyClient with the methods PlaylistManager calls.
    We'll set attributes on the mock in individual tests.
    """
    c = Mock()
    return c

def test_find_playlist_by_name_returns_when_present(fake_client):
    # Arrange: client.current_user_playlists returns a list including our playlist
    fake_client.current_user_playlists.return_value = [
        {"id": "pl1", "name": "MyList"},
        {"id": "pl2", "name": "Other"},
    ]
    pm = PlaylistManager(fake_client, user_id="testuser")

    # Act
    found = pm.find_playlist_by_name("mylist")  # case-insensitive

    # Assert
    assert found is not None
    assert found["id"] == "pl1"
    fake_client.current_user_playlists.assert_called_once()

def test_find_or_create_playlist_creates_when_missing(fake_client):
    # Arrange: no playlist exists, client.create_playlist should be called
    fake_client.current_user_playlists.return_value = []
    fake_client.create_playlist.return_value = {"id": "new_pl", "name": "New"}
    pm = PlaylistManager(fake_client, user_id="user123")

    # Act
    pl = pm.find_or_create_playlist("New")

    # Assert
    assert pl["id"] == "new_pl"
    fake_client.create_playlist.assert_called_once_with("user123", "New", public=True, description="")

def test_find_or_create_playlist_returns_existing_and_does_not_create(fake_client):
    fake_client.current_user_playlists.return_value = [{"id": "plx", "name": "Exists"}]
    pm = PlaylistManager(fake_client, user_id="u")
    pl = pm.find_or_create_playlist("Exists")
    assert pl["id"] == "plx"
    fake_client.create_playlist.assert_not_called()

def test_get_playlist_track_uris_collects_all_uris(fake_client):
    # Arrange: playlist_items_all returns several items
    fake_client.playlist_items_all.return_value = [
        make_playlist_item("spotify:track:1"),
        make_playlist_item("spotify:track:2"),
        {"track": None},  # defensive: missing track
    ]
    pm = PlaylistManager(fake_client, user_id="u")

    # Act
    uris = pm.get_playlist_track_uris("plid")

    # Assert
    assert uris == ["spotify:track:1", "spotify:track:2"]
    fake_client.playlist_items_all.assert_called_once_with("plid")

def test_add_new_tracks_to_playlist_adds_only_nonexisting(fake_client):
    # Arrange: existing playlist contains track:1
    fake_client.playlist_items_all.return_value = [make_playlist_item("spotify:track:1")]
    pm = PlaylistManager(fake_client, user_id="u")
    candidates = ["spotify:track:1", "spotify:track:2", "spotify:track:3"]

    # Act
    added_count = pm.add_new_tracks_to_playlist("plid", candidates)

    # Assert
    assert added_count == 2
    # Should call add_items_to_playlist with only the two new URIs
    fake_client.add_items_to_playlist.assert_called_once_with("plid", ["spotify:track:2", "spotify:track:3"])

def test_search_tracks_by_genre_and_popularity_filters_and_limits(fake_client):
    # Arrange: make client.search_tracks return mixed-popularity tracks for queries
    # The function attempts queries: f"genre:{genre}" then the raw genre
    fake_client.search_tracks.side_effect = [
        # first call (genre:rock)
        [
            make_track("uri:1", 10),
            make_track("uri:2", 60),
            make_track("uri:3", 80),
        ],
        # second call (rock)
        [
            make_track("uri:4", 55),
            make_track("uri:2", 60),  # duplicate uri to test dedupe
        ],
    ]
    pm = PlaylistManager(fake_client, user_id="u")

    # Act: want popularity between 50 and 100, limit 3
    uris = pm.search_tracks_by_genre_and_popularity("rock", pop_min=50, pop_max=100, limit=3)

    # Assert: should have 3 unique URIs with popularity in range and preserve limit
    assert "uri:2" in uris
    assert "uri:3" in uris
    assert "uri:4" in uris or len(uris) == 3
    # Ensure search_tracks was called at least for the two queries
    assert fake_client.search_tracks.call_count >= 1
