#!/bin/bash
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"
echo "=========================================="
echo "   🎮 Launching Steam Presence GUI...     "
echo "=========================================="
echo "Opening interface. The window will appear on your screen."
echo ""
exec "$DIR/venv/bin/python" "$DIR/gui.py" "$@"
