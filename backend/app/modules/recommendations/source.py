"""Arbeitnow public feed adapter. Default disabled; never fetch arbitrary URLs."""

import json
from datetime import UTC, datetime
from html.parser import HTMLParser
from typing import Protocol
from urllib.parse import urlsplit
from uuid import uuid4

import httpx
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from redis.exceptions import RedisError

from app.modules.ai.client import _retry_after, strict_json
from app.modules.ai.errors import AiFailure

SOURCE_VERSION = "arbeitnow-public-v2"
ENDPOINT = "https://www.arbeitnow.com/api/job-board-api"
SOURCE_HOSTS = {
    "www.arbeitnow.com": "arbeitnow",
    "www.arbeitnow.co.uk": "arbeitnow_uk",
    "www.arbeitnow.fr": "arbeitnow_fr",
    "www.arbeitnow.ch": "arbeitnow_ch",
    "www.arbeitnow.nl": "arbeitnow_nl",
}
MAX_PAGE_RECORDS = 300
MAX_RECORDS = 3 * MAX_PAGE_RECORDS
CACHE_KEY = "resume:arbeitnow:feed:v2"
LOCK_KEY = "resume:arbeitnow:refresh:v2"


class JobSource(Protocol):
    available: bool
    config_id: str

    def fetch(self) -> list[dict]:
        """Real normalized records with source identity, text, URL and filter metadata.
        Failures raise AiFailure(SOURCE_UNAVAILABLE), never a successful empty result.
        """
        ...


