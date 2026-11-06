"""Explicit application/worker settings. No environment reads or network at import."""

from collections.abc import Mapping
from dataclasses import dataclass, field
import os
from pathlib import Path

from dotenv import dotenv_values
from pydantic import SecretStr

from .client import DeepSeekClient
from .schemas import ModelSettings


@dataclass(frozen=True)
class ModelConfiguration:
    settings: ModelSettings = field(default_factory=ModelSettings)
    api_key: SecretStr = field(default_factory=lambda: SecretStr(""), repr=False)

    @classmethod
    def from_mapping(cls, values: Mapping):
        # Never pass a secret-bearing mapping into validation errors or logging.
        if (
            values.get("MODEL_PROVIDER", "deepseek") != "deepseek"
            or values.get("DEEPSEEK_MODEL", "deepseek-flash") != "deepseek-flash"
            or values.get("OCR_PROVIDER", "deepseek") != "deepseek"
        ):
            raise ValueError("Unsupported model provider, model or OCR configuration")
        enabled = values.get("MODEL_CALLS_ENABLED", "false")
        if type(enabled) is bool:
            pass
        elif type(enabled) is str and enabled in {"true", "false"}:
            enabled = enabled == "true"
        else:
            raise ValueError("MODEL_CALLS_ENABLED must be true or false")
        key = values.get("DEEPSEEK_API_KEY", "")
        if isinstance(key, SecretStr):
            key = key.get_secret_value()
        if not isinstance(key, str):
            raise ValueError("Invalid model credential configuration")
        if enabled and (
            not key or not key.isascii() or any(ord(c) < 33 or ord(c) > 126 for c in key)
        ):
            raise ValueError("Live model calls require a valid server-side credential")
        return cls(ModelSettings(enable_live_calls=enabled), SecretStr(key))


def create_model_client(configuration: ModelConfiguration):
    if not isinstance(configuration, ModelConfiguration):
        raise TypeError("Expected ModelConfiguration")
    if not configuration.settings.enable_live_calls:
        return DeepSeekClient(configuration.settings)
    return DeepSeekClient.live(configuration.settings, configuration.api_key)


def load_model_configuration(local_path: Path | None = None) -> ModelConfiguration:
    """Read at the application boundary only; deployment environment takes precedence.

    Resolve the optional private file against the project, never the working directory.
    Do not mutate os.environ or include secret-bearing values in validation messages.
    """
    path = local_path if local_path is not None else Path(__file__).resolve().parents[3] / ".env.local"
    local = dotenv_values(path, interpolate=False) if path.is_file() else {}
    return ModelConfiguration.from_mapping({**local, **os.environ})
