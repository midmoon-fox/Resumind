from .visibility import section_has_content, item_has_content
"""Playwright adapter for the versioned frontend internal print route."""
from dataclasses import dataclass, field
import hashlib
from io import BytesIO
import json
import base64
import os
import signal
import subprocess
import sys
from urllib.parse import urlsplit

from .preflight import PreflightUnavailable, PreflightFailed
from .content_check import missing_text_paths


@dataclass(frozen=True)
class PrintTicket:
    url: str
    token: str = field(repr=False)


def snapshot_digest(snapshot):
    printable = {key: snapshot[key] for key in ("document", "style", "templateId", "templateVersion")}
    return hashlib.sha256(json.dumps(printable, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def validate_ready(ready, snapshot):
    if (not isinstance(ready, dict) or ready.get("ready") is not True
            or ready.get("snapshotDigest") != snapshot_digest(snapshot)
            or ready.get("templateId") != snapshot["templateId"]
            or ready.get("templateVersion") != snapshot["templateVersion"]
            or ready.get("fontsReady") is not True or ready.get("paper") != "A4"
            or not isinstance(ready.get("issues"), list)):
        raise PreflightUnavailable("print page did not confirm the fixed snapshot and font readiness")
    for issue in ready["issues"]:
        if (not isinstance(issue, dict) or set(issue) != {"code", "severity", "path", "message"}
                or any(not isinstance(value, str) for value in issue.values())
                or issue["severity"] not in {"ERROR", "WARNING"}
                or not any(issue["path"] == prefix or issue["path"].startswith(prefix + "/") for prefix in ("/document", "/style", "/templateId", "/templateVersion"))):
            raise PreflightUnavailable("print page returned invalid issues")
    return ready["issues"]


class PdfRenderer:
    def __init__(self, *, origin, issue_ticket, timeout_ms=15000):
        parsed = urlsplit(origin)
        if parsed.scheme != "https" and not (parsed.scheme == "http" and parsed.hostname in {"127.0.0.1", "localhost", "::1"}):
            raise ValueError("print origin requires HTTPS or loopback HTTP")
        if parsed.path not in {"", "/"} or parsed.query or parsed.fragment or parsed.username:
            raise ValueError("expected an origin without credentials or path")
        self.origin = (parsed.scheme, parsed.netloc)
        self.issue_ticket = issue_ticket
        if type(timeout_ms) is not int or not 100 <= timeout_ms <= 60000:
            raise ValueError("render timeout must be 100..60000 milliseconds")
        self.timeout_ms = timeout_ms

    def run(self, snapshot, *, pdf=False, html=False):
        if pdf and html:
            raise ValueError("choose one export format")
        ticket = self.issue_ticket(snapshot)
        payload = json.dumps({"origin": self.origin, "timeout": self.timeout_ms, "ticket": {"url": ticket.url, "token": ticket.token}, "snapshot": snapshot, "pdf": pdf, "html": html}, ensure_ascii=False).encode()
        kwargs = {"creationflags": subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP} if os.name == "nt" else {"start_new_session": True}
        process = subprocess.Popen([sys.executable, "-m", "resume_b.pdf_worker"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, **kwargs)
        try:
            output, _ = process.communicate(payload, timeout=self.timeout_ms / 1000)
        except subprocess.TimeoutExpired as error:
            if os.name == "nt":
                subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
            else:
                os.killpg(process.pid, signal.SIGKILL)
            process.communicate()
            raise PreflightUnavailable("isolated render process exceeded its deadline") from error
        try:
            result = json.loads(output)
        except (ValueError, UnicodeError) as error:
            raise PreflightUnavailable("isolated renderer failed") from error
        if result.get("error") == "PREFLIGHT_FAILED":
            raise PreflightFailed(result["issues"])
        if process.returncode != 0 or result.get("error"):
            raise PreflightUnavailable("isolated renderer failed")
        if pdf or html:
            data = base64.b64decode(result["pdf" if pdf else "html"], validate=True)
            if pdf:
                validate_pdf(data, snapshot)
            return data
        return result["report"]

    def _run_ticket(self, snapshot, ticket, *, pdf=False, html=False):
        from playwright.sync_api import sync_playwright, TimeoutError as BrowserTimeout

        url = urlsplit(ticket.url)
        if ((url.scheme, url.netloc) != self.origin or not url.path.startswith("/internal/print/")
                or url.username or url.fragment or not ticket.token or "\r" in ticket.token or "\n" in ticket.token):
            raise PreflightUnavailable("invalid print authorization scope")
        blocked = []
        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True, timeout=self.timeout_ms)
                try:
                    context = browser.new_context(service_workers="block")
                    context.set_default_timeout(self.timeout_ms)
                    def restricted(route):
                        target = urlsplit(route.request.url)
                        if (target.scheme, target.netloc) != self.origin:
                            blocked.append(True)
                            route.abort()
                        else:
                            headers = {**route.request.headers, "authorization": "Bearer " + ticket.token}
                            route.continue_(headers=headers)
                    context.route("**/*", restricted)
                    page = context.new_page()
                    page.emulate_media(media="print")
                    response = page.goto(ticket.url, wait_until="domcontentloaded", timeout=self.timeout_ms)
                    if response is None or response.status != 200:
                        raise PreflightUnavailable("internal print page is unavailable")
                    page.wait_for_function("() => window.__RESUME_PRINT_READY__?.ready === true", timeout=self.timeout_ms)
                    page.wait_for_function("() => document.fonts.status === 'loaded' && [...document.images].every(i => i.complete && i.naturalWidth > 0)", timeout=self.timeout_ms)
                    ready = page.evaluate("() => window.__RESUME_PRINT_READY__")
                    issues = validate_ready(ready, snapshot)
                    if blocked:
                        raise PreflightUnavailable("print page attempted to load resources outside its origin")
                    if not pdf and not html:
                        return {"completed": True, "issues": issues}
                    if any(issue["severity"] == "ERROR" for issue in issues):
                        raise PreflightFailed(issues)
                    if html:
                        from .html_export import package_page
                        return package_page(page, context, snapshot, ticket, self.origin, self.timeout_ms)
                    data = page.pdf(format="A4", landscape=False, print_background=True, prefer_css_page_size=False)
                    validate_pdf(data, snapshot)
                    return data
                finally:
                    browser.close()
        except BrowserTimeout as error:
            raise PreflightUnavailable("print page or PDF rendering timed out") from error

    def inspect(self, snapshot, format):
        if format not in {"PDF", "HTML"}:
            raise PreflightUnavailable("DOCX requires a Word mapping inspector")
        return self.run(snapshot)

    def render(self, snapshot):
        if snapshot.get("format") != "PDF":
            raise PreflightUnavailable("this renderer handles PDF only")
        return self.run(snapshot, pdf=True)


def validate_pdf(data, snapshot=None):
    from pypdf import PdfReader
    if not isinstance(data, bytes) or not data.startswith(b"%PDF-"):
        raise PreflightUnavailable("renderer did not produce a PDF")
    try:
        reader = PdfReader(BytesIO(data), strict=True)
        if reader.is_encrypted or not reader.pages:
            raise ValueError("empty or encrypted PDF")
        text = []
        for page in reader.pages:
            width, height = float(page.mediabox.width), float(page.mediabox.height)
            if abs(width - 595.28) > 2 or abs(height - 841.89) > 2:
                raise ValueError("expected portrait A4")
            text.append(page.extract_text() or "")
        if not "".join(text).strip():
            raise ValueError("PDF contains no readable text")
    except Exception as error:
        raise PreflightUnavailable("PDF validation failed") from error
    if snapshot is not None:
        missing = [{"code": "CONTENT_MISSING", "severity": "ERROR", "path": path, "message": "PDF 缺少应显示的正文，请检查模板映射"}
                   for path in missing_text_paths("".join(text), expected_text(snapshot["document"]))]
        if missing:
            raise PreflightFailed(missing)


def expected_text(document):
    profile = document["profile"]
    for key in ("name", "phone", "email", "intention"):
        yield "/document/profile/" + key, profile[key] or ""
    for i, section in enumerate(document["sections"]):
        if not section_has_content(section, profile):
            continue
        path = f"/document/sections/{i}"
        yield path + "/title", section["title"]
        if section["type"] == "EDUCATION":
            for j, education in enumerate(profile["education"]):
                for key in ("school", "major", "degree"):
                    yield f"/document/profile/education/{j}/{key}", education[key]
        elif section["type"] == "SKILLS":
            for j, skill in enumerate(profile["skills"]):
                yield f"/document/profile/skills/{j}", skill
        else:
            def rich(node, pointer):
                if node["type"] == "text":
                    yield pointer + "/text", node["text"]
                for n, child in enumerate(node.get("content", [])):
                    yield from rich(child, pointer + f"/content/{n}")
            for j, item in enumerate(section["items"]):
                if not item_has_content(item):
                    continue
                item_path = path + f"/items/{j}"
                for key in ("title", "subtitle"):
                    yield item_path + "/" + key, item[key]
                yield from rich(item["description"], item_path + "/description")
