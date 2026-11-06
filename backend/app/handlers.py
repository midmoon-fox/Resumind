"""A task handlers. C runner calls prepare -> execute -> commit; AI runs outside DB transactions."""
import io
from copy import deepcopy

from docx import Document
from docx.table import Table
from pypdf import PdfReader, PdfWriter
from sqlalchemy import select

from .core import conflict, invalid, sha
from .models import (Experience, ExperienceSource, File, JdVersion, JobDescription,
                     Material, Segment, now, uid)
from .ports import JdAnalysis, MaterialAnalysis, TaskContext, TextPart
from .services import add_source, jd_version, leaves, owned, valid_file
from .storage import checked_docx
from .schemas import TaskError


def extract_parts(content, mime, ai):
    if mime in {'text/plain', 'text/markdown'}:
        return [TextPart(text=content.decode('utf-8-sig'), page=None, extractionMethod='TEXT')]
    if mime == 'application/vnd.openxmlformats-officedocument.wordprocessingml.document':
        checked_docx(content).close()
        doc = Document(io.BytesIO(content))
        lines = []
        for block in doc.iter_inner_content():
            if isinstance(block, Table):
                lines.extend('\t'.join(cell.text for cell in row.cells) for row in block.rows)
            else:
                lines.append(block.text)
        return [TextPart(text='\n'.join(lines), page=None, extractionMethod='DOCX')]
    if mime == 'application/pdf':
        reader = PdfReader(io.BytesIO(content))
        parts = []
        if reader.is_encrypted or len(reader.pages) > 50:
            invalid('PDF不符合解析限制')
        for number, page in enumerate(reader.pages, 1):
            text = page.extract_text() or ''
            if text.strip():
                parts.append(TextPart(text=text, page=number, extractionMethod='PDF_TEXT'))
            else:
                # C receives a single-page PDF, not an invented image or empty successful OCR.
                writer, buffer = PdfWriter(), io.BytesIO()
                writer.add_page(page)
                writer.write(buffer)
                recognized = ai.recognize(buffer.getvalue(), 'application/pdf')
                parts.extend(TextPart(text=p.text, page=number, extractionMethod=p.extraction_method)
                             for p in [TextPart.model_validate(p) for p in recognized])
        return parts
    if mime in {'image/png', 'image/jpeg'}:
        return [TextPart.model_validate(p) for p in ai.recognize(content, mime)]
    invalid('不支持的解析格式')


def check_parts(parts):
    if sum(len(p.text) for p in parts) > 100000:
        invalid('提取文本超过100000字符，需拆分材料')
    if not any(p.text.strip() for p in parts):
        invalid('未提取到可读文字')


class MaterialHandler:
    kind = 'PARSE_MATERIAL'

    def __init__(self, sessions, tasks, ai, storage):
        self.sessions, self.tasks, self.ai, self.storage = sessions, tasks, ai, storage

    def check(self, db, ctx, lock=False):
        obj = owned(db, Material, ctx.resource_id, ctx.user_id, lock=lock)
        if ctx.input_json.get('materialId') != obj.id:
            conflict('任务资源与固定输入不一致')
        if obj.status not in {'QUEUED', 'PROCESSING', 'FAILED'}:
            conflict('材料不允许继续处理')
        if obj.file_id:
            file = valid_file(db, obj.file_id, ctx.user_id, 'MATERIAL')
            if file.id != ctx.input_json.get('fileId') or file.object_key != ctx.input_json.get('objectKey'):
                conflict('材料文件输入已失效')
        elif obj.input_text != ctx.input_json.get('text'):
            conflict('材料固定输入已失效')
        return obj

    def prepare(self, ctx: TaskContext):
        with self.sessions.begin() as db:
            self.tasks.assert_lease(db, ctx)
            self.check(db, ctx)
            return deepcopy(ctx.input_json)

    def execute(self, snapshot):
        if snapshot.get('fileId'):
            parts = extract_parts(self.storage.read(snapshot['objectKey']), snapshot['mimeType'], self.ai)
        else:
            parts = [TextPart(text=snapshot['text'], page=None, extractionMethod='TEXT')]
        check_parts(parts)
        segments = []
        for part in parts:
            for offset in range(0, len(part.text), 4000):
                text = part.text[offset:offset + 4000]
                if text.strip():
                    segments.append(dict(id=uid(), ordinal=len(segments) + 1, page=part.page,
                                         text=text, extractionMethod=part.extraction_method))
        analysis = MaterialAnalysis.model_validate(self.ai.extract_experiences(deepcopy(segments)))
        if len({c.candidate_key for c in analysis.candidates}) != len(analysis.candidates):
            invalid('模型 candidateKey 重复')
        segment_ids = {p['id'] for p in segments}
        for candidate in analysis.candidates:
            fields = leaves(candidate.data.model_dump(by_alias=True))
            covered = set()
            for source in candidate.provenance:
                if (source.origin != 'MATERIAL' or source.turn_ids or not source.segment_ids or
                    not set(source.segment_ids) <= segment_ids or source.json_pointer not in fields):
                    invalid('模型返回不可信的字段来源')
                covered.add(source.json_pointer)
            required = {p for p, value in fields.items() if value not in ('', None, False)}
            if not required <= covered:
                invalid('模型经历事实缺少原材料来源')
        return dict(segments=segments, analysis=analysis)

    def commit(self, db, ctx: TaskContext, result):
        self.tasks.assert_lease(db, ctx)
        obj = self.check(db, ctx, lock=True)
        # Failure before this transaction commits cannot leave partially accepted candidates.
        for part in result['segments']:
            db.add(Segment(id=part['id'], user_id=ctx.user_id, material_id=obj.id, ordinal=part['ordinal'],
                           page_no=part['page'], text=part['text'], extraction_method=part['extractionMethod']))
        db.flush()
        for candidate in result['analysis'].candidates:
            exp = Experience(user_id=ctx.user_id, workspace_id=obj.workspace_id, generation_task_id=ctx.task_id,
                candidate_key=candidate.candidate_key, type=candidate.type, data_json=candidate.data.model_dump(by_alias=True),
                status='CANDIDATE', revision=1, excluded=False)
            db.add(exp)
            db.flush()
            for source in candidate.provenance:
                for segment_id in set(source.segment_ids):
                    add_source(db, exp, source.json_pointer, origin='MATERIAL', segment_id=segment_id)
        obj.status, obj.error_json = 'READY', None
        return dict(resourceType='MATERIAL', resourceId=obj.id, resourceUrl='/api/materials/' + obj.id)

    def started(self, db, ctx):
        obj = self.check(db, ctx, lock=True)
        obj.status, obj.error_json = 'PROCESSING', None

    def failed(self, db, ctx, error):
        obj = owned(db, Material, ctx.resource_id, ctx.user_id, lock=True)
        obj.status, obj.error_json = 'FAILED', TaskError.model_validate(error).model_dump(by_alias=True)

    def retry(self, db, ctx):
        obj = self.check(db, ctx, lock=True)
        if obj.status != 'FAILED':
            conflict('只有失败材料可重试')
        obj.status, obj.error_json = 'QUEUED', None

    def cancelled(self, db, ctx):
        obj = owned(db, Material, ctx.resource_id, ctx.user_id, lock=True, include_deleted=True)
        if obj.deleted_at is None:
            obj.status = 'FAILED'
            obj.error_json = dict(code='TASK_CANCELLED', message='任务已取消', canRetry=False)


