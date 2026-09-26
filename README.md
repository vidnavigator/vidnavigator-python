# VidNavigator Python SDK

The official Python client for the [VidNavigator Developer API](https://docs.vidnavigator.com): transcribe, analyze, search, and extract structured data from video and audio at scale.

[![PyPI version](https://img.shields.io/pypi/v/vidnavigator)](https://pypi.org/project/vidnavigator/)
[![Python](https://img.shields.io/pypi/pyversions/vidnavigator)](https://pypi.org/project/vidnavigator/)
[![License](https://img.shields.io/pypi/l/vidnavigator)](https://github.com/vidnavigator/vidnavigator-python/blob/main/LICENSE)

---

## Contents

- [Installation](#installation) · [Authentication](#authentication) · [Quick start](#quick-start) · [Which method should I use?](#which-method-should-i-use)
- **Online videos:** [Transcripts](#transcripts) · [AI analysis](#ai-analysis) · [Structured extraction](#structured-extraction) · [Tweet claim analysis](#tweet-claim-analysis)
- **Long-running work:** [Background jobs](#background-jobs) · [Recipes](#recipes) · [Webhooks](#webhooks)
- **TikTok:** [Profile scraping](#tiktok-profile-scraping) · [Keyword search](#tiktok-keyword-search)
- **Your own files:** [Semantic search](#semantic-search) · [File uploads](#file-uploads) · [Namespaces](#namespaces)
- **Reference:** [Per-call usage](#per-call-usage) · [Usage & billing](#usage--billing) · [Error handling](#error-handling) · [Configuration](#configuration) · [Upgrading from 1.x](#upgrading-from-1x)

---

## What You Can Do

| Capability | Online Videos | Uploaded Files |
|---|:---:|:---:|
| Transcripts (segments with timestamps or plain text) | Yes | Yes |
| AI analysis (summary, people, places, key subjects, Q&A) | Yes | Yes |
| Structured data extraction (your custom schema) | Yes | Yes |
| Semantic search across content | Yes (YouTube) | Yes |
| File upload, storage, and management | -- | Yes |
| Namespace organization and scoped search | -- | Yes |
| TikTok profile scraping and keyword search | Yes | -- |
| Tweet claim analysis | Yes | -- |
| Background jobs for long media, with optional signed webhooks | Yes | -- |

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

> **Transcript** = fast extraction of the platform's own captions, via `get_transcript`. **Transcribe** = speech-to-text by AI models, via `transcribe_video`. Use it when captions are unavailable.

**Supported upload formats:** mp4, webm, mov, avi, wmv, flv, mkv, m4a, mp3, mpeg, mpga, wav.

**Fully typed:** every response is a Pydantic model with IDE autocompletion. Compatible with both Pydantic v1 and v2.

---

## Installation

```bash
pip install vidnavigator
```

Requires Python 3.7+.

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

## Quick Start

```python
from vidnavigator import VidNavigatorClient

client = VidNavigatorClient()

# 1. Captions of a YouTube video
resp = client.get_transcript(video_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ", transcript_text=True)
print(resp.data.transcript)

# 2. Speech-to-text for a video without captions (any length)
resp = client.transcribe_video(video_url="https://www.instagram.com/reel/C86ZvEaqRmo/", transcript_text=True)
print(resp.data.transcript)

# 3. Structured data from a video
resp = client.extract_video_data(
    video_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    schema={"mood": {"type": "String", "description": "Overall mood in one word"}},
)
print(resp.data)  # {"mood": "upbeat"}
```

---

## Which Method Should I Use?

| I want to... | Use | Returns |
|---|---|---|
| Get the captions of a video (fast, cheap) | `get_transcript` | immediately |
| Transcribe audio when there are no captions (Instagram, TikTok, ...) | `transcribe_video` | when the job finishes |
| Summarize a video or ask a question about it | `analyze_video` | immediately |
| Pull specific fields out of a video into a `dict` | `extract_video_data` | when the job finishes |
| Analyze the claim made in a tweet | `get_tweet_statement` | when the job finishes |
| List a TikTok profile's videos | `scrape_tiktok_profile` | when the job finishes |
| Search TikTok by keyword | `search_tiktok` | when the job finishes |
| Find YouTube videos about a topic | `search_youtube` | immediately |
| Work with your own audio/video files | `upload_file`, then `get_file`, `analyze_file`, `extract_file_data`, `search_files` | immediately |
| Process **many** videos at once | the `submit_*` version of a job method | a job handle, right away |

"When the job finishes" methods run as [background jobs](#background-jobs). They block until the result is ready, however long the media is. Each one also has a `submit_*` version that returns immediately.

---

## Transcripts

### Captions from any supported platform

A single `get_transcript` method handles every supported platform (YouTube, Vimeo, X/Twitter, TikTok, Facebook, Dailymotion, Loom, etc.). The API detects the platform from the URL. **Note:** Instagram has no captions, so use `transcribe_video` instead.

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

Pass `transcript_text=True` to get one plain string instead of segments:

```python
resp = client.get_transcript(video_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ", transcript_text=True)
print(resp.data.transcript)
# "We're no strangers to love. You know the rules and so do I..."
```

`get_transcript` parameters:

| Parameter | Type | Description |
|---|---|---|
| `video_url` | `str` | URL of the video |
| `language` | `str` | ISO 639-1 language code (e.g. `"en"`, `"fr"`) |
| `transcript_text` | `bool` | Return the transcript as a single string instead of segments |
| `metadata_only` | `bool` | Return only video metadata, no transcript |
| `fallback_to_metadata` | `bool` | Return metadata with an empty transcript instead of raising `NotFoundError` when no captions exist |
| `include_usage` | `bool` | Attach a per-call `usage` block (see [Per-call usage](#per-call-usage)) |

> `get_youtube_transcript` still works as a deprecated alias for `get_transcript`.

### Speech-to-text

For videos without captions, `transcribe_video` runs speech-to-text. It runs as a [background job](#background-jobs): the call submits the video, waits until the transcript is ready, and returns it. Long videos work the same way as short ones.

```python
resp = client.transcribe_video(video_url="https://www.instagram.com/reel/C86ZvEaqRmo/")

print(resp.data.video_info.title)
for segment in resp.data.transcript:
    print(f"[{segment.start:.1f}s] {segment.text}")
```

For Instagram carousel posts, pick one video with `?img_index=N` in the URL, or transcribe all of them:

```python
resp = client.transcribe_video(
    video_url="https://www.instagram.com/p/ABC123/",
    all_videos=True,
)

print(resp.data.carousel_info.video_count)
for video in resp.data.videos:
    print(f"Video {video.index} ({video.status}): {video.transcript}")
```

`transcribe_video` parameters:

| Parameter | Type | Description |
|---|---|---|
| `video_url` | `str` | URL of the video (`?img_index=N` selects one video of an Instagram carousel) |
| `transcript_text` | `bool` | Return the transcript as a single string instead of segments |
| `all_videos` | `bool` | Carousel posts only: transcribe every video. Returns `carousel_info` and `videos` instead of `video_info` and `transcript`. |
| `include_usage` | `bool` | Attach a `usage` block to the result |
| `webhook_url` | `str` | Optional; see [Webhooks](#webhooks) |
| `timeout` | `float` | Seconds to wait for the job (default 3600; `None` waits indefinitely). See [Timeouts](#timeouts-never-lose-the-task_id). |

### Captions first, speech-to-text as a fallback

Captions are faster and cheaper than speech-to-text, so a common pattern is to try them first:

```python
from vidnavigator import BadRequestError, NotFoundError

def best_transcript(url):
    try:
        return client.get_transcript(video_url=url, transcript_text=True).data.transcript
    except (NotFoundError, BadRequestError):  # no captions, or a platform without captions
        return client.transcribe_video(video_url=url, transcript_text=True).data.transcript
```

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

for person in analysis.people or []:
    print(f"{person.name} -- {person.context}")
# "Rick Astley -- Singer and performer of the song"

for subject in analysis.key_subjects or []:
    print(f"{subject.name} -- {subject.description}")
# "commitment -- Central theme of never abandoning a loved one"
```

`query` is optional. Without it you get the summary, people, places and key subjects. Pass `transcript_text=True` to also receive the transcript as one string.

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

Describe the fields you want and the API fills them in from the video's transcript. It's useful for building pipelines, populating databases, or feeding downstream systems.

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
            "items": {"type": "String", "description": "A topic"},
        },
        "has_spoken_lyrics": {
            "type": "Boolean",
            "description": "Whether the video contains spoken or sung lyrics",
        },
    },
    what_to_extract="Focus on the tone and content of the lyrics.",
)

print(resp.data)
# {"mood": "upbeat", "main_topics": ["love", "commitment"], "has_spoken_lyrics": True}
```

`extract_video_data` runs as a [background job](#background-jobs). With `transcribe=True` (the default), a video without captions (Instagram, TikTok, Facebook, ...) is transcribed first, however long it is. YouTube videos rely on their captions. Set `transcribe=False` to never run speech-to-text.

The extracted fields are in `resp.data`. `resp.video_info` is not populated for online videos; call `get_transcript(video_url=..., metadata_only=True)` if you also need the metadata.

### Schema format

Each field needs a `type` and a `description`. A schema can have at most 10 top-level fields and 3 levels of nesting.

| `type` | Extra keys | Example value |
|---|---|---|
| `String`, `Number`, `Integer`, `Boolean` | -- | `"upbeat"`, `4.5`, `3`, `True` |
| `Enum` | `enum`: the allowed values | `"positive"` |
| `Array` | `items`: the schema of one element | `["love", "commitment"]` |
| `Object` | `properties`: the sub-fields | `{"name": "Rick", "role": "singer"}` |

```python
schema = {
    "sentiment": {
        "type": "Enum",
        "description": "Overall sentiment of the video",
        "enum": ["positive", "negative", "neutral"],
    },
    "speaker": {
        "type": "Object",
        "description": "The main speaker or singer",
        "properties": {
            "name": {"type": "String", "description": "Their name"},
            "role": {"type": "String", "description": "Their role in the video"},
        },
    },
    "key_takeaway": {"type": "String", "description": "The single most important takeaway"},
}
```

An invalid schema raises `BadRequestError` with `error_code == "invalid_schema"` **before** anything is transcribed or billed.

### From a schema file

Keep schemas in JSON or YAML files and pass `schema_file` instead of `schema`:

```yaml
# meeting-schema.yaml
action_items:
  type: Array
  description: Action items mentioned in the meeting
  items:
    type: String
    description: One action item
decisions_made:
  type: Array
  description: Key decisions that were agreed upon
  items:
    type: String
    description: One decision
```

```python
resp = client.extract_video_data(video_url="...", schema_file="./meeting-schema.yaml")
```

### From an uploaded file

```python
resp = client.extract_file_data(
    file_id="your_file_id",
    schema_file="./meeting-schema.yaml",  # or schema={...}
    what_to_extract="Extract action items and deadlines.",
)
print(resp.data)
```

### Token usage

```python
resp = client.extract_video_data(
    video_url="...",
    schema={"summary": {"type": "String", "description": "One-line summary"}},
    include_usage=True,
)
tokens = resp.usage.analysis_tokens
print(f"LLM tokens: {tokens.total_tokens} (prompt {tokens.prompt_tokens}, completion {tokens.completion_tokens})")
```

---

## Tweet Claim Analysis

```python
resp = client.get_tweet_statement(tweet_id="1585841080431321088")

print(resp.data.final_statement)    # the core claim, in the author's voice
print(resp.data.detailed_analysis)  # claim, context, evidence and stance
print(resp.data.claim_type, resp.data.intent, resp.data.tone)
print(resp.data.topics, resp.data.entities)
print(resp.data.tweet_media_summary)  # summary of attached video/images, if any
```

Videos attached to the tweet (or to the tweet it quotes) are transcribed in full, so this runs as a [background job](#background-jobs) too. `claim_type`, `intent`, `tone`, `emotion` and `authority` are based on the original tweet text only.

---

## Background Jobs

Speech-to-text and TikTok operations run as **background jobs** on the API: submitting one returns a `task_id` immediately, and the result is read by polling. The work happens on VidNavigator's servers, not in your process. The SDK only uses these job endpoints, so media of any length works without special handling.

Each job operation comes in two shapes:

| Operation | Blocking: wait and return the result | Non-blocking: return a job handle |
|---|---|---|
| Speech-to-text | `transcribe_video(...)` | `submit_transcribe_video(...)` |
| Structured extraction | `extract_video_data(...)` | `submit_extract_video_data(...)` |
| Tweet claim analysis | `get_tweet_statement(...)` | `submit_tweet_statement(...)` |
| TikTok profile scrape | `scrape_tiktok_profile(...)` | `submit_tiktok_profile_scrape(...)` |
| TikTok keyword search | `search_tiktok(...)` | `submit_tiktok_search(...)` |

Both shapes take the same parameters, except that `include_usage`, `timeout` and (for TikTok) `limit` are passed to `result()` on a handle.

### Blocking: one call, one result

```python
resp = client.transcribe_video(video_url="https://www.instagram.com/reel/C86ZvEaqRmo/")
print(resp.data.transcript)
```

The call submits the job, polls it until it finishes, and returns the result, raising an exception if the job failed.

### Non-blocking: submit now, collect later

`submit_*` methods return a `Job` handle as soon as the job is accepted:

```python
job = client.submit_transcribe_video(video_url="https://www.instagram.com/reel/C86ZvEaqRmo/")
print(job.task_id)   # "550e8400-e29b-41d4-a716-446655440000", save it
print(job.status())  # "processing"

# ... do other work ...

resp = job.result()  # waits if needed, then returns the same TranscriptResponse as transcribe_video
```

| Member | Description |
|---|---|
| `task_id` | The job's id. Keep it; see [Timeouts](#timeouts-never-lose-the-task_id). |
| `job_type` | `"transcribe"`, `"extract_video"`, `"tweet_statement"`, `"tiktok_profile"` or `"tiktok_search"` |
| `status()` | Polls once and returns the `task_status` (`"processing"`, `"completed"` or `"failed"`) |
| `done()` | Polls once; `True` when the job is `completed` or `failed` |
| `result(...)` | Waits, then returns the same object as the blocking method; raises if the job failed |
| `wait(...)` | Waits, then returns the raw poll response: job metadata, the `request` you sent, `webhook` delivery status |
| `refresh()` | Polls once and returns the raw poll response |
| `webhook_url`, `check_status_url`, `data` | What the API returned when the job was submitted |

`result()` and `wait()` accept:

| Argument | Default | Description |
|---|---|---|
| `timeout` | `3600` | Seconds to wait; `None` waits indefinitely |
| `include_usage` | `False` | Attach the job's `usage` block (available once completed) |
| `poll_interval` | `3` | Seconds between polls |
| `fast_start` | `True` | Poll every second for the first 10 seconds, so short clips return quickly |
| `limit`, `cursor` | -- | TikTok jobs only: which page of results to return |
| `raise_on_failure` | `True` | `wait()` only: pass `False` to get a failed job back instead of an exception |

### How polling works

1. **Submit.** One POST; the API answers with a `task_id`. Errors such as insufficient credit are raised here, before any polling.
2. **Poll.** The SDK fetches the job right away, then every second for 10 seconds, then every 3 seconds. It keeps polling until the status is `completed` or `failed`.
3. **Finish.** A completed job is turned into the typed result; a failed job raises the matching exception.

Polling is free and is not rate-limited. A job's result stays readable for **1 hour after it finishes**, and reading it does not consume it.

### Timeouts: never lose the `task_id`

Blocking calls and `result()` wait up to `timeout` seconds (default one hour). When the timeout passes, they raise `JobTimeoutError`, but the job **keeps running on the server**. The error carries the `task_id` and a ready-to-use handle:

```python
from vidnavigator import JobTimeoutError

try:
    resp = client.transcribe_video(video_url=url, timeout=600)
except JobTimeoutError as exc:
    print("Still running:", exc.task_id)
    resp = exc.job.result()  # keep waiting on the same job
```

Later, or from another process, rebuild the handle from a saved id with `resume_job`:

```python
job = client.resume_job("transcribe", task_id)
if job.done():
    resp = job.result()
```

### Failures

A failed job reports an `error` object with an `error` code, a `message` and an `http_status`. The SDK raises the exception matching that status, so the same `except` clauses work everywhere:

```python
from vidnavigator import BadRequestError, PaymentRequiredError, VidNavigatorError

try:
    resp = client.transcribe_video(video_url=url)
except PaymentRequiredError:
    print("Out of transcription credit")
except BadRequestError as exc:
    print(exc.error_code, exc)  # e.g. "unsupported_platform"
except VidNavigatorError as exc:
    print("Job failed:", exc)
```

To inspect a failure without an exception, use `job.wait(raise_on_failure=False)` and read `resp.data.error`. A failed job has all its charges reverted.

### Submit-time errors

Some errors happen before a job exists. No task is created, so there is nothing to poll:

| Exception | Status | When |
|---|---|---|
| `PaymentRequiredError` | 402 | Not enough credit to start the job. It can also be raised by `result()` or a blocking call when the job runs out of credit while running. |
| `TooManyActiveJobsError` (subclass of `RateLimitExceeded`) | 429 | Too many jobs already running for your account; retry once some finish ([recipe](#stay-under-the-running-job-limit)) |
| `BadRequestError` | 400 | Invalid parameters, an invalid extraction schema, or a non-public `webhook_url` |

### Result types

| Operation | Returned by the blocking method and by `result()` |
|---|---|
| Transcribe | `TranscriptResponse` (`data.video_info`, `data.transcript`), or `TranscribeAllVideosResponse` with `all_videos=True` |
| Extract | `ExtractionApiResponse` (`data` is a `dict` matching your schema) |
| Tweet | `TweetStatementResponse` (`data.final_statement`, `data.detailed_analysis`, ...) |
| TikTok profile / search | `TikTokProfileResponse` / `TikTokSearchResponse`: the first page of results |

---

## Recipes

### Process many videos at once

Submit every job first, then collect the results. Submitting takes a fraction of a second per job, and all the jobs then run **at the same time on the server**:

```python
urls = [
    "https://www.tiktok.com/@a/video/1",
    "https://www.tiktok.com/@b/video/2",
    "https://www.tiktok.com/@c/video/3",
]

jobs = [client.submit_transcribe_video(video_url=url, transcript_text=True) for url in urls]
results = [job.result() for job in jobs]

for url, resp in zip(urls, results):
    print(url, resp.data.transcript[:80])
```

Collecting the results one after the other doesn't slow things down: while you wait on the first job, the others keep running. With jobs that take 60 s, 40 s and 90 s, the whole batch takes about **90 s, the slowest job**. Calling the blocking `transcribe_video` in a loop would take 60 + 40 + 90 = 190 s, because each job would only start after the previous one finished.

If one job may fail without stopping the batch, catch errors per job:

```python
from vidnavigator import VidNavigatorError

for url, job in zip(urls, jobs):
    try:
        print(url, job.result().data.transcript[:80])
    except VidNavigatorError as exc:
        print(url, "failed:", exc.error_code, exc)
```

### Handle results as soon as they finish

`[job.result() for job in jobs]` returns results in submission order. To act on each job the moment it finishes, check them in turn:

```python
import time

pending = list(jobs)
while pending:
    for job in list(pending):
        if job.done():            # one free poll
            handle(job.result())  # already finished: returns immediately
            pending.remove(job)
    time.sleep(3)
```

### Stay under the running-job limit

Your account can only run a certain number of jobs at once. Past that limit, a submit raises `TooManyActiveJobsError` and no task is created. For large batches, keep a bounded number of jobs running and submit the next one when a slot frees up:

```python
import time
from vidnavigator import TooManyActiveJobsError, VidNavigatorError

MAX_RUNNING = 5
queue = list(urls)
running = []  # (url, job) pairs
results, errors = {}, {}

while queue or running:
    # Fill free slots
    while queue and len(running) < MAX_RUNNING:
        try:
            running.append((queue[0], client.submit_transcribe_video(video_url=queue[0])))
            queue.pop(0)
        except TooManyActiveJobsError:
            break  # the account is at its limit; retry after some jobs finish

    # Collect finished jobs
    for url, job in list(running):
        if job.done():
            try:
                results[url] = job.result()
            except VidNavigatorError as exc:
                errors[url] = exc
            running.remove((url, job))

    time.sleep(3)
```

### Survive a restart

A job keeps running if your process stops, and its result stays readable for 1 hour after it finishes. Save the `task_id` when you submit, and resume with `resume_job`:

```python
import json

job = client.submit_extract_video_data(video_url=url, schema=schema)
with open("jobs.json", "w") as f:
    json.dump({"job_type": job.job_type, "task_id": job.task_id}, f)

# ... after a restart ...
with open("jobs.json") as f:
    saved = json.load(f)
resp = client.resume_job(saved["job_type"], saved["task_id"]).result()
```

### Transcribe every video of a TikTok profile

```python
profile = client.scrape_tiktok_profile(profile_url="https://www.tiktok.com/@tiktok", max_posts=20, limit=20)

jobs = [
    client.submit_transcribe_video(video_url=video.url, transcript_text=True)
    for video in profile.data.videos or []
    if video.url
]
for job in jobs:
    print(job.result().data.transcript[:80])
```

### Get notified instead of polling

Pass a `webhook_url` and let VidNavigator call your server when each job finishes. See [Webhooks](#webhooks).

---

## Webhooks

A background job can call your server when it finishes. Every job method, blocking or `submit_*`, accepts a `webhook_url` and passes it through to the API unchanged. **Webhooks are optional:** polling always works, whether or not a webhook is configured.

```python
job = client.submit_extract_video_data(
    video_url="https://www.tiktok.com/@user/video/1234567890",
    schema={"summary": {"type": "String", "description": "One-line summary"}},
    webhook_url="https://example.com/hooks/vidnavigator",
)
```

- The URL must be a publicly reachable `https` address. Private, loopback and link-local hosts are rejected with `BadRequestError`.
- You can also set an account-level default webhook in **Studio → API**. A per-request `webhook_url` overrides it, and `webhook_url=""` opts a single job out of it.
- `job.webhook_url` shows which webhook the job will call (`None` if none).
- For TikTok jobs, the event is only a notification: `event.data.result` holds `stats` and `download_url_available`, and you read the videos with the job handle (`client.resume_job("tiktok_search", event.data.task_id).result()`).
- If a result is larger than 256 KB, it is left out of the event (`data.result_truncated` is `True`).

### Receive and verify deliveries

Deliveries are signed with HMAC-SHA256 using your signing secret. `construct_webhook_event` checks the signature and the timestamp, then returns a typed `WebhookEvent`. Always pass the **raw** request body, not re-serialized JSON:

```python
from flask import Flask, request
from vidnavigator import VidNavigatorClient, WebhookSignatureError, construct_webhook_event

app = Flask(__name__)
client = VidNavigatorClient()
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
        # The job handle gives the typed result, even when the event omits it
        resp = client.resume_job("transcribe", event.data.task_id).result()
        save_transcript(event.data.task_id, resp.data.transcript)
    elif event.type.endswith(".failed"):
        print(event.data.task_id, event.data.error.error, event.data.error.message)

    return "", 200
```

`event.data.result` also holds the result as a plain `dict` (unless it was truncated), if you'd rather skip the extra request.

| Event types | Sent when |
|---|---|
| `transcribe.completed` / `transcribe.failed` | A speech-to-text job finishes |
| `extract_video.completed` / `extract_video.failed` | An extraction job finishes |
| `tweet_statement.completed` / `tweet_statement.failed` | A tweet analysis finishes |
| `tiktok_profile.completed` / `tiktok_profile.failed` | A profile scrape finishes |
| `tiktok_search.completed` / `tiktok_search.failed` | A keyword search finishes |

`construct_webhook_event` rejects deliveries whose timestamp is more than 5 minutes from the current time. Change the window with `tolerance_seconds=` (or pass `None` to skip the check). To verify without parsing, use `verify_webhook_signature(body, header, secret)`, which raises the same `WebhookSignatureError`.

Delivery is at-least-once and best effort: up to 5 attempts over about 13 minutes. Return a 2xx response quickly, deduplicate on `X-VidNavigator-Delivery`, and treat polling as the source of truth. See the [webhooks guide](https://docs.vidnavigator.com/guides/webhooks) for the full contract.

---

## TikTok Profile Scraping

`scrape_tiktok_profile` runs a [background job](#background-jobs) and returns the first page of videos:

```python
result = client.scrape_tiktok_profile(
    profile_url="https://www.tiktok.com/@tiktok",
    max_posts=100,
    after_datetime="2024-01-01",
    limit=50,
)
task_id = result.data.task_id

for video in result.data.videos or []:
    print(video.title, video.published_at, video.likes, video.url)
```

To start the scrape without waiting, use `submit_tiktok_profile_scrape(...)`, then call `job.result(limit=50)` when you want the videos.

| Parameter | Type | Description |
|---|---|---|
| `profile_url` | `str` | Public TikTok profile URL |
| `max_posts` | `int` | Stop once this many matching videos are collected |
| `after_datetime` / `before_datetime` | `str` / `date` / `datetime` | Only include videos published in this window |
| `min_likes` / `max_likes` | `int` | Like-count filters |
| `webhook_url` | `str` | Optional; see [Webhooks](#webhooks) |
| `limit` | `int` | Page size of the returned first page (default 50) |
| `include_usage`, `timeout` | | As for other [job methods](#background-jobs) |

`after_datetime` and `before_datetime` accept `YYYY-MM-DD` strings, ISO datetimes with a timezone, or Python `date` / `datetime` objects. In responses, `video.published_at` is a Python `datetime`, and `views`, `likes`, `reposts` and `comments` are integers.

### Read the remaining pages

```python
pagination = result.data.pagination

while pagination and pagination.has_next:
    page = client.get_tiktok_profile_scrape(task_id, cursor=pagination.next_cursor, limit=50)
    for video in page.data.videos or []:
        print(video.title, video.url)
    pagination = page.data.pagination
```

### Download the full result

Completed scrapes usually include a `download_url`: a short-lived (about 1 hour) link to one JSON file with every video. Calling `get_tiktok_profile_scrape` again creates a fresh link.

```python
import json
from urllib.request import urlopen

if result.data.download_url:
    with urlopen(result.data.download_url) as response:
        full_profile = json.load(response)

    for video in full_profile.get("videos", []):
        print(video.get("title"), video.get("url"))  # plain dicts, not typed models
```

---

## TikTok Keyword Search

`search_tiktok` runs a background job and returns the first page of results. `submit_tiktok_search` returns a handle instead.

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
| `webhook_url` | `str` | Optional; see [Webhooks](#webhooks) |
| `limit` | `int` | Page size of the returned first page (default 50) |
| `include_usage`, `timeout` | | As for other [job methods](#background-jobs) |

Without `sort_by`, results come back newest first. If you set `after_datetime` but not `published_within`, the smallest window covering `after_datetime` is picked automatically. `parallel_search_slices` is not a time filter; use `published_within` or the datetime bounds for that.

Read further pages with `get_tiktok_search(task_id, cursor=...)`, exactly as for [profiles](#read-the-remaining-pages). Completed searches may include a `download_url` with the full JSON result.

---

## Semantic Search

### Search YouTube

Search across all of YouTube. This runs a standard YouTube search, then ranks the results with AI analysis of their transcripts.

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

| Parameter | Type | Description |
|---|---|---|
| `query` | `str` | Natural-language search query |
| `use_enhanced_search` | `bool` | AI-enhanced query (default: `True`) |
| `start_year` / `end_year` | `int` | Filter by publish date |
| `focus` | `str` | `"relevance"` (default), `"popularity"`, or `"brevity"` |
| `duration` | `int` | Filter by video duration in seconds |
| `max_results` | `int` | Max candidate videos to analyze and return; each one is billed, so this caps cost (defaults to your plan ceiling) |
| `include_usage` | `bool` | Attach a per-call `usage` block to the response |

> `search_videos` still works as a deprecated alias for `search_youtube`.

### Search your uploaded files

Search the content of your [uploaded files](#file-uploads) in natural language. Results are ranked by relevance, with the timestamps where the matching content appears:

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

Upload audio or video files for persistent storage. Once processed, files can be transcribed, analyzed, searched, and used for extraction, just like online videos.

### Upload and process

```python
result = client.upload_file("./meeting.mp4", wait_for_completion=True)
file_id = result["file_id"]
print(result["file_status"])  # "completed"
```

With `wait_for_completion=False` (the default), the upload returns immediately and processing continues in the background. Check `get_file(file_id).data.file_info.status` until it is `"completed"`.

### Retrieve a file and its transcript

```python
resp = client.get_file(file_id)  # pass transcript_text=True for a single string
info = resp.data.file_info

print(f"{info.name} ({info.duration}s, {info.status})")
print(f"Namespaces: {[ns.name for ns in info.namespaces or []]}")

for segment in resp.data.transcript or []:
    print(f"[{segment.start:.1f}s] {segment.text}")
```

### List and filter files

```python
resp = client.get_files(limit=20, status="completed")
for f in resp.data.files:
    print(f"{f.name} -- {f.status}")

# Filter by namespace
resp = client.get_files(namespace_id="ns_client_calls")

# Paginate
resp = client.get_files(limit=20, offset=20)
print(resp.data.has_more)
```

### File management

```python
client.get_file_url(file_id)            # signed download URL
client.retry_file_processing(file_id)   # retry after failure
client.cancel_file_upload(file_id)      # cancel in-progress processing
client.delete_file(file_id)             # permanently delete
```

---

## Namespaces

Organize uploaded files into namespaces. Use them to group content by project, client, topic, or any other category, then scope searches and listings to specific namespaces.

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

## Per-call usage

Pass `include_usage=True` to see exactly which meters a call charged, how many credits were deducted, and (for AI features) how many LLM tokens were used.

It is supported by `get_transcript`, `transcribe_video`, `analyze_video`, `analyze_file`, `extract_video_data`, `extract_file_data`, `search_youtube`, `search_files`, `get_tweet_statement`, `scrape_tiktok_profile`, `search_tiktok`, `get_tiktok_profile_scrape`, `get_tiktok_search`, and `job.result(include_usage=True)`. For background jobs, usage appears once the job is `completed`; failed jobs have all their charges reverted.

```python
resp = client.search_youtube(query="react best practices", include_usage=True)

usage = resp.usage
if usage:
    print(f"Credits this call: {usage.total_credits}")

    for charge in usage.charges or []:
        print(f"  {charge.service_type}: {charge.quantity} unit(s), {charge.credits} credits")

    # LLM token tally (analyze / extract / YouTube search / tweet analysis)
    tokens = usage.analysis_tokens
    if tokens:
        print(f"  LLM tokens: {tokens.total_tokens}")
```

| Field | Description |
|---|---|
| `charges` | List of `UsageCharge` (one per meter): `service_type`, `quantity`, `credits`, `waived`, `credits_saved`, and (analysis only) nested `tokens` |
| `total_credits` | Net credits deducted by the call |
| `waived` | Present when a cache-hit sponsorship waived charges (`waived.credits_saved`) |
| `analysis_tokens` | The LLM token counts (`prompt_tokens`, `completion_tokens`, `total_tokens`) |
| `charge_for(service_type)` | The charge entry for one meter, e.g. `usage.charge_for("transcription_hour")` |

Meters: `standard_request`, `residential_request`, `transcription_hour`, `analysis_request`, `search_request` and `scene_analysis_hour`.

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

## Error Handling

Every API error maps to a specific exception, and all of them inherit from `VidNavigatorError`:

```python
from vidnavigator import NotFoundError, RateLimitExceeded, VidNavigatorError

try:
    client.get_file("nonexistent-id")
except NotFoundError:
    print("File not found")
except RateLimitExceeded:
    print("Rate limit hit -- slow down")
except VidNavigatorError as exc:
    print("Something else went wrong:", exc)
```

| Exception | Status | When |
|---|---|---|
| `BadRequestError` | 400 | Invalid parameters or schema |
| `AuthenticationError` | 401 | Missing or invalid API key |
| `PaymentRequiredError` | 402 | Not enough credits; upgrade or top up |
| `AccessDeniedError` | 403 | Insufficient permissions, or content that requires login or age verification |
| `NotFoundError` | 404 | Resource not found, including an unknown or expired job `task_id` |
| `StorageQuotaExceededError` | 413 | Storage quota exceeded |
| `RateLimitExceeded` | 429 | Too many requests |
| `TooManyActiveJobsError` | 429 | Too many background jobs already running. Subclass of `RateLimitExceeded`. |
| `GeoRestrictedError` | 451 | Content unavailable in your region |
| `SystemOverloadError` | 503 | Temporary overload (check `.retry_after_seconds`) |
| `ServerError` | 5xx | Unexpected server error |
| `JobTimeoutError` | -- | A blocking call or `job.result()` hit its `timeout`. The job keeps running; resume with `.job` or `.task_id`. |
| `WebhookSignatureError` | -- | A webhook delivery failed signature or timestamp verification |
| `VidNavigatorError` | -- | Base class for all errors, also raised for network failures |

API exceptions carry the details of the error response:

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

The same exceptions, with the same fields, are raised when a background job fails.

---

## Configuration

```python
client = VidNavigatorClient(
    api_key="YOUR_API_KEY",       # or set VIDNAVIGATOR_API_KEY env var
    base_url="https://...",       # override for staging / self-hosted
    timeout=60,                   # per HTTP request, in seconds (default: 30)
    session=my_requests_session,  # bring your own requests.Session
)
```

The client's `timeout` applies to each HTTP request. It is separate from the `timeout` argument of job methods such as `transcribe_video(timeout=...)`, which limits how long to wait for a whole job.

Use the client as a context manager to close its HTTP session automatically:

```python
with VidNavigatorClient() as client:
    resp = client.get_transcript(video_url="...")
    print(resp.data.transcript)
```

One client can be reused for any number of calls. If you use threads, create one client per thread.

---

## Upgrading from 1.x

Version 2.0 runs speech-to-text and TikTok operations as background jobs. Most code keeps working unchanged. Check these points:

| In 1.x | In 2.0 |
|---|---|
| `transcribe_video`, `extract_video_data` and `get_tweet_statement` made one long HTTP request | They submit a job and poll it. Same arguments and return types, and no media duration limit. They can raise `JobTimeoutError` (default wait: one hour). |
| `extract_video_data(...).video_info` held the video metadata | `video_info` is `None` for online videos; use `get_transcript(video_url=..., metadata_only=True)` |
| `extract_video_data(..., include_usage=True).usage.total_tokens` | Use `usage.analysis_tokens.total_tokens` |
| `submit_tiktok_profile_scrape` / `submit_tiktok_search` returned the submit response | They return a `Job`. `job.data.task_id` still works; **`job.status` is now a method**, so replace `task.status == "success"` checks. |
| Manual polling loops on `get_tiktok_profile_scrape` | `scrape_tiktok_profile(...)`, or `job.result()` on a submitted job |
| `task.data.error_message` on failed TikTok tasks | Deprecated; read `task.data.error` (`error`, `message`, `http_status`), or let `job.result()` raise |
| A 401 raised the generic `VidNavigatorError` | It raises `AuthenticationError` |

New in 2.0: `submit_transcribe_video`, `submit_extract_video_data`, `submit_tweet_statement`, `scrape_tiktok_profile`, `search_tiktok`, `resume_job`, `webhook_url` on every job method, `sort_by` and `published_within` for TikTok search, the webhook helpers, and `status_code` / `error_code` / `docs_url` / `payload` on every API exception.

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
