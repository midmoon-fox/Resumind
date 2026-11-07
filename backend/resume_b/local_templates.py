"""Shared, static HTML for preview and exports. No user HTML, scripts or network assets."""
from pathlib import Path
from uuid import uuid4

from .visibility import section_has_content, item_has_content

from jinja2 import Environment, FileSystemLoader, StrictUndefined, select_autoescape
from markupsafe import Markup, escape

from .documents import validate_document, validate_style, validate_template
from .html_export import static_html
from .preflight import PreflightUnavailable
from .word_renderer import date_label

ASSETS = Path(__file__).resolve().parents[1] / "assets/templates"

# 编辑预览的 hover 高亮与定位提示样式
EDIT_CSS = """
[data-edit-key], [data-edit-item-id] { cursor: pointer; position: relative; }
[data-edit-key].edit-hover, [data-edit-item-id].edit-hover {
  outline: 3px solid #ef4444; outline-offset: 2px; border-radius: 4px;
}
.edit-hover::after {
  content: '点击编辑此模块';
  position: absolute; top: -26px; right: 0;
  background: #ef4444; color: #fff;
  font-size: 12px; line-height: 1; padding: 4px 8px;
  border-radius: 4px; white-space: nowrap; z-index: 20;
}
"""

BRIDGE_JS = """
(function () {
  var channel = '__CHANNEL__';
  var resumeId = '__RESUME_ID__';
  var revision = __REVISION__;
  function keyOf(el) {
    var node = el;
    while (node && node.getAttribute) {
      var k = node.getAttribute('data-edit-key');
      if (k) return k;
      node = node.parentElement;
    }
    return null;
  }
  function send(el) {
    var key = keyOf(el);
    if (!key) return;
    parent.postMessage({
      type: 'resume-preview:select',
      bridgeVersion: 1,
      channel: channel,
      resumeId: resumeId,
      revision: revision,
      target: {
        key: key,
        itemId: (el.closest('[data-edit-item-id]') || el).getAttribute('data-edit-item-id') || null,
        field: el.getAttribute('data-edit-field') || null
      }
    }, '*');
  }
  var els = document.querySelectorAll('[data-edit-key], [data-edit-item-id]');
  for (var i = 0; i < els.length; i++) {
    (function (el) {
      el.setAttribute('tabindex', '0');
      el.setAttribute('role', 'button');
      el.addEventListener('keydown', function(event) { if(event.key === 'Enter' || event.key === ' ') { event.preventDefault(); event.stopPropagation(); send(el); } });
      el.addEventListener('focus', function() { el.classList.add('edit-hover'); });
      el.addEventListener('blur', function() { el.classList.remove('edit-hover'); });
      el.addEventListener('mouseenter', function () { el.classList.add('edit-hover'); });
      el.addEventListener('mouseleave', function () { el.classList.remove('edit-hover'); });
      el.addEventListener('click', function (event) { event.stopPropagation(); send(event.target.closest('[data-edit-field]') || el); });
    })(els[i]);
  }
})();
"""


def inline(node):
    result = escape(node["text"])
    for mark in node.get("marks", []):
        tag = {"bold": "strong", "italic": "em", "underline": "u"}.get(mark["type"])
        if tag:
            result = Markup("<{}>{}</{}>").format(tag, result, tag)
        elif mark["type"] == "textStyle":
            result = Markup('<span style="color:{}">{}</span>').format(mark["attrs"]["color"], result)
        elif mark["type"] == "link":
            result = Markup('<a href="{}" rel="noopener noreferrer">{}</a>').format(mark["attrs"]["href"], result)
    return result


class StaticHtmlRenderer:
    def _render_root(self, snapshot):
        document, style = snapshot["document"], snapshot["style"]
        validate_document(document)
        validate_style(style)
        validate_template(snapshot["templateId"], snapshot["templateVersion"])
        directory = ASSETS / snapshot["templateVersion"]
        if not directory.is_dir():
            raise PreflightUnavailable("versioned HTML assets are unavailable")
        environment = Environment(loader=FileSystemLoader(directory), undefined=StrictUndefined,
                                  autoescape=select_autoescape(default=True), trim_blocks=True, lstrip_blocks=True)
        profile = document["profile"]
        contacts = [profile[key] for key in ("phone", "email") if profile[key]]
        if profile["age"] is not None:
            contacts.append(f"{profile['age']}岁")
        layout = snapshot["templateId"] + ".html.j2" if snapshot["templateId"] in {"ribbon", "sidebar"} else "resume.html.j2"
        root = environment.get_template(layout).render(
            profile=profile, sections=[{**s, "items": [i for i in s["items"] if item_has_content(i)]} for s in document["sections"] if section_has_content(s, profile)],
            style=style, templateId=snapshot["templateId"], contacts=contacts,
            inline=inline, dates=date_label,
            themeInk="#24282E" if style["accentColor"] in {"#D4A72C", "#AAA3BE", "#879FB7"} else "#FFFFFF")
        css = "\n".join((directory / name).read_text(encoding="utf-8")
                        for name in ("base.css", snapshot["templateId"] + ".css"))
        return root, css

    def render(self, snapshot):
        root, css = self._render_root(snapshot)
        def deny_resource(_):
            if _ == snapshot["document"]["profile"].get("photoData") and _ is not None:
                return _
            raise PreflightUnavailable("static templates cannot fetch resources")
        return static_html(root, [{"css": css, "base": "https://template.invalid/"}],
                           "https://template.invalid/", deny_resource, snapshot["document"])

    def render_editable(self, snapshot, resume_id, revision, channel):
        """编辑预览：保留定位属性并注入桥接脚本；channel 由前端生成传入。"""
        root, css = self._render_root(snapshot)
        nonce = uuid4().hex
        bridge = (BRIDGE_JS.replace("__CHANNEL__", channel).replace("__RESUME_ID__", resume_id)
                  .replace("__REVISION__", str(int(revision))))
        csp = f"default-src 'none'; img-src data:; style-src 'unsafe-inline'; script-src 'nonce-{nonce}'; base-uri 'none'; form-action 'none'"
        return ('<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">'
                f'<meta http-equiv="Content-Security-Policy" content="{csp}">'
                f'<title>简历</title><style>{css}\n{EDIT_CSS}</style></head><body>{root}'
                f'<script nonce="{nonce}">{bridge}</script></body></html>').encode()

    def inspect(self, snapshot, format):
        if format != "HTML":
            raise PreflightUnavailable("HTML inspector requires HTML")
        self.render(snapshot)
        return {"completed": True, "issues": []}
