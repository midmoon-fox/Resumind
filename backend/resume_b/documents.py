"""Document validation shared by manual editing and AI result submission.

Ownership and fact verification remain the calling service's responsibility.
"""
import math
import re
from uuid import UUID

from .richtext import ContentError, validate_richtext

SECTION_TYPES = frozenset({
    "EDUCATION", "PROJECTS", "INTERNSHIPS", "CAMPUS", "AWARDS", "SKILLS",
    "ACHIEVEMENTS", "CERTIFICATES", "GOAL", "CHARTS", "HOBBIES", "PUBLICATIONS",
    "REFERENCES", "SOCIAL_LINKS", "STRENGTHS", "TEXT", "VOLUNTEERING", "WORK_EXPERIENCE",
})
COLORS = frozenset({"#333333", "#1F2937", "#2563EB"})
TEMPLATE_NAMES = {"simple": "简洁通用", "project": "项目突出", "ribbon": "紫韵雅致", "sidebar": "蓝灰双栏"}
DEFAULT_STYLE = {"fontFamily": "Microsoft YaHei", "fontSize": 14, "lineHeight": 1.6, "accentColor": "#333333", "sectionGap": 12}


def require(condition, path, message):
    if not condition:
        raise ContentError(path, message)


def fields(value, names, path):
    require(isinstance(value, dict), path, "expected object")
    require(set(value) == set(names.split()), path, "missing or unsupported fields")


def string(value, path, limit=None):
    require(isinstance(value, str), path, "expected string")
    if limit is not None:
        require(len(value) <= limit, path, f"maximum {limit} characters")


def uuid4(value, path):
    try:
        parsed = UUID(value) if isinstance(value, str) else None
    except ValueError:
        parsed = None
    require(parsed is not None and parsed.version == 4 and str(parsed) == value, path, "expected lowercase canonical UUID v4")


def dates(record, path):
    for key in ("startDate", "endDate"):
        date = record[key]
        require(date is None or isinstance(date, str) and re.fullmatch(r"[0-9]{4}-(0[1-9]|1[0-2])", date) is not None, path + "/" + key, "expected YYYY-MM or null")
    require(type(record["isCurrent"]) is bool, path + "/isCurrent", "expected boolean")
    require(not record["isCurrent"] or record["endDate"] is None, path + "/endDate", "current entry must have null endDate")


def validate_style(style):
    fields(style, "fontFamily fontSize lineHeight accentColor sectionGap", "/style")
    require(isinstance(style["fontFamily"], str) and style["fontFamily"] in {"Microsoft YaHei", "SimSun"}, "/style/fontFamily", "unsupported font")
    require(isinstance(style["accentColor"], str) and style["accentColor"] in COLORS, "/style/accentColor", "unsupported color")
    for key, low, high in (("fontSize", 10, 20), ("sectionGap", 0, 32)):
        require(type(style[key]) is int and low <= style[key] <= high, "/style/" + key, f"expected integer {low}..{high}")
    line = style["lineHeight"]
    require(type(line) in {int, float} and math.isfinite(line) and 1.1 <= line <= 2, "/style/lineHeight", "expected number 1.1..2")


def validate_template(key, version):
    require(isinstance(key, str) and key in TEMPLATE_NAMES, "/templateId", "unsupported template key")
    require(isinstance(version, str) and len(version) <= 20 and re.fullmatch(r"(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)", version) is not None, "/templateVersion", "expected stable semantic version")


