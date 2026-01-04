"""
Spotify Client
Handles Spotify API authentication and playback monitoring.
"""

import spotipy
from spotipy.oauth2 import SpotifyOAuth
from typing import Optional, Dict


class SpotifyClient:
    """Client for Spotify Web API."""

    def __init__(self, client_id: str, client_secret: str, redirect_uri: str):
        """
        Initialize Spotify client.

        Args:
            client_id: Spotify app client ID
            client_secret: Spotify app client secret
            redirect_uri: OAuth redirect URI
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri

        # Set up OAuth with required scopes
        scope = "user-read-currently-playing user-read-playback-state"

        self.sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri=redirect_uri,
            scope=scope,
            cache_path=".spotify_cache"
        ))

    def get_current_track(self) -> Optional[Dict]:
        """
        Get currently playing track information.

        Returns:
            Dict with track info or None if nothing playing
        """
        try:
            current = self.sp.current_playback()

            if current is None or not current.get('is_playing'):
                return None

            track = current['item']
            if track is None:
                return None

            # Extract relevant information
            track_info = {
                'id': track['id'],
                'name': track['name'],
                'artist': ', '.join([artist['name'] for artist in track['artists']]),
                'album': track['album']['name'],
                'album_art_url': self._get_largest_image(track['album']['images']),
                'duration_ms': track['duration_ms'],
                'progress_ms': current.get('progress_ms', 0),
                'is_playing': current['is_playing']
            }

            return track_info

        except Exception as e:
            print(f"Error getting current track: {e}")
            return None

    def get_track_features(self, track_id: str) -> Optional[Dict]:
        """
        Get audio features for a track (energy, danceability, etc.).

        Args:
            track_id: Spotify track ID

        Returns:
            Dict with audio features or None
        """
        try:
            features = self.sp.audio_features([track_id])[0]
            return features
        except Exception as e:
            print(f"Error getting track features: {e}")
            return None

    @staticmethod
    def _get_largest_image(images: list) -> Optional[str]:
        """
        Get the largest image URL from Spotify image list.

        Args:
            images: List of image dicts from Spotify API

        Returns:
            URL of largest image or None
        """
        if not images:
            return None

        # Images are typically sorted largest to smallest
        # Return the first one (largest)
        return images[0]['url']

    def test_connection(self) -> bool:
        """Test if Spotify connection is working."""
        try:
            user = self.sp.current_user()
            print(f"Connected to Spotify as: {user['display_name']}")
            return True
        except Exception as e:
            print(f"Spotify connection test failed: {e}")
            return False
