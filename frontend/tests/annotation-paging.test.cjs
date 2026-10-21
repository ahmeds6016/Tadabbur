const assert = require('node:assert/strict');
const { readFileSync } = require('node:fs');
const { test } = require('node:test');
const vm = require('node:vm');
const { transform } = require('next/dist/build/swc');
const { createRequestIdentity } = require('../app/lib/requestIdentity.js');
const settle = async () => { for (let i = 0; i < 20; i++) await Promise.resolve(); };

async function mount() {
  let source = readFileSync(`${__dirname}/../app/annotations/page.js`, 'utf8');
  source = source.replace('  const formatDate =', '  globalThis.actions = { setSearchQuery, handleSearch, handleTagFilter };\n  const formatDate =');
  const compiled = await transform(source, { filename: 'page.jsx', jsc: { parser: { syntax: 'ecmascript', jsx: true }, transform: { react: { runtime: 'automatic' } } }, module: { type: 'commonjs' } });
  const state = [], refs = [], effects = [], urls = [];
  let cursor = 0, refCursor = 0, authCallback;
  const user = { uid: 'reader', getIdToken: async () => 'offline' };
  const context = { exports: {}, console, require: name => {
    if (name === 'react') return {
      useState(initial) { const i = cursor++; if (!(i in state)) state[i] = initial; return [state[i], value => { state[i] = typeof value === 'function' ? value(state[i]) : value; }]; },
      useRef(initial) { const i = refCursor++; return refs[i] ||= { current: initial }; },
      useEffect(fn) { effects.push(fn); },
    };
    if (name === 'firebase/auth') return { onAuthStateChanged: (_, fn) => { authCallback = fn; return () => {}; } };
    if (name.endsWith('/firebase')) return { auth: { currentUser: user } };
    if (name.endsWith('/requestIdentity')) return { createRequestIdentity };
    if (name.endsWith('/config')) return { BACKEND_URL: 'https://offline.invalid' };
    if (name.endsWith('/backendHealth')) return { reportBackendSuccess() {}, reportBackendFailure() {} };
    if (name.endsWith('/scripture')) return { displayTranslation: text => text };
    if (name.startsWith('../components/') || name === 'next/link') return () => null;
    return require(name);
  }, fetch: async url => {
    urls.push(url);
    return { ok: true, json: async () => ({ annotations: [], results: [], tags: [], next_cursor: 'page-two' }) };
  } };
  vm.createContext(context); vm.runInContext(compiled.code, context);
  function render() { cursor = refCursor = 0; return context.exports.default(); }
  render(); effects[0](); await authCallback(user); render();
  function button(node) {
    if (!node || typeof node !== 'object') return null;
    if (node.props?.children === 'Load more reflections') return node;
    for (const child of [node.props?.children].flat(Infinity)) { const result = button(child); if (result) return result; }
    return null;
  }
  return { urls, context, render, async more() { button(render()).props.onClick(); await settle(); render(); } };
}

test('Load more keeps the submitted query after editing or clearing the draft', async () => {
  const view = await mount();
  view.context.actions.setSearchQuery('patience'); view.render();
  await view.context.actions.handleSearch(); view.render();
  view.context.actions.setSearchQuery(''); view.render();
  await view.more();
  assert.match(view.urls.at(-1), /\/annotations\/search\?q=patience&cursor=page-two$/);
  view.context.actions.setSearchQuery('gratitude'); view.render();
  await view.more();
  assert.match(view.urls.at(-1), /\/annotations\/search\?q=patience&cursor=page-two$/);
});

test('Load more keeps list filters even when the search draft is nonempty', async () => {
  const view = await mount();
  view.context.actions.setSearchQuery('unsubmitted'); view.render();
  view.context.actions.handleTagFilter('private tag'); await settle(); view.render();
  await view.more();
  assert.match(view.urls.at(-1), /\/annotations\/user\?limit=100&cursor=page-two&tag=private%20tag$/);
});
