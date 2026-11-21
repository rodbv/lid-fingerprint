import pytest

from fingerprint_tray import find_lid_state, fingerprint_state

PAM_WITH_LID_CHECK = """\
auth [success=ignore default=1] pam_exec.so quiet /usr/bin/grep -q open {lid}
auth sufficient pam_fprintd.so
"""


@pytest.fixture
def lid(tmp_path):
    state = tmp_path / "lid" / "LID" / "state"
    state.parent.mkdir(parents=True)
    return state


@pytest.fixture
def pam(tmp_path, lid):
    path = tmp_path / "system-auth"
    path.write_text(PAM_WITH_LID_CHECK.format(lid=lid))
    return path


def test_open_lid_with_lid_check_in_pam_is_on(lid, pam):
    lid.write_text("state:      open\n")

    assert fingerprint_state(lid, pam) == "on"


def test_closed_lid_with_lid_check_in_pam_is_off(lid, pam):
    lid.write_text("state:      closed\n")

    assert fingerprint_state(lid, pam) == "off"


def test_pam_without_lid_check_is_unconfigured(lid, tmp_path):
    lid.write_text("state:      open\n")
    pam = tmp_path / "system-auth"
    pam.write_text("auth sufficient pam_fprintd.so\n")

    assert fingerprint_state(lid, pam) == "unconfigured"


def test_pam_without_fprintd_is_unconfigured(lid, tmp_path):
    lid.write_text("state:      open\n")
    pam = tmp_path / "system-auth"
    pam.write_text(f"auth required pam_exec.so quiet /usr/bin/grep -q open {lid}\n")

    assert fingerprint_state(lid, pam) == "unconfigured"


def test_missing_pam_file_is_unconfigured(lid, tmp_path):
    lid.write_text("state:      open\n")

    assert fingerprint_state(lid, tmp_path / "missing") == "unconfigured"


def test_unreadable_lid_state_is_unconfigured(lid, pam):
    lid.mkdir()

    assert fingerprint_state(lid, pam) == "unconfigured"


def test_machine_without_lid_is_unconfigured(pam):
    assert fingerprint_state(None, pam) == "unconfigured"


def test_find_lid_state_returns_the_first_lid(lid):
    lid.write_text("state:      open\n")

    assert find_lid_state(lid.parent.parent) == lid


def test_find_lid_state_without_lid_returns_none(tmp_path):
    assert find_lid_state(tmp_path) is None
