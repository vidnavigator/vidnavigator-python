# Contributing & Development Guide

Internal reference for developing, testing, and publishing the VidNavigator Python SDK.

---

## Project Structure

```
vidnavigator-python/
  vidnavigator/           # SDK source code (published to PyPI)
    __init__.py           #   Package exports and __version__
    client.py             #   VidNavigatorClient with all API methods
    models.py             #   Pydantic response models
    exceptions.py         #   Exception hierarchy + status/error-code mapping
    jobs.py               #   AsyncJob handle: background-job polling, timeouts, results
    webhooks.py           #   Webhook signature verification and event parsing
  tests/                  # Test suite (not published)
    fixtures/             #   Test media files (git-ignored)
    test_client_endpoints.py   # Mocked unit tests for every client method
    conftest.py / helpers.py   # Shared fixtures (instant polling) and mock payload builders
    test_async_jobs.py         # Job handles, polling schedule, timeouts, blocking calls
    test_tiktok_webhooks.py    # TikTok jobs, webhook_url pass-through, new filters
    test_webhooks.py           # Webhook signature verification tests
    test_error_mapping.py      # HTTP status -> exception mapping tests
    test_extract_endpoints.py  # Extraction endpoint unit tests
    test_models_extract.py     # Extraction model parsing tests
    test_version.py            # Version consistency across the three declarations
    test_integration.py        # Live API integration tests
    test_platforms.py          # Live, opt-in: every platform, captions + speech-to-text
    test_webhook_delivery.py   # Live, opt-in: end-to-end signed webhook deliveries
  test.py                 # Convenience CLI runner for pytest
  pyproject.toml          # Package metadata, dependencies, build config
  openapi.json            # API spec (source of truth for SDK updates)
  README.md               # Public-facing documentation (shown on PyPI)
  CONTRIBUTING.md         # This file
```

---

## Setup

```bash
# Clone the repo
git clone https://github.com/vidnavigator/vidnavigator-python.git
cd vidnavigator-python

# Install in editable mode with dev dependencies
pip install -e ".[dev]"
```

This installs the SDK from your local source (so code changes take effect immediately) plus `pytest` and `python-dotenv`.

---

## Running Tests

### Unit tests (no API key needed)

```bash
python test.py
# or
pytest tests/ -v --ignore=tests/test_integration.py
```

These mock all HTTP calls and run in ~1 second.

### Integration tests (requires API key)

Create a `.env` file at the project root:

```
VIDNAVIGATOR_API_KEY=your_key_here
```

Then:

```bash
python test.py --live       # integration only
python test.py --all        # unit + integration
# or
pytest tests/test_integration.py -v
```

Integration tests hit the live API. They are skipped automatically when the API key is not set, so `pytest tests/` is always safe to run.

Some integration tests need extra inputs and are skipped unless these are set:

| Variable | Enables |
|---|---|
| `VIDNAVIGATOR_TIKTOK_PROFILE_URL` | TikTok profile scrape lifecycle (e.g. `https://www.tiktok.com/@tiktok`) |
| `VIDNAVIGATOR_TRANSCRIBE_URL` | Async transcription success path (a short non-YouTube video, e.g. a TikTok URL) |
| `VIDNAVIGATOR_TWEET_ID` | Tweet claim analysis test (e.g. `1585841080431321088`) |
| `VIDNAVIGATOR_BASE_URL` | Run against a local or staging API (local backend: `http://localhost:5001/v1`) |
| `VIDNAVIGATOR_PLATFORM_TESTS=1` | `tests/test_platforms.py`: captions and speech-to-text on every supported platform (billed) |
| `VIDNAVIGATOR_WEBHOOK_SITE_TOKEN` + `VIDNAVIGATOR_WEBHOOK_SECRET` | `tests/test_webhook_delivery.py`: real signed deliveries, read back from a webhook.site inbox that is the account's default webhook |

Keep API keys and the webhook secret in your shell or `.env`, never in the repository.

### Test fixtures

Large binary files (e.g. `tests/fixtures/video-test.mp4`) are git-ignored. Each developer should place their own test media in `tests/fixtures/`.

---

## Building the Package

```bash
# Install build tools (one time)
pip install build twine

# Build sdist and wheel
python -m build
```

This creates `dist/vidnavigator-X.Y.Z.tar.gz` and `dist/vidnavigator-X.Y.Z-py3-none-any.whl`.

### Verify the build

```bash
twine check dist/*
```

---

## Publishing to PyPI

### Test PyPI (dry run)

```bash
twine upload --repository testpypi dist/*
```

Verify at https://test.pypi.org/project/vidnavigator/

### Production PyPI

```bash
twine upload dist/*
```

You'll need PyPI credentials or an API token. To use a token:

```bash
twine upload dist/* -u __token__ -p pypi-YOUR_TOKEN_HERE
```

Or configure `~/.pypirc`:

```ini
[pypi]
username = __token__
password = pypi-YOUR_TOKEN_HERE
```

---

## Release Checklist

1. **Update the version** in three places:
   - `pyproject.toml` (`version = "X.Y.Z"`)
   - `vidnavigator/__init__.py` (`__version__ = "X.Y.Z"`)
   - `vidnavigator/client.py` (`USER_AGENT = "vidnavigator-python/X.Y.Z"`)

2. **Run the full test suite:**
   ```bash
   python test.py --all
   ```

3. **Clean old builds:**
   ```bash
   rm -rf dist/ build/ *.egg-info
   ```

4. **Build and verify:**
   ```bash
   python -m build
   twine check dist/*
   ```

5. **Publish:**
   ```bash
   twine upload dist/*
   ```

6. **Tag the release in git:**
   ```bash
   git tag v1.0.0
   git push origin v1.0.0
   ```

---

## Updating the SDK for API Changes

1. Update `openapi.json` with the latest spec.
2. Update `vidnavigator/models.py` with new/changed schemas.
3. Update `vidnavigator/client.py` with new/changed methods.
4. Update `vidnavigator/exceptions.py` if new error codes were introduced.
5. Add unit tests in `tests/` for the new functionality.
6. Run `python test.py --all` to verify everything works.
7. Update `README.md` if the changes affect the public API surface.
