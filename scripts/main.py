#!/usr/bin/env python3
"""
SpottyHue - Main Entry Point
Sync Spotify album artwork colors to Philips Hue lights.
"""

import os
import sys
from dotenv import load_dotenv
from src.spotify_client import SpotifyClient
from src.hue_controller import HueController
from src.spottyhue import SpottyHue


def load_config():
    """Load configuration from .env file."""
    load_dotenv()

    config = {
        # Hue configuration
        'hue_bridge_ip': os.getenv('HUE_BRIDGE_IP'),
        'hue_username': os.getenv('HUE_USERNAME'),

        # Spotify configuration
        'spotify_client_id': os.getenv('SPOTIFY_CLIENT_ID'),
        'spotify_client_secret': os.getenv('SPOTIFY_CLIENT_SECRET'),
        'spotify_redirect_uri': os.getenv('SPOTIFY_REDIRECT_URI', 'http://localhost:8888/callback'),

        # App settings
        'hue_light_ids': os.getenv('HUE_LIGHT_IDS', '11,12,13'),
        'update_interval': int(os.getenv('UPDATE_INTERVAL', '2')),
        'num_colors': int(os.getenv('NUM_COLORS', '3'))
    }

    # Validate required config
    required = ['hue_bridge_ip', 'hue_username', 'spotify_client_id', 'spotify_client_secret']
    missing = [key for key in required if not config.get(key)]

    if missing:
        print("✗ Missing required configuration:")
        for key in missing:
            print(f"  - {key.upper()}")
        print("\nPlease set these in your .env file.")
        print("See .env.example for reference.")
        sys.exit(1)

    # Parse light IDs
    config['hue_light_ids'] = [int(x.strip()) for x in config['hue_light_ids'].split(',')]

    return config


def main():
    """Main entry point."""
    print("Loading configuration...")
    config = load_config()

    print("Initializing Spotify client...")
    spotify = SpotifyClient(
        client_id=config['spotify_client_id'],
        client_secret=config['spotify_client_secret'],
        redirect_uri=config['spotify_redirect_uri']
    )

    print("Initializing Hue controller...")
    hue = HueController(
        bridge_ip=config['hue_bridge_ip'],
        username=config['hue_username']
    )

    print("Starting SpottyHue...\n")
    app = SpottyHue(
        spotify_client=spotify,
        hue_controller=hue,
        light_ids=config['hue_light_ids'],
        num_colors=config['num_colors'],
        update_interval=config['update_interval']
    )

    # Run the app
    app.run()


if __name__ == "__main__":
    main()
