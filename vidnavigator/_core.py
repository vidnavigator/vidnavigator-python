"""Transport-independent request building shared by the sync and async clients.

Each ``build_*`` function turns a method's arguments into a :class:`Request`
describing the HTTP call and how to parse its response. The clients only
send requests: :class:`~vidnavigator.VidNavigatorClient` with ``requests``,
:class:`~vidnavigator.AsyncVidNavigatorClient` with ``httpx``.
"""

from __future__ import annotations

import json
import mimetypes
import os
from datetime import date, datetime
from typing import Any, Callable, Dict, List, NamedTuple, Optional, Union

from .exceptions import VidNavigatorError
from . import models

DEFAULT_BASE_URL = "https://api.vidnavigator.com/v1"
USER_AGENT = "vidnavigator-python/2.1.0"
API_KEY_ENV_VAR = "VIDNAVIGATOR_API_KEY"

DateLike = Union[str, date, datetime]


def parse_model(model_cls: Any, raw: Any) -> Any:
    """Parse JSON dict into a Pydantic model (v1: parse_obj, v2: model_validate)."""
    if hasattr(model_cls, "model_validate"):
        return model_cls.model_validate(raw)
    return model_cls.parse_obj(raw)


def format_datetime(value: DateLike) -> str:
    """Serialize TikTok date/datetime filters."""
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return value


def guess_schema_content_type(file_path: str) -> str:
    """Return a stable content type for uploaded JSON/YAML schema files."""
    ext = os.path.splitext(file_path)[1].lower()
    if ext in {".yaml", ".yml"}:
        return "application/yaml"
    if ext == ".json":
        return "application/json"
    return mimetypes.guess_type(file_path)[0] or "application/octet-stream"


def resolve_api_key(api_key: Optional[str]) -> str:
    from .exceptions import AuthenticationError

    api_key = api_key or os.getenv(API_KEY_ENV_VAR)
    if not api_key:
        raise AuthenticationError(
            "API key was not provided. Pass it explicitly or set the VIDNAVIGATOR_API_KEY env var."
        )
    return api_key


def default_headers(api_key: str) -> Dict[str, str]:
    return {"X-API-Key": api_key, "User-Agent": USER_AGENT, "Accept": "application/json"}


class Upload(NamedTuple):
    """A file to send as a multipart field; the client opens it while sending."""

    field: str
    path: str
    filename: str
    content_type: str


def _identity(raw: Any) -> Any:
    return raw


class Request(NamedTuple):
    method: str
    path: str
    kwargs: Dict[str, Any]  # json_body / params / data, exactly as passed to _request
    parse: Callable[[Any], Any] = _identity
    upload: Optional[Upload] = None
    job_type: Optional[str] = None  # set for job submits


def _model(model_cls: Any) -> Callable[[Any], Any]:
    return lambda raw: parse_model(model_cls, raw)


def _json(method: str, path: str, body: Dict[str, Any], model_cls: Any) -> Request:
    return Request(method, path, {"json_body": body}, _model(model_cls))


def _bool_form(fields: Dict[str, Any]) -> Dict[str, Any]:
    return {k: ("true" if v else "false") if isinstance(v, bool) else v for k, v in fields.items()}


def _schema_upload(schema_file: str) -> Upload:
    if not os.path.isfile(schema_file):
        raise FileNotFoundError(schema_file)
    return Upload(
        "schema",
        schema_file,
        os.path.basename(schema_file),
        guess_schema_content_type(schema_file),
    )


def _schema_request(
    path: str,
    fields: Dict[str, Any],
    schema: Optional[Dict[str, Any]],
    schema_file: Optional[str],
    model_cls: Any,
) -> Request:
    """JSON body with ``schema``, or multipart with an uploaded schema file.

    ``None`` values in *fields* are omitted.
    """
    if (schema is None) == (schema_file is None):
        raise ValueError("Pass exactly one of schema or schema_file.")
    fields = {k: v for k, v in fields.items() if v is not None}
    if schema_file is not None:
        return Request("POST", path, {"data": _bool_form(fields)}, _model(model_cls),
                       upload=_schema_upload(schema_file))
    return Request("POST", path, {"json_body": {**fields, "schema": schema}}, _model(model_cls))


