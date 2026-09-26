"""Live end-to-end webhook tests: real deliveries, read back from webhook.site.

Opt-in. Requires an account whose default webhook points at a webhook.site
inbox, plus that account's signing secret (Studio -> API):

    VIDNAVIGATOR_API_KEY=...                  # key of that account
    VIDNAVIGATOR_WEBHOOK_SITE_TOKEN=<uuid>    # the inbox id in https://webhook.site/<uuid>
    VIDNAVIGATOR_WEBHOOK_SECRET=...           # the account's webhook signing secret
    pytest tests/test_webhook_delivery.py -v
"""

import json
import os
import time
from urllib.request import Request, urlopen

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

import pytest

from vidnavigator import VidNavigatorClient, construct_webhook_event

_api_key = os.getenv("VIDNAVIGATOR_API_KEY")
_base_url = os.getenv("VIDNAVIGATOR_BASE_URL")
SITE_TOKEN = os.getenv("VIDNAVIGATOR_WEBHOOK_SITE_TOKEN")
SECRET = os.getenv("VIDNAVIGATOR_WEBHOOK_SECRET")
pytestmark = pytest.mark.skipif(
    not (_api_key and SITE_TOKEN and SECRET),
    reason="set VIDNAVIGATOR_WEBHOOK_SITE_TOKEN and VIDNAVIGATOR_WEBHOOK_SECRET to run webhook delivery tests",
)

YT = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
SCHEMA = {"mood": {"type": "String", "description": "One word describing the mood"}}
DELIVERY_TIMEOUT = int(os.getenv("VIDNAVIGATOR_WEBHOOK_TIMEOUT_SECONDS", "90"))


@pytest.fixture(scope="module")
def client():
    kwargs = {"api_key": _api_key, "timeout": 120}
    if _base_url:
        kwargs["base_url"] = _base_url
    with VidNavigatorClient(**kwargs) as c:
        yield c


def _site_json(url, data=None):
    req = Request(url, data=data, headers={"Accept": "application/json", "User-Agent": "vidnavigator-sdk-tests"})
    with urlopen(req, timeout=30) as resp:
        return json.load(resp)


def _header(request, name):
    value = (request.get("headers") or {}).get(name.lower())
    return value[0] if isinstance(value, list) else value


def _deliveries(token, task_id):
    page = _site_json(f"https://webhook.site/token/{token}/requests?sorting=newest&per_page=50")
    return [r for r in page.get("data", []) if _header(r, "X-VidNavigator-Task-Id") == task_id]


def _wait_for_delivery(token, task_id, timeout=DELIVERY_TIMEOUT):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        found = _deliveries(token, task_id)
        if found:
            return found[0]
        time.sleep(3)
    pytest.fail(f"No webhook delivery for task {task_id} within {timeout}s")


def _verified_event(request):
    """Verify the delivery's signature exactly as a receiver would, and parse it."""
    return construct_webhook_event(
        request["content"].encode("utf-8"),
        _header(request, "X-VidNavigator-Signature"),
        SECRET,
        tolerance_seconds=None,  # webhook.site may be read well after delivery
    )


def test_default_webhook_delivers_signed_completed_event(client):
    job = client.submit_extract_video_data(video_url=YT, schema=SCHEMA, transcribe=False)
    assert job.webhook_url == f"https://webhook.site/{SITE_TOKEN}"
    resp = job.result(timeout=300)

    delivery = _wait_for_delivery(SITE_TOKEN, job.task_id)
    assert delivery["method"] == "POST"
    assert _header(delivery, "X-VidNavigator-Event") == "extract_video.completed"
    assert _header(delivery, "X-VidNavigator-Delivery")

    event = _verified_event(delivery)
    assert event.type == "extract_video.completed"
    assert event.id
    assert event.data.task_id == job.task_id
    assert event.data.task_status == "completed"
    assert event.data.result == resp.data

    # The job reports its webhook delivery status once delivered.
    deadline = time.monotonic() + 30
    status = job.refresh().data.webhook
    while (status is None or status.status != "delivered") and time.monotonic() < deadline:
        time.sleep(2)
        status = job.refresh().data.webhook
    assert status is not None and status.status == "delivered"
    assert status.attempts >= 1


def test_failed_job_delivers_failed_event(client):
    job = client.submit_transcribe_video(video_url=YT)  # YouTube is unsupported by speech-to-text
    job.wait(raise_on_failure=False, timeout=300)

    event = _verified_event(_wait_for_delivery(SITE_TOKEN, job.task_id))
    assert event.type == "transcribe.failed"
    assert event.data.task_status == "failed"
    assert event.data.error.error == "unsupported_platform"
    assert event.data.error.http_status == 400


def test_empty_webhook_url_opts_out_of_default(client):
    job = client.submit_extract_video_data(
        video_url=YT, schema=SCHEMA, transcribe=False, webhook_url="",
    )
    assert job.webhook_url is None
    job.result(timeout=300)
    assert job.refresh().data.webhook is None

    time.sleep(15)  # give a (wrong) delivery time to arrive
    assert _deliveries(SITE_TOKEN, job.task_id) == []


def test_per_request_webhook_overrides_default(client):
    other_token = _site_json("https://webhook.site/token", data=b"")["uuid"]
    other_url = f"https://webhook.site/{other_token}"

    job = client.submit_extract_video_data(
        video_url=YT, schema=SCHEMA, transcribe=False, webhook_url=other_url,
    )
    assert job.webhook_url == other_url
    job.result(timeout=300)

    event = _verified_event(_wait_for_delivery(other_token, job.task_id))
    assert event.type == "extract_video.completed"
    assert _deliveries(SITE_TOKEN, job.task_id) == []


def test_tiktok_search_webhook_is_a_notification(client):
    job = client.submit_tiktok_search(query="ai tools", max_results=5)
    assert job.webhook_url == f"https://webhook.site/{SITE_TOKEN}"
    page = job.result(limit=5, timeout=300)

    event = _verified_event(_wait_for_delivery(SITE_TOKEN, job.task_id))
    assert event.type == "tiktok_search.completed"
    # The event is a summary; the results themselves are read with the job handle.
    assert event.data.result["stats"]["results_count"] == len(page.data.results)
    assert "download_url_available" in event.data.result
    assert "results" not in event.data.result
    assert page.data.is_completed
