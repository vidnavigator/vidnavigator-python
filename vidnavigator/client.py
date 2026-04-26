"""VidNavigator Developer API Python client."""

from __future__ import annotations

import json
import mimetypes
import os
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Union
import requests

from .exceptions import (
    AccessDeniedError,
    AuthenticationError,
    BadRequestError,
    GeoRestrictedError,
    NotFoundError,
    PaymentRequiredError,
    RateLimitExceeded,
    ServerError,
    StorageQuotaExceededError,
    SystemOverloadError,
    VidNavigatorError,
)
from . import models


DEFAULT_BASE_URL = "https://api.vidnavigator.com/v1"
USER_AGENT = "vidnavigator-python/1.0.1"


def _parse_model(model_cls: Any, raw: Any) -> Any:
    """Parse JSON dict into a Pydantic model (v1: parse_obj, v2: model_validate)."""
    if hasattr(model_cls, "model_validate"):
        return model_cls.model_validate(raw)
    return model_cls.parse_obj(raw)


def _format_yyyy_mm_dd(value: Union[str, date, datetime]) -> str:
    """Serialize TikTok profile date filters in API-required YYYY-MM-DD format."""
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    return value


class VidNavigatorClient:
    """Client for interacting with the VidNavigator Developer API.

    Parameters
    ----------
    api_key:
        Your VidNavigator API key. This is sent via the *X-API-Key* header.
    base_url:
        Override the default API base URL (useful for testing/staging).
    timeout:
        Request timeout (seconds).
    session:
        Optional *requests.Session* to use. If *None*, a new session is created.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        *,
        base_url: str = DEFAULT_BASE_URL,
        timeout: int | float = 30,
        session: Optional[requests.Session] = None,
    ) -> None:
        api_key = api_key or os.getenv("VIDNAVIGATOR_API_KEY")
        if not api_key:
            raise AuthenticationError(
                "API key was not provided. Pass it explicitly or set the VIDNAVIGATOR_API_KEY env var."
            )

        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = session or requests.Session()
        self.session.headers.update(
            {
                "X-API-Key": api_key,
                "User-Agent": USER_AGENT,
                "Accept": "application/json",
            }
        )

    # ---------------------------------------------------------------------
    # Internal helpers
    # ---------------------------------------------------------------------
    def _request(
        self,
        method: str,
        path: str,
        *,
        params: Optional[Dict[str, Any]] = None,
        json_body: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        files: Any = None,
        stream: bool = False,
    ) -> Any:
        body = json_body
        url = f"{self.base_url}{path}"

        try:
            response = self.session.request(
                method,
                url,
                params=params,
                json=body,
                data=data,
                files=files,
                timeout=self.timeout,
                stream=stream,
            )
        except requests.RequestException as exc:
            raise VidNavigatorError(f"Request failed: {exc}") from exc

        if stream:
            return response

        try:
            payload = response.json()
        except ValueError:
            payload = {"status": "error", "message": response.text}

        if response.ok:
            return payload

        status_code = response.status_code
        error_msg = payload.get("message") or response.reason

        if status_code == 400:
            raise BadRequestError(error_msg)
        if status_code == 402:
            raise PaymentRequiredError(error_msg)
        if status_code == 403:
            raise AccessDeniedError(error_msg)
        if status_code == 404:
            raise NotFoundError(error_msg)
        if status_code == 413:
            raise StorageQuotaExceededError(error_msg)
        if status_code == 429:
            raise RateLimitExceeded(error_msg)
        if status_code == 451:
            raise GeoRestrictedError(error_msg)
        if status_code == 503:
            retry_int = None
            raw_retry = payload.get("retry_after_seconds")
            if raw_retry is not None:
                try:
                    retry_int = int(raw_retry)
                except (TypeError, ValueError):
                    retry_int = None
            raise SystemOverloadError(error_msg, retry_after_seconds=retry_int)
        if status_code >= 500:
            raise ServerError(error_msg)

        raise VidNavigatorError(f"Unexpected response ({status_code}): {error_msg}")

    # ---------------------------------------------------------------------
    # Public API methods
    # ---------------------------------------------------------------------

    # Transcripts ------------------------------------------------------------------
    def get_transcript(
        self,
        *,
        video_url: str,
        language: Optional[str] = None,
        metadata_only: bool = False,
        fallback_to_metadata: bool = False,
        transcript_text: bool = False,
    ) -> models.TranscriptResponse:
        """Extract transcript from a non-YouTube online video.

        For YouTube URLs, use :meth:`get_youtube_transcript` instead.
        """
        payload: Dict[str, Any] = {
            "video_url": video_url,
            "metadata_only": metadata_only,
            "fallback_to_metadata": fallback_to_metadata,
            "transcript_text": transcript_text,
        }
        if language:
            payload["language"] = language
        raw = self._request("POST", "/transcript", json_body=payload)
        return _parse_model(models.TranscriptResponse, raw)

    def get_youtube_transcript(
        self,
        *,
        video_url: str,
        language: Optional[str] = None,
        metadata_only: bool = False,
        fallback_to_metadata: bool = False,
        transcript_text: bool = False,
    ) -> models.TranscriptResponse:
        """Extract transcript from a YouTube video."""
        payload: Dict[str, Any] = {
            "video_url": video_url,
            "metadata_only": metadata_only,
            "fallback_to_metadata": fallback_to_metadata,
            "transcript_text": transcript_text,
        }
        if language:
            payload["language"] = language
        raw = self._request("POST", "/youtube/transcript", json_body=payload)
        return _parse_model(models.TranscriptResponse, raw)

    def transcribe_video(
        self,
        *,
        video_url: str,
        transcript_text: bool = False,
        all_videos: bool = False,
    ) -> Union[models.TranscriptResponse, models.TranscribeAllVideosResponse]:
        """Transcribe an online video using speech-to-text.

        When *all_videos* is True (carousel posts), the response shape includes
        *carousel_info* and *videos* instead of a single *video_info*.
        """
        payload: Dict[str, Any] = {
            "video_url": video_url,
            "transcript_text": transcript_text,
            "all_videos": all_videos,
        }
        raw = self._request("POST", "/transcribe", json_body=payload)
        if all_videos:
            return _parse_model(models.TranscribeAllVideosResponse, raw)
        return _parse_model(models.TranscriptResponse, raw)

    # Files ------------------------------------------------------------------------
    def get_files(
        self,
        *,
        limit: int = 50,
        offset: int = 0,
        status: Optional[str] = None,
        namespace_id: Optional[str] = None,
    ) -> models.FilesListResponse:
        """Retrieve a paginated list of uploaded files.

        Parameters
        ----------
        namespace_id:
            Filter by namespace. Only files in this namespace are returned.
        """
        params: Dict[str, Any] = {"limit": limit, "offset": offset}
        if status:
            params["status"] = status
        if namespace_id is not None:
            params["namespace_id"] = namespace_id
        raw = self._request("GET", "/files", params=params)
        return _parse_model(models.FilesListResponse, raw)

    def get_file(
        self,
        file_id: str,
        *,
        transcript_text: bool = False,
    ) -> models.FileResponse:
        """Retrieve details (and transcript) for a specific file."""
        params: Optional[Dict[str, Any]] = None
        if transcript_text:
            params = {"transcript_text": "true"}
        raw = self._request("GET", f"/file/{file_id}", params=params)
        return _parse_model(models.FileResponse, raw)

    # Analysis ---------------------------------------------------------------------
    def analyze_video(
        self,
        *,
        video_url: str,
        query: Optional[str] = None,
        transcript_text: bool = False,
    ) -> models.AnalysisResponse:
        payload: Dict[str, Any] = {"video_url": video_url, "transcript_text": transcript_text}
        if query:
            payload["query"] = query
        raw = self._request("POST", "/analyze/video", json_body=payload)
        return _parse_model(models.AnalysisResponse, raw)

    def analyze_file(
        self,
        *,
        file_id: str,
        query: Optional[str] = None,
        transcript_text: bool = False,
    ) -> models.AnalysisResponse:
        payload: Dict[str, Any] = {"file_id": file_id, "transcript_text": transcript_text}
        if query:
            payload["query"] = query
        raw = self._request("POST", "/analyze/file", json_body=payload)
        return _parse_model(models.AnalysisResponse, raw)

    # Extraction -------------------------------------------------------------------
    def extract_video_data(
        self,
        *,
        video_url: str,
        schema: Dict[str, Any],
        what_to_extract: Optional[str] = None,
        transcribe: bool = True,
        include_usage: bool = False,
    ) -> models.ExtractionApiResponse:
        """Extract structured data from an online video transcript using a custom schema."""
        payload: Dict[str, Any] = {
            "video_url": video_url,
            "schema": schema,
            "transcribe": transcribe,
            "include_usage": include_usage,
        }
        if what_to_extract is not None:
            payload["what_to_extract"] = what_to_extract
        raw = self._request("POST", "/extract/video", json_body=payload)
        return _parse_model(models.ExtractionApiResponse, raw)

    # TikTok -----------------------------------------------------------------------
    def submit_tiktok_profile_scrape(
        self,
        *,
        profile_url: str,
        max_posts: Optional[int] = None,
        after_date: Optional[Union[str, date, datetime]] = None,
        before_date: Optional[Union[str, date, datetime]] = None,
        min_likes: Optional[int] = None,
        max_likes: Optional[int] = None,
    ) -> models.TikTokProfileSubmitResponse:
        """Start an async TikTok profile scrape and return the task metadata.

        Date filters must be YYYY-MM-DD strings. ``date`` and ``datetime`` values
        are accepted and serialized to that format automatically.
        """
        payload: Dict[str, Any] = {"profile_url": profile_url}
        if max_posts is not None:
            payload["max_posts"] = max_posts
        if after_date is not None:
            payload["after_date"] = _format_yyyy_mm_dd(after_date)
        if before_date is not None:
            payload["before_date"] = _format_yyyy_mm_dd(before_date)
        if min_likes is not None:
            payload["min_likes"] = min_likes
        if max_likes is not None:
            payload["max_likes"] = max_likes
        raw = self._request("POST", "/tiktok/profile", json_body=payload)
        return _parse_model(models.TikTokProfileSubmitResponse, raw)

    def get_tiktok_profile_scrape(
        self,
        task_id: str,
        *,
        cursor: Optional[str] = None,
        limit: int = 50,
    ) -> models.TikTokProfileResponse:
        """Poll an async TikTok profile scrape task and retrieve a page of videos."""
        params: Dict[str, Any] = {"limit": limit}
        if cursor is not None:
            params["cursor"] = cursor
        raw = self._request("GET", f"/tiktok/profile/{task_id}", params=params)
        return _parse_model(models.TikTokProfileResponse, raw)

    def extract_file_data(
        self,
        *,
        file_id: str,
        schema: Dict[str, Any],
        what_to_extract: Optional[str] = None,
        include_usage: bool = False,
    ) -> models.ExtractionApiResponse:
        """Extract structured data from an uploaded file's transcript using a custom schema."""
        payload: Dict[str, Any] = {
            "file_id": file_id,
            "schema": schema,
            "include_usage": include_usage,
        }
        if what_to_extract is not None:
            payload["what_to_extract"] = what_to_extract
        raw = self._request("POST", "/extract/file", json_body=payload)
        return _parse_model(models.ExtractionApiResponse, raw)

    # Search -----------------------------------------------------------------------
    def search_videos(
        self,
        *,
        query: str,
        use_enhanced_search: bool = True,
        start_year: Optional[int] = None,
        end_year: Optional[int] = None,
        focus: str = "relevance",
        duration: Optional[int] = None,
    ) -> models.VideoSearchResponse:
        payload: Dict[str, Any] = {
            "query": query,
            "use_enhanced_search": use_enhanced_search,
            "focus": focus,
        }
        if start_year is not None:
            payload["start_year"] = start_year
        if end_year is not None:
            payload["end_year"] = end_year
        if duration is not None:
            payload["duration"] = duration
        raw = self._request("POST", "/search/video", json_body=payload)
        return _parse_model(models.VideoSearchResponse, raw)

    def search_files(
        self,
        *,
        query: str,
        namespace_ids: Optional[List[str]] = None,
    ) -> models.FileSearchResponse:
        payload: Dict[str, Any] = {"query": query}
        if namespace_ids is not None:
            payload["namespace_ids"] = namespace_ids
        raw = self._request("POST", "/search/file", json_body=payload)
        return _parse_model(models.FileSearchResponse, raw)

    # Namespaces -------------------------------------------------------------------
    def get_namespaces(self) -> models.NamespaceListResponse:
        """List all namespaces for the authenticated user."""
        raw = self._request("GET", "/namespaces")
        return _parse_model(models.NamespaceListResponse, raw)

    def create_namespace(self, name: str) -> models.NamespaceResponse:
        """Create a new namespace."""
        raw = self._request("POST", "/namespaces", json_body={"name": name})
        return _parse_model(models.NamespaceResponse, raw)

    def update_namespace(self, namespace_id: str, name: str) -> models.MessageResponse:
        """Rename a namespace."""
        raw = self._request(
            "PUT",
            f"/namespaces/{namespace_id}",
            json_body={"name": name},
        )
        return _parse_model(models.MessageResponse, raw)

    def delete_namespace(self, namespace_id: str) -> models.MessageResponse:
        """Delete a namespace."""
        raw = self._request("DELETE", f"/namespaces/{namespace_id}")
        return _parse_model(models.MessageResponse, raw)

    def update_file_namespaces(
        self,
        file_id: str,
        namespace_ids: List[str],
    ) -> models.FileNamespacesResponse:
        """Replace namespace assignments for a file.

        Returns the updated *namespace_ids* and resolved *namespaces*.
        """
        raw = self._request(
            "PUT",
            f"/file/{file_id}/namespaces",
            json_body={"namespace_ids": namespace_ids},
        )
        return _parse_model(models.FileNamespacesResponse, raw)

    # Uploads ----------------------------------------------------------------------
    def upload_file(
        self,
        file_path: str,
        *,
        wait_for_completion: bool = False,
        namespace_ids: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Upload an audio or video file.

        Parameters
        ----------
        file_path: str
            Path to the local file.
        wait_for_completion: bool
            If *True*, the call will wait until processing finishes before returning.
        namespace_ids: Optional[List[str]]
            Namespace IDs to assign (sent as a JSON array string per API spec).
        """
        if not os.path.isfile(file_path):
            raise FileNotFoundError(file_path)

        data: Dict[str, Any] = {
            "wait_for_completion": "true" if wait_for_completion else "false",
        }
        if namespace_ids is not None:
            data["namespace_ids"] = json.dumps(namespace_ids)

        filename = os.path.basename(file_path)
        content_type = mimetypes.guess_type(file_path)[0] or "application/octet-stream"

        with open(file_path, "rb") as fp:
            files = {"file": (filename, fp, content_type)}
            return self._request("POST", "/upload/file", data=data, files=files)

    def retry_file_processing(self, file_id: str) -> Dict[str, Any]:
        return self._request("POST", f"/file/{file_id}/retry")

    def cancel_file_upload(self, file_id: str) -> Dict[str, Any]:
        return self._request("POST", f"/file/{file_id}/cancel")

    def delete_file(self, file_id: str) -> Dict[str, Any]:
        return self._request("DELETE", f"/file/{file_id}/delete")

    def get_file_url(self, file_id: str) -> Dict[str, Any]:
        return self._request("GET", f"/file/{file_id}/url")

    # System -----------------------------------------------------------------------
    def get_usage(self) -> models.UsageResponse:
        """Retrieve current API usage and storage information."""
        raw = self._request("GET", "/usage")
        return _parse_model(models.UsageResponse, raw)

    def health_check(self) -> models.HealthResponse:
        raw = self._request("GET", "/health")
        return _parse_model(models.HealthResponse, raw)

    # Tweet analysis ---------------------------------------------------------------
    def get_tweet_statement(self, *, tweet_id: str) -> models.TweetStatementResponse:
        """Extract a structured claim analysis from an X/Twitter tweet."""
        raw = self._request("POST", "/tweet/statement", json_body={"tweet_id": tweet_id})
        return _parse_model(models.TweetStatementResponse, raw)

    # Convenience ------------------------------------------------------------------
    def close(self) -> None:
        """Close the underlying HTTP session."""
        self.session.close()

    def __enter__(self) -> "VidNavigatorClient":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