def _submit(job_type: str, request: Request) -> Request:
    return request._replace(job_type=job_type)


def _with_optional(payload: Dict[str, Any], **values: Any) -> Dict[str, Any]:
    for key, value in values.items():
        if value is not None:
            payload[key] = value
    return payload


# ---------------------------------------------------------------------------
# Transcripts
# ---------------------------------------------------------------------------

def get_transcript(
    *,
    video_url: str,
    language: Optional[str] = None,
    metadata_only: bool = False,
    fallback_to_metadata: bool = False,
    transcript_text: bool = False,
    include_usage: bool = False,
) -> Request:
    payload: Dict[str, Any] = {
        "video_url": video_url,
        "metadata_only": metadata_only,
        "fallback_to_metadata": fallback_to_metadata,
        "transcript_text": transcript_text,
        "include_usage": include_usage,
    }
    if language:
        payload["language"] = language
    return _json("POST", "/transcript", payload, models.TranscriptResponse)


def submit_transcribe_video(
    *,
    video_url: str,
    transcript_text: bool = False,
    all_videos: bool = False,
    webhook_url: Optional[str] = None,
) -> Request:
    payload = _with_optional(
        {"video_url": video_url, "transcript_text": transcript_text, "all_videos": all_videos},
        webhook_url=webhook_url,
    )
    return _submit("transcribe", _json("POST", "/transcribe/async", payload, models.AsyncJobSubmitResponse))


# ---------------------------------------------------------------------------
# Files
# ---------------------------------------------------------------------------

def get_files(
    *,
    limit: int = 50,
    offset: int = 0,
    status: Optional[str] = None,
    namespace_id: Optional[str] = None,
) -> Request:
    params: Dict[str, Any] = {"limit": limit, "offset": offset}
    if status:
        params["status"] = status
    if namespace_id is not None:
        params["namespace_id"] = namespace_id
    return Request("GET", "/files", {"params": params}, _model(models.FilesListResponse))


def get_file(file_id: str, *, transcript_text: bool = False) -> Request:
    params = {"transcript_text": "true"} if transcript_text else None
    return Request("GET", f"/file/{file_id}", {"params": params}, _model(models.FileResponse))


def upload_file(
    file_path: str,
    *,
    wait_for_completion: bool = False,
    namespace_ids: Optional[List[str]] = None,
) -> Request:
    if not os.path.isfile(file_path):
        raise FileNotFoundError(file_path)
    data: Dict[str, Any] = {"wait_for_completion": "true" if wait_for_completion else "false"}
    if namespace_ids is not None:
        data["namespace_ids"] = json.dumps(namespace_ids)
    content_type = mimetypes.guess_type(file_path)[0] or "application/octet-stream"
    upload = Upload("file", file_path, os.path.basename(file_path), content_type)
    return Request("POST", "/upload/file", {"data": data}, upload=upload)


def file_action(method: str, path: str) -> Request:
    return Request(method, path, {})


# ---------------------------------------------------------------------------
# Analysis and extraction
# ---------------------------------------------------------------------------

def _analyze(path: str, key: str, value: str, query: Optional[str], transcript_text: bool,
             include_usage: bool) -> Request:
    payload: Dict[str, Any] = {key: value, "transcript_text": transcript_text, "include_usage": include_usage}
    if query:
        payload["query"] = query
    return _json("POST", path, payload, models.AnalysisResponse)


def analyze_video(*, video_url: str, query: Optional[str] = None, transcript_text: bool = False,
                  include_usage: bool = False) -> Request:
    return _analyze("/analyze/video", "video_url", video_url, query, transcript_text, include_usage)


def analyze_file(*, file_id: str, query: Optional[str] = None, transcript_text: bool = False,
                 include_usage: bool = False) -> Request:
    return _analyze("/analyze/file", "file_id", file_id, query, transcript_text, include_usage)


