"""Bounded child-process PDF rendering of server-owned HTML, without a print HTTP endpoint."""
import base64
import json
import os
import signal
import subprocess
import sys

from .local_templates import StaticHtmlRenderer
from .pdf_renderer import validate_pdf
from .preflight import PreflightUnavailable


class LocalPdfRenderer:
    def __init__(self, timeout_seconds=40):
        self.timeout_seconds = timeout_seconds
        self.html = StaticHtmlRenderer()

    def render(self, snapshot):
        source = self.html.render(snapshot)
        flags = ({"creationflags": subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP}
                 if os.name == 'nt' else {"start_new_session": True})
        payload = json.dumps({"html": source.decode('utf-8')}, ensure_ascii=False).encode('utf-8')
        try:
            process = subprocess.Popen([sys.executable, '-m', 'resume_b.local_pdf_worker'],
                                       stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, **flags)
            try:
                stdout, _ = process.communicate(payload, timeout=self.timeout_seconds)
            except subprocess.TimeoutExpired:
                # Terminate the browser/driver tree as well as its Python parent.
                if os.name == 'nt':
                    subprocess.run(['taskkill','/PID',str(process.pid),'/T','/F'],
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
                else:
                    os.killpg(process.pid, signal.SIGKILL)
                process.communicate()
                raise
            output = json.loads(stdout)
            if process.returncode != 0 or output.get('error'):
                raise ValueError('render unavailable')
            data = base64.b64decode(output['pdf'], validate=True)
        except (OSError, ValueError, KeyError, subprocess.TimeoutExpired) as error:
            raise PreflightUnavailable('PDF rendering requires Playwright, Chromium and supported Chinese fonts') from error
        validate_pdf(data, snapshot)
        return data

    def inspect(self, snapshot, format):
        if format != 'PDF':
            raise PreflightUnavailable('PDF inspector requires PDF')
        self.render(snapshot)
        return {"completed": True, "issues": []}
