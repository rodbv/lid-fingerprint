#!/usr/bin/env bash
# Removes the tray indicator and returns PAM to the base profile, fingerprint off.
set -euo pipefail
cd "$(dirname "$0")"

BIN=$HOME/.local/bin/fingerprint-tray
ICON_DIR=$HOME/.local/share/icons/hicolor/scalable/status
AUTOSTART=$HOME/.config/autostart/fingerprint-tray.desktop

pkill -f "python3 $BIN" || true
rm -f -- "$BIN" "$AUTOSTART" "$ICON_DIR"/fprint-lid-open-symbolic.svg "$ICON_DIR"/fprint-lid-closed-symbolic.svg

sudo ./pam-setup uninstall
