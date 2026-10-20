const assert = require('node:assert/strict');
const { readFileSync } = require('node:fs');
const { test } = require('node:test');
const vm = require('node:vm');
const { transform } = require('next/dist/build/swc');
const { createRequestIdentity } = require('../app/lib/requestIdentity.js');

const settle = async () => { for (let i = 0; i < 20; i++) await Promise.resolve(); };
const person = uid => ({ uid, getIdToken: async () => uid });

async function mount(page) {
  const state = [], refs = [], effects = [], pending = [];
  let cursor = 0, refCursor = 0, authCallback;
  const auth = { currentUser: null }, exports = {};
  const file = page === 'home' ? `${__dirname}/../app/page.js` : `${__dirname}/../app/${page}/page.js`;
  const compiled = await transform(readFileSync(file, 'utf8'), {
    filename: 'page.jsx',
    jsc: { parser: { syntax: 'ecmascript', jsx: true }, transform: { react: { runtime: 'automatic' } } },
    module: { type: 'commonjs' },
  });
  vm.runInNewContext(compiled.code, {
    exports, TypeError, window: { location: { assign() {} } },
    fetch: async url => ({ ok: true, json: () => new Promise(resolve => pending.push({ url, resolve })) }),
    require: name => {
      if (name === 'react') return {
        useState(initial) { const i = cursor++; if (!(i in state)) state[i] = initial; return [state[i], v => { state[i] = typeof v === 'function' ? v(state[i]) : v; }]; },
        useRef(initial) { const i = refCursor++; return refs[i] ||= { current: initial }; },
        useEffect(fn) { effects.push(fn); },
      };
      if (name === 'firebase/auth') return { onAuthStateChanged: (_, callback) => { authCallback = callback; return () => {}; } };
      if (name.endsWith('/firebase')) return { auth };
      if (name.endsWith('/requestIdentity')) return { createRequestIdentity };
      if (name.endsWith('/config')) return { BACKEND_URL: 'https://offline.invalid' };
      if (name.endsWith('/backendHealth')) return { reportBackendFailure() {}, reportBackendSuccess() {} };
      if (name.endsWith('/errors')) return require('../app/lib/errors.js');
      if (name.startsWith('../components/') || name.startsWith('./components/') || name.startsWith('./hooks/') || name.startsWith('./utils/') || name === 'next/link') return () => null;
      if (name.endsWith('/scripture')) return { displayTranslation: text => text };
      return require(name);
    },
  });
  function render() { cursor = 0; refCursor = 0; return exports.default(); }
  render();
  const cleanup = effects.find(fn => fn.toString().includes('onAuthStateChanged'))();
  return { state, pending, render, cleanup, async change(user) { auth.currentUser = user; const result = authCallback(user); await settle(); return { result }; } };
}

for (const page of ['saved', 'history']) {
  test(`${page}: account B wins when account A resolves late, and logout clears data`, async () => {
    const view = await mount(page);
    await view.change(person('A'));
    const old = view.pending.splice(0);
    await view.change(person('B'));
    const newer = view.pending.splice(0);
    for (const item of newer) item.resolve({ saved: [{ id: 'B' }], history: [{ id: 'B' }], folders: [] });
    await settle();
    for (const item of old) item.resolve({ saved: [{ id: 'A-private' }], history: [{ id: 'A-private' }], folders: [{ name: 'A-private' }] });
    await settle();
    assert.ok(JSON.stringify(view.state).includes('B'));
    assert.ok(!JSON.stringify(view.state).includes('A-private'));
    await view.change(null);
    assert.ok(!JSON.stringify(view.state).includes('"id":"B"'));
    view.cleanup();
  });
}

test('request generations reject prior same-UID requests and an A/B/A switch', () => {
  const identity = createRequestIdentity();
  const old = identity.start('search', 'A');
  const newer = identity.start('search', 'A');
  assert.equal(identity.current(old, 'A'), false);
  assert.equal(identity.current(newer, 'A'), true);
  identity.reset();
  identity.start('search', 'A');
  assert.equal(identity.current(newer, 'A'), false);
});

test('a late onboarding completion cannot overwrite a later auth generation, even A/B/A', async () => {
  const view = await mount('home');
  await view.change(person('A'));
  view.pending.splice(0).forEach(item => item.resolve({ is_new_user: true })); await settle();
  const oldCompletion = view.render().props.onProfileComplete;
  await view.change(person('B'));
  view.pending.splice(0).forEach(item => item.resolve({ is_new_user: true })); await settle();
  await view.change(person('A'));
  view.pending.splice(0).forEach(item => item.resolve({ is_new_user: true })); await settle();
  const newCompletion = view.render().props.onProfileComplete;
  oldCompletion({ persona: 'private-old-A' });
  assert.ok(!JSON.stringify(view.state).includes('private-old-A'));
  newCompletion({ persona: 'curious_explorer' });
  assert.ok(JSON.stringify(view.state).includes('curious_explorer'));
  view.cleanup();
});
