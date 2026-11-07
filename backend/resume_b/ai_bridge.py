"""B document operations used by C; all writes share the caller's transaction."""
from copy import deepcopy
from uuid import uuid4

from .documents import default_style, fields, require, validate_document, validate_style, validate_template
from .service import RevisionConflict, StateConflict
from .templates import TemplateService


def reassign_nested_ids(document):
    document = deepcopy(document)
    for education in document["profile"]["education"]:
        education["id"] = str(uuid4())
    for section in document["sections"]:
        section["id"] = str(uuid4())
        for item in section["items"]:
            item["id"] = str(uuid4())
    return document


def target_value(document, target):
    require(isinstance(target, dict), "/target", "expected target object")
    kind = target.get("kind")
    if kind == "ITEM_DESCRIPTION":
        fields(target, "kind sectionId itemId", "/target")
    elif kind == "SECTION_CONTENT":
        fields(target, "kind sectionId", "/target")
    elif kind == "PROFILE_FIELD":
        fields(target, "kind sectionId field", "/target")
    elif kind == "SECTION_FIELD":
        fields(target, "kind sectionId field", "/target")
    else:
        require(False, "/target/kind", "unsupported target")
    section = next((s for s in document["sections"] if s["id"] == target["sectionId"]), None)
    require(section is not None, "/target/sectionId", "section does not exist")
    if kind == "ITEM_DESCRIPTION":
        item = next((i for i in section["items"] if i["id"] == target["itemId"]), None)
        require(item is not None, "/target/itemId", "item does not exist")
        return deepcopy(item["description"])
    if kind == "SECTION_CONTENT":
        require(section["type"] not in {"EDUCATION", "SKILLS", "CHARTS", "SOCIAL_LINKS", "TEXT"}, "/target/sectionId", "section cannot be rewritten as item descriptions")
        return {"items": [{"itemId": item["id"], "description": deepcopy(item["description"])} for item in section["items"]]}
    if kind == "SECTION_FIELD":
        field = target["field"]
        require(field in {"text"} and section["type"] == "TEXT", "/target/field", "section field target only supports TEXT text")
        return deepcopy(section[field])
    field = target["field"]
    require(isinstance(field, str) and field in {"education", "skills"} and section["type"] == field.upper(), "/target/field", "profile target does not match section")
    return {field: deepcopy(document["profile"][field])}


def replace_target(document, target, proposed):
    original = target_value(document, target)
    result = deepcopy(document)
    section = next(s for s in result["sections"] if s["id"] == target["sectionId"])
    kind = target["kind"]
    if kind == "ITEM_DESCRIPTION":
        next(i for i in section["items"] if i["id"] == target["itemId"])["description"] = deepcopy(proposed)
    elif kind == "SECTION_CONTENT":
        fields(proposed, "items", "/proposed")
        require(isinstance(proposed["items"], list), "/proposed/items", "expected array")
        for item in proposed["items"]:
            fields(item, "itemId description", "/proposed/items")
        require([i["itemId"] for i in proposed["items"]] == [i["itemId"] for i in original["items"]], "/proposed/items", "item identity and order must be unchanged")
        for item, candidate in zip(section["items"], proposed["items"]):
            item["description"] = deepcopy(candidate["description"])
    elif kind == "SECTION_FIELD":
        section[target["field"]] = deepcopy(proposed)
    else:
        field = target["field"]
        fields(proposed, field, "/proposed")
        require(isinstance(proposed[field], list) and len(proposed[field]) == len(original[field]), "/proposed/" + field, "profile entry count must be unchanged")
        if field == "education":
            for old, new in zip(original[field], proposed[field]):
                require(isinstance(new, dict) and all(new.get(key) == old[key] for key in ("id", "startDate", "endDate", "isCurrent")), "/proposed/education", "education identity and dates must be unchanged")
        result["profile"][field] = deepcopy(proposed[field])
    validate_document(result, previous=document)
    return result


