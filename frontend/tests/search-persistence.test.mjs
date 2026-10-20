// Run: node frontend/tests/search-persistence.test.mjs
import assert from 'node:assert/strict';
import { test } from 'node:test';

const store = new Map();
globalThis.sessionStorage = {
  getItem: (k) => (store.has(k) ? store.get(k) : null),
  setItem: (k, v) => store.set(k, String(v)),
  removeItem: (k) => store.delete(k),
};
const { saveSearchState, loadSearchState } = await import('../app/utils/searchPersistence.js');

test("a later account never sees the previous account's last answer", () => {
  store.clear();
  saveSearchState('2:255', 'tafsir', { summary: 'A private answer' }, 'uid-A');
  assert.equal(loadSearchState('uid-B'), null);
  assert.equal(store.size, 0, 'the foreign state is removed, not just hidden');
});

test('a guest never sees a signed-in reader\'s answer, and vice versa', () => {
  store.clear();
  saveSearchState('2:255', 'tafsir', { summary: 'x' }, 'uid-A');
  assert.equal(loadSearchState('guest'), null);
  saveSearchState('1:1', 'tafsir', { summary: 'y' }, 'guest');
  assert.equal(loadSearchState('uid-A'), null);
});

test('the same reader still gets their answer back after a refresh', () => {
  store.clear();
  saveSearchState('94:5', 'tafsir', { summary: 'mine' }, 'uid-A');
  assert.equal(loadSearchState('uid-A').response.summary, 'mine');
  saveSearchState('94:5', 'tafsir', { summary: 'guest' }, 'guest');
  assert.equal(loadSearchState('guest').response.summary, 'guest');
});
