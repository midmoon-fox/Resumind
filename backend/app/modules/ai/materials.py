"""Material -> reviewed candidates. No resource IDs, confirmation, ORM or file parsing."""

import json
import re
import unicodedata
from collections import defaultdict

from pydantic import TypeAdapter

from app.modules.tasks.schemas import ResourceId

from .client import DeepSeekClient
from .errors import AiFailure
from .experience_schemas import (
    ExperienceCandidate,
    ExperienceData,
    ExperienceReview,
    MaterialDraft,
    MaterialExtraction,
    MaterialProvenance,
    MaterialSegment,
)
from .prompts import MATERIAL_INSTRUCTION, MATERIAL_REPAIR_INSTRUCTION, MATERIAL_REPAIR_VERSION, MATERIAL_VERSION
from .schemas import AbilityResult

SCALARS = ("name", "startDate", "endDate", "background", "personalRole")
ARRAYS = ("actions", "outcomes", "technologies")
PERSONAL_FIELDS = frozenset({"personalRole", "isCurrent", *ARRAYS})
MATERIAL_SOURCE_ERROR = (
    "材料已收到，但 AI 整理的部分经历无法在原文中核实，暂未生成经历卡片。"
    "请在后台任务中重试；仍失败时可粘贴文字材料，或手动添加经历。"
)


class _MissingFieldEvidence(AiFailure):
    def __init__(self, paths):
        self.paths = sorted(paths)
        super().__init__("MODEL_SOURCE_INVALID", MATERIAL_SOURCE_ERROR, can_retry=True)


def _facts(data: ExperienceData) -> dict[str, str | bool]:
    values = data.model_dump()
    facts = {"/" + key: values[key] for key in SCALARS if values[key]}
    if data.isCurrent:
        facts["/isCurrent"] = True
    for key in ARRAYS:
        for index, value in enumerate(values[key]):
            facts[f"/{key}/{index}"] = value
    return facts


def _normalized(value):
    return unicodedata.normalize("NFKC", value).casefold()


def _numbers(value):
    return set(re.findall(r"\d+(?:\.\d+)?(?:%|％)?", _normalized(value)))


def _literal_technology(value, quotes):
    value = re.sub(r"\s+", "", _normalized(value))
    pattern = r"(?<![a-z0-9_+#])" + re.escape(value) + r"(?![a-z0-9_+#])"
    return any(re.search(pattern, re.sub(r"\s+", "", _normalized(quote))) for quote in quotes)


def _date_supported(value, quotes):
    dates = set()
    for quote in quotes:
        for year, month in re.findall(
            r"(?<!\d)([0-9]{4})(?:年|[-/.])(0?[1-9]|1[0-2])(?:月)?(?!\d)",
            _normalized(quote),
        ):
            dates.add(f"{year}-{int(month):02d}")
    return value in dates


def _personal_reason(evidence, sources):
    scopes = {sources[item.segmentId].attribution for item in evidence}
    if scopes == {"PERSONAL"}:
        return None
    if scopes == {"TEAM"}:
        return "TEAM_CONTEXT"
    if scopes == {"DEPENDENCY"}:
        return "DEPENDENCY_ONLY"
    if len(scopes) > 1:
        return "MIXED_ATTRIBUTION"
    return "PERSONAL_CONTRIBUTION_UNCONFIRMED"


