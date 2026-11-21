import getpass
import os
import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).parent.parent / "sbin" / "lid-fingerprint-check"


@pytest.fixture
def lid(tmp_path):
    return tmp_path / "state"


@pytest.fixture
def runtime_root(tmp_path):
    user_dir = tmp_path / "run" / str(os.getuid())
    user_dir.mkdir(parents=True)
    return user_dir.parent


def check(lid, runtime_root, override=None):
    if override is not None:
        (runtime_root / str(os.getuid()) / "lid-fingerprint").write_text(override)
    env = {"PAM_USER": getpass.getuser()}
    return subprocess.run([SCRIPT, lid, runtime_root], env=env, check=False).returncode


def test_open_lid_without_override_allows_the_fingerprint(lid, runtime_root):
    lid.write_text("state:      open\n")

    assert check(lid, runtime_root) == 0


def test_closed_lid_without_override_skips_the_fingerprint(lid, runtime_root):
    lid.write_text("state:      closed\n")

    assert check(lid, runtime_root) == 1


def test_override_on_allows_the_fingerprint_with_the_lid_closed(lid, runtime_root):
    lid.write_text("state:      closed\n")

    assert check(lid, runtime_root, override="on\n") == 0


def test_override_off_skips_the_fingerprint_with_the_lid_open(lid, runtime_root):
    lid.write_text("state:      open\n")

    assert check(lid, runtime_root, override="off\n") == 1


def test_unknown_override_follows_the_lid(lid, runtime_root):
    lid.write_text("state:      closed\n")

    assert check(lid, runtime_root, override="maybe\n") == 1
