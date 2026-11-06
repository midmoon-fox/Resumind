import test from 'node:test';
import assert from 'node:assert/strict';
import { modulePickerOptions, sectionRegistry } from '../src/types/sectionRegistry.ts';
test('module picker lists every module once and custom is last', () => {
  const leaves = modulePickerOptions.flatMap((option) =>
    'children' in option ? option.children : [option],
  );
  assert.deepEqual(leaves.map((o) => o.value).sort(), sectionRegistry.map((o) => o.type).sort());
  assert.equal(new Set(leaves.map((o) => o.value)).size, leaves.length);
  assert.equal(modulePickerOptions.at(-1)?.value, 'TEXT');
  assert.equal(modulePickerOptions.at(-1)?.label, '自定义');
  assert.equal(sectionRegistry.at(-1)?.type, 'TEXT');
});
