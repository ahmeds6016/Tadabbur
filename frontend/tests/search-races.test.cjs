// Execute the actual MainApp handlers with deferred responses and fake hook state.
const assert = require('node:assert/strict');
const { readFileSync } = require('node:fs');
const { test } = require('node:test');
const vm = require('node:vm');
const { transform } = require('next/dist/build/swc');
const { createRequestIdentity } = require('../app/lib/requestIdentity.js');
const settle = async () => { for (let i = 0; i < 16; i++) await Promise.resolve(); };

async function mount(user = null) {
  let source = readFileSync(`${__dirname}/../app/page.js`, 'utf8');
  source = source.replace('  const saveQueryToHistory = async',
    '  globalThis.testSearch = { handleGetTafsir, handleCancelSearch, setQuery, loading: isTafsirLoading, searchTimeoutRef, badgePopup };\n  const saveQueryToHistory = async');
  source = source.replace('  // Annotation handlers (centralized',
    '  globalThis.testShare = { ensureShareId, pendingShareRequest, currentShareId };\n  // Annotation handlers (centralized');
  source = source.replace('  // Actually save with the chosen folder', '  globalThis.testSave = { handleSaveSearch, existingFolders, showFolderPicker };\n  // Actually save with the chosen folder');
  source += '\nexport { MainAppContent };';
  const compiled = await transform(source, { filename: 'page.jsx',
    jsc: { parser: { syntax: 'ecmascript', jsx: true }, transform: { react: { runtime: 'automatic' } } }, module: { type: 'commonjs' } });
  const state = [], refs = [], effectState = [], effects = [], timers = new Map(), pending = [];
  let cursor = 0, refCursor = 0, effectCursor = 0, timer = 0;
  const exports = {}, auth = { currentUser: user };
  const context = {
    exports, AbortController, TypeError, console,
    window: { location: { origin: 'https://offline.invalid' } },
    sessionStorage: { getItem: () => '0', setItem() {} },
    setTimeout(fn) { timers.set(++timer, fn); return timer; }, clearTimeout(id) { timers.delete(id); },
    fetch: async (url, options) => {
      if (url.includes('/verse/')) return { ok: true, json: async () => ({ arabic: 'Preview' }) };
      return new Promise(resolve => pending.push({ url, options, resolve }));
    },
    require: name => {
      if (name === 'react') return {
        useState(initial) { const i = cursor++; if (!(i in state)) state[i] = typeof initial === 'function' ? initial() : initial; return [state[i], v => { state[i] = typeof v === 'function' ? v(state[i]) : v; }]; },
        useRef(initial) { const i = refCursor++; return refs[i] ||= { current: initial }; },
        useCallback: fn => fn,
        useEffect(fn, dependencies) {
          const i = effectCursor++, previous = effectState[i];
          if (!previous || dependencies?.some((value, j) => !Object.is(value, previous[j]))) {
            if (fn.toString().includes('answerGeneration.current += 1')) effects.push(fn);
            effectState[i] = dependencies;
          }
        },
      };
      if (name === 'next/navigation') return { useSearchParams: () => ({ get: () => null }) };
      if (name === './lib/requestIdentity') return { createRequestIdentity };
      if (name === './lib/firebase') return { auth };
      if (name === './lib/errors') return require('../app/lib/errors.js');
      if (name === './lib/config') return { BACKEND_URL: 'https://offline.invalid', getPersonaTheme: () => ({}), getPersonaIcon: () => '' };
      if (name === './hooks/useToast') return { useToast: () => ({ toasts: [], showSuccess() {}, showError() {} }) };
      if (name === './hooks/useOnboarding') return { useOnboarding: () => ({ onboardingState: { hasSeenFeatureIntro: true, hasSearched: true }, markStepComplete() {}, markFeatureIntroSeen() {}, isLoaded: true }) };
      if (name === './hooks/useTextSelection') return () => ({ selectedText: '', clearSelection() {} });
      if (name === './lib/backendHealth') return { reportBackendFailure() {}, reportBackendSuccess() {} };
      if (name.startsWith('./') || name.startsWith('../config')) return () => null;
      if (name === 'firebase/auth') return {};
      return require(name);
    },
  };
  vm.createContext(context); vm.runInContext(compiled.code, context);
  function render() {
    cursor = refCursor = effectCursor = 0;
    exports.MainAppContent({ user, isGuest: !user, userProfile: { persona: 'curious_explorer' } });
    effects.splice(0).forEach(effect => effect());
  }
  render();
  return { context, state, timers, pending, render, async start(query) {
    context.testSearch.setQuery(query); render();
    const result = context.testSearch.handleGetTafsir({ preventDefault() {} }); await settle(); return { result };
  } };
}

