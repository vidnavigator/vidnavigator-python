"""Unit tests for the scenes (`include_scenes`): extraction and files (mocked HTTP).

The payloads are trimmed copies of real answers of the API.
"""

import asyncio
from unittest.mock import patch

import pytest

from vidnavigator import (
    AsyncJob,
    AsyncVidNavigatorClient,
    BadRequestError,
    ScenesNotAvailableError,
    VidNavigatorClient,
)
from vidnavigator.exceptions import error_from_response
from vidnavigator.models import (
    ExtractionApiResponse,
    FileResponse,
    FileScenesResponse,
    VideoScene,
)

from .helpers import accepted, job

VIDEO = "https://www.dailymotion.com/video/x84243e"
SCENES = [
    {"start": 0.0, "end": 2.0, "description": "A wooden table holds a bowl of crackers and a bowl of pâté.",
     "on_screen_text": "PATÊ DE FRANGO CREMOSO"},
    {"start": 2.0, "end": 6.0, "description": "A hand tips shredded chicken into a glass bowl.",
     "on_screen_text": "500 g FRANGO DESFIADO COZIDO"},
]
SCHEMA = {"type": "object", "properties": {"dish": {"type": "string", "description": "Name of the dish"}}}
FILE_EXTRACTION_WITH_SCENES = {
    "status": "success",
    "data": {"dish": "PATÊ DE FRANGO CREMOSO"},
    "file_info": {"id": "f1", "scenes_status": "completed"},
    "frames_analyzed": 30,
}
NO_SCENES = {
    "status": "error", "error": "scenes_not_available", "error_code": "scenes_not_available",
    "message": 'This file has no scenes yet. Start their analysis with POST /v1/watch/file {"file_id": "f1"}, '
               "or upload with include_scenes, then call again.",
    "scenes_status": "none",
}


# What POST /v1/extract/async answers: the job type is still extract_video.
EXTRACT_ACCEPTED = accepted("extract_video", check_status_url="/v1/extract/task_1")


@pytest.fixture
def client():
    return VidNavigatorClient(api_key="test_key")


# ---------------------------------------------------------------------------
# Extraction
# ---------------------------------------------------------------------------

def test_extract_video_data_with_scenes(client):
    done = job("extract_video", "completed", result={"dish": "PATÊ DE FRANGO CREMOSO"})
    done["data"]["video_info"] = {"title": "Patê de frango"}
    done["data"]["frames_analyzed"] = 30
    with patch.object(client, "_request", side_effect=[EXTRACT_ACCEPTED, done]) as req:
        resp = client.extract_video_data(video_url=VIDEO, schema=SCHEMA, include_scenes=True, timeout=5)
    submit = req.call_args_list[0]
    assert submit[0] == ("POST", "/extract/async")
    assert submit[1]["json_body"] == {"video_url": VIDEO, "transcribe": True, "include_scenes": True, "schema": SCHEMA}
    assert isinstance(resp, ExtractionApiResponse)
    assert resp.data == {"dish": "PATÊ DE FRANGO CREMOSO"} and resp.frames_analyzed == 30


def test_extract_video_data_without_scenes_sends_no_include_scenes(client):
    with patch.object(client, "_request", return_value=EXTRACT_ACCEPTED) as req:
        handle = client.submit_extract_video_data(video_url=VIDEO, schema=SCHEMA)
    assert "include_scenes" not in req.call_args[1]["json_body"]
    assert handle.job_type == "extract_video" and handle.check_status_url == "/v1/extract/task_1"


def test_extract_video_job_result_carries_the_scenes(client):
    handle = client.resume_job("extract_video", "task_1")
    done = job("extract_video", "completed", result={"dish": "PATÊ DE FRANGO CREMOSO"})
    done["data"]["frames_analyzed"] = 30
    with patch.object(client, "_request", return_value=done) as req:
        resp = handle.result(timeout=5)
    assert req.call_args[0] == ("GET", "/extract/task_1")
    assert isinstance(resp, ExtractionApiResponse)
    assert resp.frames_analyzed == 30 and resp.scenes_error is None and resp.transcript_error is None


def test_a_missing_source_is_told_and_the_other_one_is_used(client):
    raw = {"status": "success", "data": {"dish": "PATÊ DE FRANGO CREMOSO"}, "frames_analyzed": 2,
           "transcript_error": {"error": "transcript_not_available", "message": "No transcript found for this video."}}
    with patch.object(client, "_request", return_value=raw):
        resp = client.extract_file_data(file_id="f1", schema=SCHEMA, include_scenes=True)
    assert resp.transcript_error.error == "transcript_not_available"
    assert resp.frames_analyzed == 2

    raw = {"status": "success", "data": {"dish": "Pâté"},
           "scenes_error": {"error": "frames_not_available", "message": "This video has no picture we can read."}}
    with patch.object(client, "_request", return_value=raw):
        resp = client.extract_file_data(file_id="f1", schema=SCHEMA, include_scenes=True)
    assert resp.scenes_error.error == "frames_not_available"
    assert resp.frames_analyzed is None


