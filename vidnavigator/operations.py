"""Operation objects: one attribute per background job, like the JavaScript SDK.

``client.tiktok_search(...)`` runs the search and waits for the result,
``client.tiktok_search.submit(...)`` returns a job handle right away, and
``client.tiktok_search.resume(task_id)`` rebuilds that handle later. They take
the same parameters as the matching ``search_tiktok`` / ``submit_tiktok_search``
methods, which stay available.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable, Generic, TypeVar

if TYPE_CHECKING:
    # Typing only: IDEs and type checkers see each operation's real
    # parameters; nothing here is imported at runtime.
    from typing_extensions import ParamSpec

    _RunParams = ParamSpec("_RunParams")
    _SubmitParams = ParamSpec("_SubmitParams")
    _Result = TypeVar("_Result")
    _Handle = TypeVar("_Handle")

    class Operation(Generic[_RunParams, _Result, _SubmitParams, _Handle]):
        job_type: str

        def __init__(
            self,
            job_type: str,
            run: Callable[_RunParams, _Result],
            submit: Callable[_SubmitParams, _Handle],
            resume: Callable[[str, str], _Handle],
        ) -> None: ...

        def __call__(self, *args: _RunParams.args, **kwargs: _RunParams.kwargs) -> _Result: ...

        def submit(self, *args: _SubmitParams.args, **kwargs: _SubmitParams.kwargs) -> _Handle: ...

        def resume(self, task_id: str) -> _Handle: ...

else:

    class Operation:
        """A background job operation: call it to wait for the result, or use ``submit`` / ``resume``."""

        def __init__(self, job_type: str, run: Callable[..., Any], submit: Callable[..., Any],
                     resume: Callable[[str, str], Any]) -> None:
            self.job_type = job_type
            self._run = run
            self._submit = submit
            self._resume = resume
            self.__doc__ = run.__doc__

        def __call__(self, *args: Any, **kwargs: Any) -> Any:
            """Submit the job and wait for its result (same as the matching blocking method)."""
            return self._run(*args, **kwargs)

        def submit(self, *args: Any, **kwargs: Any) -> Any:
            """Submit the job and return its handle immediately (same as the matching ``submit_*`` method)."""
            return self._submit(*args, **kwargs)

        def resume(self, task_id: str) -> Any:
            """Rebuild the handle of a job of this type submitted earlier."""
            return self._resume(self.job_type, task_id)

        def __repr__(self) -> str:
            return f"Operation(job_type={self.job_type!r})"


__all__ = ["Operation"]
