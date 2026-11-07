import test from 'node:test';
import assert from 'node:assert/strict';
import { latestTemplate, supportsTheme } from '../src/services/templatePolicy.ts';

test('selects the newest version independently of server ordering', () => {
  const old = { id: 'project', version: '1.0.0', stylePolicy: { colors: ['#333333'] } };
  const current = { id: 'project', version: '1.1.0', stylePolicy: { colors: ['#333333', '#357A5B'] } };
  for (const rows of [[old, current], [current, old]]) {
    assert.equal(latestTemplate(rows, 'project'), current);
    assert.equal(supportsTheme(latestTemplate(rows, 'project'), '#357A5B'), true);
  }
  assert.equal(latestTemplate([current, { ...current, version: '1.10.0' }], 'project')?.version, '1.10.0');
});

test('unsupported and unavailable template colors are excluded', () => {
  const limited = { id: 'simple', version: '2.0.0', stylePolicy: { colors: ['#2563EB'] } };
  assert.equal(supportsTheme(limited, '#2563EB'), true);
  assert.equal(supportsTheme(limited, '#357A5B'), false);
  assert.equal(supportsTheme(latestTemplate([limited], 'missing'), '#2563EB'), false);
});