def test_extract_file_data_with_scenes_json_and_schema_file(client, tmp_path):
    raw = {"status": "success", "data": {"dish": "Pâté"}, "file_info": {"id": "f1", "scenes_status": "completed"},
           "frames_analyzed": 30}
    with patch.object(client, "_request", return_value=raw) as req:
        resp = client.extract_file_data(file_id="f1", schema=SCHEMA, include_scenes=True)
    assert req.call_args[1]["json_body"] == {"file_id": "f1", "schema": SCHEMA, "include_usage": False,
                                             "include_scenes": True}
    assert resp.frames_analyzed == 30 and resp.file_info.scenes_status == "completed"

    schema_file = tmp_path / "schema.json"
    schema_file.write_text('{"type": "object", "properties": {"dish": {"type": "string", "description": "Name of the dish"}}}', encoding="utf-8")
    with patch.object(client, "_request", return_value=raw) as req:
        client.extract_file_data(file_id="f1", schema_file=str(schema_file), include_scenes=True)
    assert req.call_args[1]["data"] == {"file_id": "f1", "include_usage": "false", "include_scenes": "true"}


# ---------------------------------------------------------------------------
# Files
# ---------------------------------------------------------------------------

def test_upload_file_with_scenes(client, tmp_path):
    video = tmp_path / "clip.mp4"
    video.write_bytes(b"not a real video")
    raw = {"status": "success", "file_id": "f1", "file_status": "processing",
           "data": {"file_info": {"id": "f1", "scenes_status": "processing"}}}
    with patch.object(client, "_request", return_value=raw) as req:
        resp = client.upload_file(str(video), include_scenes=True)
    assert req.call_args[1]["data"] == {"wait_for_completion": "false", "include_scenes": "true"}
    assert resp["data"]["file_info"]["scenes_status"] == "processing"

    with patch.object(client, "_request", return_value=raw) as req:
        client.upload_file(str(video))
    assert req.call_args[1]["data"] == {"wait_for_completion": "false"}
    assert "min_timeout" not in req.call_args[1]          # the default timeout is kept


def test_upload_file_waiting_for_completion_outlasts_the_default_timeout(client, tmp_path):
    # The API holds the request up to 15 minutes; the 30 s default cut it off.
    video = tmp_path / "meeting.mp4"
    video.write_bytes(b"not a real video")
    raw = {"status": "success", "file_id": "f1", "file_status": "completed",
           "data": {"file_info": {"id": "f1", "status": "completed"}}}
    with patch.object(client, "_request", return_value=raw) as req:
        client.upload_file(str(video), wait_for_completion=True)
    assert req.call_args[1]["data"] == {"wait_for_completion": "true"}
    assert req.call_args[1]["min_timeout"] == 960.0


def test_watch_file_starts_the_analysis(client):
    raw = {"status": "success", "data": {"file_id": "f1", "scenes_status": "processing",
                                         "message": "Scene analysis started."}}
    with patch.object(client, "_request", return_value=raw) as req:
        resp = client.watch_file("f1")
    req.assert_called_once_with("POST", "/watch/file", json_body={"file_id": "f1"})
    assert isinstance(resp, FileScenesResponse)
    assert resp.data.scenes_status == "processing" and resp.data.file_id == "f1"


def test_analyze_file_scenes_is_an_alias_of_watch_file(client):
    """The name before 3.3.0 still works, and calls POST /watch/file too."""
    raw = {"status": "success", "data": {"file_id": "f1", "scenes_status": "completed", "message": "there"}}
    with patch.object(client, "_request", return_value=raw) as req:
        resp = client.analyze_file_scenes("f1")
    req.assert_called_once_with("POST", "/watch/file", json_body={"file_id": "f1"})
    assert isinstance(resp, FileScenesResponse) and resp.data.scenes_status == "completed"


def test_get_file_carries_the_scenes_once_they_are_there(client):
    raw = {"status": "success", "data": {
        "file_info": {"id": "f1", "name": "clip.mp4", "status": "completed", "scenes_status": "completed"},
        "transcript": [{"text": "Música", "start": 0.0, "end": 4.0}], "scenes": SCENES, "frames_analyzed": 30}}
    with patch.object(client, "_request", return_value=raw):
        resp = client.get_file("f1")
    assert isinstance(resp, FileResponse)
    assert resp.data.file_info.scenes_status == "completed"
    assert all(isinstance(scene, VideoScene) for scene in resp.data.scenes)
    assert resp.data.scenes[0].on_screen_text == "PATÊ DE FRANGO CREMOSO" and resp.data.frames_analyzed == 30


def test_get_file_reads_frames_analyzed_inside_file_info(client):
    """The API sends ``frames_analyzed`` inside ``file_info``; ``data.frames_analyzed`` still gives it."""
    raw = {"status": "success", "data": {
        "file_info": {"id": "f1", "name": "clip.mp4", "status": "completed", "scenes_status": "completed",
                      "frames_analyzed": 30},
        "transcript": [{"text": "Música", "start": 0.0, "end": 4.0}], "scenes": SCENES}}
    with patch.object(client, "_request", return_value=raw):
        resp = client.get_file("f1")
    assert resp.data.file_info.frames_analyzed == 30
    assert resp.data.frames_analyzed == 30


