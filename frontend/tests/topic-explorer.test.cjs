// Offline component lifecycle checks using the installed Next JSX compiler.
const assert = require('node:assert/strict');
const { readFileSync } = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const { test } = require('node:test');
const { transform } = require('next/dist/build/swc');

const source = readFileSync(path.join(__dirname, '../app/components/TopicExplorer.jsx'), 'utf8');
const seeds = require('../../backend/data/topic_seeds.json');
const compiled = transform(source, {
  filename: 'TopicExplorer.jsx',
  jsc: { parser: { syntax: 'ecmascript', jsx: true }, transform: { react: { runtime: 'automatic' } } },
  module: { type: 'commonjs' },
});

async function mount(fetch) {
  const state = [], timers = new Map();
  let cursor = 0, effect, cleanup, timerId = 0;
  const exports = {};
  const context = {
    exports, AbortController, fetch,
    setTimeout: (fn, delay) => { timers.set(++timerId, { fn, delay }); return timerId; },
    clearTimeout: id => timers.delete(id),
    require: name => {
      if (name === 'react') return {
        useState: initial => {
          const slot = cursor++;
          if (!(slot in state)) state[slot] = initial;
          return [state[slot], value => { state[slot] = value; }];
        },
        useEffect: fn => { effect = fn; },
      };
      if (name === '../lib/config') return { BACKEND_URL: 'https://offline.invalid' };
      if (name === './SurahVersePicker') return { THEME_QUICK_SELECTS: seeds.map(seed => ({
        label: seed.name, verses: seed.verse_refs.map(query => ({ query })),
      })) };
      return require(name);
    },
  };
  vm.runInNewContext((await compiled).code, context);
  const selected = [];
  const render = () => {
    cursor = 0;
    return exports.default({ text: 'patience during hardship', user: null, onSelect: ref => selected.push(ref) });
  };
  render();
  cleanup = effect();
  return { state, timers, render, cleanup, selected };
}

const settle = async () => { for (let i = 0; i < 8; i++) await Promise.resolve(); };
function nodes(tree) {
  if (!tree || typeof tree !== 'object') return [];
  return [tree, ...[tree.props?.children].flat(Infinity).flatMap(nodes)];
}

test('resolves on arrival, renders references, and preserves verse selection', async () => {
  const calls = [];
  const view = await mount(async (...args) => {
    calls.push(args);
    return { ok: true, json: async () => ({ topics: [{ name: 'Patience', confidence: .9, verse_refs: ['2:153', null, 'invalid'] }] }) };
  });
  await settle();
  assert.equal(calls.length, 1);
  assert.deepEqual(JSON.parse(calls[0][1].body), { text: 'patience during hardship' });
  const tree = nodes(view.render());
  const buttons = tree.filter(node => node.type === 'button');
  assert.equal(buttons.length, 1); // No additional action needed to resolve.
  assert.equal(buttons[0].props.children, '2:153');
  buttons[0].props.onClick();
  assert.deepEqual(view.selected, ['2:153']);
  assert.ok(tree.some(node => node.props?.['aria-live'] === 'polite'));
  assert.equal(view.state[1], false);
  assert.equal(view.timers.size, 0);
  view.cleanup();
});

test('null response offers all eight curated themes', async () => {
  const view = await mount(async () => ({ ok: true, json: async () => null }));
  await settle();
  assert.equal(view.state[0].length, 8);
  assert.ok(nodes(view.render()).some(node => node.type === 'button' && node.props.children === '39:53'));
  view.cleanup();
});

test('30 second timeout aborts and retains the curated fallback', async () => {
  let signal;
  const view = await mount((url, options) => {
    signal = options.signal;
    return new Promise((resolve, reject) => signal.addEventListener('abort', () => reject(new Error('aborted'))));
  });
  assert.equal(view.timers.size, 1);
  const timer = [...view.timers.values()][0];
  assert.equal(timer.delay, 30000);
  timer.fn();
  await settle();
  assert.equal(signal.aborted, true);
  assert.equal(view.state[0].length, 8);
  assert.equal(view.state[1], false);
  view.cleanup();
});

test('unmount aborts and prevents a stale response from updating state', async () => {
  let finish, signal;
  const view = await mount((url, options) => {
    signal = options.signal;
    return new Promise(resolve => { finish = resolve; });
  });
  view.cleanup();
  assert.equal(signal.aborted, true);
  assert.equal(view.timers.size, 0);
  finish({ ok: true, json: async () => ({ topics: [{ name: 'Old result', verse_refs: ['2:153'] }] }) });
  await settle();
  assert.equal(view.state[0], null);
});
