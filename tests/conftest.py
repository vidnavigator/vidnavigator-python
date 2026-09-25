from unittest.mock import patch

import pytest


@pytest.fixture
def no_sleep():
    """Make job polling instant; yields the patched ``time.sleep`` for assertions."""
    with patch("vidnavigator.jobs.time.sleep") as sleep:
        yield sleep
