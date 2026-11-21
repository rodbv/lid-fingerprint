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
# pam_fprintd defaults (man pam_fprintd), so the test behaves like sudo.
VERIFY_MAX_TRIES = 3
VERIFY_TIMEOUT_MS = 30_000
VERIFY_MESSAGES = {
    "match": "Fingerprint matched",
    "no-match": "Fingerprint did not match",
    "not-enrolled": "No finger enrolled: run fprintd-enroll",
}


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


def verify_outcome(output: str) -> tuple[str, str]:
    """Read the fprintd-verify output and return (kind, message for the user)."""
    lines = [line.strip() for line in output.splitlines() if line.strip()]
    results = [line for line in lines if line.startswith("Verify result:") and "(done)" in line]
    if results and "verify-match" in results[-1]:
        kind = "match"
    elif results and "verify-no-match" in results[-1]:
        kind = "no-match"
    elif "NoEnrolledPrints" in output:
        kind = "not-enrolled"
    else:
        return "error", f"Fingerprint test failed: {lines[-1] if lines else 'no output'}"
    return kind, VERIFY_MESSAGES[kind]


def should_retry(kind: str, attempt: int) -> bool:
    return kind == "no-match" and attempt < VERIFY_MAX_TRIES


def main() -> None:
    # Qt stays out of module scope so the tests run without PyQt6.
    from PyQt6.QtCore import QProcess, QTimer
    from PyQt6.QtGui import QAction, QIcon
    from PyQt6.QtWidgets import QApplication, QMenu, QSystemTrayIcon

    app = QApplication(sys.argv)
    app.setApplicationName("Fingerprint lid")
    app.setQuitOnLastWindowClosed(False)

    tray = QSystemTrayIcon()
    menu = QMenu()
    # No exclusive QActionGroup: Plasma draws its members as radio buttons, not check marks.
    mode_actions = {}

    def choose(mode: str) -> None:
        # An exception in a Qt slot aborts the whole tray process.
        with contextlib.suppress(OSError):
            write_override(OVERRIDE_FILE, mode)
        refresh()

    for mode, label in MODES.items():
        action = QAction(label, menu, checkable=True)
        action.triggered.connect(lambda _checked, m=mode: choose(m))
        menu.addAction(action)
        mode_actions[mode] = action
    menu.addSeparator()

    verify = QProcess()
    verify.setProgram("fprintd-verify")
    verify.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
    test_action = QAction("Test fingerprint", menu)
    verify_timeout = QTimer(singleShot=True, interval=VERIFY_TIMEOUT_MS)
    verify_timeout.timeout.connect(verify.kill)
    attempt = 0

    def start_test() -> None:
        nonlocal attempt
        attempt = 1
        test_action.setEnabled(False)
        tray.showMessage("Fingerprint test", "Touch the reader")
        verify.start()
        verify_timeout.start()

    def finish_test() -> None:
        nonlocal attempt
        output = bytes(verify.readAllStandardOutput()).decode(errors="replace")
        if verify.exitStatus() == QProcess.ExitStatus.CrashExit:
            kind, message = "error", "Fingerprint test stopped: no match within 30 seconds"
        else:
            kind, message = verify_outcome(output)
        if should_retry(kind, attempt):
            attempt += 1
            tray.showMessage(
                "Fingerprint test",
                f"No match, touch the reader again ({attempt} of {VERIFY_MAX_TRIES})",
            )
            verify.start()
            return
        verify_timeout.stop()
        icon = QSystemTrayIcon.MessageIcon
        tray.showMessage(
            "Fingerprint test", message, icon.Information if kind == "match" else icon.Warning
        )
        test_action.setEnabled(True)

    def test_failed_to_start(error: QProcess.ProcessError) -> None:
        if error == QProcess.ProcessError.FailedToStart:
            verify_timeout.stop()
            tray.showMessage("Fingerprint test", "fprintd-verify is missing: install fprintd")
            test_action.setEnabled(True)

    test_action.triggered.connect(start_test)
    verify.finished.connect(finish_test)
    verify.errorOccurred.connect(test_failed_to_start)
    menu.addAction(test_action)
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
        current = read_override() or "lid"
        for mode, action in mode_actions.items():
            action.setEnabled(state != "unconfigured")
            action.setChecked(mode == current)
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
