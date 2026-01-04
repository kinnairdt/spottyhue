"""
Color Extractor
Extracts dominant colors from album artwork images.
"""

import requests
from io import BytesIO
from PIL import Image
from colorthief import ColorThief
from typing import List, Tuple
import tempfile


class ColorExtractor:
    """Extract dominant colors from images."""

    @staticmethod
    def extract_colors_from_url(image_url: str, num_colors: int = 3) -> List[Tuple[int, int, int]]:
        """
        Extract dominant colors from an image URL.

        Args:
            image_url: URL of the image
            num_colors: Number of colors to extract

        Returns:
            List of RGB tuples
        """
        try:
            # Download image
            response = requests.get(image_url, timeout=10)
            response.raise_for_status()

            # Save to temporary file (ColorThief requires a file path)
            with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as tmp_file:
                tmp_file.write(response.content)
                tmp_path = tmp_file.name

            # Extract colors
            color_thief = ColorThief(tmp_path)

            if num_colors == 1:
                # Get single dominant color
                color = color_thief.get_color(quality=1)
                return [color]
            else:
                # Get color palette
                palette = color_thief.get_palette(color_count=num_colors, quality=1)
                return palette

        except Exception as e:
            print(f"Error extracting colors: {e}")
            # Return default colors if extraction fails
            return [(255, 0, 0), (0, 255, 0), (0, 0, 255)][:num_colors]

    @staticmethod
    def extract_colors_advanced(image_url: str, num_colors: int = 3) -> List[Tuple[int, int, int]]:
        """
        Extract colors using k-means clustering with Pillow.
        Alternative method if ColorThief doesn't work well.

        Args:
            image_url: URL of the image
            num_colors: Number of colors to extract

        Returns:
            List of RGB tuples
        """
        try:
            # Download image
            response = requests.get(image_url, timeout=10)
            response.raise_for_status()

            # Load image
            img = Image.open(BytesIO(response.content))

            # Resize for faster processing
            img = img.resize((150, 150))

            # Convert to RGB if needed
            if img.mode != 'RGB':
                img = img.convert('RGB')

            # Get colors using quantize
            img_quantized = img.quantize(colors=num_colors)
            palette = img_quantized.getpalette()

            # Extract RGB values
            colors = []
            for i in range(num_colors):
                r = palette[i * 3]
                g = palette[i * 3 + 1]
                b = palette[i * 3 + 2]
                colors.append((r, g, b))

            return colors

        except Exception as e:
            print(f"Error in advanced extraction: {e}")
            return [(255, 0, 0), (0, 255, 0), (0, 0, 255)][:num_colors]

    @staticmethod
    def filter_colors(colors: List[Tuple[int, int, int]],
                     min_brightness: int = 30,
                     max_brightness: int = 230) -> List[Tuple[int, int, int]]:
        """
        Filter out colors that are too dark or too bright.

        Args:
            colors: List of RGB tuples
            min_brightness: Minimum brightness (0-255)
            max_brightness: Maximum brightness (0-255)

        Returns:
            Filtered list of colors
        """
        filtered = []
        for r, g, b in colors:
            # Calculate brightness
            brightness = (r + g + b) / 3
            if min_brightness <= brightness <= max_brightness:
                filtered.append((r, g, b))

        # If all colors filtered out, return original
        return filtered if filtered else colors

    @staticmethod
    def boost_saturation(rgb: Tuple[int, int, int], factor: float = 1.3) -> Tuple[int, int, int]:
        """
        Boost color saturation to make colors more vibrant.

        Args:
            rgb: RGB tuple
            factor: Saturation boost factor (>1 increases saturation)

        Returns:
            Boosted RGB tuple
        """
        r, g, b = rgb

        # Convert to HSV
        r_norm, g_norm, b_norm = r / 255.0, g / 255.0, b / 255.0
        max_val = max(r_norm, g_norm, b_norm)
        min_val = min(r_norm, g_norm, b_norm)
        diff = max_val - min_val

        # Calculate saturation
        s = 0 if max_val == 0 else diff / max_val

        # Boost saturation
        s = min(1.0, s * factor)

        # Convert back to RGB
        if diff == 0:
            return rgb  # Gray color, no change

        if max_val == r_norm:
            h = ((g_norm - b_norm) / diff) % 6
        elif max_val == g_norm:
            h = ((b_norm - r_norm) / diff) + 2
        else:
            h = ((r_norm - g_norm) / diff) + 4

        h = h / 6.0

        # HSV to RGB
        def hue_to_rgb(p, q, t):
            if t < 0: t += 1
            if t > 1: t -= 1
            if t < 1/6: return p + (q - p) * 6 * t
            if t < 1/2: return q
            if t < 2/3: return p + (q - p) * (2/3 - t) * 6
            return p

        if s == 0:
            r = g = b = max_val
        else:
            q = max_val * (1 + s) if max_val < 0.5 else max_val + s - max_val * s
            p = 2 * max_val - q
            r = hue_to_rgb(p, q, h + 1/3)
            g = hue_to_rgb(p, q, h)
            b = hue_to_rgb(p, q, h - 1/3)

        return (int(r * 255), int(g * 255), int(b * 255))
