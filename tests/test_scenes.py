"""Unit tests for the scenes (`include_scenes`): analysis, extraction, files, the background analysis (mocked HTTP).

The payloads are trimmed copies of real answers of the API.
"""

import asyncio
from unittest.mock import patch

import pytest

from vidnavigator import (
    AsyncJob,
    AsyncVidNavigatorClient,
    BadRequestError,
    Job,
    ScenesNotAvailableError,
    VidNavigatorClient,
    VidNavigatorError,
)
from vidnavigator.exceptions import error_from_response
from vidnavigator.models import (
    AnalysisResponse,
    AnalyzeVideoJobResponse,
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
ANALYSIS = {
    "summary": "How to make a creamy chicken pâté.",
    "query_answer": {"answer": "Chicken 500 g; mayonnaise 300 g.", "best_segment_index": 5,
                     "relevant_segments": ["5:6", "9"]},
}
ANALYSIS_WITH_SCENES = {
    "status": "success",
    "data": {
        "video_info": {"title": "Patê de frango", "duration": 79},
        "transcript": [{"text": "Música", "start": 0.0, "end": 4.0}],
        "transcript_analysis": ANALYSIS,
        "scenes": SCENES,
        "frames_analyzed": 30,
    },
    "usage": {
        "charges": [
            {"service_type": "standard_request", "quantity": 1.0, "credits": 0.0001},
            {"service_type": "frame_analysis", "quantity": 30.0, "credits": 0.03},
            {"service_type": "analysis_request", "quantity": 1.0, "credits": 0.01},
        ],
        "total_credits": 0.0401,
    },
}
SCHEMA = {"type": "object", "properties": {"dish": {"type": "string", "description": "Name of the dish"}}}
NO_SCENES = {
    "status": "error", "error": "scenes_not_available", "error_code": "scenes_not_available",
    "message": "This file has no scenes yet. Start their analysis with POST /v1/file/f1/scenes, "
               "or upload with include_scenes, then call again.",
    "scenes_status": "none",
}


@pytest.fixture
def client():
    return VidNavigatorClient(api_key="test_key")


# ---------------------------------------------------------------------------
# Analysis of an online video
# ---------------------------------------------------------------------------

def test_analyze_video_with_scenes(client):
    with patch.object(client, "_request", return_value=ANALYSIS_WITH_SCENES) as req:
        resp = client.analyze_video(video_url=VIDEO, query="How much chicken?", include_scenes=True, include_usage=True)
    assert isinstance(resp, AnalysisResponse)
    assert req.call_args[0] == ("POST", "/analyze/video")
    assert req.call_args[1]["json_body"] == {
        "video_url": VIDEO, "transcript_text": False, "include_usage": True,
        "query": "How much chicken?", "include_scenes": True,
    }
    assert resp.data.frames_analyzed == 30
    assert all(isinstance(scene, VideoScene) for scene in resp.data.scenes)
    assert resp.data.scenes[1].on_screen_text == "500 g FRANGO DESFIADO COZIDO"
    assert resp.data.transcript_analysis.query_answer.answer.startswith("Chicken 500 g")
    assert resp.data.scenes_error is None and resp.data.transcript_error is None
    assert [charge.service_type for charge in resp.usage.charges] == [
        "standard_request", "frame_analysis", "analysis_request"]


def test_analyze_video_without_scenes_sends_what_it_always_sent(client):
    raw = {"status": "success", "data": {"video_info": {"title": "t"}, "transcript": [],
                                         "transcript_analysis": {"summary": "A summary"}}}
    with patch.object(client, "_request", return_value=raw) as req:
        resp = client.analyze_video(video_url=VIDEO)
    assert req.call_args[1]["json_body"] == {"video_url": VIDEO, "transcript_text": False, "include_usage": False}
    # Scenes that were not asked for are absent, not an empty list.
    assert resp.data.scenes is None and resp.data.frames_analyzed is None


def test_a_missing_source_is_told_and_the_other_one_is_used(client):
    raw = {"status": "success", "data": {
        "video_info": {"title": "t"}, "transcript": [], "transcript_analysis": {"summary": "From the picture."},
        "transcript_error": {"error": "transcript_not_available", "message": "No transcript found for this video."},
        "scenes": SCENES, "frames_analyzed": 2}}
    with patch.object(client, "_request", return_value=raw):
        resp = client.analyze_video(video_url=VIDEO, include_scenes=True)
    assert resp.data.transcript_error.error == "transcript_not_available"
    assert len(resp.data.scenes) == 2

    raw = {"status": "success", "data": {
        "video_info": {"title": "t"}, "transcript": [{"text": "Hello", "start": 0, "end": 1}],
        "transcript_analysis": {"summary": "From the speech."},
        "scenes_error": {"error": "frames_not_available", "message": "This video has no picture we can read."}}}
    with patch.object(client, "_request", return_value=raw):
        resp = client.analyze_video(video_url=VIDEO, include_scenes=True)
    assert resp.data.scenes_error.error == "frames_not_available"
    assert resp.data.scenes is None


# ---------------------------------------------------------------------------
# The same analysis as a background job
# ---------------------------------------------------------------------------

def test_submit_analyze_video_returns_handle(client):
    with patch.object(client, "_request", return_value=accepted("analyze/video")) as req:
        handle = client.submit_analyze_video(video_url=VIDEO, query="How much chicken?", include_scenes=True,
                                             webhook_url="https://example.com/hook")
    assert isinstance(handle, Job)
    assert handle.job_type == "analyze_video" and handle.task_id == "task_1"
    req.assert_called_once_with(
        "POST", "/analyze/video/async",
        json_body={"video_url": VIDEO, "transcript_text": False, "query": "How much chicken?",
                   "include_scenes": True, "webhook_url": "https://example.com/hook"},
    )


def test_submit_analyze_video_minimal_body(client):
    with patch.object(client, "_request", return_value=accepted("analyze/video")) as req:
        client.submit_analyze_video(video_url=VIDEO)
    assert req.call_args[1]["json_body"] == {"video_url": VIDEO, "transcript_text": False}


def test_analysis_job_result_is_an_analysis_response(client):
    handle = client.resume_job("analyze_video", "task_1")
    done = job("analyze_video", "completed", result=ANALYSIS_WITH_SCENES["data"], usage=ANALYSIS_WITH_SCENES["usage"])
    with patch.object(client, "_request", return_value=done) as req:
        resp = handle.result(timeout=5, include_usage=True)
    assert req.call_args[0] == ("GET", "/analyze/video/task_1")
    assert isinstance(resp, AnalysisResponse)
    assert resp.data.frames_analyzed == 30 and len(resp.data.scenes) == 2
    assert resp.usage.total_credits == 0.0401
    with patch.object(client, "_request", return_value=done):
        polled = handle.refresh()
    assert isinstance(polled, AnalyzeVideoJobResponse) and polled.data.result.frames_analyzed == 30


def test_a_failed_analysis_job_raises_the_api_error(client):
    handle = client.resume_job("analyze_video", "task_1")
    failed = job("analyze_video", "failed", error={
        "error": "video_unavailable", "message": "This video is unavailable or was removed.", "http_status": 404})
    with patch.object(client, "_request", return_value=failed):
        with pytest.raises(VidNavigatorError) as raised:
            handle.result(timeout=5)
    assert raised.value.error_code == "video_unavailable"


# ---------------------------------------------------------------------------
# Extraction
# ---------------------------------------------------------------------------

def test_extract_video_data_with_scenes(client):
    done = job("extract_video", "completed", result={"dish": "PATÊ DE FRANGO CREMOSO"})
    done["data"]["video_info"] = {"title": "Patê de frango"}
    done["data"]["frames_analyzed"] = 30
    with patch.object(client, "_request", side_effect=[accepted("extract/video"), done]) as req:
        resp = client.extract_video_data(video_url=VIDEO, schema=SCHEMA, include_scenes=True, timeout=5)
    submit = req.call_args_list[0]
    assert submit[0] == ("POST", "/extract/video/async")
    assert submit[1]["json_body"] == {"video_url": VIDEO, "transcribe": True, "include_scenes": True, "schema": SCHEMA}
    assert isinstance(resp, ExtractionApiResponse)
    assert resp.data == {"dish": "PATÊ DE FRANGO CREMOSO"} and resp.frames_analyzed == 30


def test_extract_video_data_without_scenes_sends_no_include_scenes(client):
    with patch.object(client, "_request", return_value=accepted("extract/video")) as req:
        client.submit_extract_video_data(video_url=VIDEO, schema=SCHEMA)
    assert "include_scenes" not in req.call_args[1]["json_body"]


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


def test_analyze_file_scenes_starts_the_analysis(client):
    raw = {"status": "success", "data": {"file_id": "f1", "scenes_status": "processing",
                                         "message": "Scene analysis started."}}
    with patch.object(client, "_request", return_value=raw) as req:
        resp = client.analyze_file_scenes("f1")
    assert req.call_args[0] == ("POST", "/file/f1/scenes")
    assert isinstance(resp, FileScenesResponse)
    assert resp.data.scenes_status == "processing" and resp.data.file_id == "f1"


def test_get_file_carries_the_scenes_once_they_are_there(client):
    raw = {"status": "success", "data": {
        "file_info": {"id": "f1", "name": "clip.mp4", "status": "completed", "scenes_status": "completed"},
        "transcript": [{"text": "Música", "start": 0.0, "end": 4.0}], "scenes": SCENES, "frames_analyzed": 30}}
    with patch.object(client, "_request", return_value=raw):
        resp = client.get_file("f1")
    assert isinstance(resp, FileResponse)
    assert resp.data.file_info.scenes_status == "completed"
    assert resp.data.scenes[0].on_screen_text == "PATÊ DE FRANGO CREMOSO" and resp.data.frames_analyzed == 30


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


def test_analyze_file_with_scenes(client):
    raw = {"status": "success", "data": {"file_info": {"id": "f1", "scenes_status": "completed"}, "transcript": [],
                                         "transcript_analysis": ANALYSIS, "scenes": SCENES, "frames_analyzed": 30}}
    with patch.object(client, "_request", return_value=raw) as req:
        resp = client.analyze_file(file_id="f1", query="How much chicken?", include_scenes=True)
    assert req.call_args[1]["json_body"]["include_scenes"] is True
    assert len(resp.data.scenes) == 2


# ---------------------------------------------------------------------------
# The file has no scenes yet
# ---------------------------------------------------------------------------

def test_scenes_not_available_is_its_own_error():
    error = error_from_response(409, NO_SCENES)
    assert isinstance(error, ScenesNotAvailableError)
    assert error.status_code == 409 and error.error_code == "scenes_not_available"
    assert error.scenes_status == "none"
    assert "POST /v1/file/f1/scenes" in error.message

    still_running = error_from_response(409, dict(NO_SCENES, scenes_status="processing"))
    assert still_running.scenes_status == "processing"
    assert error_from_response(409, {"error": "scenes_not_available"}).scenes_status is None


def test_the_usual_way_to_get_the_scenes_of_a_file(client):
    """Ask, be told there are none, start them, ask again."""
    started = {"status": "success", "data": {"file_id": "f1", "scenes_status": "processing", "message": "started"}}
    answer = {"status": "success", "data": {"file_info": {"id": "f1"}, "transcript": [],
                                            "transcript_analysis": ANALYSIS, "scenes": SCENES, "frames_analyzed": 30}}
    with patch.object(client, "_request", side_effect=[error_from_response(409, NO_SCENES), started, answer]) as req:
        with pytest.raises(ScenesNotAvailableError) as raised:
            client.analyze_file(file_id="f1", include_scenes=True)
        assert raised.value.scenes_status == "none"
        assert client.analyze_file_scenes("f1").data.scenes_status == "processing"
        assert client.analyze_file(file_id="f1", include_scenes=True).data.frames_analyzed == 30
    assert [call[0][1] for call in req.call_args_list] == ["/analyze/file", "/file/f1/scenes", "/analyze/file"]


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
            with patch.object(client, "_request", return_value=ANALYSIS_WITH_SCENES) as req:
                analysis = await client.analyze_video(video_url=VIDEO, include_scenes=True)
            sent = req.call_args[1]["json_body"]
            with patch.object(client, "_request", return_value=accepted("analyze/video")):
                handle = await client.submit_analyze_video(video_url=VIDEO, include_scenes=True)
            started = {"status": "success", "data": {"file_id": "f1", "scenes_status": "completed", "message": "there"}}
            with patch.object(client, "_request", return_value=started) as req:
                scenes = await client.analyze_file_scenes("f1")
            return analysis, sent, handle, scenes, req.call_args[0]
        finally:
            await client.aclose()

    analysis, sent, handle, scenes, call = asyncio.run(go())
    assert analysis.data.frames_analyzed == 30 and sent["include_scenes"] is True
    assert isinstance(handle, AsyncJob) and handle.job_type == "analyze_video"
    assert scenes.data.scenes_status == "completed" and call == ("POST", "/file/f1/scenes")