def submit_extract_video_data(
    *,
    video_url: str,
    schema: Optional[Dict[str, Any]] = None,
    schema_file: Optional[str] = None,
    what_to_extract: Optional[str] = None,
    transcribe: bool = True,
    webhook_url: Optional[str] = None,
) -> Request:
    fields = {
        "video_url": video_url,
        "transcribe": transcribe,
        "what_to_extract": what_to_extract,
        "webhook_url": webhook_url,
    }
    return _submit("extract_video", _schema_request(
        "/extract/video/async", fields, schema, schema_file, models.AsyncJobSubmitResponse,
    ))


def extract_file_data(
    *,
    file_id: str,
    schema: Optional[Dict[str, Any]] = None,
    schema_file: Optional[str] = None,
    what_to_extract: Optional[str] = None,
    include_usage: bool = False,
) -> Request:
    if (schema is None) == (schema_file is None):
        raise ValueError("Pass exactly one of schema or schema_file.")
    if schema_file is not None:
        data: Dict[str, Any] = {"file_id": file_id, "include_usage": "true" if include_usage else "false"}
        if what_to_extract is not None:
            data["what_to_extract"] = what_to_extract
        return Request("POST", "/extract/file", {"data": data}, _model(models.ExtractionApiResponse),
                       upload=_schema_upload(schema_file))
    payload: Dict[str, Any] = {"file_id": file_id, "schema": schema, "include_usage": include_usage}
    if what_to_extract is not None:
        payload["what_to_extract"] = what_to_extract
    return _json("POST", "/extract/file", payload, models.ExtractionApiResponse)


# ---------------------------------------------------------------------------
# TikTok
# ---------------------------------------------------------------------------

def submit_tiktok_profile_scrape(
    *,
    profile_url: str,
    max_posts: Optional[int] = None,
    after_datetime: Optional[DateLike] = None,
    before_datetime: Optional[DateLike] = None,
    min_likes: Optional[int] = None,
    max_likes: Optional[int] = None,
    webhook_url: Optional[str] = None,
) -> Request:
    payload = _with_optional(
        {"profile_url": profile_url},
        max_posts=max_posts,
        after_datetime=None if after_datetime is None else format_datetime(after_datetime),
        before_datetime=None if before_datetime is None else format_datetime(before_datetime),
        min_likes=min_likes,
        max_likes=max_likes,
        webhook_url=webhook_url,
    )
    return _submit("tiktok_profile", _json("POST", "/tiktok/profile", payload, models.TikTokProfileSubmitResponse))


def submit_tiktok_search(
    *,
    query: str,
    max_results: Optional[int] = None,
    parallel_search_slices: Optional[int] = None,
    sort_by: Optional[str] = None,
    published_within: Optional[str] = None,
    after_datetime: Optional[DateLike] = None,
    before_datetime: Optional[DateLike] = None,
    min_likes: Optional[int] = None,
    max_likes: Optional[int] = None,
    min_views: Optional[int] = None,
    max_views: Optional[int] = None,
    webhook_url: Optional[str] = None,
) -> Request:
    payload = _with_optional(
        {"query": query},
        max_results=max_results,
        parallel_search_slices=parallel_search_slices,
        sort_by=sort_by,
        published_within=published_within,
        after_datetime=None if after_datetime is None else format_datetime(after_datetime),
        before_datetime=None if before_datetime is None else format_datetime(before_datetime),
        min_likes=min_likes,
        max_likes=max_likes,
        min_views=min_views,
        max_views=max_views,
        webhook_url=webhook_url,
    )
    return _submit("tiktok_search", _json("POST", "/tiktok/search", payload, models.TikTokSearchSubmitResponse))


def _tiktok_page(path: str, model_cls: Any, cursor: Optional[str], limit: int, include_usage: bool) -> Request:
    params: Dict[str, Any] = {"limit": limit}
    if cursor is not None:
        params["cursor"] = cursor
    if include_usage:
        params["include_usage"] = "true"
    return Request("GET", path, {"params": params}, _model(model_cls))


