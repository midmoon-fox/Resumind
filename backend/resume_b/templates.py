"""Initial public definitions; published layout assets are integrated separately."""
from .documents import COLORS, SECTION_TYPES, TEMPLATE_NAMES, string, validate_template
from .documents import require
from .richtext import validate_richtext
from copy import deepcopy


def get_template(key: str, version: str = "1.0.0") -> dict:
    validate_template(key, version)
    require(version == "1.0.0", "/templateVersion", "initial seed definitions only cover version 1.0.0")
    return {
        "id": key,
        "version": version,
        "name": TEMPLATE_NAMES[key],
        "supportedFormats": ["PDF", "DOCX", "HTML"],
        "allowedSectionTypes": sorted(SECTION_TYPES),
        "stylePolicy": {
            "fontFamilies": ["Microsoft YaHei", "SimSun"],
            "colors": ["#333333", "#1F2937", "#2563EB"],
            "fontSizeMin": 10, "fontSizeMax": 20,
            "lineHeightMin": 1.1, "lineHeightMax": 2,
        },
        "previewUrl": None,
    }


class TemplateService:
    def __init__(self, session, *, preview_url=None):
        self.session, self.preview_url = session, preview_url

    def definition(self, key, version, *, allow_retired=False):
        from sqlalchemy import select
        from .models import Template
        statement = select(Template).where(Template.template_key == key, Template.version == version)
        row = self.session.scalar(statement)
        require(row is not None and (row.status == "ACTIVE" or allow_retired and row.status == "RETIRED"), "/templateId", "template version is not available")
        return row

    def validate(self, key, version, document, style, *, allow_retired=False):
        row = self.definition(key, version, allow_retired=allow_retired)
        policy = row.style_policy_json
        require(style["fontFamily"] in policy["fontFamilies"], "/style/fontFamily", "font is outside this template policy")
        require(style["accentColor"] in policy["colors"], "/style/accentColor", "color is outside this template policy")
        require(policy["fontSizeMin"] <= style["fontSize"] <= policy["fontSizeMax"], "/style/fontSize", "font size is outside this template policy")
        require(policy["lineHeightMin"] <= style["lineHeight"] <= policy["lineHeightMax"], "/style/lineHeight", "line height is outside this template policy")
        for i, section in enumerate(document["sections"]):
            require(section["type"] in row.section_types_json, f"/document/sections/{i}/type", "section is not supported by this template")
            for item in section["items"]:
                validate_richtext(item["description"], allowed_colors=set(policy["colors"]))
        return row

    def list(self, *, page=1, page_size=20):
        from sqlalchemy import select
        from .models import Template
        from .preflight import PreflightUnavailable
        rows = self.session.scalars(select(Template).where(Template.status == "ACTIVE")
            .order_by(Template.created_at.desc(), Template.id.desc()).offset((page-1)*page_size).limit(page_size))
        result = []
        for row in rows:
            preview = None
            if row.preview_file_id is not None:
                if self.preview_url is None:
                    raise PreflightUnavailable("published template preview provider is unavailable")
                preview = self.preview_url(self.session, row.preview_file_id)
            result.append({"id": row.template_key, "version": row.version, "name": row.name, "supportedFormats": row.formats_json,
                           "allowedSectionTypes": row.section_types_json, "stylePolicy": row.style_policy_json, "previewUrl": preview})
        return result

    def publish(self, definition, *, vue_asset_version, docx_object_key, verify_assets, preview_file_id=None):
        """Trusted release operation; immutable assets are prepared before opening this transaction."""
        from sqlalchemy import select
        from .models import Template
        from .schemas import TemplateOutput
        from .service import StateConflict
        from .documents import uuid4 as validate_uuid
        definition = TemplateOutput.model_validate(definition).model_dump()
        validate_template(definition["id"], definition["version"])
        string(definition["name"], "/name", 100)
        string(vue_asset_version, "/vueAssetVersion", 100)
        string(docx_object_key, "/docxObjectKey", 512)
        require(bool(definition["name"].strip()) and bool(vue_asset_version) and bool(docx_object_key), "", "template name and immutable asset identifiers are required")
        require(definition["previewUrl"] is None, "/previewUrl", "preview URLs are derived from the published preview file")
        if preview_file_id is not None:
            validate_uuid(preview_file_id, "/previewFileId")
        formats = definition["supportedFormats"]
        sections = definition["allowedSectionTypes"]
        policy = definition["stylePolicy"]
        require(bool(formats) and len(set(formats)) == len(formats), "/supportedFormats", "expected unique supported formats")
        require(bool(sections) and len(set(sections)) == len(sections) and set(sections) <= SECTION_TYPES, "/allowedSectionTypes", "expected supported section types")
        require(bool(policy["fontFamilies"]) and set(policy["fontFamilies"]) <= {"Microsoft YaHei", "SimSun"}, "/stylePolicy/fontFamilies", "unsupported font policy")
        require(bool(policy["colors"]) and set(policy["colors"]) <= COLORS, "/stylePolicy/colors", "unsupported color policy")
        require(10 <= policy["fontSizeMin"] <= policy["fontSizeMax"] <= 20 and 1.1 <= policy["lineHeightMin"] <= policy["lineHeightMax"] <= 2, "/stylePolicy", "style bounds exceed the contract")
        values = {"name": definition["name"], "formats_json": formats, "section_types_json": sections, "style_policy_json": policy,
                  "vue_asset_version": vue_asset_version, "docx_object_key": docx_object_key, "preview_file_id": preview_file_id}
        row = self.session.scalar(select(Template).where(Template.template_key == definition["id"], Template.version == definition["version"]).with_for_update())
        if row is not None and any(getattr(row, key) != value for key, value in values.items()):
            raise StateConflict("published template versions cannot be changed in place")
        # This callback checks release metadata/ownership only; no remote upload while holding locks.
        verified = verify_assets(self.session, definition["id"], definition["version"], vue_asset_version, docx_object_key, preview_file_id)
        if verified is not True:
            raise StateConflict("template assets were not explicitly verified")
        if row is None:
            row = Template(template_key=definition["id"], version=definition["version"], status="ACTIVE", **deepcopy(values))
            self.session.add(row)
            self.session.flush()
        return row

    def retire(self, key, version):
        from sqlalchemy import select
        from .models import Template, utcnow
        row = self.session.scalar(select(Template).where(Template.template_key == key, Template.version == version).with_for_update())
        require(row is not None, "/templateId", "template version does not exist")
        if row.status != "RETIRED":
            row.status = "RETIRED"
            row.updated_at = utcnow()
            self.session.flush()
        return row
