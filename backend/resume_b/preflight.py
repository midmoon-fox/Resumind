"""Export preflight: field checks plus mandatory format-specific trial rendering."""
from copy import deepcopy

from .documents import require


class PreflightUnavailable(Exception):
    pass


class PreflightFailed(Exception):
    def __init__(self, issues):
        self.issues = issues


def preflight(resume, format, inspect_layout, *, render_context=None):
    require(format in {"PDF", "DOCX", "HTML"}, "/format", "unsupported format")
    issues = []
    profile = resume.document_json["profile"]
    for key in ("name", "intention"):
        if not profile[key].strip():
            issues.append({"code": "REQUIRED_FIELD", "severity": "ERROR", "path": "/document/profile/" + key, "message": "正式导出需要填写此字段"})
    if not (profile["phone"] or "").strip() and not profile["email"].strip():
        issues.append({"code": "CONTACT_REQUIRED", "severity": "ERROR", "path": "/document/profile/phone", "message": "请填写电话或邮箱"})
    # Read-only fixed input: rendering must never observe subsequent ORM mutations.
    snapshot = deepcopy({"document": resume.document_json, "style": resume.style_json,
                         "templateId": resume.template_key, "templateVersion": resume.template_version})
    if render_context is not None:
        snapshot["renderContext"] = deepcopy(render_context)
    try:
        result = inspect_layout(snapshot, format)
    except (TimeoutError, OSError) as error:
        raise PreflightUnavailable("trial rendering did not complete") from error
    # Require explicit completion; None or an empty accidental return cannot mean success.
    if not isinstance(result, dict) or result.get("completed") is not True or not isinstance(result.get("issues"), list):
        raise PreflightUnavailable("trial rendering has no valid completion result")
    for issue in result["issues"]:
        if (not isinstance(issue, dict) or set(issue) != {"code", "severity", "path", "message"}
                or any(not isinstance(issue[key], str) for key in issue)
                or issue["severity"] not in {"ERROR", "WARNING"}
                or not any(issue["path"] == prefix or issue["path"].startswith(prefix + "/") for prefix in ("/document", "/style", "/templateId", "/templateVersion"))):
            raise PreflightUnavailable("trial rendering returned invalid issues")
        issues.append(deepcopy(issue))
    return {"canExport": not any(issue["severity"] == "ERROR" for issue in issues), "issues": issues}
