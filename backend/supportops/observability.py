import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from functools import wraps
from typing import ParamSpec, TypeVar

from langsmith import Client
from langsmith.run_trees import RunTree

from supportops.config import Settings

LOGGER = logging.getLogger(__name__)
Parameters = ParamSpec("Parameters")
Result = TypeVar("Result")


@dataclass(frozen=True)
class Step:
    name: str
    started: datetime
    ended: datetime
    status: str


class WorkflowTrace:
    """Collect only fixed node names, timing and success state."""

    def __init__(self, settings: Settings | None) -> None:
        self.settings = settings
        self.started = datetime.now(UTC)
        self.steps: list[Step] = []

    def node(self, function: Callable[Parameters, Result]) -> Callable[Parameters, Result]:
        if not self.settings or not self.settings.supportops_langsmith_enabled:
            return function

        @wraps(function)
        def timed(*args: Parameters.args, **kwargs: Parameters.kwargs) -> Result:
            started = datetime.now(UTC)
            status = "interrupted_or_failed"
            try:
                result = function(*args, **kwargs)
                status = "ok"
                return result
            finally:
                self.steps.append(Step(function.__name__, started, datetime.now(UTC), status))

        return timed

    def publish(self, status: str) -> None:
        settings = self.settings
        if (
            not settings
            or not settings.supportops_langsmith_enabled
            or not settings.supportops_langsmith_api_key
        ):
            return
        try:
            client = Client(
                api_url="https://api.smith.langchain.com",
                api_key=settings.supportops_langsmith_api_key.get_secret_value(),
                timeout_ms=3000,
                omit_traced_runtime_info=True,
            )
            parent = RunTree(
                name="SupportOps ticket workflow",
                run_type="chain",
                inputs={},
                project_name=settings.supportops_langsmith_project,
                client=client,
                start_time=self.started,
            )
            parent.end(outputs={"status": status})
            parent.post()
            for step in sorted(self.steps, key=lambda value: value.started):
                child = parent.create_child(
                    name=step.name, run_type="chain", inputs={}, start_time=step.started
                )
                child.end(end_time=step.ended, outputs={"status": step.status})
                child.post()
            client.flush()
        except Exception:
            # Tracing is optional. Transport failures never affect ticket processing.
            LOGGER.warning("Could not publish sanitized workflow trace")
