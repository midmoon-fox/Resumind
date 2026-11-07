type Target = { kind: string; sectionId?: string; itemId?: string; field?: string };
type Doc = {
  profile?: { skills: string };
  sections: Array<{ id: string; kind: string; text?: string; items: Array<{ id: string; html?: string }> }>;
};

function hasText(text = '') {
  return Boolean(text.replace(/[\u200b-\u200d\ufeff]/g, '').trim());
}

function hasRichText(html = '') {
  return hasText(html.replace(/<[^>]*>/g, '').replace(/&nbsp;|&#(?:160|x0*a0);/gi, ' '));
}

export function validateAiTarget(doc: Doc, target: Target): string {
  const section = doc.sections.find((s) => s.id === target.sectionId);
  if (!section) return '该模块已删除或尚未保存，请重新打开模块后再试';
  if (target.kind === 'SECTION_FIELD') {
    if (section.kind !== 'TEXT' || target.field !== 'text')
      return '此模块暂不支持 AI 帮助，请手动填写';
    if (!hasRichText(section.text)) return '请先在自定义模块中填写主题或内容要点，再使用 AI 帮助';
  } else if (target.kind === 'ITEM_DESCRIPTION') {
    if (['EDUCATION', 'SKILLS', 'CHARTS', 'SOCIAL_LINKS', 'TEXT'].includes(section.kind))
      return '此模块暂不支持该 AI 帮助方式';
    const item = section.items.find((i) => i.id === target.itemId);
    if (!item) return '该条目已删除，请选择现有条目后重试';
    if (!hasRichText(item.html)) return '请先填写一些实际经历，再使用 AI 帮助';
  } else if (target.kind === 'PROFILE_FIELD') {
    if (
      !['education', 'skills'].includes(target.field || '') ||
      section.kind !== target.field?.toUpperCase()
    )
      return '此字段暂不支持 AI 帮助';
    if (target.field === 'skills' && !hasText(doc.profile?.skills))
      return '请先填写掌握的技能或工具，再使用 AI 帮助';
  } else return '此模块暂不支持 AI 帮助，请手动填写';
  return '';
}