const answer = summary => ({ ok: true, json: async () => ({ summary }) });

test('an old search finally cannot clear the newer timer or loading state', async () => {
  const view = await mount();
  const a = await view.start('2:255');
  view.context.testSearch.handleCancelSearch(); view.render();
  const b = await view.start('2:256');
  const timerB = view.context.testSearch.searchTimeoutRef.current;
  assert.ok(view.timers.has(timerB));
  view.pending.find(p => JSON.parse(p.options.body).query === '2:255').resolve(answer('Old answer'));
  await a.result; view.render();
  assert.ok(view.timers.has(timerB));
  assert.equal(view.context.testSearch.loading, true);
  view.pending.find(p => JSON.parse(p.options.body).query === '2:256').resolve(answer('New answer'));
  await b.result; view.render();
  assert.equal(view.context.testSearch.loading, false);
  assert.equal(view.timers.has(timerB), false);
  assert.ok(!JSON.stringify(view.state).includes('Old answer'));
});

test('a late old-answer share cannot replace or clear a new answer share', async () => {
  const view = await mount();
  const a = await view.start('2:255');
  view.pending.find(p => p.url.endsWith('/tafsir')).resolve(answer('First answer'));
  await a.result; view.render();
  const shareA = view.context.testShare.ensureShareId(); await settle();
  const b = await view.start('2:256');
  view.pending.filter(p => p.url.endsWith('/tafsir')).at(-1).resolve(answer('Second answer'));
  await b.result; view.render();
  const shareB = view.context.testShare.ensureShareId(); await settle();
  const pendingB = view.context.testShare.pendingShareRequest.current;
  view.pending.filter(p => p.url.endsWith('/share'))[0].resolve({ ok: true, json: async () => ({ share_id: 'old' }) });
  assert.equal(await shareA, null);
  assert.equal(view.context.testShare.pendingShareRequest.current, pendingB);
  view.pending.filter(p => p.url.endsWith('/share'))[1].resolve({ ok: true, json: async () => ({ share_id: 'new' }) });
  assert.equal(await shareB, 'new'); view.render();
  assert.equal(view.context.testShare.currentShareId, 'new');
});


test('a study award header shows the earned badge without putting it in the answer', async () => {
  const view = await mount({ uid: 'reader', getIdToken: async () => 'offline' });
  const search = await view.start('2:255');
  view.pending.find(p => p.url.endsWith('/tafsir')).resolve({
    ...answer('Study answer'), headers: { get: key => key === 'X-Newly-Earned-Badges' ? '["explore_10"]' : null },
  });
  await settle();
  const lookup = view.pending.find(p => p.url.endsWith('/badges'));
  assert.ok(lookup, 'study awards must be resolved for the popup');
  lookup.resolve({ ok: true, json: async () => ({ badges: [{ id: 'explore_10', name: 'Explorer', earned: true }] }) });
  view.pending.find(p => p.url.endsWith('/query-history')).resolve({ ok: true });
  await search.result; await settle(); view.render();
  assert.equal(view.context.testSearch.badgePopup.id, 'explore_10');
});


test('the save dialog follows folder cursors beyond the first 100 documents', async () => {
  const view = await mount({ uid: 'reader', getIdToken: async () => 'offline' });
  const search = await view.start('2:255');
  view.pending.find(p => p.url.endsWith('/tafsir')).resolve(answer('Study answer'));
  await settle();
  view.pending.find(p => p.url.endsWith('/query-history')).resolve({ ok: true });
  await search.result; view.render();
  const saving = view.context.testSave.handleSaveSearch(); await settle();
  view.pending.find(p => p.url.includes('/saved-searches/folders')).resolve({ ok: true, json: async () => ({ folders: [{ name: 'First' }], next_cursor: 'doc100' }) });
  await settle();
  const secondPage = view.pending.find(p => p.url.includes('cursor=doc100'));
  assert.ok(secondPage, 'folder picker must follow next_cursor');
  secondPage.resolve({ ok: true, json: async () => ({ folders: [{ name: 'First' }, { name: 'Later' }], next_cursor: null }) });
  await saving; view.render();
  assert.deepEqual(Array.from(view.context.testSave.existingFolders), ['First', 'Later']);
  assert.equal(view.context.testSave.showFolderPicker, true);
});
