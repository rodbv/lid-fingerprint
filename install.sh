#!/usr/bin/env bash
# Installs the tray indicator for the current user, then the PAM profile with sudo.
set -euo pipefail
cd "$(dirname "$0")"

BIN=$HOME/.local/bin/fingerprint-tray
ICON_DIR=$HOME/.local/share/icons/hicolor/scalable/status
AUTOSTART=$HOME/.config/autostart/fingerprint-tray.desktop

rpm -q fprintd-pam python3-pyqt6 >/dev/null ||
    { echo "Install the requirements first: sudo dnf install fprintd-pam python3-pyqt6" >&2; exit 1; }

install -Dm755 src/fingerprint_tray.py "$BIN"
install -Dm644 -t "$ICON_DIR" data/icons/*.svg
mkdir -p "$(dirname "$AUTOSTART")"
sed "s|@BIN@|$BIN|" data/fingerprint-tray.desktop.in >"$AUTOSTART"

sudo ./pam-setup install

pkill -f "python3 $BIN" || true
setsid -f "$BIN" >/dev/null 2>&1

enrolled=$(fprintd-list "$USER" 2>&1 || true)
if [[ $enrolled == *"no fingers enrolled"* ]]; then
    echo "No finger enrolled yet. Run: fprintd-enroll"
fi
echo "Done. The tray icon starts at every login."
