# VidNavigator Python SDK

The official Python client for the [VidNavigator Developer API](https://docs.vidnavigator.com) -- transcribe, analyze, search, and extract structured data from video and audio at scale.

[![PyPI version](https://img.shields.io/pypi/v/vidnavigator)](https://pypi.org/project/vidnavigator/)
[![Python](https://img.shields.io/pypi/pyversions/vidnavigator)](https://pypi.org/project/vidnavigator/)
[![License](https://img.shields.io/pypi/l/vidnavigator)](https://github.com/vidnavigator/vidnavigator-python/blob/main/LICENSE)

---

## What You Can Do

| Capability | Online Videos | Uploaded Files |
|---|:---:|:---:|
| Transcripts (segments with timestamps or plain text) | Yes | Yes |
| AI analysis (summary, people, places, key subjects, Q&A) | Yes | Yes |
| Structured data extraction (your custom schema) | Yes | Yes |
| Semantic search across content | Yes | Yes |
| File upload, storage, and management | -- | Yes |
| Namespace organization and scoped search | -- | Yes |
| TikTok profile scraping and keyword search | Yes | -- |
| Tweet claim analysis | Yes | -- |
| Async jobs for long videos, with signed webhooks | Yes | -- |

## Supported Platforms

| Platform | Transcript | Transcribe (speech-to-text) | Carousel |
|----------|:----------:|:---------------------------:|:--------:|
| YouTube | Yes | - | - |
| Instagram Reels | - | Yes | Yes |
| Instagram Posts | - | Yes | Yes (`all_videos`) |
| TikTok | Yes | Yes | - |
| X / Twitter | Yes | Yes | - |
| Vimeo | Yes | Yes | - |
| Facebook | Yes | Yes | - |
| Dailymotion | Yes | Yes | - |
| Loom | Yes | Yes | - |
| Uploaded files | Yes | Yes | - |

> **Transcript** = fast caption/subtitle extraction via `get_transcript`. **Transcribe** = speech-to-text via AI models via `transcribe_video` (works when captions are unavailable).

**Supported upload formats:** mp4, webm, mov, avi, wmv, flv, mkv, m4a, mp3, mpeg, mpga, wav.

**Fully typed** -- every response is a Pydantic model with IDE autocompletion. Compatible with both Pydantic v1 and v2.

---

## Installation

```bash
pip install vidnavigator
```

Requires Python 3.7+

---

## Authentication

```python
from vidnavigator import VidNavigatorClient

# Pass your API key directly
client = VidNavigatorClient(api_key="YOUR_API_KEY")

# Or set the environment variable and the client picks it up automatically
# export VIDNAVIGATOR_API_KEY=your_key_here
client = VidNavigatorClient()
```

Get your API key at [vidnavigator.com](https://vidnavigator.com).

---

## Transcripts

### Any supported platform

A single `get_transcript` method handles every supported platform (YouTube, Vimeo, X/Twitter, TikTok, Facebook, Dailymotion, Loom, etc.). The API auto-detects the platform from the URL. **Note:** Instagram uses `transcribe_video` (speech-to-text) instead.

```python
resp = client.get_transcript(
    video_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
)

print(resp.data.video_info.title)
# "Rick Astley - Never Gonna Give You Up (Official Music Video)"

for segment in resp.data.transcript:
    print(f"[{segment.start:.1f}s] {segment.text}")
# [0.0s] We're no strangers to love
# [3.2s] You know the rules and so do I
# ...
```

> `get_youtube_transcript` still works as a deprecated alias for `get_transcript`, but you should migrate to `get_transcript`.

### Plain text instead of segments

```python
resp = client.get_transcript(
    video_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    transcript_text=True,
)

print(resp.data.transcript)
# "We're no strangers to love. You know the rules and so do I..."
```

### Speech-to-text transcription

For videos where captions aren't available, use speech-to-text:

```python
resp = client.transcribe_video(
    video_url="https://www.instagram.com/reel/C86ZvEaqRmo/",
)
```

`transcribe_video` runs as a [background job](#background-jobs): it submits the video, polls until the transcript is ready, and returns it. Long videos work the same way as short ones.

For Instagram carousel posts with multiple videos:

```python
resp = client.transcribe_video(
    video_url="https://www.instagram.com/p/ABC123/",
    all_videos=True,
)

print(resp.data.carousel_info.video_count)
for video in resp.data.videos:
    print(f"Video {video.index}: {video.video_info.title}")
```

### Additional options

All transcript methods support these parameters:

| Parameter | Type | Description |
|---|---|---|
| `language` | `str` | ISO 639-1 language code (e.g. `"en"`, `"fr"`) |
| `transcript_text` | `bool` | Return transcript as a single string instead of segments |
| `metadata_only` | `bool` | Return only video metadata, no transcript |
| `fallback_to_metadata` | `bool` | Return metadata with empty transcript instead of 404 if unavailable |
| `include_usage` | `bool` | Attach a per-call `usage` block to the response (see [Per-call usage](#per-call-usage)) |

---

## AI Analysis

Analyze any video or uploaded file. The API returns a summary, identifies people and places, extracts key subjects, and can answer natural-language questions about the content.

### Analyze an online video

```python
resp = client.analyze_video(
    video_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    query="What is the main message of this song?",
)

analysis = resp.data.transcript_analysis

print(analysis.summary)
# "The song is a declaration of unwavering commitment and loyalty..."

print(analysis.query_answer.answer)
# "The main message is a promise to never give up on someone..."

for person in analysis.people:
    print(f"{person.name} -- {person.context}")
# "Rick Astley -- Singer and performer of the song"

for subject in analysis.key_subjects:
    print(f"{subject.name} -- {subject.description}")
# "commitment -- Central theme of never abandoning a loved one"
```

### Analyze an uploaded file

```python
resp = client.analyze_file(
    file_id="your_file_id",
    query="What are the key action items from this meeting?",
)
print(resp.data.transcript_analysis.summary)
```

---

## Structured Extraction

Define a custom JSON schema and the API extracts structured data from any transcript. Ideal for building pipelines, populating databases, or feeding downstream systems.

### From an online video

```python
resp = client.extract_video_data(
    video_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    schema={
        "mood": {
            "type": "String",
            "description": "Overall mood of the video in one word",
        },
        "main_topics": {
            "type": "Array",
            "description": "List of main topics discussed",
        },
        "has_spoken_lyrics": {
            "type": "Boolean",
            "description": "Whether the video contains spoken or sung lyrics",
        },
    },
    what_to_extract="Focus on the tone and content of the lyrics.",
    transcribe=True,  # auto-transcribe non-YouTube videos when captions are unavailable
)

print(resp.data)
# {"mood": "upbeat", "main_topics": ["love", "commitment"], "has_spoken_lyrics": true}
```

`extract_video_data` also runs as a [background job](#background-jobs), so auto-transcription works for long videos too. The extracted fields are in `resp.data`. `resp.video_info` is not populated for online videos, because job results carry only the extracted data; call `get_transcript(video_url=..., metadata_only=True)` if you need the metadata.

### From an uploaded file

```python
resp = client.extract_file_data(
    file_id="your_file_id",
    schema={
        "action_items": {
            "type": "Array",
            "description": "List of action items mentioned in the meeting",
        },
        "decisions_made": {
            "type": "Array",
            "description": "Key decisions that were agreed upon",
        },
    },
)
print(resp.data)
```

You can also upload a JSON or YAML schema file using multipart form data:

```python
resp = client.extract_file_data(
    file_id="your_file_id",
    schema_file="./meeting-schema.yaml",
    what_to_extract="Extract action items and deadlines.",
)
```

### Track token usage

```python
resp = client.extract_video_data(
    video_url="...",
    schema={"summary": {"type": "String", "description": "One-line summary"}},
    include_usage=True,
)
if resp.usage:
    print(f"Tokens used: {resp.usage.total_tokens}")
```

---

## Per-call usage

Pass `include_usage=True` to most methods to attach a `usage` block describing exactly which meters were charged, how many credits were deducted, and (for AI endpoints) the LLM token tally.

Supported on: `get_transcript`, `transcribe_video`, `analyze_video`, `analyze_file`, `extract_video_data`, `extract_file_data`, `search_youtube`, `search_files`, `get_tweet_statement`, `scrape_tiktok_profile`, `search_tiktok`, job handles (`job.result(include_usage=True)`), and the TikTok pagers (`get_tiktok_profile_scrape`, `get_tiktok_search`). For background jobs, usage is read when polling and appears only once the job is `completed`. Failed jobs have all their charges reverted.

```python
resp = client.search_youtube(query="react best practices", include_usage=True)

usage = resp.usage
if usage:
    print(f"Credits this call: {usage.total_credits}")

    for charge in usage.charges or []:
        print(f"  {charge.service_type}: {charge.quantity} unit(s), {charge.credits} credits")

    # LLM token tally (present for analyze / extract / youtube search)
    tokens = usage.analysis_tokens
    if tokens:
        print(f"  LLM tokens: {tokens.total_tokens}")
```

The `usage` object exposes:

| Field | Description |
|---|---|
| `charges` | List of `UsageCharge` (one per meter): `service_type`, `quantity`, `credits`, `waived`, `credits_saved`, and (analysis only) nested `tokens` |
| `total_credits` | Net credits deducted by the call |
| `waived` | Present when a cache-hit sponsorship waived charges (`waived.credits_saved`) |
| `analysis_tokens` | Convenience accessor for the LLM `tokens` on the `analysis_request` charge |
| `charge_for(service_type)` | Helper returning the charge entry for a given meter |

For `/extract/*`, the token counts are also mirrored as flat `usage.prompt_tokens` / `usage.completion_tokens` / `usage.total_tokens` for convenience.

---

## Background Jobs

Speech-to-text and TikTok operations run as **background jobs** on the API: submitting returns a `task_id` immediately, and the result is read by polling. The SDK only uses these job endpoints. It never calls the synchronous speech-to-text endpoints, so long media works without special handling.

Each operation comes in two shapes:

| Operation | Blocking: wait and return the result | Non-blocking: return a job handle |
|---|---|---|
| Speech-to-text | `transcribe_video(...)` | `submit_transcribe_video(...)` |
| Structured extraction | `extract_video_data(...)` | `submit_extract_video_data(...)` |
| Tweet claim analysis | `get_tweet_statement(...)` | `submit_tweet_statement(...)` |
| TikTok profile scrape | `scrape_tiktok_profile(...)` | `submit_tiktok_profile_scrape(...)` |
| TikTok keyword search | `search_tiktok(...)` | `submit_tiktok_search(...)` |

### Blocking: one call, one result

```python
resp = client.transcribe_video(video_url="https://www.instagram.com/reel/C86ZvEaqRmo/")
print(resp.data.transcript)
```

The call submits the job, polls it, and returns the result, raising an exception if the job failed. It polls every second for the first 10 seconds, so short clips come back quickly, and then every 3 seconds. Polling is free and not rate-limited.

### Non-blocking: submit now, collect later

`submit_*` methods return an `AsyncJob` handle right away. Use them to run many jobs at once:

```python
urls = ["https://www.tiktok.com/@a/video/1", "https://www.tiktok.com/@b/video/2"]

jobs = [client.submit_transcribe_video(video_url=url) for url in urls]
for job in jobs:
    print(job.task_id)  # save these: they are how you get back to the job

results = [job.result() for job in jobs]  # waits for each in turn
```

An `AsyncJob` has:

| Member | Description |
|---|---|
| `task_id` | The job's id. Keep it; see [Timeouts](#timeouts-never-lose-the-task_id). |
| `job_type` | `"transcribe"`, `"extract_video"`, `"tweet_statement"`, `"tiktok_profile"` or `"tiktok_search"` |
| `status()` | Polls once and returns `task_status` |
| `done()` | Polls once; `True` when the job is `completed` or `failed` |
| `result(timeout=..., include_usage=...)` | Waits, then returns the same object as the blocking method; raises if the job failed |
| `wait(...)` | Waits, then returns the raw poll response (job metadata, `request` echo, `webhook` delivery status) |
| `refresh()` | Polls once and returns the raw poll response |
| `webhook_url`, `check_status_url`, `data` | What the API returned when the job was submitted |

`result()` and `wait()` accept `timeout`, `include_usage`, `poll_interval` (default 3 seconds) and `fast_start` (default `True`, the 1-second polling for the first 10 seconds). For TikTok jobs they also accept `limit` and `cursor`.

### Timeouts: never lose the `task_id`

Blocking calls and `result()` wait up to `timeout` seconds (default 3600; pass `None` to wait indefinitely). When the timeout passes, they raise `AsyncJobTimeoutError`. The job itself **keeps running on the server**, and its result stays readable for **1 hour after it finishes**. The error carries the `task_id` and a ready-to-use handle:

```python
from vidnavigator import AsyncJobTimeoutError

try:
    resp = client.transcribe_video(video_url=url, timeout=600)
except AsyncJobTimeoutError as exc:
    save_for_later(exc.task_id)
    resp = exc.job.result()  # or keep waiting right away
```

Later, or from another process, rebuild the handle from the saved id:

```python
job = client.resume_job("transcribe", task_id)
if job.done():
    resp = job.result()
```

### Failures

A failed job reports an `error` object (`error`, `message`, `http_status`), and the SDK raises the matching exception, the same one the API would return for that status:

```python
from vidnavigator import BadRequestError, PaymentRequiredError

try:
    resp = client.transcribe_video(video_url=url)
except PaymentRequiredError:
    print("Out of transcription credit")
except BadRequestError as exc:
    print(exc.error_code, exc)  # e.g. "unsupported_platform"
```

To inspect a failure without an exception, use `job.wait(raise_on_failure=False)` and read `resp.data.error`.

### Submit-time errors

Some errors happen before a job exists. No task is created, so there is nothing to poll:

| Exception | Status | When |
|---|---|---|
| `PaymentRequiredError` | 402 | Not enough credit to start the job |
| `TooManyActiveJobsError` (subclass of `RateLimitExceeded`) | 429 | Too many jobs already running for your account; retry once some finish |
| `BadRequestError` | 400 | Invalid parameters, an invalid extraction schema, or a non-public `webhook_url` |

### Result types

| Operation | `result()` / blocking return value |
|---|---|
| Transcribe | `TranscriptResponse` (`data.video_info`, `data.transcript`), or `TranscribeAllVideosResponse` with `all_videos=True` |
| Extract | `ExtractionApiResponse` (`data` is a `dict` matching your schema) |
| Tweet | `TweetStatementResponse` (`data.final_statement`, `data.detailed_analysis`, ...) |
| TikTok profile / search | `TikTokProfileResponse` / `TikTokSearchResponse`: the first page of results |

---

## Webhooks

A background job can also call you back when it finishes. Every job method, blocking or `submit_*`, accepts a `webhook_url` and passes it through to the API unchanged. Webhooks are optional. Polling always works, whether or not a webhook is configured.

```python
job = client.submit_extract_video_data(
    video_url="https://www.tiktok.com/@user/video/1234567890",
    schema={"summary": {"type": "String", "description": "One-line summary"}},
    webhook_url="https://example.com/hooks/vidnavigator",
)
```

- The URL must be a publicly reachable `https` address. Private, loopback and link-local hosts are rejected.
- A per-request `webhook_url` overrides the account-level default set in **Studio → API**. Pass `webhook_url=""` to opt a single job out of that default.
- For TikTok tasks, the event is a notification only: it carries `stats`, and you read the results with the poller.
- If a result is larger than 256 KB, it is left out of the event (`data.result_truncated` is `True`). Fetch it with the poller instead.

### Verify and parse deliveries

Deliveries are signed with HMAC-SHA256 using your signing secret. `construct_webhook_event` checks the signature and timestamp, then returns a typed `WebhookEvent`. Always pass the **raw** request body, not re-serialized JSON:

```python
from flask import Flask, request
from vidnavigator import WebhookSignatureError, construct_webhook_event

app = Flask(__name__)
WEBHOOK_SECRET = "your_signing_secret"

@app.post("/hooks/vidnavigator")
def vidnavigator_webhook():
    try:
        event = construct_webhook_event(
            request.get_data(),
            request.headers.get("X-VidNavigator-Signature"),
            WEBHOOK_SECRET,
        )
    except WebhookSignatureError:
        return "invalid signature", 400

    delivery_id = request.headers.get("X-VidNavigator-Delivery")  # stable across retries
    if already_processed(delivery_id):
        return "", 200

    if event.type == "transcribe.completed":
        if event.data.result_truncated:
            result = client.resume_job("transcribe", event.data.task_id).result().data
        else:
            result = event.data.result  # plain dict
        save_transcript(event.data.task_id, result)
    elif event.type.endswith(".failed"):
        print(event.data.error.error, event.data.error.message)

    return "", 200
```

Event types: `transcribe.*`, `extract_video.*`, `tweet_statement.*`, `tiktok_profile.*` and `tiktok_search.*`, each ending in `.completed` or `.failed`.

`construct_webhook_event` rejects deliveries whose timestamp is more than 5 minutes away from the current time. Change the window with `tolerance_seconds=` (or pass `None` to skip the check). If you only need the check, `verify_webhook_signature(body, header, secret)` raises the same `WebhookSignatureError` without parsing the body.

Delivery is at-least-once and best effort: up to 5 attempts over about 13 minutes. Your endpoint should return a 2xx response quickly and deduplicate on `X-VidNavigator-Delivery`. Treat polling as the source of truth. See the [webhooks guide](https://docs.vidnavigator.com/guides/webhooks) for the full contract.

---

## TikTok Profile Scraping

TikTok profile scraping runs as a [background job](#background-jobs). `scrape_tiktok_profile` waits for it and returns the first page of videos:

```python
result = client.scrape_tiktok_profile(
    profile_url="https://www.tiktok.com/@tiktok",
    max_posts=100,
    after_datetime="2024-01-01",
    limit=50,
)
task_id = result.data.task_id

for video in result.data.videos or []:
    print(video.title, video.url)
```

To start the scrape without waiting, use `submit_tiktok_profile_scrape(...)`, which returns an [`AsyncJob`](#non-blocking-submit-now-collect-later) handle. Then call `job.result(limit=50)` when you want the videos.

| Parameter | Type | Description |
|---|---|---|
| `profile_url` | `str` | Public TikTok profile URL |
| `max_posts` | `int` | Stop once this many matching videos are collected |
| `after_datetime` / `before_datetime` | `str` / `date` / `datetime` | Only include videos published in this window |
| `min_likes` / `max_likes` | `int` | Like-count filters |
| `webhook_url` | `str` | Optional; passed through to the API (`""` opts out of your account default) |
| `limit` | `int` | Page size of the returned first page (blocking call only) |

### Read results with pagination

Use cursor pagination when you want to process videos page by page:

```python
cursor = None

while True:
    page = client.get_tiktok_profile_scrape(task_id, cursor=cursor, limit=50)

    for video in page.data.videos or []:
        print(video.title, video.published_at, video.likes, video.url)

    pagination = page.data.pagination
    if not pagination or not pagination.has_next:
        break
    cursor = pagination.next_cursor
```

### Download the full profile result

For large profiles, use `download_url` when it is returned. It points to a short-lived JSON file containing the complete scrape result:

```python
import json
from urllib.request import urlopen

completed = client.get_tiktok_profile_scrape(task_id)

if completed.data.download_url:
    with urlopen(completed.data.download_url) as response:
        full_profile = json.load(response)

    for video in full_profile.get("videos", []):
        print(video.get("title"), video.get("published_at"), video.get("likes"), video.get("url"))
```

`after_datetime` and `before_datetime` accept `YYYY-MM-DD` strings or ISO format with timezone. You can pass strings in that format, or Python `date` / `datetime` objects. In typed SDK responses, `video.published_at` is parsed as a Python `datetime`, and numeric fields such as `views`, `likes`, `reposts`, and `comments` are integers.

### Use scraped videos with transcripts or extraction

Each TikTok video has a `url`, so you can pass it to the normal transcript, transcription, analysis, or extraction methods. If you used pagination, loop through `result.data.videos`; if you used `download_url`, loop through `full_profile["videos"]`.

```python
for video in result.data.videos or []:
    if not video.url:
        continue

    transcript = client.get_transcript(
        video_url=video.url,
        transcript_text=True,
        fallback_to_metadata=True,
    )
    print(transcript.data.transcript)
```

For downloaded JSON results, use dictionary access:

```python
for video in full_profile.get("videos", []):
    video_url = video.get("url")
    if not video_url:
        continue

    transcript = client.get_transcript(video_url=video_url, transcript_text=True)
    print(transcript.data.transcript)
```

```python
schema = {
    "hook": {
        "type": "String",
        "description": "The opening hook or main attention grabber",
    },
    "products": {
        "type": "Array",
        "description": "Products, brands, or offers mentioned in the video",
    },
}

for video in result.data.videos or []:
    if not video.url:
        continue

    extracted = client.extract_video_data(
        video_url=video.url,
        schema=schema,
        what_to_extract="Extract marketing hooks and mentioned products.",
        transcribe=True,
    )
    print(video.url, extracted.data)
```

---

## TikTok Keyword Search

TikTok keyword search also runs as a background job. `search_tiktok` waits and returns the first page; `submit_tiktok_search` returns a handle instead. Page further with `get_tiktok_search(task_id, cursor=...)`, as for profiles.

```python
result = client.search_tiktok(
    query="ai tools",
    max_results=100,
    sort_by="most_liked",
    published_within="this_month",
    min_views=1000,
    limit=50,
)

for item in result.data.results or []:
    print(item.description, item.published_at, item.stats.views if item.stats else None, item.url)

print(result.data.stats.sort_by, result.data.stats.published_within)  # what the search actually ran with
```

| Parameter | Type | Description |
|---|---|---|
| `query` | `str` | Keyword phrase (at least 2 characters) |
| `max_results` | `int` | Cap on merged results. `0` or omitted means no cap. |
| `parallel_search_slices` | `int` | `1`-`4` concurrent search chains, deduplicated. More slices return more unique videos but bill up to N times the residential pages. |
| `sort_by` | `str` | `"relevance"`, `"most_liked"` or `"newest"`, applied by TikTok |
| `published_within` | `str` | `"all"`, `"past_24_hours"`, `"this_week"`, `"this_month"`, `"last_3_months"` or `"last_6_months"` (rolling windows) |
| `after_datetime` / `before_datetime` | `str` / `date` / `datetime` | Exact publish-date bounds |
| `min_likes` / `max_likes` / `min_views` / `max_views` | `int` | Engagement filters |
| `webhook_url` | `str` | Optional; passed through to the API (`""` opts out of your account default) |

Without `sort_by`, results are sorted newest first. If you set `after_datetime` but not `published_within`, the smallest window that covers `after_datetime` is picked automatically. `parallel_search_slices` is not a time filter; use `published_within` or the datetime bounds for that. Completed tasks may include a short-lived `download_url` for the full JSON payload.

---

## Tweet Claim Analysis

```python
resp = client.get_tweet_statement(tweet_id="1234567890123456789")

print(resp.data.final_statement)
print(resp.data.claim_type)
```

Videos attached to the tweet (or to the tweet it quotes) are transcribed in full, so this also runs as a [background job](#background-jobs). To start it without waiting, use `submit_tweet_statement(tweet_id=...)`, then call `.result()` on the handle.

---

## Semantic Search

Search across your uploaded files using natural language. Results are ranked by AI relevance, not keyword matching.

### Search YouTube videos

Search across all of YouTube (not limited to indexed videos). This performs a standard YouTube search and applies AI reranking to the results (no vector search).

```python
results = client.search_youtube(
    query="how to train a neural network from scratch",
    start_year=2023,
    max_results=5,
)

print(f"Found {results.data.total_found} results")
print(results.data.explanation)

for r in results.data.results:
    print(f"{r.title} (score: {r.relevance_score})")
    print(f"  {r.transcript_summary}")
```

> `search_videos` still works as a deprecated alias for `search_youtube` (the endpoint moved from `/search/video` to `/youtube/search`).

| Parameter | Type | Description |
|---|---|---|
| `query` | `str` | Natural-language search query |
| `use_enhanced_search` | `bool` | AI-enhanced ranking (default: `True`) |
| `start_year` / `end_year` | `int` | Filter by publish date |
| `focus` | `str` | `"relevance"` (default), `"popularity"`, or `"brevity"` |
| `duration` | `int` | Filter by video duration in seconds |
| `max_results` | `int` | Max candidate videos to analyse/return (caps cost; defaults to plan ceiling) |
| `include_usage` | `bool` | Attach a per-call `usage` block to the response |

### Search uploaded files

```python
results = client.search_files(
    query="customer feedback about pricing",
    namespace_ids=["ns_client_calls"],  # optional: scope to specific namespaces
)

for r in results.data.results:
    print(f"{r.name} (score: {r.relevance_score})")
    print(f"  Timestamps: {r.timestamps}")
    print(f"  {r.relevant_text}")
```

---

## File Uploads

Upload audio or video files for persistent storage. Once processed, files can be transcribed, analyzed, searched, and used for extraction -- just like online videos.

### Upload and process

```python
result = client.upload_file("./meeting.mp4", wait_for_completion=True)
file_id = result["file_id"]
print(result["file_status"])  # "completed"
```

Set `wait_for_completion=False` (default) to upload in the background and poll later.

### Retrieve a file and its transcript

```python
resp = client.get_file(file_id)
info = resp.data.file_info

print(f"{info.name} ({info.duration}s, {info.status})")
print(f"Namespaces: {[ns.name for ns in info.namespaces]}")

for segment in resp.data.transcript:
    print(f"[{segment.start:.1f}s] {segment.text}")
```

### List and filter files

```python
resp = client.get_files(limit=20, status="completed")
for f in resp.data.files:
    print(f"{f.name} -- {f.status}")

# Filter by namespace
resp = client.get_files(namespace_id="ns_client_calls")
```

### File management

```python
client.get_file_url(file_id)            # signed download URL
client.retry_file_processing(file_id)   # retry after failure
client.cancel_file_upload(file_id)      # cancel in-progress upload
client.delete_file(file_id)             # permanently delete
```

---

## Namespaces

Organize uploaded files into namespaces. Use them to group content by project, client, topic, or any other category -- then scope searches and listings to specific namespaces.

```python
# Create
ns = client.create_namespace(name="Client Calls")
print(ns.data.id)  # "ns_abc123"

# List all
for ns in client.get_namespaces().data:
    print(f"{ns.id}: {ns.name}")

# Rename
client.update_namespace("ns_abc123", name="Sales Calls")

# Upload a file into a namespace
client.upload_file("./call.mp3", namespace_ids=["ns_abc123"])

# Reassign a file's namespaces
resp = client.update_file_namespaces(file_id, namespace_ids=["ns_abc123", "ns_def456"])
print(resp.data.namespaces)  # updated namespace list

# Delete (files are unlinked, not deleted)
client.delete_namespace("ns_abc123")
```

---

## Error Handling

Every API error maps to a specific exception you can catch:

```python
from vidnavigator import VidNavigatorClient, RateLimitExceeded, NotFoundError

client = VidNavigatorClient()

try:
    client.get_file("nonexistent-id")
except NotFoundError:
    print("File not found")
except RateLimitExceeded:
    print("Rate limit hit -- slow down")
```

| Exception | Status | When |
|---|---|---|
| `BadRequestError` | 400 | Invalid parameters |
| `AuthenticationError` | 401 | Missing or invalid API key |
| `PaymentRequiredError` | 402 | Usage limit reached -- upgrade required |
| `AccessDeniedError` | 403 | Insufficient permissions |
| `NotFoundError` | 404 | Resource not found (including an unknown or expired job `task_id`) |
| `StorageQuotaExceededError` | 413 | Storage quota exceeded |
| `RateLimitExceeded` | 429 | Too many requests |
| `TooManyActiveJobsError` | 429 | Too many background jobs already running. Subclass of `RateLimitExceeded`. |
| `GeoRestrictedError` | 451 | Content unavailable in your region |
| `SystemOverloadError` | 503 | Temporary overload (check `.retry_after_seconds`) |
| `ServerError` | 5xx | Unexpected server error |
| `AsyncJobTimeoutError` | -- | A blocking call or `job.result()` hit its `timeout`; the job keeps running (use `.task_id` or `.job` to resume) |
| `WebhookSignatureError` | -- | A webhook delivery failed signature or timestamp verification |
| `VidNavigatorError` | -- | Base class for all errors |

API exceptions also expose the details of the error response:

```python
from vidnavigator import BadRequestError

try:
    client.extract_video_data(video_url=url, schema={"x": {"type": "Nope", "description": "?"}})
except BadRequestError as exc:
    print(exc.status_code)  # 400
    print(exc.error_code)   # "invalid_schema" -- machine-readable, safe to branch on
    print(exc.docs_url)     # link to the relevant docs, when provided
    print(exc.payload)      # the full JSON error body
```

The same exceptions are raised when a background job fails, built from the job's `error` object.

---

## Usage & Billing

```python
usage = client.get_usage().data

print(f"Credits: {usage.credits.monthly_remaining} / {usage.credits.monthly_total}")
print(f"Storage: {usage.storage.used_formatted} / {usage.storage.limit_formatted}")

if usage.usage:
    print(f"Standard requests: {usage.usage.standard_request.used}")
    print(f"Residential requests: {usage.usage.residential_request.used}")
    print(f"Search requests: {usage.usage.search_request.used}")
    print(f"Analysis requests: {usage.usage.analysis_request.used}")
    print(f"Transcription hours: {usage.usage.transcription_hour.used}")
```

---

## Configuration

```python
client = VidNavigatorClient(
    api_key="YOUR_API_KEY",       # or set VIDNAVIGATOR_API_KEY env var
    base_url="https://...",       # override for staging / self-hosted
    timeout=60,                   # request timeout in seconds (default: 30)
    session=my_requests_session,  # bring your own requests.Session
)
```

The client's `timeout` applies to each HTTP request. It is separate from the `timeout` argument of blocking job methods such as `transcribe_video(timeout=...)`, which limits how long to wait for the job as a whole.

The client can be used as a context manager to automatically close the HTTP session:

```python
with VidNavigatorClient() as client:
    resp = client.get_transcript(video_url="...")
    print(resp.data.transcript)
```

---

## Requirements

- Python 3.7+
- [`requests`](https://pypi.org/project/requests/) >= 2.31
- [`pydantic`](https://pypi.org/project/pydantic/) >= 1.10 (v1 and v2 both supported)

---

## Documentation

Full API reference and guides: **[docs.vidnavigator.com](https://docs.vidnavigator.com)**

---

## License

Apache License 2.0 -- see [LICENSE](LICENSE) for details.
