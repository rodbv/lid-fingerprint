import pytest

from fingerprint_tray import (
    CHECK_SCRIPT,
    find_lid_state,
    fingerprint_state,
    read_override,
    write_override,
)

PAM_WITH_LID_CHECK = """\
auth [success=ignore ignore=ignore default=1] pam_exec.so quiet {script} {lid} /run/user
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
    path.write_text(PAM_WITH_LID_CHECK.format(script=CHECK_SCRIPT, lid=lid))
    return path


@pytest.fixture
def override_file(tmp_path):
    return tmp_path / "lid-fingerprint"


def test_open_lid_with_lid_check_in_pam_is_on(lid, pam, override_file):
    lid.write_text("state:      open\n")

    assert fingerprint_state(lid, pam, override_file) == "on"


def test_closed_lid_with_lid_check_in_pam_is_off(lid, pam, override_file):
    lid.write_text("state:      closed\n")

    assert fingerprint_state(lid, pam, override_file) == "off"


def test_override_on_with_the_lid_closed_is_forced_on(lid, pam, override_file):
    lid.write_text("state:      closed\n")
    write_override(override_file, "on")

    assert fingerprint_state(lid, pam, override_file) == "forced-on"


def test_override_off_with_the_lid_open_is_forced_off(lid, pam, override_file):
    lid.write_text("state:      open\n")
    write_override(override_file, "off")

    assert fingerprint_state(lid, pam, override_file) == "forced-off"


def test_override_without_lid_check_in_pam_is_unconfigured(lid, tmp_path, override_file):
    lid.write_text("state:      open\n")
    write_override(override_file, "on")
    pam = tmp_path / "system-auth"
    pam.write_text("auth sufficient pam_fprintd.so\n")

    assert fingerprint_state(lid, pam, override_file) == "unconfigured"


def test_write_override_lid_removes_the_override(override_file):
    write_override(override_file, "off")

    write_override(override_file, "lid")

    assert read_override(override_file) is None
    assert not override_file.exists()


def test_unknown_override_value_reads_as_none(override_file):
    override_file.write_text("maybe\n")

    assert read_override(override_file) is None


def test_pam_with_a_grep_lid_check_instead_of_the_check_script_is_unconfigured(
    lid, tmp_path, override_file
):
    lid.write_text("state:      open\n")
    pam = tmp_path / "system-auth"
    pam.write_text(
        f"auth [success=ignore default=1] pam_exec.so quiet /usr/bin/grep -q open {lid}\n"
        "auth sufficient pam_fprintd.so\n"
    )

    assert fingerprint_state(lid, pam, override_file) == "unconfigured"


def test_pam_without_lid_check_is_unconfigured(lid, tmp_path, override_file):
    lid.write_text("state:      open\n")
    pam = tmp_path / "system-auth"
    pam.write_text("auth sufficient pam_fprintd.so\n")

    assert fingerprint_state(lid, pam, override_file) == "unconfigured"


def test_pam_without_fprintd_is_unconfigured(lid, tmp_path, override_file):
    lid.write_text("state:      open\n")
    pam = tmp_path / "system-auth"
    pam.write_text(f"auth required pam_exec.so quiet {CHECK_SCRIPT} {lid} /run/user\n")

    assert fingerprint_state(lid, pam, override_file) == "unconfigured"


def test_missing_pam_file_is_unconfigured(lid, tmp_path, override_file):
    lid.write_text("state:      open\n")

    assert fingerprint_state(lid, tmp_path / "missing", override_file) == "unconfigured"


def test_unreadable_lid_state_is_unconfigured(lid, pam, override_file):
    lid.mkdir()

    assert fingerprint_state(lid, pam, override_file) == "unconfigured"


def test_machine_without_lid_is_unconfigured(pam, override_file):
    assert fingerprint_state(None, pam, override_file) == "unconfigured"


def test_find_lid_state_returns_the_first_lid(lid):
    lid.write_text("state:      open\n")

    assert find_lid_state(lid.parent.parent) == lid


def test_find_lid_state_without_lid_returns_none(tmp_path):
    assert find_lid_state(tmp_path) is None
