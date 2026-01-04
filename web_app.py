#!/usr/bin/env python3
"""
SpottyHue Web Interface
Modern web UI for controlling Spotify to Hue light sync.
"""

import os
import threading
import time
import secrets
import logging
from typing import Dict, List, Optional
from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
from dotenv import load_dotenv
from werkzeug.middleware.proxy_fix import ProxyFix

from src.spotify_client import SpotifyClient
from src.hue_controller import HueController
from src.spottyhue import SpottyHue

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__,
            template_folder='web/templates',
            static_folder='web/static')

# Production security settings
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', secrets.token_hex(32))
app.config['SESSION_COOKIE_SECURE'] = os.getenv('SESSION_COOKIE_SECURE', 'False').lower() == 'true'
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['PERMANENT_SESSION_LIFETIME'] = 3600  # 1 hour
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max request size
app.config['JSON_SORT_KEYS'] = False

# Disable debug mode in production
DEBUG_MODE = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'

# CORS configuration - restrict in production
if os.getenv('FLASK_ENV') == 'production':
    CORS(app, resources={
        r"/api/*": {
            "origins": os.getenv('ALLOWED_ORIGINS', 'http://localhost:5001').split(','),
            "methods": ["GET", "POST"],
            "allow_headers": ["Content-Type"]
        }
    })
else:
    CORS(app)

# Handle proxy headers if behind reverse proxy
if os.getenv('BEHIND_PROXY', 'False').lower() == 'true':
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)


class SyncManager:
    """Manages the synchronization state and background thread."""

    def __init__(self):
        self.active = False
        self.thread: Optional[threading.Thread] = None
        self.spotify_client: Optional[SpotifyClient] = None
        self.hue_controller: Optional[HueController] = None
        self.spottyhue_app: Optional[SpottyHue] = None
        
        self.current_config = {
            'light_ids': [int(x) for x in os.getenv('HUE_LIGHT_IDS', '11,12,13').split(',')],
            'num_colors': int(os.getenv('NUM_COLORS', '3')),
            'update_interval': int(os.getenv('UPDATE_INTERVAL', '2')),
            'brightness': int(os.getenv('BRIGHTNESS', '254'))
        }
        
        # State visible to API
        self.current_track_info = None

    def initialize_clients(self):
        """Initialize Spotify and Hue clients."""
        if not self.spotify_client:
            self.spotify_client = SpotifyClient(
                client_id=os.getenv('SPOTIFY_CLIENT_ID'),
                client_secret=os.getenv('SPOTIFY_CLIENT_SECRET'),
                redirect_uri=os.getenv('SPOTIFY_REDIRECT_URI')
            )

        if not self.hue_controller:
            self.hue_controller = HueController(
                bridge_ip=os.getenv('HUE_BRIDGE_IP'),
                username=os.getenv('HUE_USERNAME')
            )

        return self.spotify_client, self.hue_controller

    def get_spottyhue_app(self) -> SpottyHue:
        """Create or return existing SpottyHue instance."""
        self.initialize_clients()
        
        if not self.spottyhue_app:
            self.spottyhue_app = SpottyHue(
                spotify_client=self.spotify_client,
                hue_controller=self.hue_controller,
                light_ids=self.current_config['light_ids'],
                num_colors=self.current_config['num_colors'],
                update_interval=self.current_config['update_interval'],
                brightness=self.current_config['brightness']
            )
        else:
            # Update mutable config
            self.spottyhue_app.light_ids = self.current_config['light_ids']
            self.spottyhue_app.num_colors = min(self.current_config['num_colors'], len(self.current_config['light_ids']))
            self.spottyhue_app.update_interval = self.current_config['update_interval']
            self.spottyhue_app.brightness = self.current_config['brightness']
            
        return self.spottyhue_app

    def start_sync(self):
        """Start the sync process in a background thread."""
        if self.active:
            return False, "Sync already running"

        try:
            self.get_spottyhue_app() # Ensure app is ready
            self.active = True
            self.thread = threading.Thread(target=self._sync_loop, daemon=True)
            self.thread.start()
            logger.info("Sync started")
            return True, "Sync started"
        except Exception as e:
            logger.exception("Failed to start sync")
            return False, str(e)

    def stop_sync(self):
        """Stop the sync process."""
        if not self.active:
            return False, "Sync not running"
        
        self.active = False
        self.current_track_info = None
        logger.info("Sync stopped")
        return True, "Sync stopped"

    def _sync_loop(self):
        """Background loop."""
        current_track_id = None
        
        logger.info("Entering sync loop")
        
        while self.active:
            try:
                # Use the spottyhue app methods
                app_instance = self.get_spottyhue_app()
                
                track = self.spotify_client.get_current_track()

                if track and track['id'] != current_track_id:
                    current_track_id = track['id']
                    self.current_track_info = track
                    
                    # This now handles color extraction, state update, and light update internally
                    app_instance.sync_colors_to_lights(track)
                    logger.info(f"Synced: {track['name']}")

                time.sleep(self.current_config['update_interval'])

            except Exception as e:
                logger.error(f"Sync error: {e}")
                time.sleep(5)

    def get_status(self):
        """Get current status including colors from SpottyHue instance."""
        colors = []
        if self.spottyhue_app:
            colors = self.spottyhue_app.current_colors
            
        return {
            'active': self.active,
            'config': self.current_config,
            'current_track': self.current_track_info,
            'current_colors': colors
        }
        
    def get_light_color(self, light_id: int):
        """Get current color for a light from SpottyHue instance."""
        if self.spottyhue_app and light_id in self.spottyhue_app.light_colors:
            return self.spottyhue_app.light_colors[light_id]
        return None


