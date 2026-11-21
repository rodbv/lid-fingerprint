#!/usr/bin/python3
"""Tray icon that shows whether sudo and the lock screen accept the fingerprint."""

import contextlib
import os
import sys
from pathlib import Path

LID_DIR = Path("/proc/acpi/button/lid")
PAM_SYSTEM_AUTH = Path("/etc/pam.d/system-auth")
CHECK_SCRIPT = "/usr/local/sbin/lid-fingerprint-check"
# The PAM check script reads this exact path, so XDG_RUNTIME_DIR must not move it.
OVERRIDE_FILE = Path(f"/run/user/{os.getuid()}/lid-fingerprint")
POLL_MS = 2000

# Icon names, not pixmaps: plasmashell resolves them in the panel's own theme and colors.
ICONS = {
    "on": ("fprint-lid-open-symbolic", "Fingerprint on: lid open"),
    "off": ("fprint-lid-closed-symbolic", "Fingerprint off: lid closed, password only"),
    "forced-on": ("fprint-lid-open-symbolic", "Fingerprint on: forced from the menu"),
    "forced-off": (
        "fprint-lid-closed-symbolic",
        "Fingerprint off: forced from the menu, password only",
    ),
    "unconfigured": (
        "action-unavailable-symbolic",
        "Fingerprint: PAM has no lid check (run pam-setup install)",
    ),
}
MODES = {"lid": "Follow lid", "on": "Always on", "off": "Always off"}


def find_lid_state(lid_dir: Path = LID_DIR) -> Path | None:
    return next(iter(sorted(lid_dir.glob("*/state"))), None)


def read_override(path: Path = OVERRIDE_FILE) -> str | None:
    try:
        value = path.read_text().strip()
    except OSError:
        return None
    return value if value in ("on", "off") else None


def write_override(path: Path, mode: str) -> None:
    if mode == "lid":
        path.unlink(missing_ok=True)
    else:
        path.write_text(f"{mode}\n")


def fingerprint_state(
    lid_state: Path | None,
    pam_system_auth: Path = PAM_SYSTEM_AUTH,
    override_file: Path = OVERRIDE_FILE,
) -> str:
    try:
        pam = pam_system_auth.read_text()
    except OSError:
        return "unconfigured"
    if lid_state is None or f"{CHECK_SCRIPT} {lid_state}" not in pam or "pam_fprintd.so" not in pam:
        return "unconfigured"
    if forced := read_override(override_file):
        return f"forced-{forced}"
    try:
        lid = lid_state.read_text()
    except OSError:
        return "unconfigured"
    return "on" if "open" in lid else "off"


def main() -> None:
    # Qt stays out of module scope so the tests run without PyQt6.
    from PyQt6.QtCore import QTimer
    from PyQt6.QtGui import QAction, QActionGroup, QIcon
    from PyQt6.QtWidgets import QApplication, QMenu, QSystemTrayIcon

    app = QApplication(sys.argv)
    app.setApplicationName("Fingerprint lid")
    app.setQuitOnLastWindowClosed(False)

    tray = QSystemTrayIcon()
    menu = QMenu()
    modes = QActionGroup(menu)
    mode_actions = {}

    def choose(mode: str) -> None:
        # An exception in a Qt slot aborts the whole tray process.
        with contextlib.suppress(OSError):
            write_override(OVERRIDE_FILE, mode)
        refresh()

    for mode, label in MODES.items():
        action = QAction(label, menu, checkable=True)
        action.triggered.connect(lambda _checked, m=mode: choose(m))
        modes.addAction(action)
        menu.addAction(action)
        mode_actions[mode] = action
    menu.addSeparator()
    quit_action = QAction("Quit", menu)
    quit_action.triggered.connect(app.quit)
    menu.addAction(quit_action)
    tray.setContextMenu(menu)

    lid_state = find_lid_state()
    shown = None

    def refresh() -> None:
        nonlocal shown
        state = fingerprint_state(lid_state)
        modes.setEnabled(state != "unconfigured")
        mode_actions[read_override() or "lid"].setChecked(True)
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
