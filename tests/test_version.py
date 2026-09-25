"""Guard against the version drifting between the three places it is declared."""

import re
from pathlib import Path

import vidnavigator
from vidnavigator.client import USER_AGENT

ROOT = Path(__file__).resolve().parent.parent


def test_versions_match():
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    declared = re.search(r'^version = "([^"]+)"', pyproject, re.MULTILINE).group(1)
    assert vidnavigator.__version__ == declared
    assert USER_AGENT == f"vidnavigator-python/{declared}"