def _sanitize(draft, sources):
    facts = _facts(draft.data)
    evidence_by_path = defaultdict(list)
    seen = set()
    for evidence in draft.evidence:
        identity = (evidence.jsonPointer, evidence.segmentId, evidence.quote)
        if (
            identity in seen
            or evidence.jsonPointer not in facts
            or evidence.segmentId not in sources
            or evidence.quote not in sources[evidence.segmentId].text
        ):
            raise AiFailure("MODEL_SOURCE_INVALID", MATERIAL_SOURCE_ERROR, can_retry=True)
        seen.add(identity)
        evidence_by_path[evidence.jsonPointer].append(evidence)
    if set(evidence_by_path) != set(facts):
        raise _MissingFieldEvidence(set(facts) - set(evidence_by_path))

    allowed, reviews = {}, []
    for pointer, value in facts.items():
        evidence = evidence_by_path[pointer]
        quotes = [item.quote for item in evidence]
        field = pointer.split("/")[1]
        reason = None
        if field in {"startDate", "endDate"}:
            if not _date_supported(value, quotes):
                reason = "DATE_NOT_IN_SOURCE"
        elif isinstance(value, str):
            if not _numbers(value) <= _numbers("\n".join(quotes)):
                raise AiFailure("MODEL_FACT_UNSUPPORTED", "AI 整理出了原文中没有的数字，暂未生成经历卡片。请重试，或手动填写并核对经历。", can_retry=True)
            if field == "technologies" and not _literal_technology(value, quotes):
                raise AiFailure("MODEL_FACT_UNSUPPORTED", "AI 整理出了原文未提到的技术名称，暂未生成经历卡片。请重试，或手动填写并核对经历。", can_retry=True)
        if reason is None and (
            field in PERSONAL_FIELDS
            or all(sources[item.segmentId].attribution == "DEPENDENCY" for item in evidence)
        ):
            reason = _personal_reason(evidence, sources)
        if reason is None and field == "isCurrent":
            text = _normalized("\n".join(quotes))
            if not (
                any(word in text for word in ("至今", "目前", "仍在", "进行中"))
                or re.search(r"\b(?:present|currently|ongoing)\b", text)
            ):
                reason = "CURRENT_STATUS_UNSUPPORTED"
        if reason:
            reviews.append(
                ExperienceReview(
                    proposedPath=pointer, proposedValue=value, reason=reason, evidence=evidence
                )
            )
        else:
            allowed[pointer] = value

    clean = {
        "name": "",
        "startDate": None,
        "endDate": None,
        "isCurrent": False,
        "background": "",
        "personalRole": "",
        "actions": [],
        "outcomes": [],
        "technologies": [],
    }
    provenance = []

    def preserve(old_path, new_path):
        ids = {item.segmentId for item in evidence_by_path[old_path]}
        provenance.append(
            MaterialProvenance(
                jsonPointer=new_path,
                segmentIds=[source_id for source_id in sources if source_id in ids],
            )
        )

    for key in (*SCALARS, "isCurrent"):
        path = "/" + key
        if path in allowed:
            clean[key] = allowed[path]
            preserve(path, path)
    for key in ARRAYS:
        for index, _ in enumerate(getattr(draft.data, key)):
            old_path = f"/{key}/{index}"
            if old_path in allowed:
                new_path = f"/{key}/{len(clean[key])}"
                clean[key].append(allowed[old_path])
                preserve(old_path, new_path)
    data = ExperienceData.model_validate(clean)
    return ExperienceCandidate(
        type=draft.type,
        data=data,
        provenance=provenance,
        reviewItems=reviews,
        conflicts=draft.conflicts,
        reviewOnly=not bool(
            data.name or data.background or data.personalRole or data.actions or data.outcomes
        ),
    )


class MaterialExtractor:
    def __init__(self, client: DeepSeekClient):
        self.client = client

    def extract(
        self, material_id: str, segments: list[MaterialSegment]
    ) -> AbilityResult[MaterialExtraction]:
        TypeAdapter(ResourceId).validate_python(material_id)
        if not 1 <= len(segments) <= 1000 or not all(
            isinstance(segment, MaterialSegment) for segment in segments
        ):
            raise ValueError("Expected validated material segments")
        sources = {segment.id: segment for segment in segments}
        if len(sources) != len(segments):
            raise ValueError("Duplicate material source IDs")
        if any(segment.materialId != material_id for segment in segments):
            raise ValueError("Segments belong to a different material")
        if sum(len(segment.text) for segment in segments) > 100_000:
            raise AiFailure("MODEL_INPUT_TOO_LARGE", "材料原文超过100000字符")
        payload = {"segments": [segment.model_dump(exclude={"materialId", "page"}) for segment in segments]}
        # One bounded correction for omitted citations. Every supplied reference, quote,
        # number, technology and attribution is still checked; no partial result is saved.
        for attempt in range(2):
            response = self.client.complete_json(
                instruction=MATERIAL_INSTRUCTION if attempt == 0 else MATERIAL_REPAIR_INSTRUCTION,
                user_content=json.dumps(payload, ensure_ascii=False),
                output_type=MaterialDraft,
                prompt_version=MATERIAL_VERSION if attempt == 0 else MATERIAL_REPAIR_VERSION,
            )
            candidates, missing = [], []
            for index, draft in enumerate(response.value.experiences):
                try:
                    candidates.append(_sanitize(draft, sources))
                except _MissingFieldEvidence as error:
                    missing.append({"candidateIndex": index, "paths": error.paths})
            if not missing:
                return AbilityResult(
                    MaterialExtraction(materialId=material_id, candidates=candidates, warnings=response.value.warnings),
                    response.metadata,
                )
            if attempt == 1:
                raise _MissingFieldEvidence(path for item in missing for path in item["paths"])
            payload["missingEvidence"] = missing
