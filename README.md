# SpottyHue 🎵💡

Sync your Spotify album artwork colors to your Philips Hue lights in real-time

Vibecoded in an hour because i didnt find anything better. 
Will it work for you...maybe...
It works for me, so raise a PR with changes if it breaks for you. 

There are 1001 ways this could be better but it just works and that is good enough for me at the moment. 

![SpottyHue](https://img.shields.io/badge/Python-3.11+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![Docker](https://img.shields.io/badge/docker-ready-blue.svg)

## What It Does

SpottyHue monitors your Spotify playback and automatically extracts dominant colors from the currently playing song's album artwork, then applies those colors to your Philips Hue lights. Each light gets a different color from the album art, creating an immersive, dynamic listening experience that changes with every track.

## ✨ Features

### New Minimalist Web Interface
- 🎨 **Focus on Music** - A clean, mobile-first design centered around the album art.
- 📱 **Adaptive UI** - The background gradient smoothly shifts to match the current track's colors.
- 🚦 **Single Button Control** - A prominent "Play/Pause" button floating on the album art toggles the sync.
- 🎨 **Palette Visualization** - See exactly which colors have been extracted from the artwork.
- ⚙️ **Smart Settings Drawer** - All configuration is tucked away in a slide-up modal to reduce clutter.

### Advanced Light Control
- 🏠 **Group Support** - Select entire rooms (Living Room, Bedroom) with one click.
- 💡 **Individual Light Control** - Granular control to pick specific bulbs for syncing.
- 🔄 **Smart Auto-Switching** - Automatically detects if you have Groups; if not, falls back to individual lights.
- ⚡ **Optimistic UI** - Interface updates instantly for a snappy feel.

### Core Architecture
- 🧩 **Modular Design** - Clean separation between Spotify, Hue, and Color extraction logic.
- 🐳 **Docker Optimized** - Runs in a single optimized container with threaded workers for stability.
- 🔒 **Secure** - Production-ready security headers, CORS policies, and environment variable configuration.

## 🚀 Quick Start (Docker - Recommended)

The easiest way to run SpottyHue is using Docker Compose.

**Prerequisites:**
- Docker and Docker Compose installed
- Philips Hue Bridge on your network
- Spotify Premium account

**Steps:**

1. **Clone the repository:**
   ```bash
   git clone https://github.com/yourusername/spottyhue.git
   cd spottyhue
   ```

2. **Configure Environment:**
   Create a `.env` file (copy from `.env.example`):
   ```bash
   cp .env.example .env
   ```
   Edit `.env` with your credentials:
   ```env
   # Hue Bridge IP (Find in Hue App -> Settings -> Hue Bridges -> (i))
   HUE_BRIDGE_IP=192.168.1.X
   # Hue Username (Run scripts/hue_auth.py first if you don't have one)
   HUE_USERNAME=your_hue_username

   # Spotify API (https://developer.spotify.com/dashboard)
   SPOTIFY_CLIENT_ID=your_client_id
   SPOTIFY_CLIENT_SECRET=your_client_secret
   SPOTIFY_REDIRECT_URI=http://localhost:8888/callback
   ```

3. **Run with Docker:**
   ```bash
   docker-compose up -d --build
   ```

4. **Access the UI:**
   Open **http://localhost:5001** in your browser.

## 📱 Using the App

1. **Start Syncing:** Click the large Play button on the album art.
2. **Configure Lights:**
   - Click the **"Configure Lights"** button at the bottom.
   - Switch between **Groups** (Rooms) or **Lights** tabs.
   - Tap items to toggle them for sync (selected items turn white).
3. **Adjust Settings:**
   - **Brightness:** Master brightness for all synced lights.
   - **Color Count:** How many dominant colors to extract (1-5).
   - **Update Speed:** How often to check for track changes (default: 2s).

## 🔧 Architecture & Troubleshooting

### System Architecture
The application uses a **Flask** backend with a background `SyncManager` thread.
- **Frontend:** Vanilla JS + Tailwind CSS (no build step required).
- **Backend:** Python 3.11, Flask, Spotipy, Hue API.
- **Deployment:** Gunicorn server configured with single-worker/multi-thread mode to ensure state consistency across requests.

### Common Issues

**"No groups/lights found"**
- Ensure your Hue Bridge IP and Username are correct in `.env`.
- Ensure the container is on the same network as the Bridge (Docker `network_mode: bridge` is default, but `host` mode may be needed for discovery on some setups).

**UI says "Stopped" but lights are changing**
- This was a bug in older versions using multiple Gunicorn workers. Ensure you are using the latest `Dockerfile` which enforces `--workers 1 --threads 8`.

**"Failed to connect to Spotify"**
- Check that your `SPOTIFY_REDIRECT_URI` matches exactly what is in your Spotify Developer Dashboard.
- The first run requires a browser-based OAuth flow. Check the container logs (`docker-compose logs -f`) for the auth URL if it doesn't open automatically.

## 🛠 Manual Installation (Python)

If you prefer running without Docker:

1. **Install Dependencies:**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Authenticate Hue Bridge:**
   ```bash
   python scripts/hue_auth.py
   # Press the link button on your bridge when prompted
   ```

3. **Run the Server:**
   ```bash
   python web_app.py
   ```

## 📝 License

MIT License. Built with ❤️ for music lovers.