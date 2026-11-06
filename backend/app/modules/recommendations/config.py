"""Explicit source selection. Model credentials are outside this configuration."""

from collections.abc import Mapping
from io import StringIO
from pathlib import Path
from typing import Literal

from dotenv import dotenv_values
from pydantic import BaseModel, ConfigDict

from .source import ArbeitnowSource


class JobSourceSettings(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid", frozen=True)
    provider: Literal["none", "arbeitnow"] = "none"
    enable_live_calls: bool = False

    @classmethod
    def from_mapping(cls, values: Mapping):
        raw = values.get("JOB_SOURCE_CALLS_ENABLED", "false")
        if type(raw) is bool:
            enabled = raw
        elif raw in ("true", "false"):
            enabled = raw == "true"
        else:
            raise ValueError("JOB_SOURCE_CALLS_ENABLED must be true or false")
        result = cls(provider=values.get("JOB_SOURCE", "none"), enable_live_calls=enabled)
        if enabled and result.provider == "none":
            raise ValueError("Enabled source requires an explicit provider")
        return result


def create_source(settings: JobSourceSettings, *, cache=None):
    if not isinstance(settings, JobSourceSettings):
        raise TypeError("Expected JobSourceSettings")
    if not settings.enable_live_calls:
        return ArbeitnowSource()
    if settings.provider != "arbeitnow":
        raise ValueError("No live provider selected")
    return ArbeitnowSource(enabled=True, cache=cache)


def read_job_environment(path: Path):
    """Development CLI only: parse selected single-line settings, without interpolation.
    A's final application passes its own mapping; build() never opens an env file.
    """
    allowed = {"JOB_SOURCE", "JOB_SOURCE_CALLS_ENABLED", "REDIS_URL"}
    selected = []
    with path.open(encoding="utf-8-sig") as stream:
        for line in stream:
            key = line.partition("=")[0].strip()
            if key.startswith("export "):
                key = key[7:].strip()
            if key in allowed:
                selected.append(line)
    return dotenv_values(stream=StringIO("".join(selected)), interpolate=False)
