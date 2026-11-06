type Target = { kind: string; sectionId?: string; itemId?: string; field?: string };
type Doc = {
  sections: Array<{ id: string; kind: string; text?: string; items: Array<{ id: string }> }>;
};
export function validateAiTarget(doc: Doc, target: Target): string {
  const section = doc.sections.find((s) => s.id === target.sectionId);
  if (!section) return '该模块已删除或尚未保存，请重新打开模块后再试';
  if (target.kind === 'SECTION_FIELD') {
    if (section.kind !== 'TEXT' || target.field !== 'text')
      return '此模块暂不支持 AI 帮助，请手动填写';
    const content = (section.text || '')
      .replace(/<[^>]*>/g, '')
      .replace(/&nbsp;|&#160;/g, ' ')
      .trim();
    if (!content) return '请先在自定义模块中填写主题或内容要点，再使用 AI 帮助';
  } else if (target.kind === 'ITEM_DESCRIPTION') {
    if (['EDUCATION', 'SKILLS', 'CHARTS', 'SOCIAL_LINKS', 'TEXT'].includes(section.kind))
      return '此模块暂不支持该 AI 帮助方式';
    if (!section.items.some((i) => i.id === target.itemId))
      return '该条目已删除，请选择现有条目后重试';
  } else if (target.kind === 'PROFILE_FIELD') {
    if (
      !['education', 'skills'].includes(target.field || '') ||
      section.kind !== target.field?.toUpperCase()
    )
      return '此字段暂不支持 AI 帮助';
  } else return '此模块暂不支持 AI 帮助，请手动填写';
  return '';
}
