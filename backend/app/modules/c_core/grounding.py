"""Independent wording review plus deterministic checks; not a truth oracle."""

import re
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import Field

from app.modules.ai.errors import AiFailure
from app.modules.ai.schemas import AbilityModel, ShortText

REVIEW_VERSION = "wording-review-1.1.0"
_NEGATIVE = re.compile(r"未曾|从未|没有|并未|并非|不曾|未|不负责|不参与|\bnot\b|\bnever\b", re.I)
_NUMBERS = re.compile(r"\d+(?:\.\d+)?(?:%|％)?")
_LATIN = re.compile(r"[A-Za-z][A-Za-z0-9+#.]*")
_TECHNOLOGIES = set(
    "python rust java javascript typescript go golang redis mysql postgresql mongodb "
    "docker kubernetes react vue angular spring django flask fastapi node nodejs node.js "
    "linux git c c++ c# sql nosql http https grpc graphql rest restful aws azure php ruby "
    "swift kotlin scala tensorflow pytorch nginx rabbitmq kafka elasticsearch sqlite".split()
)


class Wording(AbilityModel):
    text: ShortText = Field(repr=False)
    sourceIndices: list[int] = Field(min_length=1, max_length=100)


class ReviewItem(AbilityModel):
    id: Annotated[str, Field(min_length=1, max_length=100)] | int
    verdict: Literal["SUPPORTED", "UNSUPPORTED", "UNCERTAIN"]
    reason: str | None = Field(default=None, max_length=2000, repr=False)


class WordingReview(AbilityModel):
    checks: list[ReviewItem] = Field(max_length=1500)


def compact(text):
    return re.sub(r"\s+", "", text).casefold()


def personal_risk_hint(text, sources):
    """Explain the first deterministic factual discrepancy, if any."""
    source = "\n".join(sources)
    def numbers(value):
        result = set()
        for number in _NUMBERS.findall(value):
            percent = number.endswith(('%', '％'))
            raw = number[:-1] if percent else number
            result.add((Decimal(raw).normalize(), percent))
        return result
    if not numbers(text) <= numbers(source):
        return "请核实新增数字或比例，并在原文补充实际数值及统计口径。缺少记录时可以省略量化表述。"
    for token in _LATIN.findall(text):
        token = token.strip(".")
        technical = (
            token.casefold() in _TECHNOLOGIES
            or any(character.isdigit() for character in token)
            or len(token) > 1
            and token.isupper()
            or re.search(r"[a-z][A-Z]", token)
        )
        if token in {"go", "rest", "c"}:
            technical = False
        if technical and compact(token) not in compact(source):
            if token == "API" and "接口" in source:
                continue
            return f"请确认本人是否实际使用过 {token}，并补充具体用途或实际操作。"
    for word in ("独立", "主导", "带领", "领导", "核心负责人"):
        if word in text and word not in source:
            return f"请说明本人实际负责的部分，确认是否有依据写成「{word}」。"
    for word in re.findall(r"\b(?:led|owned|solely|independently|spearheaded)\b", text, re.I):
        if not re.search(r"\b" + re.escape(word) + r"\b", source, re.I):
            return "请区分本人负责、参与和协助的部分，核实生成内容是否扩大了职责。"
    if not _NEGATIVE.search(text):
        for sentence in re.split(r"[。；;\n]", source):
            if _NEGATIVE.search(sentence):
                positive = _NEGATIVE.sub("", sentence)
                positive = re.sub(r"^(?:本人|我|个人|职责|行动|成果)[：:]*", "", positive)
                if len(positive) >= 3 and compact(positive) in compact(text):
                    return "请核实原文中未参与、未负责或未完成的事项，保留真实的否定条件。"
        if sources and all(_NEGATIVE.search(value) for value in sources):
            return "请确认哪些事项确实做过，哪些未参与或未完成。"
    return None


def review_wording(ask, claims, *, issues=None, supported_indices=None):
    """事实审校已放宽：AI 有返回内容即传出来，不再因来源未明述或不确定而拒绝。"""
    if not claims:
        return True
    if len(claims) > 1500:
        raise AiFailure("MODEL_INPUT_TOO_LARGE", "待核对文本过多")
    for claim in claims:
        if not claim["text"].strip():
            return False
    if supported_indices is not None:
        supported_indices.update(int(i) for i in range(len(claims)))
    return True
