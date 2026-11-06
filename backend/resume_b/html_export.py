"""Self-contained static HTML extracted from the same versioned print page."""
import base64
import html as escaping
import re
from urllib.parse import urljoin, urlsplit

from lxml import html
import tinycss2

from .pdf_renderer import expected_text
from .preflight import PreflightUnavailable, PreflightFailed
from .content_check import missing_text_paths

ALLOWED_TAGS = set("main article section header footer address time small dl dt dd em strong b i u a ul ol li h1 h2 h3 h4 h5 h6 table thead tbody tfoot tr td th colgroup col caption div span p br hr img".split())
ATTRIBUTES = set("class id lang dir title style href rel alt width height colspan rowspan start".split())
DATA_MIME = {"image/png", "image/jpeg", "image/gif", "image/webp", "font/ttf", "font/otf", "font/woff", "font/woff2", "application/font-woff"}


def rewrite_css(css, base_url, embed, *, inline=False):
    nodes = tinycss2.parse_component_value_list(css, skip_comments=True) if inline else tinycss2.parse_stylesheet(css, skip_comments=True)
    def walk(tokens):
        for token in tokens:
            if token.type == "error" or token.type == "at-rule" and token.lower_at_keyword == "import":
                raise PreflightUnavailable("HTML export does not accept broken CSS or imported stylesheets")
            if token.type == "url":
                value = embed(urljoin(base_url, token.value)) if not token.value.startswith("#") else token.value
                token.value = value
                token.representation = 'url("' + value + '")'
            elif token.type == "function" and token.lower_name == "url":
                args = [t for t in token.arguments if t.type != "whitespace"]
                if len(args) != 1 or args[0].type != "string":
                    raise PreflightUnavailable("unsupported CSS resource expression")
                value = args[0].value
                value = embed(urljoin(base_url, value)) if not value.startswith("#") else value
                token.arguments = tinycss2.parse_component_value_list('"' + value + '"')
            else:
                for key in ("content", "prelude", "arguments"):
                    children = getattr(token, key, None)
                    if isinstance(children, list):
                        walk(children)
    walk(nodes)
    return tinycss2.serialize(nodes)


def static_html(root_html, styles, base_url, embed, document):
    root = html.fromstring(root_html)
    for element in list(root.iter()):
        if element is not root and root not in element.iterancestors():
            continue
        if not isinstance(element.tag, str):
            if element.getparent() is not None:
                element.getparent().remove(element)
            continue
        tag = element.tag.lower()
        if tag in {"script", "style", "link", "meta", "base", "button", "input", "textarea", "select", "iframe", "object", "embed", "form"} or "data-editor-only" in element.attrib or "data-private-source" in element.attrib:
            if element is root:
                raise PreflightUnavailable("invalid print root")
            element.drop_tree()
            continue
        if tag not in ALLOWED_TAGS:
            raise PreflightUnavailable("print root contains unsupported static markup")
        image_source = element.get("src") if tag == "img" else None
        for name in list(element.attrib):
            keep_scoped = re.fullmatch(r"data-v-[a-f0-9]+", name) is not None
            if name not in ATTRIBUTES and not keep_scoped and name != "data-resume-print-root":
                del element.attrib[name]
        if "style" in element.attrib:
            element.set("style", rewrite_css(element.get("style"), base_url, embed, inline=True))
        if "href" in element.attrib:
            address = element.get("href")
            parsed = urlsplit(address)
            if not address.startswith("#") and parsed.scheme not in {"http", "https", "mailto"}:
                del element.attrib["href"]
            elif parsed.path.startswith(("/api/", "/internal/")) and parsed.netloc == urlsplit(base_url).netloc:
                del element.attrib["href"]
            else:
                element.set("rel", "noopener noreferrer")
        if tag == "img":
            if not image_source:
                raise PreflightUnavailable("print image has no source")
            element.set("src", embed(urljoin(base_url, image_source)))
    css = "\n".join(rewrite_css(sheet["css"], sheet["base"], embed) for sheet in styles)
    # Prevent style-tag termination even if a trusted CSS string contains '<'.
    css = css.replace("<", "\\3C ")
    content = html.tostring(root, encoding="unicode", method="html")
    csp = "default-src 'none'; img-src data:; font-src data:; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'"
    result = ('<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta http-equiv="Content-Security-Policy" content="' + escaping.escape(csp, quote=True) + '"><title>简历</title><style>' + css + '</style></head><body>' + content + '</body></html>').encode()
    text = "".join(root.itertext())
    missing = [{"code": "CONTENT_MISSING", "severity": "ERROR", "path": path, "message": "HTML 缺少应显示的正文"} for path in missing_text_paths(text, expected_text(document))]
    if missing:
        raise PreflightFailed(missing)
    return result


def package_page(page, context, snapshot, ticket, origin, timeout_ms):
    extracted = page.evaluate("""() => {
      const roots = document.querySelectorAll('[data-resume-print-root]');
      if (roots.length !== 1) throw new Error('expected one static print root');
      const root = roots[0];
      return {root:root.outerHTML, styles:[...document.styleSheets].map(sheet =>
        ({base:sheet.href || location.href, css:[...sheet.cssRules].map(r=>r.cssText).join('\\n')}))};
    }""")
    cache = {}
    total = 0
    def embed(address):
        nonlocal total
        if address.startswith("data:"):
            mime = address[5:].split(";", 1)[0]
            if mime not in DATA_MIME or ";base64," not in address:
                raise PreflightUnavailable("unsupported embedded HTML resource")
            base64.b64decode(address.split(",", 1)[1], validate=True)
            return address
        if address in cache:
            return cache[address]
        parsed = urlsplit(address)
        if ((parsed.scheme, parsed.netloc) != origin or not parsed.path.startswith(("/assets/", "/fonts/", "/static/")) or parsed.username):
            raise PreflightUnavailable("HTML resource is outside published static assets")
        response = context.request.get(address, headers={"Authorization": "Bearer " + ticket.token}, max_redirects=0, timeout=timeout_ms)
        if response.status != 200:
            raise PreflightUnavailable("HTML asset could not be packaged")
        mime = response.headers.get("content-type", "").split(";", 1)[0].lower()
        if mime not in DATA_MIME:
            raise PreflightUnavailable("HTML asset MIME type is not supported")
        data = response.body()
        total += len(data)
        if len(data) > 20 * 1024 * 1024 or total > 32 * 1024 * 1024:
            raise PreflightUnavailable("HTML assets exceed package size limit")
        cache[address] = f"data:{mime};base64," + base64.b64encode(data).decode()
        response.dispose()
        return cache[address]
    return static_html(extracted["root"], extracted["styles"], page.url, embed, snapshot["document"])


class HtmlRenderer:
    def __init__(self, print_renderer):
        self.print_renderer = print_renderer

    def render(self, snapshot):
        return self.print_renderer.run(snapshot, html=True)

    def inspect(self, snapshot, format):
        if format != "HTML":
            raise PreflightUnavailable("HTML inspector received a different format")
        self.render(snapshot)
        return {"completed": True, "issues": []}
