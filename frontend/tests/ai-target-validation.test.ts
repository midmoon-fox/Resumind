import test from 'node:test';
import assert from 'node:assert/strict';
import { validateAiTarget } from '../src/services/aiTargetValidation.ts';
const target = { kind: 'SECTION_FIELD', sectionId: 'custom', field: 'text' };
test('empty custom input is caught before save or AI requests', () => {
  const doc = { sections: [{ id: 'custom', kind: 'TEXT', items: [], text: '<p><br></p>' }] };
  assert.match(validateAiTarget(doc, target), /填写主题或内容要点/);
  doc.sections[0]!.text = '<p>根据我已有的项目经验整理个人简介</p>';
  assert.equal(validateAiTarget(doc, target), '');
});
test('deleted and unsupported targets have readable frontend errors', () => {
  assert.match(validateAiTarget({ sections: [] }, target), /已删除或尚未保存/);
  assert.match(
    validateAiTarget({ sections: [{ id: 'custom', kind: 'CHARTS', items: [] }] }, target),
    /暂不支持/,
  );
});

test('empty skill and experience content is caught before requesting a rewrite', () => {
  const skills = { kind: 'PROFILE_FIELD', sectionId: 'skills', field: 'skills' };
  const item = { kind: 'ITEM_DESCRIPTION', sectionId: 'projects', itemId: 'entry' };
  const entry = { id: 'entry', html: '<p>&#xA0;<br>\u200b</p>' };
  const doc = {
    profile: { skills: ' \u200b\n' },
    sections: [
      { id: 'skills', kind: 'SKILLS', items: [] },
      { id: 'projects', kind: 'PROJECTS', items: [entry] },
    ],
  };
  assert.match(validateAiTarget(doc, skills), /填写掌握的技能/);
  assert.match(validateAiTarget(doc, item), /填写一些实际经历/);
  doc.profile.skills = 'Python';
  entry.html = '<p>整理接口测试记录</p>';
  assert.equal(validateAiTarget(doc, skills), '');
  assert.equal(validateAiTarget(doc, item), '');
});
