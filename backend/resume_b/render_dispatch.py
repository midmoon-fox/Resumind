"""Route formats; missing backends cannot claim successful preflight."""
from .documents import require
from .preflight import PreflightUnavailable


class ResumeRenderers:
    def __init__(self, *, pdf, word, html=None):
        self.backends = {"PDF": pdf, "DOCX": word, "HTML": html}

    def backend(self, format):
        require(isinstance(format, str) and format in self.backends, "/format", "unsupported export format")
        renderer = self.backends[format]
        if renderer is None:
            raise PreflightUnavailable("requested format renderer is not available")
        return renderer

    def inspect(self, snapshot, format):
        return self.backend(format).inspect(snapshot, format)

    def render(self, snapshot):
        return self.backend(snapshot["format"]).render(snapshot)
