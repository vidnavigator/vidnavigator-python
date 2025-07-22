"""VidNavigator Python SDK

A lightweight wrapper around the VidNavigator Developer API.
"""

from importlib.metadata import version, PackageNotFoundError

try:
    __version__ = version(__name__)
except PackageNotFoundError:
    # Fallback when running from source
    __version__ = "0.1.0"

from .client import VidNavigatorClient  # noqa: E402

__all__ = ["VidNavigatorClient", "__version__"] 