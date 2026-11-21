#!/usr/bin/python3
"""Tray icon that shows whether sudo and the lock screen accept the fingerprint."""

import sys
from pathlib import Path

LID_DIR = Path("/proc/acpi/button/lid")
PAM_SYSTEM_AUTH = Path("/etc/pam.d/system-auth")
POLL_MS = 2000

# Icon names, not pixmaps: plasmashell resolves them in the panel's own theme and colors.
ICONS = {
    "on": ("fprint-lid-open-symbolic", "Fingerprint on: lid open"),
    "off": ("fprint-lid-closed-symbolic", "Fingerprint off: lid closed, password only"),
    "unconfigured": (
        "action-unavailable-symbolic",
        "Fingerprint: PAM has no lid check (run pam-setup install)",
    ),
}


def find_lid_state(lid_dir: Path = LID_DIR) -> Path | None:
    return next(iter(sorted(lid_dir.glob("*/state"))), None)


def fingerprint_state(lid_state: Path | None, pam_system_auth: Path = PAM_SYSTEM_AUTH) -> str:
    try:
        pam = pam_system_auth.read_text()
    except OSError:
        return "unconfigured"
    if lid_state is None or str(lid_state) not in pam or "pam_fprintd.so" not in pam:
        return "unconfigured"
    try:
        lid = lid_state.read_text()
    except OSError:
        return "unconfigured"
    return "on" if "open" in lid else "off"


def main() -> None:
    # Qt stays out of module scope so the tests run without PyQt6.
    from PyQt6.QtCore import QTimer
    from PyQt6.QtGui import QAction, QIcon
    from PyQt6.QtWidgets import QApplication, QMenu, QSystemTrayIcon

    app = QApplication(sys.argv)
    app.setApplicationName("Fingerprint lid")
    app.setQuitOnLastWindowClosed(False)

    tray = QSystemTrayIcon()
    menu = QMenu()
    quit_action = QAction("Quit", menu)
    quit_action.triggered.connect(app.quit)
    menu.addAction(quit_action)
    tray.setContextMenu(menu)

    lid_state = find_lid_state()
    shown = None

    def refresh() -> None:
        nonlocal shown
        state = fingerprint_state(lid_state)
        if state != shown:
            icon_name, tooltip = ICONS[state]
            tray.setIcon(QIcon.fromTheme(icon_name))
            tray.setToolTip(tooltip)
            shown = state

    refresh()
    tray.show()
    timer = QTimer()
    timer.timeout.connect(refresh)
    timer.start(POLL_MS)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
