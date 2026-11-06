"""Sanitized model ability errors; never attach HTTP request/response bodies."""

from app.modules.tasks.schemas import TaskError


class AiFailure(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        *,
        can_retry: bool = False,
        retry_after_seconds: int | None = None,
    ):
        self.error = TaskError(code=code, message=message, canRetry=can_retry)
        self.retry_after_seconds = retry_after_seconds
        super().__init__(code)


def invalid_output():
    return AiFailure("MODEL_INVALID_OUTPUT", "模型输出不符合约定")
