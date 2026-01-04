#!/bin/bash
# SpottyHue Setup Script

echo "================================================"
echo "SpottyHue Setup"
echo "================================================"
echo ""

# Check Python version
echo "Checking Python version..."
python3 --version
if [ $? -ne 0 ]; then
    echo "✗ Python 3 is required but not found"
    exit 1
fi

# Create virtual environment
if [ ! -d ".venv" ]; then
    echo ""
    echo "Creating virtual environment..."
    python3 -m venv .venv
    echo "✓ Virtual environment created"
else
    echo "✓ Virtual environment already exists"
fi

# Activate virtual environment
echo ""
echo "Activating virtual environment..."
source .venv/bin/activate

# Install dependencies
echo ""
echo "Installing dependencies..."
pip install -r requirements.txt

if [ $? -eq 0 ]; then
    echo ""
    echo "✓ Dependencies installed successfully!"
else
    echo ""
    echo "✗ Failed to install dependencies"
    exit 1
fi

# Check if .env exists
echo ""
if [ ! -f ".env" ]; then
    echo "⚠ No .env file found"
    echo "Please create one from .env.example and add your Spotify credentials"
else
    echo "✓ .env file exists"
fi

echo ""
echo "================================================"
echo "Setup Complete!"
echo "================================================"
echo ""
echo "Next steps:"
echo "1. Authenticate with Hue bridge (if not done):"
echo "   source .venv/bin/activate"
echo "   python scripts/hue_auth.py"
echo ""
echo "2. Get Spotify API credentials from:"
echo "   https://developer.spotify.com/dashboard"
echo ""
echo "3. Add them to your .env file:"
echo "   SPOTIFY_CLIENT_ID=your_id"
echo "   SPOTIFY_CLIENT_SECRET=your_secret"
echo "   SPOTIFY_REDIRECT_URI=http://127.0.0.1:8888/callback"
echo ""
echo "4. Start the web interface:"
echo "   source .venv/bin/activate"
echo "   python web_app.py"
echo ""
echo "5. Open browser to: http://localhost:5001"
echo ""
