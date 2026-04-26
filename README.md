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
| TikTok profile scraping | Yes | -- |
| Tweet claim analysis | Yes | -- |

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

### YouTube

```python
resp = client.get_youtube_transcript(
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

### Other platforms (Vimeo, X/Twitter, TikTok, etc.)

For most non-YouTube platforms, you can use either `get_transcript` (fast, caption-based) or `transcribe_video` (speech-to-text). **Note:** Instagram only supports `transcribe_video`.

```python
# TikTok (can use get_transcript or transcribe_video)
resp = client.get_transcript(
    video_url="https://www.tiktok.com/@user/video/1234567890",
)
```

### Plain text instead of segments

```python
resp = client.get_youtube_transcript(
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

## TikTok Profile Scraping

TikTok profile scraping is asynchronous. Submit the scrape first, then poll until the task is no longer `processing` before reading videos:

```python
import time

task = client.submit_tiktok_profile_scrape(
    profile_url="https://www.tiktok.com/@tiktok",
    max_posts=100,
    after_date="2024-01-01",
)

task_id = task.data.task_id

while True:
    result = client.get_tiktok_profile_scrape(task_id, limit=50)
    if result.data.task_status != "processing":
        break
    time.sleep(5)

if result.data.task_status == "failed":
    raise RuntimeError(result.data.error_message or "TikTok scrape failed")
```

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

`after_date` and `before_date` use `YYYY-MM-DD` format. You can pass strings in that format, or Python `date` / `datetime` objects. In typed SDK responses, `video.published_at` is parsed as a Python `datetime`, and numeric fields such as `views`, `likes`, `reposts`, and `comments` are integers.

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

## Tweet Claim Analysis

```python
resp = client.get_tweet_statement(tweet_id="1234567890123456789")

print(resp.data.final_statement)
print(resp.data.claim_type)
```

---

## Semantic Search

Search across your indexed videos or uploaded files using natural language. Results are ranked by AI relevance, not keyword matching.

### Search videos

```python
results = client.search_videos(
    query="how to train a neural network from scratch",
    start_year=2023,
)

print(f"Found {results.data.total_found} results")
print(results.data.explanation)

for r in results.data.results:
    print(f"{r.title} (score: {r.relevance_score})")
    print(f"  {r.transcript_summary}")
```

| Parameter | Type | Description |
|---|---|---|
| `query` | `str` | Natural-language search query |
| `use_enhanced_search` | `bool` | AI-enhanced ranking (default: `True`) |
| `start_year` / `end_year` | `int` | Filter by publish date |
| `focus` | `str` | `"relevance"` (default) or `"recency"` |
| `duration` | `int` | Filter by video duration in seconds |

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
| `NotFoundError` | 404 | Resource not found |
| `StorageQuotaExceededError` | 413 | Storage quota exceeded |
| `RateLimitExceeded` | 429 | Too many requests |
| `GeoRestrictedError` | 451 | Content unavailable in your region |
| `SystemOverloadError` | 503 | Temporary overload (check `.retry_after_seconds`) |
| `ServerError` | 5xx | Unexpected server error |
| `VidNavigatorError` | -- | Base class for all errors |

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

The client can be used as a context manager to automatically close the HTTP session:

```python
with VidNavigatorClient() as client:
    resp = client.get_youtube_transcript(video_url="...")
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
