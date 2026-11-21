import os
import shutil
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).parent.parent
FIXTURE = Path(__file__).parent / "fixtures" / "local"
LID_STATE = "/proc/acpi/button/lid/LID0/state"


@pytest.fixture
def profile(tmp_path):
    target = tmp_path / "profile"
    shutil.copytree(FIXTURE, target)
    return target


def patch(profile):
    subprocess.run([REPO / "pam-setup", "patch-profile", profile, LID_STATE], check=True)


def auth_lines(path):
    return [line for line in path.read_text().splitlines() if line.startswith("auth")]


def line_before_fprintd(path):
    lines = auth_lines(path)
    fprintd = next(i for i, line in enumerate(lines) if "pam_fprintd.so" in line)
    return lines[fprintd - 1]


def test_system_auth_skips_only_the_fprintd_line_when_the_lid_check_fails(profile):
    patch(profile)

    check = line_before_fprintd(profile / "system-auth")

    assert "[success=ignore ignore=ignore default=1]" in check
    assert f"pam_exec.so quiet /usr/bin/grep -q open {LID_STATE}" in check


def test_system_auth_lid_check_drops_out_with_the_fingerprint_feature(profile):
    patch(profile)

    check = line_before_fprintd(profile / "system-auth")

    assert check.endswith('{include if "with-fingerprint"}')


def test_fingerprint_auth_fails_at_once_when_the_lid_check_fails(profile):
    patch(profile)

    check = line_before_fprintd(profile / "fingerprint-auth")

    assert "[success=ignore ignore=ignore default=die]" in check
    assert LID_STATE in check


def test_lid_checks_ignore_pam_setcred_where_pam_exec_returns_pam_ignore(profile):
    patch(profile)

    for name in ("system-auth", "fingerprint-auth"):
        assert "ignore=ignore" in line_before_fprintd(profile / name)


def test_patching_twice_adds_the_lid_check_once(profile):
    patch(profile)
    patch(profile)

    for name in ("system-auth", "fingerprint-auth"):
        assert (profile / name).read_text().count(LID_STATE) == 1


def test_patch_profile_without_fprintd_line_exits_with_no_lid_check(profile):
    fingerprint_auth = profile / "fingerprint-auth"
    fingerprint_auth.write_text(
        "\n".join(
            line for line in fingerprint_auth.read_text().splitlines() if "pam_fprintd" not in line
        )
    )

    result = subprocess.run(
        [REPO / "pam-setup", "patch-profile", profile, LID_STATE],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 1
    assert "no lid check" in result.stderr


@pytest.mark.skipif(os.geteuid() == 0, reason="as root, install changes the host PAM setup")
def test_install_without_root_exits_with_run_with_sudo():
    result = subprocess.run(
        [REPO / "pam-setup", "install"], capture_output=True, text=True, check=False
    )

    assert result.returncode == 1
    assert "run with sudo" in result.stderr
