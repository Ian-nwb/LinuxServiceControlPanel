#!/usr/bin/env bash
# Usage: ./setup-dbcontrol-gui.sh
set -uo pipefail

G='\033[0;32m'; Y='\033[1;33m'; C='\033[0;36m'; B='\033[1m'; N='\033[0m'

echo -e "${C}"
cat << 'EOF'
  ____  ____    ____            _             _
 |  _ \| __ )  / ___|___  _ __ | |_ _ __ ___ | |
 | | | |  _ \ | |   / _ \| '_ \| __| '__/ _ \| |
 | |_| | |_) || |__| (_) | | | | |_| | | (_) | |
 |____/|____/  \____\___/|_| |_|\__|_|  \___/|_|
EOF
echo -e "${N}${B}          installing as a desktop app${N}\n"

SRC="$(dirname "$(readlink -f "$0")")/dbcontrol-gui.py"
BIN_DIR="$HOME/.local/bin"
APP_DIR="$HOME/.local/share/applications"

if [ ! -f "$SRC" ]; then
  echo "dbcontrol-gui.py not found next to this script. Put both files in the same folder."
  exit 1
fi

if ! python3 -c "import tkinter" >/dev/null 2>&1; then
  echo -e "${Y}python3-tk missing, installing...${N}"
  sudo apt install -y python3-tk
fi

mkdir -p "$BIN_DIR" "$APP_DIR"
cp "$SRC" "$BIN_DIR/dbcontrol-gui.py"
chmod +x "$BIN_DIR/dbcontrol-gui.py"

cat > "$APP_DIR/dbcontrol.desktop" << EOF2
[Desktop Entry]
Type=Application
Name=Service Control Panel
Comment=Start/stop MySQL, PostgreSQL, MongoDB, Redis, Docker, Nginx
Exec=python3 $BIN_DIR/dbcontrol-gui.py
Icon=applications-system
Terminal=false
Categories=Development;Utility;
EOF2

chmod +x "$APP_DIR/dbcontrol.desktop"
update-desktop-database "$APP_DIR" 2>/dev/null || true

echo -e "${G}✓ installed.${N} Search \"Service Control Panel\" in your app menu, or run:"
echo -e "  ${B}python3 $BIN_DIR/dbcontrol-gui.py${N}"
echo
echo -e "${Y}note:${N} Start/Stop/Restart trigger a pkexec auth popup (needs root for systemctl)."
echo -e "${Y}note:${N} Logs use journalctl — no extra permissions needed to read them."
