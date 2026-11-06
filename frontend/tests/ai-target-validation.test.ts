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
