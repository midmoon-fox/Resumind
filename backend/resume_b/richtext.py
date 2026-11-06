"""Restricted rich text contract, API 1.1.0 section 3.21."""

from urllib.parse import urlsplit


class ContentError(ValueError):
    def __init__(self, path: str, message: str):
        self.path = path
        super().__init__(f"{path}: {message}")


def validate_richtext(value: object, *, allowed_colors: set[str]) -> None:
    """Validate without modifying or silently dropping user content."""
    blocks = {"paragraph", "bulletList", "orderedList"}
    node_count = 0
    text_length = 0

    def fail(path, message):
        raise ContentError(path, message)

    def node(current, path, permitted, depth=1):
        nonlocal node_count, text_length
        node_count += 1
        if depth > 8 or node_count > 2000:
            fail(path, "rich text exceeds depth 8 or 2000 nodes")
        if not isinstance(current, dict):
            fail(path, "expected object")
        kind = current.get("type")
        if not isinstance(kind, str) or kind not in permitted:
            fail(path + "/type", "unsupported node in this position")
        fields = {"type"}
        if kind in {"doc", "paragraph", "bulletList", "orderedList", "listItem"}:
            fields.add("content")
        if kind == "orderedList":
            fields.add("attrs")
            attrs = current.get("attrs", {})
            if not isinstance(attrs, dict) or set(attrs) - {"start"}:
                fail(path + "/attrs", "only start is allowed")
            start = attrs.get("start", 1)
            if type(start) is not int or not 1 <= start <= 999:
                fail(path + "/attrs/start", "expected integer 1..999")
        if kind == "text":
            fields.update({"text", "marks"})
            if not isinstance(current.get("text"), str) or not current["text"]:
                fail(path + "/text", "expected nonempty text")
            text_length += len(current["text"])
            if text_length > 10000:
                fail(path + "/text", "description exceeds 10000 characters")
            marks = current.get("marks", [])
            if not isinstance(marks, list):
                fail(path + "/marks", "expected array")
            seen = set()
            for i, mark in enumerate(marks):
                mark_path = f"{path}/marks/{i}"
                if not isinstance(mark, dict):
                    fail(mark_path, "expected mark object")
                name = mark.get("type")
                if not isinstance(name, str) or name not in {"bold", "italic", "underline", "link", "textStyle"} or name in seen:
                    fail(mark_path, "unsupported or duplicate mark")
                seen.add(name)
                expected = {"type", "attrs"} if name in {"link", "textStyle"} else {"type"}
                if set(mark) != expected:
                    fail(mark_path, "invalid mark fields")
                if name in {"link", "textStyle"}:
                    attr = "href" if name == "link" else "color"
                    attrs = mark["attrs"]
                    if not isinstance(attrs, dict) or set(attrs) != {attr} or not isinstance(attrs[attr], str):
                        fail(mark_path, "invalid mark attributes")
                    text = attrs[attr]
                    if name == "textStyle" and text not in allowed_colors:
                        fail(mark_path, "color not allowed by template")
                    if name == "link":
                        try:
                            url = urlsplit(text)
                            valid = url.scheme in {"http", "https", "mailto"} and (bool(url.hostname) if url.scheme != "mailto" else bool(url.path))
                        except ValueError:
                            valid = False
                        if not valid or len(text) > 2048 or any(ord(c) <= 32 for c in text):
                            fail(mark_path, "invalid link")
        if set(current) - fields:
            fail(path, "unsupported node fields")
        if "content" in fields:
            children = current.get("content", [])
            if not isinstance(children, list):
                fail(path + "/content", "expected array")
            if kind != "paragraph" and "content" not in current:
                fail(path + "/content", "content is required")
            if kind in {"bulletList", "orderedList", "listItem"} and not children:
                fail(path + "/content", "expected nonempty content")
            permitted_children = {"text", "hardBreak"} if kind == "paragraph" else {"listItem"} if kind in {"bulletList", "orderedList"} else blocks
            for i, child in enumerate(children):
                node(child, f"{path}/content/{i}", {"paragraph"} if kind == "listItem" and i == 0 else permitted_children, depth + 1)

    node(value, "", {"doc"})