def get_tiktok_profile_scrape(task_id: str, *, cursor: Optional[str] = None, limit: int = 50,
                              include_usage: bool = False) -> Request:
    return _tiktok_page(f"/tiktok/profile/{task_id}", models.TikTokProfileResponse, cursor, limit, include_usage)


def get_tiktok_search(task_id: str, *, cursor: Optional[str] = None, limit: int = 50,
                      include_usage: bool = False) -> Request:
    return _tiktok_page(f"/tiktok/search/{task_id}", models.TikTokSearchResponse, cursor, limit, include_usage)


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------

def search_youtube(
    *,
    query: str,
    use_enhanced_search: bool = True,
    start_year: Optional[int] = None,
    end_year: Optional[int] = None,
    focus: str = "relevance",
    duration: Optional[int] = None,
    max_results: Optional[int] = None,
    include_usage: bool = False,
) -> Request:
    payload = _with_optional(
        {"query": query, "use_enhanced_search": use_enhanced_search, "focus": focus,
         "include_usage": include_usage},
        start_year=start_year,
        end_year=end_year,
        duration=duration,
        max_results=max_results,
    )
    return _json("POST", "/youtube/search", payload, models.VideoSearchResponse)


def search_files(*, query: str, namespace_ids: Optional[List[str]] = None,
                 include_usage: bool = False) -> Request:
    payload = _with_optional({"query": query, "include_usage": include_usage}, namespace_ids=namespace_ids)
    return _json("POST", "/search/file", payload, models.FileSearchResponse)


# ---------------------------------------------------------------------------
# Namespaces
# ---------------------------------------------------------------------------

def get_namespaces() -> Request:
    return Request("GET", "/namespaces", {}, _model(models.NamespaceListResponse))


def create_namespace(name: str) -> Request:
    return _json("POST", "/namespaces", {"name": name}, models.NamespaceResponse)


def update_namespace(namespace_id: str, name: str) -> Request:
    return _json("PUT", f"/namespaces/{namespace_id}", {"name": name}, models.MessageResponse)


def delete_namespace(namespace_id: str) -> Request:
    return Request("DELETE", f"/namespaces/{namespace_id}", {}, _model(models.MessageResponse))


def update_file_namespaces(file_id: str, namespace_ids: List[str]) -> Request:
    return _json("PUT", f"/file/{file_id}/namespaces", {"namespace_ids": namespace_ids},
                 models.FileNamespacesResponse)


# ---------------------------------------------------------------------------
# System and tweets
# ---------------------------------------------------------------------------

def get_usage() -> Request:
    return Request("GET", "/usage", {}, _model(models.UsageResponse))


def health_check() -> Request:
    return Request("GET", "/health", {}, _model(models.HealthResponse))


def submit_tweet_statement(*, tweet_id: str, webhook_url: Optional[str] = None) -> Request:
    payload = _with_optional({"tweet_id": tweet_id}, webhook_url=webhook_url)
    return _submit("tweet_statement", _json("POST", "/tweet/statement/async", payload,
                                            models.AsyncJobSubmitResponse))


# ---------------------------------------------------------------------------
# Responses
# ---------------------------------------------------------------------------

def submitted_task_id(job_type: str, submitted: Any) -> str:
    task_id = submitted.data.task_id if submitted.data is not None else None
    if not task_id:
        raise VidNavigatorError(f"{job_type} submit response did not include a task_id")
    return task_id


def decode_response(response: Any, *, ok: bool, reason_attr: str) -> Any:
    """Return the JSON payload of a successful response, or raise the matching SDK error.

    Works for both ``requests`` and ``httpx`` responses; ``reason_attr`` names
    the attribute holding the HTTP reason phrase (``reason`` / ``reason_phrase``).
    """
    from .exceptions import error_from_response

    try:
        payload = response.json()
    except ValueError:
        payload = {"status": "error", "message": response.text}
    if ok:
        return payload
    if not isinstance(payload, dict):
        payload = {"status": "error", "message": str(payload)}
    raise error_from_response(response.status_code, payload, reason=getattr(response, reason_attr))