def validate_document(document, *, previous=None):
    """Validate complete replacement; preserve existing nested ID identity."""
    fields(document, "schemaVersion profile sections", "/document")
    require(document["schemaVersion"] == "1.0.0", "/document/schemaVersion", "unsupported schema")
    identities = {}

    def identity(value, kind, parent, path):
        uuid4(value, path)
        require(value not in identities, path, "duplicate nested ID")
        identities[value] = (kind, parent)

    profile = document["profile"]
    fields({k:v for k,v in profile.items() if k != 'photoData'}, "name phone email intention age education skills", "/document/profile")
    photo = profile.get('photoData')
    if photo is not None:
        require(isinstance(photo, str) and len(photo) <= 400000 and re.fullmatch(r'data:image/jpeg;base64,[A-Za-z0-9+/=]+', photo), '/document/profile/photoData', '照片需为 JPEG 图片且小于 300KB')
        try:
            import base64
            import io
            from PIL import Image
            with Image.open(io.BytesIO(base64.b64decode(photo.split(',', 1)[1], validate=True))) as image:
                require(image.format == 'JPEG' and image.width * image.height <= 160000, '/document/profile/photoData', '照片尺寸过大或格式不正确')
                image.verify()
        except (ValueError, OSError):
            require(False, '/document/profile/photoData', '照片损坏，请重新上传')
    for key, limit in (("name", 100), ("phone", 32), ("email", 254), ("intention", 100)):
        if key != "phone" or profile[key] is not None:
            string(profile[key], "/document/profile/" + key, limit)
    require(profile["age"] is None or type(profile["age"]) is int and 16 <= profile["age"] <= 100, "/document/profile/age", "expected integer 16..100 or null")
    for key in ("education", "skills"):
        require(isinstance(profile[key], list), "/document/profile/" + key, "expected array")
    for i, skill in enumerate(profile["skills"]):
        string(skill, f"/document/profile/skills/{i}")
    for i, education in enumerate(profile["education"]):
        path = f"/document/profile/education/{i}"
        fields(education, "id school major degree startDate endDate isCurrent", path)
        identity(education["id"], "education", None, path + "/id")
        for key in ("school", "major", "degree"):
            string(education[key], path + "/" + key)
        dates(education, path)
    sections = document["sections"]
    require(isinstance(sections, list) and len(sections) <= 50, "/document/sections", "expected at most 50 sections")
    for i, section in enumerate(sections):
        path = f"/document/sections/{i}"
        require(isinstance(section, dict), path, "expected object")
        require(set(section) <= {"id", "type", "title", "visible", "items", "chartData", "links", "text"}, path, "unsupported fields")
        require({"id", "type", "title", "visible", "items"} <= set(section), path, "missing required fields")
        identity(section["id"], "section", None, path + "/id")
        require(isinstance(section["type"], str) and section["type"] in SECTION_TYPES, path + "/type", "unsupported section type")
        string(section["title"], path + "/title")
        require(type(section["visible"]) is bool, path + "/visible", "expected boolean")
        require(isinstance(section["items"], list) and len(section["items"]) <= 50, path + "/items", "expected at most 50 items")
        require(section["type"] not in {"EDUCATION", "SKILLS"} or not section["items"], path + "/items", "profile-derived section must have no items")
        chart_data = section.get("chartData")
        links = section.get("links")
        text = section.get("text")
        if section["type"] == "CHARTS":
            require(chart_data is not None and isinstance(chart_data, list) and 0 <= len(chart_data) <= 20, path + "/chartData", "expected 0..20 chart data points")
            require(links is None and text is None, path, "chart section accepts only chartData")
            require(not section["items"], path + "/items", "chart section must have no items")
            for k, datum in enumerate(chart_data):
                dpath = f"{path}/chartData/{k}"
                fields(datum, "label value unit", dpath)
                string(datum["label"], dpath + "/label", 80)
                require(type(datum["value"]) is int and 0 <= datum["value"] <= 100, dpath + "/value", "expected integer 0..100")
                string(datum["unit"], dpath + "/unit", 20)
        elif section["type"] == "SOCIAL_LINKS":
            require(links is not None and isinstance(links, list) and 0 <= len(links) <= 20, path + "/links", "expected 0..20 links")
            require(chart_data is None and text is None, path, "social links section accepts only links")
            require(not section["items"], path + "/items", "social links section must have no items")
            for k, link in enumerate(links):
                lpath = f"{path}/links/{k}"
                fields(link, "platform label url", lpath)
                string(link["platform"], lpath + "/platform", 40)
                string(link["label"], lpath + "/label", 80)
                string(link["url"], lpath + "/url", 500)
                require(link["url"].startswith(("http://", "https://")), lpath + "/url", "expected http(s) URL")
        elif section["type"] == "TEXT":
            require(isinstance(text, dict), path + "/text", "expected richtext")
            require(chart_data is None and links is None, path, "text section accepts only text")
            require(not section["items"], path + "/items", "text section must have no items")
            try:
                validate_richtext(text, allowed_colors=COLORS)
            except ContentError as error:
                raise ContentError(path + "/text" + error.path, str(error)) from error
        else:
            require(chart_data is None and links is None and text is None, path, "items section accepts only items")
        for j, item in enumerate(section["items"]):
            item_path = f"{path}/items/{j}"
            fields(item, "id title subtitle startDate endDate isCurrent description experienceId sourceRevision", item_path)
            identity(item["id"], "item", section["id"], item_path + "/id")
            for key in ("title", "subtitle"):
                string(item[key], item_path + "/" + key)
            dates(item, item_path)
            if item["experienceId"] is None:
                require(item["sourceRevision"] is None, item_path + "/sourceRevision", "manual item must have null source revision")
            else:
                uuid4(item["experienceId"], item_path + "/experienceId")
                require(type(item["sourceRevision"]) is int and item["sourceRevision"] >= 1, item_path + "/sourceRevision", "expected positive revision")
            try:
                validate_richtext(item["description"], allowed_colors=COLORS)
            except ContentError as error:
                raise ContentError(item_path + "/description" + error.path, str(error)) from error
    if previous is not None:
        old = validate_document(previous)
        for identifier in identities.keys() & old.keys():
            require(identities[identifier] == old[identifier], "/document", "existing ID changed identity or parent")
    return identities
