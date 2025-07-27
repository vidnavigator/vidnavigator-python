"""VidNavigator Developer API Python client."""

from __future__ import annotations

import os
from typing import Any, Dict, Optional
import requests

from .exceptions import (
    AccessDeniedError,
    AuthenticationError,
    BadRequestError,
    NotFoundError,
    PaymentRequiredError,
    RateLimitExceeded,
    ServerError,
    VidNavigatorError,
)
from . import models


DEFAULT_BASE_URL = "https://api.vidnavigator.com/v1"
USER_AGENT = "vidnavigator-python/0.1.0"


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
        api_key: str | None = None,
        *,
        base_url: str = DEFAULT_BASE_URL,
        timeout: int | float = 30,
        session: Optional[requests.Session] = None,
    ) -> None:
        api_key = api_key or os.getenv("VIDNAVIGATOR_API_KEY")
        if not api_key:
            raise AuthenticationError("API key was not provided. Pass it explicitly or set the VIDNAVIGATOR_API_KEY env var.")

        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = session or requests.Session()
        self.session.headers.update({
            "X-API-Key": api_key,
            "User-Agent": USER_AGENT,
            "Accept": "application/json",
        })

    # ---------------------------------------------------------------------
    # Internal helpers
    # ---------------------------------------------------------------------
    def _request(
        self,
        method: str,
        path: str,
        *,
        params: Optional[Dict[str, Any]] = None,
        json: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        files: Any = None,
        stream: bool = False,
    ) -> Any:
        url = f"{self.base_url}{path}"

        try:
            response = self.session.request(
                method,
                url,
                params=params,
                json=json,
                data=data,
                files=files,
                timeout=self.timeout,
                stream=stream,
            )
        except requests.RequestException as exc:
            raise VidNavigatorError(f"Request failed: {exc}") from exc

        if stream:
            # For future use (e.g., downloading large files). Caller must handle.
            return response

        # Attempt to parse JSON; fall back to text
        try:
            payload = response.json()
        except ValueError:
            payload = {"status": "error", "message": response.text}

        if response.ok:
            return payload

        # Map error codes to exceptions
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
        if status_code == 429:
            raise RateLimitExceeded(error_msg)
        if status_code >= 500:
            raise ServerError(error_msg)

        # Fallback
        raise VidNavigatorError(f"Unexpected response ({status_code}): {error_msg}")

    # ---------------------------------------------------------------------
    # Public API methods
    # ---------------------------------------------------------------------

    # Transcripts ------------------------------------------------------------------
    def get_transcript(self, *, video_url: str, language: Optional[str] = None) -> models.TranscriptResponse:
        """Extract transcript from an online video.

        Parameters
        ----------
        video_url: str
            The full URL of the video (YouTube, Vimeo, etc.).
        language: Optional[str]
            Two-letter ISO language code (e.g., "en") if you want a specific language.
        """
        payload: Dict[str, Any] = {"video_url": video_url}
        if language:
            payload["language"] = language
        raw = self._request("POST", "/transcript", json=payload)
        return models.TranscriptResponse.parse_obj(raw)

    def transcribe_video(self, *, video_url: str) -> models.TranscriptResponse:
        """Transcribe an online video using speech-to-text.

        This is used for videos where a transcript is not readily available,
        such as on Instagram or TikTok.

        Parameters
        ----------
        video_url: str
            The full URL of the video to transcribe.
        """
        payload = {"video_url": video_url}
        raw = self._request("POST", "/transcribe", json=payload)
        return models.TranscriptResponse.parse_obj(raw)

    # Files ------------------------------------------------------------------------
    def get_files(
        self,
        *,
        limit: int = 50,
        offset: int = 0,
        status: Optional[str] = None,
    ) -> models.FilesListResponse:
        """Retrieve a paginated list of uploaded files."""
        params: Dict[str, Any] = {"limit": limit, "offset": offset}
        if status:
            params["status"] = status
        raw = self._request("GET", "/files", params=params)
        return models.FilesListResponse.parse_obj(raw)

    def get_file(self, file_id: str) -> models.FileResponse:
        """Retrieve details (and transcript) for a specific file."""
        raw = self._request("GET", f"/file/{file_id}")
        return models.FileResponse.parse_obj(raw)

    # Analysis ---------------------------------------------------------------------
    def analyze_video(self, *, video_url: str, query: Optional[str] = None) -> models.AnalysisResponse:
        payload = {"video_url": video_url}
        if query:
            payload["query"] = query
        raw = self._request("POST", "/analyze/video", json=payload)
        return models.AnalysisResponse.parse_obj(raw)

    def analyze_file(self, *, file_id: str, query: Optional[str] = None) -> models.AnalysisResponse:
        payload = {"file_id": file_id}
        if query:
            payload["query"] = query
        raw = self._request("POST", "/analyze/file", json=payload)
        return models.AnalysisResponse.parse_obj(raw)

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
        raw = self._request("POST", "/search/video", json=payload)
        return models.VideoSearchResponse.parse_obj(raw)

    def search_files(self, *, query: str) -> models.FileSearchResponse:
        raw = self._request("POST", "/search/file", json={"query": query})
        return models.FileSearchResponse.parse_obj(raw)

    # Uploads ----------------------------------------------------------------------
    def upload_file(self, file_path: str, *, wait_for_completion: bool = False) -> Dict[str, Any]:
        """Upload an audio or video file.

        Parameters
        ----------
        file_path: str
            Path to the local file.
        wait_for_completion: bool
            If *True*, the call will wait until processing finishes before returning.
        """
        if not os.path.isfile(file_path):
            raise FileNotFoundError(file_path)

        with open(file_path, "rb") as fp:
            files = {"file": fp}
            data = {"wait_for_completion": "true" if wait_for_completion else "false"}
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
        return models.UsageResponse.parse_obj(raw)

    def health_check(self) -> Dict[str, Any]:
        # This endpoint does not require auth; we call it anyway on same session.
        return self._request("GET", "/health")

    # Convenience ------------------------------------------------------------------
    def close(self) -> None:
        """Close the underlying HTTP session."""
        self.session.close()

    def __enter__(self) -> "VidNavigatorClient":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close() 