#!/usr/bin/env python
"""Run the VidNavigator SDK test suite.

Usage:
    python test.py              # unit tests only (mocked, no API key)
    python test.py --all        # unit + integration (requires VIDNAVIGATOR_API_KEY)
    python test.py --live       # integration only (requires VIDNAVIGATOR_API_KEY)
"""

import subprocess
import sys


def main():
    args = sys.argv[1:]

    if "--live" in args:
        cmd = [sys.executable, "-m", "pytest", "tests/test_integration.py", "-v"]
    elif "--all" in args:
        cmd = [sys.executable, "-m", "pytest", "tests/", "-v"]
    else:
        cmd = [
            sys.executable, "-m", "pytest", "tests/", "-v",
            "--ignore=tests/test_integration.py",
        ]

    print(f"Running: {' '.join(cmd)}\n")
    sys.exit(subprocess.call(cmd))


if __name__ == "__main__":
    main()