class DocumentBridge:
    def __init__(self, service, *, verify_task, verify_lease, load_suggestion, verify_fact_preservation):
        self.service = service
        self.session = service.session
        self.verify_lease = verify_lease
        self.verify_task = verify_task
        self.load_suggestion = load_suggestion
        self.verify_fact_preservation = verify_fact_preservation

    def create_draft(self, user, *, title, template_key, template_version, workspace_id=None, jd_snapshot=None):
        empty = {"schemaVersion": "1.0.0", "profile": {"name": "", "phone": "", "email": "", "intention": "", "age": None, "education": [], "skills": []}, "sections": []}
        return self.service.create(user, title=title, document=empty, style=default_style(template_key, template_version), template_key=template_key, template_version=template_version, workspace_id=workspace_id, jd_snapshot=jd_snapshot)

    def bind_generation(self, user, resume_id, task_id):
        from .documents import uuid4 as validate_uuid
        validate_uuid(task_id, "/taskId")
        resume = self.service.get(user, resume_id, lock=True)
        if resume.revision != 1 or resume.generation_task_id is not None:
            raise StateConflict("draft already bound or modified")
        self.verify_task(self.session, user, task_id, resume_id, "GENERATE_RESUME")
        resume.generation_task_id = task_id
        self.session.flush()

    def complete_generation(self, user, resume_id, task_id, lease, document, style):
        resume = self.service.get(user, resume_id, lock=True)
        if resume.generation_task_id != task_id:
            raise StateConflict("task does not own this draft")
        self.verify_task(self.session, user, task_id, resume_id, "GENERATE_RESUME")
        self.verify_lease(self.session, user, task_id, lease)
        if resume.revision != 1:
            raise RevisionConflict(resume.revision)
        validate_template(resume.template_key, resume.template_version)
        validate_document(document)
        validate_style(style)
        result = reassign_nested_ids(document)
        TemplateService(self.session).validate(resume.template_key, resume.template_version, result, style, allow_retired=True)
        self.service.check_references(self.session, user, resume.workspace_id, result, resume.jd_snapshot_json)
        self.service._cas(resume, 1, document_json=result, style_json=deepcopy(style))
        return self.service.get(user, resume_id)

    def check_generation_retry(self, user, resume_id, task_id):
        resume = self.service.get(user, resume_id, lock=True)
        self.verify_task(self.session, user, task_id, resume_id, "GENERATE_RESUME")
        if resume.generation_task_id != task_id or resume.revision != 1:
            raise StateConflict("draft cannot accept another generation attempt")
        # C reuses its original immutable input, not the current workspace facts.
        TemplateService(self.session).definition(resume.template_key, resume.template_version, allow_retired=True)
        return {"resourceId": resume.id, "taskId": task_id}

    def check_generation_cancel(self, user, resume_id, task_id):
        # Generation status is derived from C's Task; no duplicate status is written to resumes.
        return self.check_generation_retry(user, resume_id, task_id)

    def read_target(self, user, resume_id, revision, target):
        resume = self.service.get(user, resume_id)
        self.service.editable(resume)
        if resume.revision != revision:
            raise RevisionConflict(resume.revision)
        return target_value(resume.document_json, target)

    def apply_suggestion(self, user, resume_id, suggestion_id, revision):
        suggestion = self.load_suggestion(self.session, user, suggestion_id)
        if suggestion["resumeId"] != resume_id or suggestion["status"] != "READY" or suggestion["needsFactConfirmation"] is not False:
            raise StateConflict("suggestion is unavailable or requires fact confirmation")
        resume = self.service.get(user, resume_id, lock=True)
        self.service.editable(resume)
        if resume.revision != revision or suggestion["baseRevision"] != revision:
            raise RevisionConflict(resume.revision)
        original = target_value(resume.document_json, suggestion["target"])
        if original != suggestion["original"]:
            raise StateConflict("suggestion target is stale")
        result = replace_target(resume.document_json, suggestion["target"], suggestion["proposed"])
        # C's fact-preservation check is mandatory, including education/skill semantics.
        self.verify_fact_preservation(self.session, user, suggestion["target"], original, suggestion["proposed"])
        self.service.check_references(self.session, user, resume.workspace_id, result, resume.jd_snapshot_json)
        self.service._cas(resume, revision, document_json=result)
        # C marks suggestion APPLIED in this same caller-owned transaction.
        return self.service.get(user, resume_id)