class _Text(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts, self.hidden = [], 0

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style", "iframe"}:
            self.hidden += 1
        elif not self.hidden and tag in {"p", "li", "br", "h1", "h2", "h3", "div"}:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in {"script", "style", "iframe"}:
            self.hidden = max(0, self.hidden - 1)

    def handle_data(self, data):
        if not self.hidden:
            self.parts.append(data)


class FeedJob(BaseModel):
    model_config = ConfigDict(strict=True, extra="ignore")
    slug: str = Field(min_length=1, max_length=200)
    company_name: str = Field(min_length=1, max_length=200)
    title: str = Field(min_length=1, max_length=200)
    # Real feed may contain large embedded style sections; bound HTML separately from text.
    description: str = Field(min_length=1, max_length=1024 * 1024)
    remote: bool
    url: str = Field(max_length=2048)
    tags: list[str] = Field(max_length=100)
    job_types: list[str] = Field(max_length=100)
    location: str = Field(max_length=100)
    created_at: int = Field(ge=0)


class ArbeitnowSource:
    """Redis cache is shared by worker processes; public feed only, no resume sent.
    At most three pages per refresh, 10-minute cache and compare-token refresh lock.
    """

    config_id = SOURCE_VERSION

    def __init__(self, *, enabled=False, transport=None, cache=None):
        if transport is not None and not isinstance(transport, httpx.MockTransport):
            raise ValueError("Only MockTransport may be injected")
        self.available = bool(enabled or transport is not None)
        self.offline = transport is not None
        if enabled and cache is None:
            raise ValueError("Live source requires shared Redis cache/lock")
        self.cache = cache
        self.client = (
            httpx.Client(
                transport=transport,
                trust_env=False,
                follow_redirects=False,
                timeout=httpx.Timeout(15, connect=5),
            )
            if self.available
            else None
        )

    def close(self):
        if self.client:
            self.client.close()

    def fetch(self):
        if not self.available:
            raise AiFailure("SOURCE_UNAVAILABLE", "真实岗位来源尚未启用")
        cache_key, lock_key = CACHE_KEY, LOCK_KEY
        token = str(uuid4())
        locked = False
        try:
            if self.cache is not None:
                cached = self.cache.get(cache_key)
                if cached:
                    return self._convert(strict_json(cached))
                locked = bool(self.cache.set(lock_key, token, nx=True, ex=180))
                if not locked:
                    raise AiFailure(
                        "SOURCE_UNAVAILABLE",
                        "岗位来源正在刷新",
                        can_retry=True,
                        retry_after_seconds=30,
                    )
            records = []
            for page in range(1, 4):
                with self.client.stream("GET", ENDPOINT, params={"page": page}) as response:
                    if response.status_code != 200:
                        raise AiFailure(
                            "SOURCE_UNAVAILABLE",
                            "岗位来源暂不可用",
                            can_retry=True,
                            retry_after_seconds=_retry_after(response.headers.get("Retry-After")),
                        )
                    chunks, size = [], 0
                    for part in response.iter_bytes(64 * 1024):
                        size += len(part)
                        if size > 5 * 1024 * 1024:
                            raise ValueError("Feed exceeds budget")
                        chunks.append(part)
                    payload = strict_json(b"".join(chunks))
                if not isinstance(payload, dict) or not isinstance(payload.get("data"), list):
                    raise ValueError("Invalid feed")
                if len(payload["data"]) > MAX_PAGE_RECORDS:
                    raise ValueError("Too many feed records")
                records.extend(payload["data"])
                # Never follow feed-provided pagination or job URLs.
                if not payload.get("links", {}).get("next"):
                    break
            wrapped = {"fetchedAt": datetime.now(UTC).isoformat(), "records": records}
            converted = self._convert(wrapped)
            if self.cache is not None:
                self.cache.set(cache_key, json.dumps(wrapped), ex=600)
            return converted
        except AiFailure:
            raise
        except (
            httpx.HTTPError,
            ValueError,
            TypeError,
            KeyError,
            AttributeError,
            ValidationError,
            RedisError,
        ):
            raise AiFailure("SOURCE_UNAVAILABLE", "岗位来源响应不可用", can_retry=True) from None
        finally:
            if locked:
                try:
                    self.cache.eval(
                        "if redis.call('get', KEYS[1]) == ARGV[1] then "
                        "return redis.call('del', KEYS[1]) else return 0 end",
                        1,
                        lock_key,
                        token,
                    )
                except RedisError:
                    pass  # Lock expires; never expose or replace the original source error.

    @staticmethod
    def _convert(payload):
        if (
            not isinstance(payload, dict)
            or not isinstance(payload.get("records"), list)
            or len(payload["records"]) > MAX_RECORDS
        ):
            raise ValueError("Invalid cached feed")
        fetched = datetime.fromisoformat(payload["fetchedAt"])
        if fetched.tzinfo is None:
            raise ValueError("Naive fetch time")
        records, seen = [], set()
        for value in payload["records"]:
            job = FeedJob.model_validate(value)
            url = urlsplit(job.url)
            if (
                url.scheme != "https"
                or url.hostname not in SOURCE_HOSTS
                or url.port
                or url.username
                or url.password
                or not url.path.startswith(("/jobs/", "/view/"))
            ):
                raise ValueError("Invalid source URL")
            identity = (SOURCE_HOSTS[url.hostname], job.slug)
            if identity in seen:
                continue
            seen.add(identity)
            parser = _Text()
            parser.feed(job.description)
            description = "\n".join(
                line.strip() for line in "".join(parser.parts).splitlines() if line.strip()
            )
            if not description or len(description) > 100000:
                raise ValueError("Empty or oversized source text")
            records.append(
                {
                    "source_key": SOURCE_HOSTS[url.hostname],
                    "source_name": "Arbeitnow",
                    "source_job_id": job.slug,
                    "source_url": job.url,
                    "title": job.title,
                    "company": job.company_name,
                    "city": job.location,
                    "salary_text": None,
                    "description_text": description,
                    # The feed exposes a record creation time, not a documented publication time.
                    "published_at": None,
                    "source_created_at": datetime.fromtimestamp(job.created_at, UTC).isoformat(),
                    "fetched_at": fetched.astimezone(UTC).isoformat(),
                    "availability": "UNKNOWN",
                    "remote": job.remote,
                    "tags": job.tags,
                    "job_types": job.job_types,
                }
            )
        return records


def matches(job, filters):
    """Literal filter only; never silently substitute location/direction/seniority."""
    city = filters["city"].casefold()
    location_match = city in job["city"].casefold()
    if city in {"remote", "远程"}:
        location_match = job["remote"]
    direction_text = " ".join([job["title"], *job["tags"]]).casefold()
    level_text = " ".join([job["title"], *job["job_types"], job["description_text"]]).casefold()
    return (
        location_match
        and filters["direction"].casefold() in direction_text
        and filters["experienceLevel"].casefold() in level_text
    )
