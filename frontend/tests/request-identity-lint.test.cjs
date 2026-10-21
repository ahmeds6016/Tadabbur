const assert = require('node:assert/strict');
const { test } = require('node:test');
const path = require('node:path');
const { ESLint } = require('eslint');

test('request identity refs do not create missing effect dependency warnings', async () => {
  const eslint = new ESLint({ cwd: path.resolve(__dirname, '..') });
  const files = ['app/page.js', ...['annotations', 'saved', 'history', 'plans', 'progress'].map(page => `app/${page}/page.js`)];
  const results = await eslint.lintFiles(files);
  const warnings = results.flatMap(result => result.messages
    .filter(message => message.ruleId === 'react-hooks/exhaustive-deps')
    .map(message => `${path.basename(path.dirname(result.filePath))}:${message.line}: ${message.message}`));
  assert.deepEqual(warnings, []);
});
