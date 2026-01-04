"""
Philips Hue Controller
Handles communication with Hue Bridge and color conversions.
"""

import requests
import json
from typing import List, Tuple, Optional
import urllib3

# Disable SSL warnings for self-signed Hue bridge certificate
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class HueController:
    """Controller for Philips Hue lights."""

    def __init__(self, bridge_ip: str, username: str):
        """
        Initialize Hue controller.

        Args:
            bridge_ip: IP address of Hue bridge
            username: Authenticated username/API key
        """
        self.bridge_ip = bridge_ip
        self.username = username
        self.base_url = f"https://{bridge_ip}/api/{username}"

    def get_lights(self) -> dict:
        """Get all lights from the bridge."""
        response = requests.get(f"{self.base_url}/lights", verify=False, timeout=5)
        return response.json()

    def get_light(self, light_id: int) -> dict:
        """Get specific light info."""
        response = requests.get(f"{self.base_url}/lights/{light_id}", verify=False, timeout=5)
        return response.json()

    def get_groups(self) -> dict:
        """Get all groups (rooms/zones) from the bridge."""
        response = requests.get(f"{self.base_url}/groups", verify=False, timeout=5)
        return response.json()

    def set_color(self, light_id: int, rgb: Tuple[int, int, int], brightness: int = 254, transition_time: int = 10):
        """
        Set light to RGB color.

        Args:
            light_id: Light ID to control
            rgb: Tuple of (r, g, b) values (0-255)
            brightness: Brightness (0-254)
            transition_time: Transition time in deciseconds (10 = 1 second)
        """
        # Convert RGB to XY color space
        xy = self.rgb_to_xy(rgb)

        state = {
            "on": True,
            "xy": xy,
            "bri": brightness,
            "transitiontime": transition_time
        }

        response = requests.put(
            f"{self.base_url}/lights/{light_id}/state",
            json=state,
            verify=False,
            timeout=5
        )
        return response.json()

    def set_multiple_colors(self, light_colors: dict, brightness: int = 254, transition_time: int = 10):
        """
        Set multiple lights to different colors.

        Args:
            light_colors: Dict of {light_id: (r, g, b)}
            brightness: Brightness (0-254)
            transition_time: Transition time in deciseconds
        """
        results = {}
        for light_id, rgb in light_colors.items():
            results[light_id] = self.set_color(light_id, rgb, brightness, transition_time)
        return results

    def turn_off(self, light_id: int):
        """Turn off a light."""
        state = {"on": False}
        response = requests.put(
            f"{self.base_url}/lights/{light_id}/state",
            json=state,
            verify=False,
            timeout=5
        )
        return response.json()

    @staticmethod
    def rgb_to_xy(rgb: Tuple[int, int, int]) -> List[float]:
        """
        Convert RGB to XY color space for Hue lights.
        Uses the Philips Hue color conversion formula.

        Args:
            rgb: Tuple of (r, g, b) values (0-255)

        Returns:
            List of [x, y] coordinates
        """
        # Normalize RGB values to 0-1
        r, g, b = [x / 255.0 for x in rgb]

        # Apply gamma correction
        r = ((r + 0.055) / 1.055) ** 2.4 if r > 0.04045 else r / 12.92
        g = ((g + 0.055) / 1.055) ** 2.4 if g > 0.04045 else g / 12.92
        b = ((b + 0.055) / 1.055) ** 2.4 if b > 0.04045 else b / 12.92

        # Convert to XYZ using Wide RGB D65 conversion
        X = r * 0.664511 + g * 0.154324 + b * 0.162028
        Y = r * 0.283881 + g * 0.668433 + b * 0.047685
        Z = r * 0.000088 + g * 0.072310 + b * 0.986039

        # Calculate xy coordinates
        total = X + Y + Z
        if total == 0:
            return [0.0, 0.0]

        x = X / total
        y = Y / total

        # Clamp to valid range
        x = max(0.0, min(1.0, x))
        y = max(0.0, min(1.0, y))

        return [round(x, 4), round(y, 4)]

    def test_connection(self) -> bool:
        """Test if connection to bridge is working."""
        try:
            lights = self.get_lights()
            return isinstance(lights, dict) and len(lights) > 0
        except Exception as e:
            print(f"Connection test failed: {e}")
            return False
