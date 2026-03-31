# VidNavigator Python SDK

The official Python client for the [VidNavigator Developer API](https://docs.vidnavigator.com) -- transcribe, analyze, search, and extract structured data from video and audio at scale.

[![PyPI version](https://img.shields.io/pypi/v/vidnavigator)](https://pypi.org/project/vidnavigator/)
[![Python](https://img.shields.io/pypi/pyversions/vidnavigator)](https://pypi.org/project/vidnavigator/)
[![License](https://img.shields.io/pypi/l/vidnavigator)](https://github.com/vidnavigator/vidnavigator-python/blob/main/LICENSE)

---

## Features

- **Transcripts** -- YouTube, Vimeo, X/Twitter, TikTok, Instagram, and more. Segments with timestamps or plain text.
- **Speech-to-Text** -- Transcribe any online video (including carousel / multi-video posts).
- **AI Analysis** -- Summaries, people, places, key subjects, and natural-language Q&A over any transcript.
- **Semantic Search** -- Find relevant videos or uploaded files by meaning, not keywords.
- **Structured Extraction** -- Define a JSON schema and pull structured data from any transcript.
- **File Uploads** -- Upload audio/video files for persistent storage, transcription, analysis, and search.
- **Namespaces** -- Organize uploaded files into namespaces and scope searches accordingly.
- **Fully Typed** -- Pydantic response models with full IDE autocompletion (compatible with Pydantic v1 and v2).

---

## Installation

```bash
pip install vidnavigator
```

> Requires Python 3.7+

---

## Quick Start

```python
from vidnavigator import VidNavigatorClient

client = VidNavigatorClient(api_key="YOUR_API_KEY")
# Or set the VIDNAVIGATOR_API_KEY environment variable and omit api_key.
```

### Get a transcript

```python
resp = client.get_youtube_transcript(
    video_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
)
print(resp.data.video_info.title)

for segment in resp.data.transcript:
    print(f"[{segment.start:.1f}s] {segment.text}")
```

Pass `transcript_text=True` to receive the transcript as a single string instead of timed segments.
Use `get_transcript()` for non-YouTube URLs (Vimeo, X/Twitter, TikTok, etc.).

### Analyze a video

```python
resp = client.analyze_video(
    video_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    query="What is the main message of this video?",
)
analysis = resp.data.transcript_analysis
print(analysis.summary)
print(analysis.query_answer.answer)
```

### Search across indexed videos

```python
results = client.search_videos(query="machine learning tutorial")
for r in results.data.results:
    print(f"{r.title}  (score: {r.relevance_score})")
```

### Extract structured data

```python
resp = client.extract_video_data(
    video_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    schema={
        "mood": {"type": "String", "description": "Overall mood in one word"},
        "has_lyrics": {"type": "Boolean", "description": "Whether the video contains lyrics"},
    },
    what_to_extract="Infer from the transcript only.",
)
print(resp.data)  # {"mood": "upbeat", "has_lyrics": true}
```

### Upload and manage files

```python
result = client.upload_file("./meeting.mp4", wait_for_completion=True)
file_id = result["file_id"]

# Retrieve file details and transcript
file_resp = client.get_file(file_id)
print(file_resp.data.file_info.name)
print(file_resp.data.transcript)

# Analyze the uploaded file
analysis = client.analyze_file(file_id=file_id, query="Action items from this meeting?")
print(analysis.data.transcript_analysis.summary)

# Extract structured data
extracted = client.extract_file_data(
    file_id=file_id,
    schema={"action_items": {"type": "Array", "description": "List of action items"}},
)
print(extracted.data)
```

### Organize with namespaces

```python
# Create a namespace
ns = client.create_namespace(name="Client Calls")

# Upload into that namespace
client.upload_file("./call.mp3", namespace_ids=[ns.data.id])

# List files filtered by namespace
files = client.get_files(namespace_id=ns.data.id)

# Search only within a namespace
results = client.search_files(query="pricing discussion", namespace_ids=[ns.data.id])

# Reassign a file to different namespaces
client.update_file_namespaces(file_id, namespace_ids=[ns.data.id])
```

---

## API Reference

All methods return typed Pydantic models with full IDE autocompletion.

### Transcripts

| Method | Description |
|---|---|
| `get_youtube_transcript(video_url, ...)` | Get transcript for a YouTube video |
| `get_transcript(video_url, ...)` | Get transcript for non-YouTube videos (Vimeo, X, TikTok, etc.) |
| `transcribe_video(video_url, ...)` | Speech-to-text transcription for any online video |

**Common parameters:** `language`, `transcript_text`, `metadata_only`, `fallback_to_metadata`

### Analysis

| Method | Description |
|---|---|
| `analyze_video(video_url, query=, ...)` | AI analysis of an online video transcript |
| `analyze_file(file_id, query=, ...)` | AI analysis of an uploaded file's transcript |

### Extraction

| Method | Description |
|---|---|
| `extract_video_data(video_url, schema, ...)` | Extract structured data from a video transcript |
| `extract_file_data(file_id, schema, ...)` | Extract structured data from a file transcript |

### Search

| Method | Description |
|---|---|
| `search_videos(query, ...)` | Semantic search across indexed YouTube videos |
| `search_files(query, namespace_ids=, ...)` | Semantic search across uploaded files |

### Files

| Method | Description |
|---|---|
| `upload_file(file_path, ...)` | Upload audio/video for processing |
| `get_files(limit=, offset=, status=, namespace_id=)` | List uploaded files (with namespace filtering) |
| `get_file(file_id, transcript_text=)` | Get file details and transcript |
| `get_file_url(file_id)` | Get a signed download URL |
| `retry_file_processing(file_id)` | Retry a failed upload |
| `cancel_file_upload(file_id)` | Cancel an in-progress upload |
| `delete_file(file_id)` | Delete an uploaded file |

### Namespaces

| Method | Description |
|---|---|
| `get_namespaces()` | List all namespaces |
| `create_namespace(name)` | Create a new namespace |
| `update_namespace(namespace_id, name)` | Rename a namespace |
| `delete_namespace(namespace_id)` | Delete a namespace |
| `update_file_namespaces(file_id, namespace_ids)` | Reassign a file's namespaces |

### System

| Method | Description |
|---|---|
| `get_usage()` | Credits, storage, and billing info |
| `health_check()` | API health status |

---

## Error Handling

Every API error is mapped to a specific exception class so you can handle each case precisely:

```python
from vidnavigator import VidNavigatorClient, RateLimitExceeded, NotFoundError

client = VidNavigatorClient()

try:
    client.get_file("nonexistent-id")
except NotFoundError:
    print("File not found")
except RateLimitExceeded:
    print("Slow down -- rate limit hit")
```

| Exception | HTTP Status | Meaning |
|---|---|---|
| `BadRequestError` | 400 | Invalid parameters |
| `AuthenticationError` | 401 | Missing or invalid API key |
| `PaymentRequiredError` | 402 | Usage limit reached |
| `AccessDeniedError` | 403 | Insufficient permissions |
| `NotFoundError` | 404 | Resource not found |
| `StorageQuotaExceededError` | 413 | Storage quota exceeded |
| `RateLimitExceeded` | 429 | Too many requests |
| `GeoRestrictedError` | 451 | Content not available in your region |
| `SystemOverloadError` | 503 | Temporary overload (check `.retry_after_seconds`) |
| `ServerError` | 5xx | Unexpected server error |
| `VidNavigatorError` | -- | Base class for all SDK errors |

---

## Context Manager

The client can be used as a context manager to ensure the HTTP session is closed:

```python
with VidNavigatorClient(api_key="YOUR_API_KEY") as client:
    resp = client.get_youtube_transcript(video_url="https://youtube.com/watch?v=...")
    print(resp.data.transcript)
```

---

## Configuration

```python
client = VidNavigatorClient(
    api_key="YOUR_API_KEY",       # or set VIDNAVIGATOR_API_KEY env var
    base_url="https://...",       # override for staging/self-hosted
    timeout=60,                   # request timeout in seconds (default: 30)
    session=my_requests_session,  # bring your own requests.Session
)
```

---

## Documentation

Full API reference and guides: **[docs.vidnavigator.com](https://docs.vidnavigator.com)**

---

## License

Apache License 2.0 -- see [LICENSE](LICENSE) for details.
