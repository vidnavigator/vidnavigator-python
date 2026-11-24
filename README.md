# VidNavigator Python SDK

The official Python client for the [VidNavigator Developer API](https://docs.vidnavigator.com): transcribe, watch, search, and extract structured data from video and audio at scale.

[![PyPI version](https://img.shields.io/pypi/v/vidnavigator)](https://pypi.org/project/vidnavigator/)
[![Python](https://img.shields.io/pypi/pyversions/vidnavigator)](https://pypi.org/project/vidnavigator/)
[![License](https://img.shields.io/pypi/l/vidnavigator)](https://github.com/vidnavigator/vidnavigator-python/blob/main/LICENSE)

---

## Contents

- [Installation](#installation) · [Authentication](#authentication) · [Quick start](#quick-start) · [Which method should I use?](#which-method-should-i-use)
- **Online videos:** [Transcripts](#transcripts) · [Watch](#watch) · [Structured extraction](#structured-extraction) · [Tweet claim analysis](#tweet-claim-analysis)
- **Long-running work:** [Background jobs](#background-jobs) · [Recipes](#recipes) · [Async client](#async-client) · [Webhooks](#webhooks)
- **TikTok:** [Profile scraping](#tiktok-profile-scraping) · [Keyword search](#tiktok-keyword-search) · [LIVE search](#tiktok-live-search) · [LIVE room](#tiktok-live-room)
- **Your own files:** [Semantic search](#semantic-search) · [File uploads](#file-uploads) · [Namespaces](#namespaces)
- **Reference:** [Per-call usage](#per-call-usage) · [Usage & billing](#usage--billing) · [Error handling](#error-handling) · [Configuration](#configuration) · [Upgrading to 3.0](#upgrading-to-30) · [Upgrading from 1.x](#upgrading-from-1x)

---

## What You Can Do

| Capability | Online Videos | Uploaded Files |
|---|:---:|:---:|
| Transcripts (segments with timestamps or plain text) | Yes | Yes |
| Scenes: what a video shows, with the text on screen | Yes | -- |
| Structured data extraction: a summary, answers to questions, or the fields of your JSON Schema | Yes | Yes |
| Semantic search across content | Yes (YouTube) | Yes |
| File upload, storage, and management | -- | Yes |
| Namespace organization and scoped search | -- | Yes |
| TikTok profile scraping, keyword search and LIVE search | Yes | -- |
| Tweet claim analysis | Yes | -- |
| Background jobs for long media, with optional signed webhooks | Yes | -- |

## Supported Platforms

| Platform | Transcript | Transcribe (speech-to-text) | Watch (scenes) | Carousel |
|----------|:----------:|:---------------------------:|:--------------:|:--------:|
| YouTube | Yes | Yes | Yes | - |
| Instagram Reels | - | Yes | Yes | Yes |
| Instagram Posts | - | Yes | Yes | Yes (`all_videos`) |
| TikTok | Yes | Yes | Yes | - |
| X / Twitter | Yes | Yes | Yes | - |
| Vimeo | Yes | Yes | Yes | - |
| Facebook | Yes | Yes | Yes | - |
| Dailymotion | Yes | Yes | Yes | - |
| Loom | Yes | Yes | Yes | - |
| Snapchat | Yes, when Snapchat has a transcript | Yes | Yes | Yes (highlights: `img_index`, `all_videos`) |
| Uploaded files | Yes | Yes | - | - |

> **Transcript** = fast extraction of the platform's own captions, via `get_transcript`. **Transcribe** = speech-to-text by AI models, via `transcribe_video`. Use it when captions are unavailable. **Watch** = what the video shows, scene by scene, next to its transcript, via `watch_video`.

**Supported upload formats:** mp4, webm, mov, avi, wmv, flv, mkv, m4a, mp3, mpeg, mpga, wav.

**Fully typed:** every response is a Pydantic model with IDE autocompletion. Compatible with both Pydantic v1 and v2.

---

## Installation

```bash
pip install vidnavigator
```

For the [asyncio client](#async-client), install the `async` extra, which adds [`httpx`](https://pypi.org/project/httpx/):

```bash
pip install "vidnavigator[async]"
```

Requires Python 3.8+.

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

# 3. Structured data from a video (a JSON Schema, or just what_to_extract="...")
resp = client.extract_video_data(
    video_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    schema={"type": "object", "properties": {"mood": {"type": "string", "description": "Overall mood in one word"}}},
)
print(resp.data)  # {"mood": "upbeat"}

# 4. What a video shows, scene by scene, next to what it says
resp = client.watch_video(video_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ")
for scene in resp.data.scenes:
    print(scene.start, scene.end, scene.description, scene.on_screen_text)
```

---

## Which Method Should I Use?

| I want to... | Use | Returns |
|---|---|---|
| Get the captions of a video (fast, cheap) | `get_transcript` | immediately |
| Transcribe audio when there are no captions (Instagram, TikTok, ...) | `transcribe_video` | when the job finishes |
| See what a video shows, scene by scene, with its transcript | `watch_video` | when the job finishes |
| Summarize a video or ask a question about it | `extract_video_data(..., what_to_extract="...")` | when the job finishes |
| Answer from what a video shows as well (text on screen, little or no speech) | `extract_video_data(..., include_scenes=True)` | when the job finishes |
| Pull specific fields out of a video into a `dict` | `extract_video_data` | when the job finishes |
| Analyze the claim made in a tweet | `get_tweet_statement` | when the job finishes |
| List a TikTok profile's videos | `scrape_tiktok_profile` | when the job finishes |
| Search TikTok by keyword | `search_tiktok` | when the job finishes |
| Find TikTok LIVE rooms broadcasting now, with their stream URLs | `search_tiktok_live` | when the job finishes |
| Check one TikTok LIVE room or streamer, with its latest comments | `get_tiktok_live_room` | immediately |
| Find YouTube videos about a topic | `search_youtube` | immediately |
| Work with your own audio/video files | `upload_file`, then `get_file`, `extract_file_data`, `search_files` | immediately |
| Process **many** videos at once | the `submit_*` version of a job method | a job handle, right away |
| Call the API from asyncio code (FastAPI, aiohttp, bots, agents) | [`AsyncVidNavigatorClient`](#async-client) | the same results, awaited |

"When the job finishes" methods run as [background jobs](#background-jobs). They block until the result is ready, however long the media is. Each one also has a `submit_*` version that returns immediately.

---

## Transcripts

### Captions from any supported platform

A single `get_transcript` method handles every supported platform (YouTube, Vimeo, X/Twitter, TikTok, Facebook, Dailymotion, Loom, Snapchat, etc.). The API detects the platform from the URL. **Note:** Instagram has no captions, so use `transcribe_video` instead.

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

## Watch

`watch_video` reads what a video **shows**, next to what it says. The result holds the transcript and a list of scenes: for each one, when it starts and ends, a description of the picture, and the text readable on screen. It works with every platform `get_transcript` and `transcribe_video` support, and runs as a [background job](#background-jobs).

```python
resp = client.watch_video(video_url="https://www.tiktok.com/@nasa/video/7300000000000000000")

for scene in resp.data.scenes:
    print(f"[{scene.start:.0f}s - {scene.end:.0f}s] {scene.description}")
    if scene.on_screen_text:
        print(f"    on screen: {scene.on_screen_text}")
# [4s - 12s] A presenter stands in front of a world map and points at Europe.
#     on screen: BREAKING NEWS

for segment in resp.data.transcript or []:
    print(f"[{segment.start:.1f}s] {segment.text}")

print(resp.data.frames_analyzed)  # number of frames that were analyzed
```

The transcript comes from the platform's captions when it has them, and from speech-to-text otherwise. A YouTube video without captions is transcribed from its audio, like the others. A video without speech is not an error: `transcript` is empty, `transcript_error` says why, and the scenes are returned.

```python
resp = client.watch_video(video_url=url)
if resp.data.transcript_error:
    print(resp.data.transcript_error.error)  # e.g. "transcript_not_available"
print(len(resp.data.scenes), "scenes")
```

`watch_video` parameters:

| Parameter | Type | Description |
|---|---|---|
| `video_url` | `str` | URL of the video (`?img_index=N` selects one video of an Instagram carousel or a Snapchat highlight) |
| `detail` | `str` | How closely the picture is followed: `"low"`, `"auto"` (the default) or `"high"`. The number of frames depends on the video at every level: few on a fixed shot, many on a fast-cut clip. A higher level analyzes more frames when the picture changes often. |
| `include_transcript` | `bool` | Default `True`. `False` returns the scenes only (`transcript` is `None`). |
| `transcript_text` | `bool` | Return the transcript as a single string instead of segments |
| `include_usage` | `bool` | Attach a `usage` block to the result; the frames are its `frame_analysis` charge |
| `webhook_url` | `str` | Optional; see [Webhooks](#webhooks) |
| `timeout` | `float` | Seconds to wait for the job (default 3600; `None` waits indefinitely). See [Timeouts](#timeouts-never-lose-the-task_id). |

To start it without waiting, use the handle, as for any background job:

```python
job = client.watch.submit(video_url=url, detail="high")   # or client.submit_watch_video(...)
print(job.task_id)

resp = job.result(include_usage=True)                     # waits if needed
print(resp.usage.charge_for("frame_analysis").quantity)   # frames charged

job = client.watch.resume(saved_task_id)                  # the same handle, later
```

Errors worth handling: `NotFoundError` with `error_code == "frames_not_available"` (a live stream, or a clip of a few seconds, has no picture to read) and `BadRequestError` with `error_code == "video_too_long"` (videos longer than 2 hours are not accepted, except on YouTube).

---

## Structured Extraction

Say what you want from a video, in plain words with `what_to_extract`, as a standard JSON Schema, or both, and the API fills it in from what the video says and, with `include_scenes=True`, what it shows. Use it for a summary or the answer to a question as much as for building pipelines, populating databases, or feeding downstream systems.

### Summarize a video or ask a question about it

```python
resp = client.extract_video_data(
    video_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    what_to_extract="A three-sentence summary and the answer to: what is the main message of this song?",
)
print(resp.data)
# e.g. {"summary": "The song is a declaration of unwavering commitment...",
#       "main_message": "A promise to never give up on someone..."}
```

The fields are named for you, and `resp.extraction_schema` holds the schema written for them (see [Without a schema](#without-a-schema)). To get the same fields every time, name them in a schema, with what you want in each `description`:

```python
resp = client.extract_video_data(
    video_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    schema={
        "type": "object",
        "properties": {
            "summary": {"type": "string", "description": "A three-sentence summary of the video"},
            "answer": {"type": "string", "description": "The answer to: what is the main message of this song?"},
            "people": {
                "type": "array",
                "description": "The people who appear or are mentioned, each with their role",
                "items": {"type": "string"},
            },
            "key_subjects": {
                "type": "array",
                "description": "The main subjects of the video",
                "items": {"type": "string"},
            },
        },
    },
)
print(resp.data["summary"])
print(resp.data["answer"])
```

### From an online video

```python
resp = client.extract_video_data(
    video_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    schema={
        "type": "object",
        "properties": {
            "mood": {"type": "string", "description": "Overall mood of the video in one word"},
            "main_topics": {
                "type": "array",
                "description": "List of main topics discussed",
                "items": {"type": "string"},
            },
            "has_spoken_lyrics": {
                "type": "boolean",
                "description": "Whether the video contains spoken or sung lyrics",
            },
        },
    },
    what_to_extract="Focus on the tone and content of the lyrics.",
)

print(resp.data)
# {"mood": "upbeat", "main_topics": ["love", "commitment"], "has_spoken_lyrics": True}
```

`extract_video_data` runs as a [background job](#background-jobs). With `transcribe=True` (the default), a video without captions (Instagram, TikTok, Facebook, ...) is transcribed first, however long it is. YouTube videos rely on their captions. Set `transcribe=False` to never run speech-to-text.

The extracted fields are in `resp.data`, and the video's metadata in `resp.video_info`.

With `include_scenes=True` the fields can also be filled from what the video shows, not only from what is said:

```python
resp = client.extract_video_data(
    video_url="https://www.dailymotion.com/video/x84243e",
    schema={
        "type": "object",
        "properties": {
            "dish": {"type": "string", "description": "Name of the dish"},
            "ingredients": {
                "type": "array",
                "description": "Every ingredient, with its quantity",
                "items": {"type": "string"},
            },
        },
    },
    include_scenes=True,
)
print(resp.data["ingredients"])  # read from the text on screen: this video only has music
print(resp.frames_analyzed)      # 30
```

Ask for the scenes when the answer may be on screen rather than spoken (the quantities of a recipe, a price, a slide, a caption), or when the video has little or no speech. When the video has no transcript, or no picture to read, the fields are extracted from the other source and `resp.transcript_error` or `resp.scenes_error` says why.

The scenes are billed per frame analyzed, on top of the extraction: 1 credit per 2,000 frames, with at least 667 frames per hour of video.

### Schema format

`schema` is a standard JSON Schema whose root is an object. Give each property a `type` and a `description` (what to put in it). A schema can have at most 10 fields per level and 3 levels of nesting.

| `type` | Extra keys | Example value |
|---|---|---|
| `string`, `number`, `integer`, `boolean` | -- | `"upbeat"`, `4.5`, `3`, `True` |
| any of them with `enum` | `enum`: the allowed values | `"positive"` |
| `array` | `items`: the schema of one element | `["love", "commitment"]` |
| `object` | `properties`: the sub-fields | `{"name": "Rick", "role": "singer"}` |

```python
schema = {
    "type": "object",
    "properties": {
        "sentiment": {
            "type": "string",
            "description": "Overall sentiment of the video",
            "enum": ["positive", "negative", "neutral"],
        },
        "speaker": {
            "type": "object",
            "description": "The main speaker or singer",
            "properties": {
                "name": {"type": "string", "description": "Their name"},
                "role": {"type": "string", "description": "Their role in the video"},
            },
        },
        "key_takeaway": {"type": "string", "description": "The single most important takeaway"},
    },
}
```

A Pydantic model works as it is: pass `schema=MyModel.model_json_schema()` (its `$defs` and nullable fields are understood). `required` and `additionalProperties` change nothing: a field the video does not give comes back as `None`.

An invalid schema raises `BadRequestError` with `error_code == "invalid_schema"` **before** anything is transcribed or billed.

### Without a schema

Say what you want in plain words with `what_to_extract` alone. The schema is written for you and comes back on `resp.extraction_schema`: pass it as `schema` next time to get the same fields.

```python
resp = client.extract_video_data(
    video_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    what_to_extract="The mood of the song and every topic it touches on",
)
print(resp.data)               # {"mood": "upbeat", "topics": ["love", "commitment"]}
print(resp.extraction_schema)  # {"type": "object", "properties": {"mood": {...}, "topics": {...}}, ...}
```

### Where each value comes from

Every extraction says, beside `data`, the moments of the video each value was taken from: `resp.evidence` maps a field to its moments, each with `start` and `end` in seconds and `in_` (JSON key `in`): `"speech"` (said), `"picture"` (shown or written on screen, with `include_scenes=True`) or `"post"` (the post's own text, without times). A field left empty has no entry.

```python
for moment in resp.evidence.get("topics", []):
    print(moment.in_, moment.start, moment.end)   # speech 12.5 31.0
```

### From a schema file

Keep schemas in JSON or YAML files and pass `schema_file` instead of `schema`:

```yaml
# meeting-schema.yaml
type: object
properties:
  action_items:
    type: array
    description: Action items mentioned in the meeting
    items:
      type: string
  decisions_made:
    type: array
    description: Key decisions that were agreed upon
    items:
      type: string
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

`what_to_extract` alone summarizes a file or answers a question about it, as for a video:

```python
resp = client.extract_file_data(
    file_id="your_file_id",
    what_to_extract="A short summary and the answer to: what are the key action items of this meeting?",
)
```

`include_scenes=True` also uses what the file shows, once its scenes have been analyzed: see [Scenes of a file](#scenes-of-a-file).

### Token usage

```python
resp = client.extract_video_data(
    video_url="...",
    schema={"type": "object", "properties": {"summary": {"type": "string", "description": "One-line summary"}}},
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

With `include_scenes=True`, what the tweet's video and the quoted tweet's video **show** (their scenes, with the text readable on screen) is read as well and used with their transcripts, so a video without speech is summarized from its picture:

```python
resp = client.get_tweet_statement(tweet_id="1585841080431321088", include_scenes=True)

print(resp.data.tweet_media_summary)
print(resp.data.frames_analyzed)       # frames read for the scenes
if resp.data.scenes_error:             # a video's picture could not be read:
    print(resp.data.scenes_error.error)  # it was summarized from its transcript alone
```

`include_scenes` is also accepted by `submit_tweet_statement` and `client.tweet_statement.submit(...)`.

---

## Background Jobs

Speech-to-text, watch and TikTok operations run as **background jobs** on the API: submitting one returns a `task_id` immediately, and the result is read by polling. The work happens on VidNavigator's servers, not in your process. The SDK only uses these job endpoints, so media of any length works without special handling.

Each job operation comes in two shapes:

| Operation | Blocking: wait and return the result | Non-blocking: return a job handle |
|---|---|---|
| Speech-to-text | `transcribe_video(...)` | `submit_transcribe_video(...)` |
| Watch (scenes and transcript) | `watch_video(...)` | `submit_watch_video(...)` |
| Structured extraction | `extract_video_data(...)` | `submit_extract_video_data(...)` |
| Tweet claim analysis | `get_tweet_statement(...)` | `submit_tweet_statement(...)` |
| TikTok profile scrape | `scrape_tiktok_profile(...)` | `submit_tiktok_profile_scrape(...)` |
| TikTok keyword search | `search_tiktok(...)` | `submit_tiktok_search(...)` |
| TikTok LIVE search | `search_tiktok_live(...)` | `submit_tiktok_live_search(...)` |

Both shapes take the same parameters, except that `include_usage`, `timeout` and (for TikTok) `limit` are passed to `result()` on a handle.

### Operation objects

Each operation is also an object, as in the JavaScript SDK. Call it to wait for the result, use `.submit(...)` for a handle, and `.resume(task_id)` to rebuild a handle later:

```python
result = client.tiktok_search(query="grève", country="fr")      # waits, every result
job = client.tiktok_search.submit(query="grève", country="fr")  # returns a Job right away
job = client.tiktok_search.resume(saved_task_id)                # same handle, later
```

The objects are `client.transcribe`, `client.watch`, `client.extract_video`, `client.tweet_statement`, `client.tiktok_profile`, `client.tiktok_search` and `client.tiktok_live_search`. They take the same parameters as the methods in the table above, and the async client has the same ones (`await client.tiktok_search(...)`).

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
| `job_type` | `"transcribe"`, `"watch"`, `"extract_video"`, `"tweet_statement"`, `"tiktok_profile"`, `"tiktok_search"` or `"tiktok_live_search"` |
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

Polling is free, and polls have their own, higher [rate limit](https://docs.vidnavigator.com/api-reference/rate-limiting). A job's result stays readable for **1 hour after it finishes**, and reading it does not consume it.

### Timeouts: never lose the `task_id`

Blocking calls and `result()` wait up to `timeout` seconds (default one hour). When the timeout passes, they raise `TaskTimeoutError`, but the job **keeps running on the server**. The error carries the `task_id` and a ready-to-use handle:

```python
from vidnavigator import TaskTimeoutError

try:
    resp = client.transcribe_video(video_url=url, timeout=600)
except TaskTimeoutError as exc:
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
from vidnavigator import BadRequestError, InsufficientCreditsError, VidNavigatorError

try:
    resp = client.transcribe_video(video_url=url)
except InsufficientCreditsError:
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
| `InsufficientCreditsError` (a `PaymentRequiredError`) | 402 | Not enough credit to start the job (`insufficient_credits`). It can also be raised by `result()` or a blocking call when the job runs out of credit while running. |
| `TooManyActiveJobsError` (subclass of `RateLimitExceededError`) | 429 | Too many jobs already running for your account; retry once some finish ([recipe](#stay-under-the-running-job-limit)) |
| `BadRequestError` | 400 | Invalid parameters, an invalid extraction schema, or a non-public `webhook_url` |

### Result types

| Operation | Returned by the blocking method and by `result()` |
|---|---|
| Transcribe | `TranscriptResponse` (`data.video_info`, `data.transcript`), or `TranscribeAllVideosResponse` with `all_videos=True` |
| Watch | `WatchResponse` (`data.video_info`, `data.transcript`, `data.scenes`, `data.frames_analyzed`) |
| Extract | `ExtractionApiResponse` (`data` is a `dict` matching your schema; `extraction_schema` is the schema written when you gave none) |
| Tweet | `TweetStatementResponse` (`data.final_statement`, `data.detailed_analysis`, ...) |
| TikTok profile / search / LIVE search | `TikTokProfileResponse` / `TikTokSearchResponse` / `TikTokLiveSearchResponse`, with every video / result / room (all pages merged), or one page when you pass `limit` |

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

### Run many jobs from asyncio code

With the [async client](#async-client), `asyncio.gather` submits and waits for all jobs concurrently in a single thread:

```python
results = await asyncio.gather(*(client.transcribe_video(video_url=url) for url in urls))
```

---

## Async Client

`AsyncVidNavigatorClient` has the same methods, arguments and return types as `VidNavigatorClient`, as coroutines. Use it from asyncio code such as FastAPI, aiohttp, Discord bots or agent frameworks: while a job is running, waiting uses `asyncio.sleep`, so the event loop keeps serving other work. It needs the `async` extra (`pip install "vidnavigator[async]"`).

```python
import asyncio
from vidnavigator import AsyncVidNavigatorClient

async def main():
    async with AsyncVidNavigatorClient() as client:  # reads VIDNAVIGATOR_API_KEY
        resp = await client.transcribe_video(video_url="https://www.instagram.com/reel/C86ZvEaqRmo/")
        print(resp.data.transcript)

asyncio.run(main())
```

### Many jobs at once

`asyncio.gather` runs every call concurrently. Each job is submitted immediately and polled in the background of the same event loop:

```python
async with AsyncVidNavigatorClient() as client:
    results = await asyncio.gather(
        *(client.transcribe_video(video_url=url, transcript_text=True) for url in urls),
        return_exceptions=True,  # one failed job doesn't cancel the others
    )

for url, resp in zip(urls, results):
    if isinstance(resp, Exception):
        print(url, "failed:", resp)
    else:
        print(url, resp.data.transcript[:80])
```

To cap how many jobs run at once (see [the running-job limit](#stay-under-the-running-job-limit)), wrap each call in an `asyncio.Semaphore`:

```python
limit = asyncio.Semaphore(5)

async def transcribe(url):
    async with limit:
        return await client.transcribe_video(video_url=url)

results = await asyncio.gather(*(transcribe(url) for url in urls))
```

### Job handles

`submit_*` methods return an `AsyncJob`: the same members as [`Job`](#non-blocking-submit-now-collect-later), with `status()`, `done()`, `refresh()`, `wait()` and `result()` as coroutines.

```python
job = await client.submit_extract_video_data(video_url=url, schema=schema)
print(job.task_id)

if not await job.done():
    ...  # do other work
resp = await job.result()
```

Timeouts work as in the sync client: `TaskTimeoutError` carries the `task_id` and an `AsyncJob` handle, so `await exc.job.result()` resumes waiting, and `client.resume_job(job_type, task_id)` rebuilds a handle later.

### In a FastAPI app

Create one client for the app's lifetime and share it across requests:

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from vidnavigator import AsyncVidNavigatorClient

@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.vidnavigator = AsyncVidNavigatorClient()
    yield
    await app.state.vidnavigator.aclose()

app = FastAPI(lifespan=lifespan)

@app.post("/jobs")
async def start_transcription(video_url: str):
    job = await app.state.vidnavigator.submit_transcribe_video(video_url=video_url)
    return {"task_id": job.task_id}

@app.get("/jobs/{task_id}")
async def job_status(task_id: str):
    job = app.state.vidnavigator.resume_job("transcribe", task_id)
    resp = await job.refresh()
    return {"status": resp.data.task_status}
```

### Configuration

```python
import httpx

client = AsyncVidNavigatorClient(
    api_key="YOUR_API_KEY",   # or set VIDNAVIGATOR_API_KEY
    base_url="https://...",   # override for staging / self-hosted
    timeout=60,               # per HTTP request, in seconds (default: 30)
    http_client=httpx.AsyncClient(limits=httpx.Limits(max_connections=20)),  # optional; you close it yourself
)
```

Close the client with `await client.aclose()`, or use `async with`. A client you pass as `http_client` is not closed for you. The [webhook helpers](#webhooks) are plain functions and work unchanged in async code. The deprecated sync aliases `get_youtube_transcript` and `search_videos` are not available on the async client.

---

## Webhooks

A background job can call your server when it finishes. Every job method, blocking or `submit_*`, accepts a `webhook_url` and passes it through to the API unchanged. **Webhooks are optional:** polling always works, whether or not a webhook is configured.

```python
job = client.submit_extract_video_data(
    video_url="https://www.tiktok.com/@user/video/1234567890",
    schema={"type": "object", "properties": {"summary": {"type": "string", "description": "One-line summary"}}},
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
| `watch.completed` / `watch.failed` | A watch job finishes |
| `extract_video.completed` / `extract_video.failed` | An extraction job finishes |
| `tweet_statement.completed` / `tweet_statement.failed` | A tweet analysis finishes |
| `tiktok_profile.completed` / `tiktok_profile.failed` | A profile scrape finishes |
| `tiktok_search.completed` / `tiktok_search.failed` | A keyword search finishes |
| `tiktok_live_search.completed` / `tiktok_live_search.failed` | A LIVE search finishes |

`construct_webhook_event` rejects deliveries whose timestamp is more than 5 minutes from the current time. Change the window with `tolerance_seconds=` (or pass `None` to skip the check). To verify without parsing, use `verify_webhook_signature(body, header, secret)`, which raises the same `WebhookSignatureError`.

Delivery is at-least-once and best effort: up to 5 attempts over about 13 minutes. Return a 2xx response quickly, deduplicate on `X-VidNavigator-Delivery`, and treat polling as the source of truth. See the [webhooks guide](https://docs.vidnavigator.com/guides/webhooks) for the full contract.

---

## TikTok Profile Scraping

`scrape_tiktok_profile` runs a [background job](#background-jobs) and returns every matching video, all pages merged:

```python
result = client.scrape_tiktok_profile(
    profile_url="https://www.tiktok.com/@tiktok",
    max_posts=100,
    after_datetime="2024-01-01",
)
task_id = result.data.task_id

for video in result.data.videos or []:
    print(video.title, video.published_at, video.likes, video.url)
```

To start the scrape without waiting, use `client.tiktok_profile.submit(...)` (or `submit_tiktok_profile_scrape(...)`), then call `job.result()` when you want the videos.

| Parameter | Type | Description |
|---|---|---|
| `profile_url` | `str` | Public TikTok profile URL |
| `max_posts` | `int` | Stop once this many matching videos are collected |
| `after_datetime` / `before_datetime` | `str` / `date` / `datetime` | Only include videos published in this window |
| `min_likes` / `max_likes` | `int` | Like-count filters |
| `webhook_url` | `str` | Optional; see [Webhooks](#webhooks) |
| `limit` | `int` | Optional: return only the first page of this size (up to 500) instead of every video |
| `include_usage`, `timeout` | | As for other [job methods](#background-jobs) |

`after_datetime` and `before_datetime` accept `YYYY-MM-DD` strings, ISO datetimes with a timezone, or Python `date` / `datetime` objects. In responses, `video.published_at` is a Python `datetime`, and `views`, `likes`, `reposts` and `comments` are integers.

### Read the remaining pages

Only needed when you passed `limit`:

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

`search_tiktok` (or `client.tiktok_search(...)`) runs a background job and returns every result, all pages merged. `submit_tiktok_search` (or `client.tiktok_search.submit(...)`) returns a handle instead.

```python
result = client.search_tiktok(
    query="ai tools",
    max_results=100,
    sort_by="most_liked",
    published_within="this_month",
    min_views=1000,
)

for item in result.data.results or []:
    print(item.description, item.published_at, item.stats.views if item.stats else None, item.url)

print(result.data.stats.sort_by, result.data.stats.published_within)  # what the search actually ran with
```

| Parameter | Type | Description |
|---|---|---|
| `query` | `str` | Keyword phrase (at least 2 characters) |
| `max_results` | `int` | Cap on merged results. `0` or omitted means no cap. |
| `parallel_search_slices` | `int` | `1`-`4` concurrent search chains, deduplicated. More slices return more unique videos and read up to N times as many TikTok pages, which the billing below counts. |
| `sort_by` | `str` | `"relevance"`, `"most_liked"` or `"newest"`, applied by TikTok |
| `published_within` | `str` | `"all"`, `"past_24_hours"`, `"this_week"`, `"this_month"`, `"last_3_months"` or `"last_6_months"` (rolling windows) |
| `after_datetime` / `before_datetime` | `str` / `date` / `datetime` | Exact publish-date bounds |
| `min_likes` / `max_likes` / `min_views` / `max_views` | `int` | Engagement filters |
| `country` | `str` | Two-letter code (`"fr"`, `"de"`, `"jp"`, ...) whose TikTok results you get. Default `"gb"`. `"us"` is refused: TikTok asks US visitors to log in. |
| `webhook_url` | `str` | Optional; see [Webhooks](#webhooks) |
| `limit` | `int` | Optional: return only the first page of this size (up to 500) instead of every result |
| `include_usage`, `timeout` | | As for other [job methods](#background-jobs) |

Without `sort_by`, results come back newest first. If you set `after_datetime` but not `published_within`, the smallest window covering `after_datetime` is picked automatically. `parallel_search_slices` is not a time filter; use `published_within` or the datetime bounds for that.

With `limit`, read further pages with `get_tiktok_search(task_id, cursor=...)`, exactly as for [profiles](#read-the-remaining-pages). Completed searches may include a `download_url` with the full JSON result.

Billing: 1 `residential_request` per 30 results returned (`result.data.stats.results_count`), minimum 1 per search and 1 per 5 TikTok pages read (`stats.pages_fetched`).

---

## TikTok LIVE Search

`search_tiktok_live` (or `client.tiktok_live_search(...)`) finds TikTok LIVE rooms broadcasting right now for a keyword, and returns every room. `submit_tiktok_live_search` (or `client.tiktok_live_search.submit(...)`) returns a handle instead.

```python
result = client.tiktok_live_search(query="gaming", country="us")

for room in result.data.results or []:
    print(room.title, room.author.unique_id, room.stats.viewers, room.category, room.hashtags)
    if room.stream_urls:
        best = room.stream_urls.default_quality
        print("  FLV:", room.stream_urls.flv.get(best))
        print("  HLS:", room.stream_urls.hls.get(best))  # can be missing: not every LIVE offers HLS
        print("  audio only:", room.stream_urls.audio_only)
```

| Parameter | Type | Description |
|---|---|---|
| `query` | `str` | Keyword phrase (at least 2 characters) |
| `max_results` | `int` | Cap on rooms. `0` or omitted means as many as TikTok serves, about 50 per keyword. |
| `country` | `str` | Two-letter code whose LIVE rooms you get. Default `"us"`. |
| `include_stream_urls` | `bool` | Stream URLs are returned by default; pass `False` to leave them out |
| `webhook_url` | `str` | Optional; see [Webhooks](#webhooks) |
| `limit` | `int` | Optional: return only the first page of this size |
| `include_usage`, `timeout` | | As for other [job methods](#background-jobs) |

Each room (`TikTokLiveRoom`) has the same `id`, `url`, `author` and `stats` fields as a keyword search result, plus:

- `started_at`: when the LIVE started, as a `datetime`
- `stats.viewers` (watching now), `stats.total_viewers` (since the start), `stats.likes`, `stats.comments`, `stats.shares`
- `hashtags`: the `#tags` of the title; `category`: the LIVE's category on TikTok (`"Gaming"`); `game_tags`
- `stream_urls`: `flv` and `hls` URLs keyed by quality (`origin`, `uhd`, `hd`, `sd`, `ld`), `default_quality`, an `audio_only` stream, and `expires_at`. The URLs play while the LIVE is on.

Results keep TikTok's ranking. A keyword with no LIVE room in that country at that moment completes with zero results. Billing: 1 `residential_request` per 30 rooms returned (`result.data.stats.results_count`), minimum 1 per search and 1 per 5 TikTok pages read (`stats.pages_fetched`).

---

## TikTok LIVE Room

`get_tiktok_live_room` returns one LIVE room right away (no job): by room id, by streamer, or by LIVE URL. Use it to check whether someone is live, to follow a room found by [LIVE search](#tiktok-live-search), or to read its latest comments.

```python
resp = client.get_tiktok_live_room(username="tiktok", include_comments=True)
room = resp.data.room

print(room.status, room.title, room.stats.viewers, room.stats.new_followers)
if room.is_live:
    for comment in resp.data.comments:
        print(comment.created_at, comment.author.unique_id, comment.text)
else:
    print("ended at", room.ended_at)
```

| Parameter | Type | Description |
|---|---|---|
| `room_id` | `str` | A LIVE room id, e.g. the `id` of a LIVE search room |
| `username` | `str` | The streamer, with or without `@`: their current LIVE, or their last one when they are offline |
| `url` | `str` | `https://www.tiktok.com/@username/live`, the profile URL, or a room's `share_url` |
| `include_comments` | `bool` | Also return the latest comments, the pinned comment, the intro and the top viewers. Default `False`. |
| `comments_limit` | `int` | At most this many comments, 1-50 (default 50) |
| `include_stream_urls` | `bool` | Stream URLs are returned by default; pass `False` to leave them out |
| `include_usage` | `bool` | Add the `usage` block |

Pass exactly one of `room_id`, `username` or `url`. The room (`TikTokLiveRoomDetail`) has the fields of a LIVE search room, plus:

- `status` (`"live"` or `"ended"`, also `room.is_live`) and `ended_at`
- `stats.viewers` (watching now), `stats.total_viewers` (since the start), `stats.new_followers` (gained during the LIVE)
- `author.bio`, `author.following`
- `share_url`, `chat_enabled`, `subscribers_only`, `age_restricted`, `products` (items on sale)

With `include_comments=True`, `resp.data` also has `comments` (newest first; TikTok keeps only about the last 50 of a LIVE), `pinned_comment`, `intro` and `top_viewers`. A room that has ended has no comments.

A room's likes, comment count and share count are not available here: [LIVE search](#tiktok-live-search) returns them. A room or account that does not exist raises `NotFoundError` (`error_code == "live_not_found"`). The call usually takes a few seconds; it may wait up to two minutes, whatever the client's `timeout`.

Billing: 1 `residential_request` per room, 2 with `include_comments` (1 when the room has ended). Not billed when the room is not found.

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
| `use_enhanced_search` | `bool` | AI-enhanced query, slower (default: `False`, as the API) |
| `start_year` / `end_year` | `int` | Only videos published in or after `start_year`, and in or before `end_year` |
| `focus` | `str` | What comes first among the matching videos: `"relevance"` (default, the best matches), `"recency"` (the most recent), `"popularity"` (the most viewed) or `"brevity"` (the shortest) |
| `duration` | `int` | Maximum duration in seconds: longer videos are left out |
| `max_results` | `int` | Max candidate videos to analyze and return; each one is billed, so this caps cost (defaults to your plan ceiling) |
| `include_usage` | `bool` | Attach a per-call `usage` block to the response |

The filters combine. For example, the most recent videos of five minutes at most, published since 2025:

```python
results = client.search_youtube(
    query="how to train a neural network from scratch",
    focus="recency",
    duration=300,
    start_year=2025,
    max_results=5,
)
```

If your credits run out during the analysis, `search_youtube` returns the videos analysed so far instead of raising: `results.status` is then `"partial"` and `results.error_code` is `"insufficient_credits_video_search"`. A search that cannot start for lack of credits raises `PaymentRequiredError`.

```python
results = client.search_youtube(query="how to train a neural network from scratch")
if results.status == "partial":
    print(f"Credits ran out: {len(results.data.results)} videos analysed")
```

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

Upload audio or video files for persistent storage. Once processed, files can be transcribed, searched, and used for extraction, just like online videos.

### Upload and process

```python
result = client.upload_file("./meeting.mp4", wait_for_completion=True)
file_id = result["file_id"]
print(result["file_status"])  # "completed"
```

With `wait_for_completion=False` (the default), the upload returns immediately and processing continues in the background. Check `get_file(file_id).data.file_info.status` until it is `"completed"`.

### Scenes of a file

What a video file shows is analyzed once and kept with the file. Ask for it at upload, or later for a file that is already there:

```python
import time

result = client.upload_file("./recipe.mp4", include_scenes=True)   # at upload
file_id = result["file_id"]
# or, for an existing file:
client.analyze_file_scenes(file_id)

while True:
    resp = client.get_file(file_id)
    info = resp.data.file_info
    if info.status == "completed" and info.scenes_status in ("completed", "failed"):
        break
    time.sleep(3)

for scene in resp.data.scenes or []:
    print(f"[{scene.start:.0f}s] {scene.description} | on screen: {scene.on_screen_text}")
```

`file_info.scenes_status` is `"none"` (never asked for), `"processing"`, `"completed"` or `"failed"`; when it failed, `file_info.scenes_error` says why (an audio file has no picture: `frames_not_available`). Once completed, `file_info.frames_analyzed` is the number of frames read.

Once the scenes are there, `extract_file_data` uses them with `include_scenes=True`. Asked on a file that has none, it raises `ScenesNotAvailableError`:

```python
from vidnavigator import ScenesNotAvailableError

try:
    resp = client.extract_file_data(file_id=file_id, what_to_extract="What is written on the label?", include_scenes=True)
except ScenesNotAvailableError as exc:
    if exc.scenes_status == "none":
        client.analyze_file_scenes(file_id)   # start them, then call again once completed
```

The frames of a file are charged once, when its scenes are analyzed (1 credit per 2,000 frames, with at least 667 frames per hour of video). Using them afterwards adds no frame charge.

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

It is supported by `get_transcript`, `transcribe_video`, `watch_video`, `extract_video_data`, `extract_file_data`, `search_youtube`, `search_files`, `get_tweet_statement`, `scrape_tiktok_profile`, `search_tiktok`, `get_tiktok_profile_scrape`, `get_tiktok_search`, and `job.result(include_usage=True)`. For background jobs, usage appears once the job is `completed`; failed jobs have all their charges reverted.

```python
resp = client.search_youtube(query="react best practices", include_usage=True)

usage = resp.usage
if usage:
    print(f"Credits this call: {usage.total_credits}")
    if usage.credits_remaining_after is not None:
        print(f"Credits left: {usage.credits_remaining_after}")

    for charge in usage.charges or []:
        print(f"  {charge.service_type}: {charge.quantity} unit(s), {charge.credits} credits")

    # LLM token tally (extract / YouTube search / tweet analysis)
    tokens = usage.analysis_tokens
    if tokens:
        print(f"  LLM tokens: {tokens.total_tokens}")
```

| Field | Description |
|---|---|
| `charges` | List of `UsageCharge` (one per meter): `service_type`, `quantity`, `credits`, `waived`, `credits_saved`, and (analysis only) nested `tokens` |
| `total_credits` | Net credits deducted by the call |
| `credits_remaining_after` | Credits left on the account (monthly + purchased) after the call's charges; `None` on plans without a credit limit |
| `waived` | Present when charges were waived (`waived.credits_saved`) |
| `analysis_tokens` | The LLM token counts (`prompt_tokens`, `completion_tokens`, `total_tokens`) |
| `charge_for(service_type)` | The charge entry for one meter, e.g. `usage.charge_for("transcription_hour")` |

Meters: `standard_request`, `residential_request`, `transcription_hour`, `frame_analysis`, `analysis_request`, `search_request` and `scene_analysis_hour`.

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
    if usage.usage.frame_analysis:
        print(f"Frames analyzed: {usage.usage.frame_analysis.used}")
    if usage.usage.scene_analysis_hour:
        print(f"Scene analysis hours: {usage.usage.scene_analysis_hour.used}")
```

`usage_period` and `billing_period` have `start` and `end` as ISO date strings, or `None` when the account has no subscription period.

---

## Error Handling

Every API error maps to a specific exception, and all of them inherit from `VidNavigatorError`:

```python
from vidnavigator import NotFoundError, RateLimitExceededError, VidNavigatorError

try:
    client.get_file("nonexistent-id")
except NotFoundError:
    print("File not found")
except RateLimitExceededError:
    print("Rate limit hit -- slow down")
except VidNavigatorError as exc:
    print("Something else went wrong:", exc)
```

| Exception | Status | When |
|---|---|---|
| `BadRequestError` | 400 | Invalid parameters or schema |
| `AuthenticationError` | 401 | Missing or invalid API key |
| `PaymentRequiredError` | 402 | Any 402. Its two subclasses below say which one |
| `InsufficientCreditsError` | 402 | Not enough credits (`insufficient_credits`); upgrade or top up. A `PaymentRequiredError`, from 3.1.0 |
| `AccessDeniedError` | 403 | Insufficient permissions, or content that requires login or age verification |
| `NotFoundError` | 404 | Resource not found, including an unknown or expired job `task_id` |
| `ScenesNotAvailableError` | 409 | `include_scenes=True` on a file that has no scenes yet (check `.scenes_status`) |
| `StorageQuotaExceededError` | 402 | The storage of the plan is full (`storage_quota_exceeded`, on upload). A `PaymentRequiredError`, from 3.0.2 |
| `RateLimitExceededError` | 429 | Too many requests (`rate_limit_exceeded`); wait `Retry-After` seconds. Named `RateLimitExceeded` before 3.1.0, a name that still works |
| `TooManyActiveJobsError` | 429 | Too many background jobs already running. Subclass of `RateLimitExceededError`. |
| `GeoRestrictedError` | 451 | Content unavailable in your region |
| `SystemOverloadError` | 503 | Temporary overload (check `.retry_after_seconds`) |
| `ServerError` | 5xx | Unexpected server error |
| `TaskTimeoutError` | -- | A blocking call or `job.result()` hit its `timeout`. The job keeps running; resume with `.job` or `.task_id`. Named `JobTimeoutError` before 3.1.0, a name that still works |
| `WebhookSignatureError` | -- | A webhook delivery failed signature or timestamp verification |
| `VidNavigatorError` | -- | Base class for all errors, also raised for network failures |

API exceptions carry the details of the error response:

```python
from vidnavigator import BadRequestError

try:
    client.extract_video_data(video_url=url, schema={"type": "object", "properties": {"x": {"type": "nope"}}})
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

One client can be reused for any number of calls. If you use threads, create one client per thread. For asyncio code, use [`AsyncVidNavigatorClient`](#async-client).

---

## What's new in 3.1.0

- **The same error classes as the JavaScript SDK.** Running out of credits raises `InsufficientCreditsError`, a `PaymentRequiredError`, so `except PaymentRequiredError` keeps working. `RateLimitExceeded` and `JobTimeoutError` are now `RateLimitExceededError` and `TaskTimeoutError`, as in JavaScript; the former names still work.
- **The API's code for "not enough credits" is now `insufficient_credits`** (it was `limit_exceeded`). Both raise `InsufficientCreditsError`; `exc.error_code` carries the code the API sent.

## What's new in 3.0.2

- **`search_youtube` no longer turns the enhanced search on by default.** `use_enhanced_search` now defaults to `False`, as the API and the JavaScript SDK do: searches are faster. Pass `use_enhanced_search=True` to keep the former behaviour.
- **`get_file` returns `frames_analyzed`.** The API sends it inside `file_info`, which had no such field, so it was lost: it is now `file_info.frames_analyzed`, and `data.frames_analyzed` gives the same value.
- **`get_usage` keeps every counter:** `usage.scene_analysis_hour` was dropped; it is now there next to `usage.frame_analysis`.
- **`get_usage` no longer fails on an account without a subscription period.** The API sends `null` dates then; `usage_period.start`, `usage_period.end`, `billing_period.start` and `billing_period.end` are now `None` instead of raising a validation error.
- **`search_youtube` returns partial results.** When credits run out during the analysis, the videos analysed so far are returned with `status == "partial"` and `error_code == "insufficient_credits_video_search"`, as the JavaScript SDK does. Before, they were only in the `PaymentRequiredError` raised.
- **`usage.credits_remaining_after`** is documented: the credits left on the account after the call's charges, `None` on plans without a credit limit.

## What's new in 3.0.1

- **`upload_file(..., wait_for_completion=True)` no longer stops after 30 seconds.** The API holds this request until the file is processed (up to 15 minutes, then it answers with the file still `processing`), so the client's timeout is raised to 16 minutes for this call only. Before, a file that took more than 30 seconds to process ended in `VidNavigatorError: Read timed out` while it kept processing.

## What's new in 3.0.0

- **Breaking: the analysis methods are removed**, with the API endpoints they called: `analyze_video`, `submit_analyze_video`, `analyze_file`, the `"analyze_video"` job type, and their models (`AnalysisResponse`, `AnalysisData`, `AnalysisResult`, `QueryAnswerDetail`, `AnalyzeVideoJob`, `AnalyzeVideoJobResponse`). Use `extract_video_data` / `extract_file_data` with `what_to_extract`: see [Upgrading to 3.0](#upgrading-to-30).
- **Scenes in tweet claim analysis:** `get_tweet_statement`, `submit_tweet_statement` and `client.tweet_statement` take `include_scenes=True`: what the tweet's video and the quoted tweet's video show is read as well. `TweetStatementData` carries `frames_analyzed` and, when a video's picture could not be read, `scenes_error`. See [Tweet claim analysis](#tweet-claim-analysis).

## What's new in 2.7.0

- **[Where each value comes from](#where-each-value-comes-from):** extraction results carry `evidence`, the moments of the video each field was taken from (`FieldEvidence`: `start`, `end`, `in_`), on `ExtractionApiResponse`, `ExtractVideoJob` and the `extract_video.completed` webhook event.
- **YouTube speech-to-text:** `transcribe_video` takes YouTube videos, and a YouTube video without captions is transcribed by `watch_video` and by `extract_video_data` (`transcribe=True`).

## What's new in 2.6.0

- **Extraction takes a standard JSON Schema**, the only schema format the API accepts now: `{"type": "object", "properties": {...}}`, with lowercase types. A Pydantic model's `model_json_schema()` can be passed as it is. The former format (`{"field": {"type": "String", ...}}`) is refused with `invalid_schema`: see [Schema format](#schema-format).
- **[Extraction without a schema](#without-a-schema):** `extract_video_data`, `submit_extract_video_data` and `extract_file_data` take `what_to_extract` alone; the schema written for it comes back on `.extraction_schema` (also on the `extract_video.completed` webhook event).

## What's new in 2.5.0

- **Scenes in extraction:** `include_scenes=True` on `extract_video_data` and `extract_file_data` uses what the video or file shows (its scenes, with the text on screen) together with the transcript. The results carry `frames_analyzed`. (The analysis methods got it too, and a background job; they were removed in 3.0.0.)
- **[Scenes of a file](#scenes-of-a-file):** `upload_file(..., include_scenes=True)`, `analyze_file_scenes(file_id)`, `file_info.scenes_status`, and the scenes in `get_file`. `ScenesNotAvailableError` when they are asked for and not there yet.

## What's new in 2.4.0

- **Watch:** [`watch_video`](#watch) / `client.watch` reads what a video shows, next to what it says: a list of scenes (`start`, `end`, `description`, `on_screen_text`) and the transcript, in one result. `detail` sets how closely the picture is followed, `include_transcript=False` returns the scenes only. Runs as a background job like `transcribe_video`, with `submit_watch_video`, `resume_job("watch", task_id)` and the `watch.completed` / `watch.failed` webhook events.

## What's new in 2.3.1

- **YouTube search:** `focus="recency"` puts the most recent videos first, next to `"relevance"`, `"popularity"` and `"brevity"`. The `start_year`, `end_year` and `duration` filters are described precisely in [Search YouTube](#search-youtube).

## What's new in 2.3.0

- **TikTok LIVE room:** [`get_tiktok_live_room`](#tiktok-live-room) returns one room right away, by room id, streamer or LIVE URL: live or ended, viewers, new followers, the streamer's bio, and with `include_comments=True` its latest comments, pinned comment, intro and top viewers.

## What's new in 2.2.0

- **TikTok LIVE search:** `search_tiktok_live` / `client.tiktok_live_search`, with typed rooms and their stream URLs.
- **`country` on TikTok keyword search**, plus the `stats.videos_fetched` and `items_*` counters.
- **[Operation objects](#operation-objects)**, as in the JavaScript SDK: `client.tiktok_search(...)`, `.submit(...)`, `.resume(task_id)`, for every background job.
- **TikTok results come whole:** `scrape_tiktok_profile`, `search_tiktok`, `search_tiktok_live` and `job.result()` on TikTok jobs now return every item, all pages merged, like the JavaScript SDK. Before, they returned the first 50. Pass `limit` to keep getting one page.

## Upgrading to 3.0

Version 3.0 removes the analysis methods, as the API removed their endpoints. Every analysis is an extraction now: say what you want in `what_to_extract`, or name the fields in a `schema` to get the same ones every time.

| In 2.x | In 3.0 |
|---|---|
| A summary of a video | `extract_video_data(video_url=..., what_to_extract="a three-sentence summary")` |
| The answer to a `query` | `extract_video_data(video_url=..., what_to_extract="a three-sentence summary and the answer to: ...")` |
| `transcript_analysis.people`, `places`, `key_subjects` | Name them as fields of a `schema` (see [Summarize a video or ask a question about it](#summarize-a-video-or-ask-a-question-about-it)); the extracted values are in `resp.data` |
| `include_scenes=True` | The same parameter on `extract_video_data`; `resp.frames_analyzed`, `resp.scenes_error` and `resp.transcript_error` are on the response itself. For the scenes themselves, use [`watch_video`](#watch). |
| A long video, as a background job | `extract_video_data` always runs as a [background job](#background-jobs); `submit_extract_video_data` returns the handle |
| An uploaded file | `extract_file_data(file_id=..., what_to_extract=...)`, with `include_scenes=True` once the file's scenes are there |
| `transcript_text=True` to get the transcript with the analysis | `get_transcript` (or `get_file` for an uploaded file) |

## Upgrading from 1.x

Version 2.0 runs speech-to-text and TikTok operations as background jobs. Most code keeps working unchanged. Check these points:

| In 1.x | In 2.0 |
|---|---|
| `transcribe_video`, `extract_video_data` and `get_tweet_statement` made one long HTTP request | They submit a job and poll it. Same arguments and return types, and no media duration limit. They can raise `TaskTimeoutError` (default wait: one hour). |
| `extract_video_data(..., include_usage=True).usage.total_tokens` | Use `usage.analysis_tokens.total_tokens` |
| `submit_tiktok_profile_scrape` / `submit_tiktok_search` returned the submit response | They return a `Job`. `job.data.task_id` still works; **`job.status` is now a method**, so replace `task.status == "success"` checks. |
| Manual polling loops on `get_tiktok_profile_scrape` | `scrape_tiktok_profile(...)`, or `job.result()` on a submitted job |
| `task.data.error_message` on failed TikTok tasks | Deprecated; read `task.data.error` (`error`, `message`, `http_status`), or let `job.result()` raise |
| A 401 raised the generic `VidNavigatorError` | It raises `AuthenticationError` |

New in 2.0: `submit_transcribe_video`, `submit_extract_video_data`, `submit_tweet_statement`, `scrape_tiktok_profile`, `search_tiktok`, `resume_job`, `webhook_url` on every job method, `sort_by` and `published_within` for TikTok search, the webhook helpers, and `status_code` / `error_code` / `docs_url` / `payload` on every API exception.

---

## Requirements

- Python 3.8+
- [`requests`](https://pypi.org/project/requests/) >= 2.31
- [`pydantic`](https://pypi.org/project/pydantic/) >= 1.10 (v1 and v2 both supported)
- [`httpx`](https://pypi.org/project/httpx/) >= 0.23, for `AsyncVidNavigatorClient` only (`pip install "vidnavigator[async]"`)

---

## Documentation

Full API reference and guides: **[docs.vidnavigator.com](https://docs.vidnavigator.com)**

---

## License

Apache License 2.0 -- see [LICENSE](LICENSE) for details.
