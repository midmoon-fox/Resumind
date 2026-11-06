"""JD candidates with verified quote membership, never automatic confirmation."""

import json
import re

from .client import DeepSeekClient
from .errors import AiFailure
from .prompts import JD_INSTRUCTION, JD_VERSION
from .schemas import AbilityResult, JdAnalysis, SourceSegment


class JdAnalyzer:
    def __init__(self, client: DeepSeekClient):
        self.client = client

    def analyze(self, segments: list[SourceSegment]) -> AbilityResult[JdAnalysis]:
        if not 1 <= len(segments) <= 1000 or not all(
            isinstance(segment, SourceSegment) for segment in segments
        ):
            raise ValueError("Expected validated source segments")
        sources = {segment.id: segment.text for segment in segments}
        if len(sources) != len(segments):
            raise ValueError("Duplicate segment IDs")
        if sum(len(text) for text in sources.values()) > 100_000:
            raise AiFailure("MODEL_INPUT_TOO_LARGE", "岗位原文超过100000字符")
        result = self.client.complete_json(
            instruction=JD_INSTRUCTION,
            user_content=json.dumps(
                {"segments": [segment.model_dump() for segment in segments]}, ensure_ascii=False
            ),
            output_type=JdAnalysis,
            prompt_version=JD_VERSION,
        )
        for requirement in result.value.requirements:
            seen, quotes = set(), []
            for evidence in requirement.evidence:
                identity = (evidence.segmentId, evidence.quote)
                if (
                    identity in seen
                    or evidence.segmentId not in sources
                    or evidence.quote not in sources[evidence.segmentId]
                ):
                    raise AiFailure("MODEL_SOURCE_INVALID", "岗位候选引用不属于本次输入")
                seen.add(identity)
                quotes.append(evidence.quote)
            # Conservative numeric check; quote existence alone does not prove semantics.
            numbers = set(re.findall(r"\d+(?:\.\d+)?(?:%|％)?", requirement.text))
            evidence_numbers = set(re.findall(r"\d+(?:\.\d+)?(?:%|％)?", "\n".join(quotes)))
            if not numbers <= evidence_numbers:
                raise AiFailure("MODEL_FACT_UNSUPPORTED", "岗位候选包含无引文依据的数字")
        return result