def test_list_files_reads_frames_analyzed(client):
    raw = {"status": "success", "data": {
        "files": [{"id": "f1", "status": "completed", "scenes_status": "completed", "frames_analyzed": 12},
                  {"id": "f2", "status": "completed", "scenes_status": "none"}],
        "total_count": 2, "limit": 50, "offset": 0, "has_more": False}}
    with patch.object(client, "_request", return_value=raw):
        resp = client.get_files()
    assert [f.frames_analyzed for f in resp.data.files] == [12, None]


def test_a_file_with_no_picture_says_why(client):
    raw = {"status": "success", "data": {"file_info": {
        "id": "f2", "type": "audio/mp3", "status": "completed", "scenes_status": "failed",
        "scenes_error": {"error": "frames_not_available",
                         "message": "This file has no picture we can read (an audio file, or a video without a video track)."}},
        "transcript": []}}
    with patch.object(client, "_request", return_value=raw):
        resp = client.get_file("f2")
    assert resp.data.file_info.scenes_status == "failed"
    assert resp.data.file_info.scenes_error.error == "frames_not_available"
    assert resp.data.scenes is None


# ---------------------------------------------------------------------------
# The file has no scenes yet
# ---------------------------------------------------------------------------

def test_scenes_not_available_is_its_own_error():
    error = error_from_response(409, NO_SCENES)
    assert isinstance(error, ScenesNotAvailableError)
    assert error.status_code == 409 and error.error_code == "scenes_not_available"
    assert error.scenes_status == "none"
    assert "POST /v1/watch/file" in error.message

    still_running = error_from_response(409, dict(NO_SCENES, scenes_status="processing"))
    assert still_running.scenes_status == "processing"
    assert error_from_response(409, {"error": "scenes_not_available"}).scenes_status is None


def test_the_usual_way_to_get_the_scenes_of_a_file(client):
    """Ask, be told there are none, start them, ask again."""
    started = {"status": "success", "data": {"file_id": "f1", "scenes_status": "processing", "message": "started"}}
    answer = FILE_EXTRACTION_WITH_SCENES
    with patch.object(client, "_request", side_effect=[error_from_response(409, NO_SCENES), started, answer]) as req:
        with pytest.raises(ScenesNotAvailableError) as raised:
            client.extract_file_data(file_id="f1", schema=SCHEMA, include_scenes=True)
        assert raised.value.scenes_status == "none"
        assert client.watch_file("f1").data.scenes_status == "processing"
        assert client.extract_file_data(file_id="f1", schema=SCHEMA, include_scenes=True).frames_analyzed == 30
    assert [call[0][1] for call in req.call_args_list] == ["/extract/file", "/watch/file", "/extract/file"]


def test_an_audio_file_is_refused_when_its_scenes_are_asked():
    error = error_from_response(400, {
        "status": "error", "error": "frames_not_available", "error_code": "frames_not_available",
        "message": "This file has no picture we can read (an audio file, or a video without a video track)."})
    assert isinstance(error, BadRequestError) and error.error_code == "frames_not_available"


# ---------------------------------------------------------------------------
# Async client
# ---------------------------------------------------------------------------

def test_async_client_has_the_same_methods():
    async def go():
        client = AsyncVidNavigatorClient(api_key="test_key")
        try:
            with patch.object(client, "_request", return_value=FILE_EXTRACTION_WITH_SCENES) as req:
                extraction = await client.extract_file_data(file_id="f1", schema=SCHEMA, include_scenes=True)
            sent = req.call_args[1]["json_body"]
            with patch.object(client, "_request", return_value=EXTRACT_ACCEPTED) as req:
                handle = await client.submit_extract_video_data(video_url=VIDEO, schema=SCHEMA, include_scenes=True)
            submitted = req.call_args[0]
            started = {"status": "success", "data": {"file_id": "f1", "scenes_status": "completed", "message": "there"}}
            with patch.object(client, "_request", return_value=started) as req:
                scenes = await client.watch_file("f1")
                aliased = await client.analyze_file_scenes("f1")
            return extraction, sent, handle, submitted, scenes, aliased, req.call_args_list
        finally:
            await client.aclose()

    extraction, sent, handle, submitted, scenes, aliased, calls = asyncio.run(go())
    assert extraction.frames_analyzed == 30 and sent["include_scenes"] is True
    assert isinstance(handle, AsyncJob) and handle.job_type == "extract_video"
    assert submitted == ("POST", "/extract/async")
    assert scenes.data.scenes_status == "completed" and aliased.data.scenes_status == "completed"
    # watch_file, then its alias: the same request both times.
    assert [(c[0], c[1]) for c in calls] == [(("POST", "/watch/file"), {"json_body": {"file_id": "f1"}})] * 2
