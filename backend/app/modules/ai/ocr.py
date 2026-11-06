"""Page-wise OCR ability; identity/order are assigned from trusted A input."""

import base64

from .client import DeepSeekClient
from .errors import AiFailure
from .images import image_dimensions
from .prompts import OCR_INSTRUCTION, OCR_VERSION
from .schemas import ImagePage, MiB, OcrBatchResult, OcrBlock, OcrDraft, OcrPageResult

STOP_BATCH = frozenset(
    {
        "MODEL_CALLS_DISABLED",
        "MODEL_AUTH_FAILED",
        "MODEL_QUOTA_EXHAUSTED",
        "MODEL_RATE_LIMITED",
        "MODEL_NOT_AVAILABLE",
    }
)


class OcrService:
    def __init__(self, client: DeepSeekClient):
        self.client = client

    def recognize(self, pages: list[ImagePage]) -> OcrBatchResult:
        if not 1 <= len(pages) <= 50 or not all(isinstance(page, ImagePage) for page in pages):
            raise ValueError("OCR needs 1..50 validated image pages")
        identities = {(page.sourceId, page.page) for page in pages}
        if len(identities) != len(pages):
            raise ValueError("Duplicate OCR source/page")
        if sum(len(page.content) for page in pages) > 20 * MiB:
            raise AiFailure("MODEL_INPUT_TOO_LARGE", "本批图片总大小超过20MiB")
        results, stop = [], None
        for page in pages:
            if stop is not None:
                results.append(self._failure(page, stop, "NOT_ATTEMPTED"))
                continue
            try:
                image_dimensions(page)
                url = f"data:{page.mimeType};base64," + base64.b64encode(page.content).decode(
                    "ascii"
                )
                result = self.client.complete_json(
                    instruction=OCR_INSTRUCTION,
                    user_content=[
                        {"type": "text", "text": "请识别此页文字，返回 JSON。"},
                        {"type": "image_url", "image_url": {"url": url, "detail": "original"}},
                    ],
                    output_type=OcrDraft,
                    prompt_version=OCR_VERSION,
                )
                draft = result.value
                results.append(
                    OcrPageResult(
                        sourceId=page.sourceId,
                        page=page.page,
                        status="READY" if draft.blocks else "EMPTY",
                        text="\n".join(draft.blocks),
                        blocks=[
                            OcrBlock(ordinal=index + 1, text=text)
                            for index, text in enumerate(draft.blocks)
                        ],
                        uncertainties=draft.uncertainties,
                        warnings=draft.warnings,
                        error=None,
                        metadata=result.metadata,
                    )
                )
            except AiFailure as error:
                results.append(self._failure(page, error, "FAILED"))
                if error.error.code in STOP_BATCH or (
                    error.retry_after_seconds is not None and error.retry_after_seconds > 0
                ):
                    stop = error
        successful = sum(page.status in {"READY", "EMPTY"} for page in results)
        return OcrBatchResult(
            status="READY"
            if successful == len(results)
            else ("PARTIAL" if successful else "FAILED"),
            pages=results,
        )

    @staticmethod
    def _failure(page, error, status):
        return OcrPageResult(
            sourceId=page.sourceId,
            page=page.page,
            status=status,
            text=None,
            blocks=[],
            uncertainties=[],
            warnings=[],
            error=error.error,
            retryAfterSeconds=error.retry_after_seconds,
            metadata=None,
        )