class JdHandler(MaterialHandler):
    kind = 'ANALYZE_JD'

    def check(self, db, ctx, lock=False):
        obj = jd_version(db, ctx.resource_id, ctx.user_id, lock=lock)
        if ctx.input_json.get('jdVersionId') != obj.id or obj.status not in {'QUEUED', 'ANALYZING', 'FAILED'}:
            conflict('JD任务输入或状态已失效')
        if obj.file_id:
            file = valid_file(db, obj.file_id, ctx.user_id, 'JD')
            if (file.object_key != ctx.input_json.get('objectKey') or file.id != ctx.input_json.get('fileId')
                    or obj.original_text != (ctx.input_json.get('text') or '')):
                conflict('JD截图输入已失效')
        elif obj.original_text != ctx.input_json.get('text'):
            conflict('JD原文输入已失效')
        return obj

    def execute(self, snapshot):
        if snapshot.get('fileId'):
            parts = extract_parts(self.storage.read(snapshot['objectKey']), snapshot['mimeType'], self.ai)
            check_parts(parts)
            text = '\n\n'.join(value for value in ('\n'.join(p.text for p in parts), snapshot.get('text')) if value)
            if len(text) > 100000:
                invalid('文件内容与 JD 原文合计不能超过 10 万字，请精简后重新提交')
        else:
            text = snapshot['text']
        analysis = JdAnalysis.model_validate(self.ai.analyze_jd(text))
        ids = [r.id for r in analysis.requirements]
        if len(set(ids)) != len(ids):
            invalid('模型要求 ID 重复')
        for r in analysis.requirements:
            if not r.evidence_quote or r.evidence_quote not in text:
                invalid('模型JD分析缺少原文依据')
        return dict(text=text, analysis=analysis)

    def commit(self, db, ctx, result):
        self.tasks.assert_lease(db, ctx)
        obj = self.check(db, ctx, lock=True)
        obj.original_text = result['text']
        obj.job_title, obj.company_name = result['analysis'].job_title, result['analysis'].company_name
        obj.requirements_json = [r.model_dump(by_alias=True) for r in result['analysis'].requirements]
        obj.status = 'REVIEW_REQUIRED'
        return dict(resourceType='JD_VERSION', resourceId=obj.id, resourceUrl=f'/api/job-descriptions/{obj.jd_id}/versions/{obj.id}')

    def started(self, db, ctx):
        self.check(db, ctx, lock=True).status = 'ANALYZING'

    def failed(self, db, ctx, error):
        self.check(db, ctx, lock=True).status = 'FAILED'

    def retry(self, db, ctx):
        obj = self.check(db, ctx, lock=True)
        if obj.status != 'FAILED':
            conflict('只有失败 JD 可重试')
        obj.status = 'QUEUED'

    def cancelled(self, db, ctx):
        obj = owned(db, JdVersion, ctx.resource_id, ctx.user_id, lock=True)
        jd = owned(db, JobDescription, obj.jd_id, ctx.user_id, lock=True, include_deleted=True)
        if jd.deleted_at is None and obj.status != 'CONFIRMED':
            obj.status = 'FAILED'


def handlers(app):
    args = app.state.sessions, app.state.tasks, app.state.ai, app.state.storage
    return {h.kind: h for h in (MaterialHandler(*args), JdHandler(*args))}
