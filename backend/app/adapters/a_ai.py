"""A 的 AIPort 协议 → C 的 AI 能力（合并方案 F05/F06）。

- recognize(bytes, mime) 把图片/单页 PDF 转成 C 的 ImagePage[]，再转回 TextPart 字典。
- extract_experiences(segments) 把 A 片段转成 C 的 MaterialSegment[]（补齐 materialId/attribution），
  并把 C 的 ExperienceCandidate 转成 A 的 MaterialAnalysis（服务端分配 candidateKey）。
- analyze_jd(text) 把 C 的 RequirementCandidate 转成 A 的 Requirement（服务端分配 UUID，引用原文）。
"""
import io
from uuid import uuid4

from app.core import Problem
from app.modules.ai.experience_schemas import MaterialSegment
from app.modules.ai.jd import JdAnalyzer
from app.modules.ai.materials import MaterialExtractor
from app.modules.ai.ocr import OcrService
from app.modules.ai.schemas import ImagePage, SourceSegment


class AAIAdapter:
    def __init__(self, client):
        self.ocr = OcrService(client)
        self.extractor = MaterialExtractor(client)
        self.jd = JdAnalyzer(client)

    # ---- AIPort.recognize(content: bytes, mime_type: str) -> list[dict] ----
    def recognize(self, content, mime_type):
        if mime_type in ("image/png", "image/jpeg"):
            pages = [ImagePage(sourceId=str(uuid4()), page=1, mimeType=mime_type, content=content)]
        elif mime_type == "application/pdf":
            pages = [self._rasterize_pdf_page(content)]
        else:
            raise Problem(415, "UNSUPPORTED_FILE_TYPE", "OCR 仅支持 PNG/JPEG 图片或单页 PDF")
        result = self.ocr.recognize(pages)
        parts = []
        for page in result.pages:
            if page.status == "READY":
                parts.append(dict(text=page.text or "", page=page.page, extractionMethod="OCR"))
            elif page.status == "EMPTY":
                parts.append(dict(text="", page=page.page, extractionMethod="OCR"))
            else:
                code = page.error.code if page.error else "OCR_FAILED"
                raise Problem(
                    422, "VALIDATION_ERROR", "图片识别失败：" + code,
                    {"errors": [{"path": "/file", "message": "图片识别失败：" + code}]},
                )
        return parts

    def _rasterize_pdf_page(self, content):
        # F05：扫描 PDF 页栅格化为 PNG；限制 DPI/像素/总字节，单页才有意义。
        try:
            import pypdfium2 as pdfium
        except ImportError:
            raise Problem(503, "FEATURE_DISABLED", "缺少 PDF 栅格化依赖 pypdfium2") from None
        pdf = pdfium.PdfDocument(content)
        try:
            if len(pdf) != 1:
                raise Problem(422, "VALIDATION_ERROR", "OCR 仅处理单页 PDF 片段")
            page = pdf[0]
            width, height = page.get_size()
            scale = min(2.0, 2000.0 / max(width, height, 1.0))
            bitmap = page.render(scale=scale)
            pil = bitmap.to_pil().convert("RGB")
            buf = io.BytesIO()
            pil.save(buf, format="PNG")
            png = buf.getvalue()
            if len(png) > 20 * 1024 * 1024:
                raise Problem(413, "FILE_TOO_LARGE", "栅格化图片超过20MiB")
            return ImagePage(sourceId=str(uuid4()), page=1, mimeType="image/png", content=png)
        finally:
            pdf.close()

    # ---- AIPort.extract_experiences(segments: list[dict]) -> dict ----
    def extract_experiences(self, segments):
        if not segments:
            return {"candidates": []}
        material_id = segments[0].get("materialId")
        if not material_id:
            raise Problem(422, "VALIDATION_ERROR", "材料片段缺少 materialId")
        csegments = [
            MaterialSegment(
                id=s["id"],
                materialId=material_id,
                text=s["text"],
                page=s.get("page"),
                attribution=s.get("attribution", "UNSPECIFIED"),
            )
            for s in segments
        ]
        result = self.extractor.extract(material_id, csegments)
        candidates = []
        for c in result.value.candidates:
            if c.reviewOnly:
                continue  # 仅日期/技术不足以构成一条经历，不落候选
            candidates.append(
                dict(
                    candidateKey=str(uuid4()),  # 服务端分配稳定候选键
                    type=str(c.type),
                    data=c.data.model_dump(),
                    provenance=[p.model_dump() for p in c.provenance],
                )
            )
        return {"candidates": candidates}

    # ---- AIPort.analyze_jd(text: str) -> dict ----
    def analyze_jd(self, text):
        result = self.jd.analyze([SourceSegment(id=str(uuid4()), text=text, page=None)])
        requirements = [
            dict(
                id=str(uuid4()),
                category=r.category,
                text=r.text,
                necessity=str(r.necessity),
                evidenceQuote=r.evidence[0].quote,
            )
            for r in result.value.requirements
        ]
        # F06：C 的 JD 分析不提取岗位名/公司名；如实返回 null，不编造。
        return dict(jobTitle=None, companyName=None, requirements=requirements)
