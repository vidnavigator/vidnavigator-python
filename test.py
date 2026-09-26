#!/usr/bin/env python
"""Run the VidNavigator SDK test suite.

Usage:
    python test.py              # unit tests only (mocked, no API key)
    python test.py --all        # unit + integration (requires VIDNAVIGATOR_API_KEY)
    python test.py --live       # integration only (requires VIDNAVIGATOR_API_KEY)
    python test.py --live -k tiktok_profile_scrape_lifecycle

Live runs include the opt-in platform matrix and webhook delivery tests, which
skip themselves unless their environment variables are set (see CONTRIBUTING.md).
"""

import subprocess
import sys


def main():
    args = sys.argv[1:]
    passthrough_args = [
        arg for arg in args
        if arg not in {"--all", "--live"}
    ]

    if "--live" in args:
        cmd = [sys.executable, "-m", "pytest", "tests/test_integration.py", "tests/test_platforms.py", "tests/test_webhook_delivery.py", "-v"]
    elif "--all" in args:
        cmd = [sys.executable, "-m", "pytest", "tests/", "-v"]
    else:
        cmd = [
            sys.executable, "-m", "pytest", "tests/", "-v",
            "--ignore=tests/test_integration.py",
            "--ignore=tests/test_platforms.py",
            "--ignore=tests/test_webhook_delivery.py",
        ]
    cmd.extend(passthrough_args)

    print(f"Running: {' '.join(cmd)}\n")
    sys.exit(subprocess.call(cmd))


if __name__ == "__main__":
    main()
