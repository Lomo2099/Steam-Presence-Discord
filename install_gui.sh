#!/bin/bash
# ==============================================================================
# Steam Presence GUI - Installer & Environment Setup
# Installs all required modules, sets up venv, prepares config and launchers
# ==============================================================================

set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

echo "============================================================"
echo "    🎮 Steam Presence GUI - Setup & Installation Wizard     "
echo "============================================================"
echo ""

# 1. Check Python 3
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: python3 is not installed on this system."
    echo "Please install Python 3.8+ before continuing."
    exit 1
fi

PYTHON_VERSION=$(python3 --version 2>&1)
echo "✓ Found Python: $PYTHON_VERSION"

# 2. Check Tkinter
echo "Checking GUI support (tkinter)..."
if ! python3 -c "import tkinter" &> /dev/null; then
    echo "❌ Warning: tkinter module is missing from Python3."
    if [[ "$OSTYPE" == "darwin"* ]]; then
        echo "On macOS, reinstall official Python from python.org or run: brew install python-tk"
    else
        echo "On Linux/Ubuntu/Debian, install with: sudo apt install python3-tk"
        echo "On Fedora: sudo dnf install python3-tkinter"
        echo "On Arch: sudo pacman -S tk"
    fi
    exit 1
fi
echo "✓ Tkinter GUI support is available."

# 3. Create or Update Virtual Environment
echo ""
echo "Setting up virtual environment in $DIR/venv..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "✓ Virtual environment created."
else
    echo "✓ Existing virtual environment found."
fi

# 4. Upgrade pip and wheel
echo "Upgrading pip & wheel inside virtual environment..."
./venv/bin/python -m pip install --upgrade pip wheel --quiet
echo "✓ pip and wheel upgraded."

# 5. Install all required dependencies
echo ""
echo "Installing required modules beforehand from requirements.txt..."
./venv/bin/python -m pip install -r requirements.txt --quiet
echo "✓ All modules installed successfully."

# 6. Verify Imports
echo ""
echo "Verifying module imports..."
./venv/bin/python -c "
import requests
import pypresence
import steamgrid
import bs4
import psutil
import PIL
import tkinter
print('✓ Verified all modules: requests, pypresence, steamgrid, bs4, psutil, PIL, tkinter')
"

# 7. Check existing config.json beforehand
echo ""
if [ -f "config.json" ]; then
    echo "✓ Found existing config.json! Your previous data is preserved and will be loaded automatically."
else
    echo "Creating initial config.json template..."
    cat <<EOF > config.json
{
    "STEAM_API_KEY": "",
    "USER_IDS": "",
    "DISCORD_APPLICATION_ID": "869994714093465680",
    "FETCH_STEAM_RICH_PRESENCE": true,
    "FETCH_STEAM_REVIEWS": false,
    "ADD_STEAM_STORE_BUTTON": true,
    "STEAM_STORE_REGION": "us",
    "WEB_SCRAPE": false,
    "COVER_ART": {
        "STEAM_GRID_DB": {
            "ENABLED": false,
            "STEAM_GRID_API_KEY": ""
        },
        "USE_STEAM_STORE_FALLBACK": true
    },
    "LOCAL_GAMES": {
        "ENABLED": false,
        "LOCAL_DISCORD_APPLICATION_ID": "1062648118375616594",
        "GAMES": []
    },
    "GAME_OVERWRITE": {
        "ENABLED": false,
        "NAME": "",
        "SECONDS_SINCE_START": 0
    },
    "CUSTOM_ICON": {
        "ENABLED": false,
        "URL": "https://raw.githubusercontent.com/JustTemmie/steam-presence/main/readmeimages/defaulticon.png",
        "TEXT": "Steam Presence on Discord"
    },
    "BLACKLIST": [],
    "WHITELIST": []
}
EOF
    echo "✓ Default config.json created."
fi

# 8. Ensure data directory & support files exist
mkdir -p data
[ ! -f "data/games.txt" ] && touch data/games.txt
[ ! -f "data/icons.txt" ] && touch data/icons.txt
[ ! -f "data/customGameIDs.json" ] && echo "{}" > data/customGameIDs.json
[ ! -f "data/meta.json" ] && echo '{"structure-version": "1"}' > data/meta.json
echo "✓ Data directory and cache files initialized."

# 9. Create convenient launcher scripts
cat <<'EOF' > launch_gui.sh
#!/bin/bash
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"
exec "$DIR/venv/bin/python" "$DIR/gui.py" "$@"
EOF
chmod +x launch_gui.sh

# macOS Double-Clickable Finder Launcher
if [[ "$OSTYPE" == "darwin"* ]]; then
    cat <<'EOF' > "Steam Presence.command"
#!/bin/bash
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"
exec "$DIR/venv/bin/python" "$DIR/gui.py"
EOF
    chmod +x "Steam Presence.command"
    echo "✓ Created macOS double-clickable app launcher: 'Steam Presence.command'"
fi

echo "✓ Created command-line launcher: './launch_gui.sh'"

echo ""
echo "============================================================"
echo "          🎉 Installation Completed Successfully!           "
echo "============================================================"
echo "You can launch the Steam Presence GUI anytime using:"
echo "  • Terminal:  ./launch_gui.sh"
if [[ "$OSTYPE" == "darwin"* ]]; then
echo "  • Finder:    Double-click 'Steam Presence.command'"
fi
echo "============================================================"
echo ""

# Launch option
if [ -t 0 ]; then
    read -p "Would you like to launch the Steam Presence GUI now? (y/n) " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        ./launch_gui.sh
    fi
fi

