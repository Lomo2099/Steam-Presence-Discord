#!/bin/bash
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"
echo "=========================================="
echo "   🎮 Launching Steam Presence GUI...     "
echo "=========================================="
exec "$DIR/venv/bin/python" "$DIR/gui.py" "$@"
