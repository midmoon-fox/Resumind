"""Scope and factual guardrails around B's authoritative content validators."""

import copy
import re

from app.modules.tasks.lifecycle import TaskOperationError

EXPERIENCE_SECTIONS = {
    "PROJECTS": "PROJECT",
    "INTERNSHIPS": "INTERNSHIP",
    "CAMPUS": "CAMPUS",
    "AWARDS": "AWARD",
}
AI_ITEM_SECTIONS = {'PROJECTS','INTERNSHIPS','CAMPUS','AWARDS','ACHIEVEMENTS','CERTIFICATES','GOAL','HOBBIES','PUBLICATIONS','REFERENCES','STRENGTHS','VOLUNTEERING','WORK_EXPERIENCE'}
TITLES = {
    "PROJECTS": "项目经历",
    "INTERNSHIPS": "实习经历",
    "CAMPUS": "校园经历",
    "AWARDS": "获奖经历",
    "EDUCATION": "教育经历",
    "SKILLS": "专业技能",
}


def invalid(path, message="字段或引用不符合契约"):
    raise TaskOperationError(
        "VALIDATION_ERROR", message, 422, {"errors": [{"path": path, "message": message}]}
    )


def revision(actual, expected):
    if actual != expected:
        raise TaskOperationError(
            "REVISION_CONFLICT", "内容已更新，请核对后再保存", 409, {"currentRevision": actual}
        )


def state(condition):
    if not condition:
        raise TaskOperationError()


def clone(value):
    return copy.deepcopy(value)


def rich(texts):
    return {
        "type": "doc",
        "content": [
            {"type": "paragraph", **({"content": [{"type": "text", "text": text}]} if text else {})}
            for text in texts
        ]
        or [{"type": "paragraph"}],
    }


def plain(value):
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return "\n".join(plain(item) for item in value)
    if isinstance(value, dict):
        return value.get("text", "") + "\n".join(plain(item) for item in value.get("content", []))
    return ""


def read_target(document, target):
    sections = [value for value in document["sections"] if value["id"] == target["sectionId"]]
    if len(sections) != 1:
        invalid("/target/sectionId")
    section = sections[0]
    kind = target["kind"]
    if kind == "ITEM_DESCRIPTION":
        if section["type"] not in AI_ITEM_SECTIONS:
            invalid("/target")
        items = [value for value in section["items"] if value["id"] == target["itemId"]]
        if len(items) != 1:
            invalid("/target/itemId")
        return clone(items[0]["description"])
    if kind == "SECTION_CONTENT":
        if section["type"] not in AI_ITEM_SECTIONS:
            invalid("/target")
        return {
            "items": [
                {"itemId": value["id"], "description": clone(value["description"])}
                for value in section["items"]
            ]
        }
    if kind == "SECTION_FIELD":
        if target.get('field') != 'text' or section['type'] != 'TEXT':
            invalid('/target/field', '此模块不支持该 AI 文本字段')
        return clone(section['text'])
    field = target.get("field")
    if field not in {'education','skills'}:
        invalid('/target/field', '不支持的 AI 帮助字段')
    if section["type"] != {"education": "EDUCATION", "skills": "SKILLS"}[field]:
        invalid("/target/field")
    return {field: clone(document["profile"][field])}


def check_target_shape(target, original, proposed):
    """Structure/identity independent of semantic fact risk. B validates content itself."""
    kind = target["kind"]
    if kind == "SECTION_CONTENT":
        if set(proposed) != {"items"} or not isinstance(proposed["items"], list):
            invalid("/proposed")
        if any(set(item) != {"itemId", "description"} for item in proposed["items"]):
            invalid("/proposed/items")
        if [v["itemId"] for v in proposed["items"]] != [v["itemId"] for v in original["items"]]:
            invalid("/proposed/items", "模块条目集合与顺序必须保持")
    elif kind == "PROFILE_FIELD":
        field = target["field"]
        if set(proposed) != {field} or not isinstance(proposed[field], list):
            invalid("/proposed")
        if field == "education":
            before, after = original[field], proposed[field]
            if len(before) != len(after) or any(
                set(a) != set(b) for a, b in zip(before, after, strict=True)
            ):
                invalid("/proposed/education")
            for old, new in zip(before, after, strict=True):
                for key in ("id", "startDate", "endDate", "isCurrent"):
                    if old[key] != new[key]:
                        invalid("/proposed/education", "教育身份、数量和日期必须保持")


def fact_risk(target, original, proposed):
    """Detect changed factual surfaces that require independent review in abilities.
    This preliminary check alone does not decide a reviewed suggestion's applicability.
    """
    if target["kind"] == "PROFILE_FIELD":
        return original != proposed
    pairs = (
        [(original, proposed)]
        if target["kind"] in {"ITEM_DESCRIPTION", "SECTION_FIELD"}
        else [
            (old["description"], new["description"])
            for old, new in zip(original["items"], proposed["items"], strict=True)
        ]
    )
    for old, new in pairs:
        old_text, new_text = plain(old), plain(new)
        if not set(re.findall(r"\d+(?:\.\d+)?%?", new_text)) <= set(
            re.findall(r"\d+(?:\.\d+)?%?", old_text)
        ):
            return True
        # Substring matching would incorrectly allow stripping a negation such as 未负责 -> 负责.
        if new_text != old_text:
            return True
    return False
