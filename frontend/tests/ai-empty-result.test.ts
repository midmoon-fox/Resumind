import test from 'node:test';
import assert from 'node:assert/strict';
import { suggestionText } from '../src/services/aiSuggestionText.ts';
test('empty AI structures yield no usable content', () => {
  for (const value of [
    null,
    {},
    '',
    [],
    { skills: [] },
    { type: 'doc', content: [{ type: 'paragraph', content: [] }] },
    { type: 'doc', content: [{ type: 'text', text: '   ' }] },
  ])
    assert.equal(suggestionText(value).trim(), '');
});
test('text and structured skills retain generated content', () => {
  assert.equal(suggestionText({ skills: ['熟悉 Vue', '掌握 Git'] }), '熟悉 Vue\n掌握 Git');
  assert.equal(
    suggestionText({
      type: 'doc',
      content: [{ type: 'paragraph', content: [{ type: 'text', text: '真实内容' }] }],
    }),
    '真实内容',
  );
});