# Global SyncManager Instance
sync_manager = SyncManager()


# Security headers
@app.after_request
def set_security_headers(response):
    """Add security headers to all responses."""
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    response.headers['Content-Security-Policy'] = (
        "default-src 'self'; "
        "script-src 'self' https://cdn.tailwindcss.com 'unsafe-inline'; "
        "style-src 'self' https://fonts.googleapis.com 'unsafe-inline'; "
        "font-src 'self' https://fonts.gstatic.com; "
        "img-src 'self' data: https:; "
        "connect-src 'self'"
    )
    return response


@app.route('/')
def index():
    """Serve the main web interface."""
    return render_template('index.html')


@app.route('/api/status')
def get_status():
    """Get current sync status."""
    return jsonify(sync_manager.get_status())


@app.route('/api/lights')
def get_lights():
    """Get all available Hue lights."""
    try:
        spotify, hue = sync_manager.initialize_clients()
        lights = hue.get_lights()

        # Format light data
        lights_list = []
        for light_id, light in lights.items():
            light_data = {
                'id': int(light_id),
                'name': light.get('name'),
                'type': light.get('type'),
                'on': light.get('state', {}).get('on'),
                'reachable': light.get('state', {}).get('reachable'),
                'color_capable': 'color' in light.get('type', '').lower()
            }

            # Add current color if available
            current_rgb = sync_manager.get_light_color(int(light_id))
            if current_rgb:
                light_data['current_color'] = current_rgb

            lights_list.append(light_data)

        return jsonify(lights_list)
    except Exception as e:
        logger.error(f"Error getting lights: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/groups')
def get_groups():
    """Get all Hue groups (rooms/zones)."""
    try:
        spotify, hue = sync_manager.initialize_clients()
        groups = hue.get_groups()

        # Format group data
        groups_list = []
        for group_id, group in groups.items():
            # Skip group 0 (all lights)
            if group_id == '0':
                continue

            group_data = {
                'id': int(group_id),
                'name': group.get('name'),
                'type': group.get('type'),
                'lights': [int(light_id) for light_id in group.get('lights', [])],
                'class': group.get('class', ''),
            }

            groups_list.append(group_data)

        return jsonify(groups_list)
    except Exception as e:
        logger.error(f"Error getting groups: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/start', methods=['POST'])
def start_sync():
    """Start the Spotify sync."""
    # Get config from request if provided
    data = request.get_json() or {}
    
    if 'light_ids' in data:
        sync_manager.current_config['light_ids'] = data['light_ids']
    if 'num_colors' in data:
        sync_manager.current_config['num_colors'] = data['num_colors']
    if 'update_interval' in data:
        sync_manager.current_config['update_interval'] = data['update_interval']
    if 'brightness' in data:
        sync_manager.current_config['brightness'] = data['brightness']

    success, message = sync_manager.start_sync()
    
    if success:
        return jsonify({
            'message': message,
            'config': sync_manager.current_config
        })
    else:
        # If it's already running, it's not a 500 error, but we return the message
        return jsonify({'message': message})


@app.route('/api/stop', methods=['POST'])
def stop_sync():
    """Stop the Spotify sync."""
    success, message = sync_manager.stop_sync()
    return jsonify({'message': message})


@app.route('/api/config', methods=['POST'])
def update_config():
    """Update sync configuration."""
    data = request.get_json()
    
    config = sync_manager.current_config

    if 'light_ids' in data:
        config['light_ids'] = data['light_ids']

    if 'num_colors' in data:
        config['num_colors'] = data['num_colors']

    if 'update_interval' in data:
        config['update_interval'] = data['update_interval']

    if 'brightness' in data:
        config['brightness'] = data['brightness']
        
    # If active, trigger update in app instance
    if sync_manager.active:
        sync_manager.get_spottyhue_app() # This triggers the update logic inside getter

    return jsonify({
        'message': 'Configuration updated',
        'config': config
    })


@app.route('/api/test-connection')
def test_connection():
    """Test Spotify and Hue connections."""
    try:
        spotify, hue = sync_manager.initialize_clients()

        spotify_ok = spotify.test_connection()
        hue_ok = hue.test_connection()

        return jsonify({
            'spotify': spotify_ok,
            'hue': hue_ok
        })
    except Exception as e:
        logger.error(f"Connection test failed: {e}")
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    print("=" * 60)
    print("SpottyHue Web Interface")
    print("=" * 60)

    if DEBUG_MODE:
        print("\n⚠️  WARNING: Running in DEBUG mode - not suitable for production!")
    else:
        print("\n✓ Running in production mode")

    port = int(os.getenv('PORT', 5001))
    host = os.getenv('HOST', '0.0.0.0')

    print(f"\nStarting web server on {host}:{port}...")
    print(f"Open your browser to: http://localhost:{port}")
    print("\nPress Ctrl+C to stop\n")

    # Production: Use waitress or gunicorn
    # Development: Use Flask dev server
    if not DEBUG_MODE and os.getenv('USE_WAITRESS', 'False').lower() == 'true':
        try:
            from waitress import serve
            print("Using Waitress production server")
            serve(app, host=host, port=port, threads=4)
        except ImportError:
            print("⚠️  Waitress not installed. Install with: pip install waitress")
            print("Falling back to Flask development server (not recommended for production)")
            app.run(debug=False, host=host, port=port, threaded=True)
    else:
        app.run(debug=DEBUG_MODE, host=host, port=port, threaded=True)
