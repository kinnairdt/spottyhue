"""
SpottyHue Main Application
Syncs Spotify album artwork colors to Philips Hue lights.
"""

import time
import logging
from typing import Optional, List, Dict, Tuple
from .spotify_client import SpotifyClient
from .hue_controller import HueController
from .color_extractor import ColorExtractor

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class SpottyHue:
    """Main application for syncing Spotify to Hue lights."""

    def __init__(self,
                 spotify_client: SpotifyClient,
                 hue_controller: HueController,
                 light_ids: List[int],
                 num_colors: int = 3,
                 update_interval: int = 2,
                 brightness: int = 254):
        """
        Initialize SpottyHue app.

        Args:
            spotify_client: Initialized Spotify client
            hue_controller: Initialized Hue controller
            light_ids: List of light IDs to control
            num_colors: Number of colors to extract from artwork
            update_interval: How often to check for song changes (seconds)
            brightness: Brightness level (0-254)
        """
        self.spotify = spotify_client
        self.hue = hue_controller
        self.light_ids = light_ids
        self.num_colors = min(num_colors, len(light_ids))
        self.update_interval = update_interval
        self.brightness = brightness

        self.current_track_id: Optional[str] = None
        self.color_extractor = ColorExtractor()
        
        # State tracking
        self.current_colors: List[Tuple[int, int, int]] = []
        self.light_colors: Dict[int, Tuple[int, int, int]] = {}

    def get_colors_for_track(self, track_info: dict) -> List[Tuple[int, int, int]]:
        """
        Extract and process colors from the track's album artwork.
        
        Args:
            track_info: Track information dict from Spotify
            
        Returns:
            List of RGB tuples
        """
        album_art_url = track_info.get('album_art_url')
        if not album_art_url:
            logger.warning("No album artwork available")
            return []

        logger.info(f"Extracting {self.num_colors} colors from artwork: {track_info['album']}")
        
        # Extract extra colors to allow for filtering
        colors = self.color_extractor.extract_colors_from_url(album_art_url, self.num_colors + 3)

        # Filter out near-black colors (Hue can't display black)
        filtered_colors = [rgb for rgb in colors if sum(rgb) > 120]

        # If we filtered out too many, use original colors
        if len(filtered_colors) < self.num_colors:
            filtered_colors = colors

        # Take the top N colors
        final_colors = filtered_colors[:self.num_colors]
        
        # Filter and boost colors for better visuals
        return self.color_extractor.filter_colors(final_colors)

    def sync_colors_to_lights(self, track_info: dict):
        """
        Extract colors from album artwork and sync to lights.

        Args:
            track_info: Track information dict from Spotify
        """
        logger.info(f"Now Playing: {track_info['name']} - {track_info['artist']}")

        # Get processed colors
        self.current_colors = self.get_colors_for_track(track_info)
        
        if not self.current_colors:
            return

        # Map colors to lights
        self.light_colors = {}
        for i, light_id in enumerate(self.light_ids[:self.num_colors]):
            color_idx = i % len(self.current_colors)
            rgb = self.current_colors[color_idx]
            self.light_colors[light_id] = rgb
            logger.debug(f"Light {light_id}: RGB{rgb}")

        # Apply colors to lights
        logger.info("Updating lights...")
        self.hue.set_multiple_colors(self.light_colors, brightness=self.brightness, transition_time=10)
        logger.info("Lights updated!")

    def run(self):
        """Main run loop - monitor Spotify and update lights."""
        logger.info("Starting SpottyHue...")

        # Test connections
        logger.info("Testing Spotify connection...")
        if not self.spotify.test_connection():
            logger.error("Failed to connect to Spotify. Check your credentials.")
            return

        logger.info("Testing Hue connection...")
        if not self.hue.test_connection():
            logger.error("Failed to connect to Hue bridge. Check your configuration.")
            return

        logger.info("All systems ready!")
        logger.info(f"Monitoring lights: {self.light_ids}")
        logger.info(f"Checking for new songs every {self.update_interval}s")

        try:
            while True:
                # Get current track
                track = self.spotify.get_current_track()

                if track is None:
                    if self.current_track_id is not None:
                        logger.info("Playback stopped")
                        self.current_track_id = None
                    time.sleep(self.update_interval)
                    continue

                # Check if track changed
                if track['id'] != self.current_track_id:
                    self.current_track_id = track['id']
                    self.sync_colors_to_lights(track)

                time.sleep(self.update_interval)

        except KeyboardInterrupt:
            logger.info("SpottyHue stopped. Lights remain in current state.")
        except Exception as e:
            logger.exception(f"Error in run loop: {e}")
            raise

    def sync_once(self):
        """Sync current track once (useful for testing)."""
        track = self.spotify.get_current_track()
        if track:
            self.sync_colors_to_lights(track)
        else:
            print("No track currently playing")
