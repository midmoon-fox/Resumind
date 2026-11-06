"""Private child-process entrypoint. Input via stdin, never command-line secrets."""
import base64
import json
import sys

from .preflight import PreflightFailed
from .pdf_renderer import PdfRenderer, PrintTicket


def main():
    try:
        value = json.loads(sys.stdin.buffer.read())
        origin = "://".join(value["origin"])
        renderer = PdfRenderer(origin=origin, issue_ticket=None, timeout_ms=value["timeout"])
        result = renderer._run_ticket(value["snapshot"], PrintTicket(**value["ticket"]), pdf=value["pdf"], html=value.get("html", False))
        output = {"pdf" if value["pdf"] else "html": base64.b64encode(result).decode()} if value["pdf"] or value.get("html") else {"report": result}
    except PreflightFailed as error:
        output = {"error": "PREFLIGHT_FAILED", "issues": error.issues}
    except Exception:
        # Do not print private input, scoped tokens, URLs or vendor exception text.
        output = {"error": "RENDER_FAILED"}
    sys.stdout.buffer.write(json.dumps(output, ensure_ascii=False).encode())


if __name__ == "__main__":
    main()
