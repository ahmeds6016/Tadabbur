/**
 * Tests for nameInfo utility (getNameInfo + validateFirstName).
 *
 * Run with: node frontend/app/components/__tests__/nameInfo.test.js
 * (Uses built-in assert — no test framework needed.)
 */

const assert = require('assert');
const path = require('path');

// Load the JSON directly (the utility uses ESM imports, so we test the logic here)
const nameData = require(path.join(__dirname, '../../data/name_info.json'));

// ---- Re-implement the functions in CJS for testing ----

function getNameInfo(firstName) {
  if (!firstName || typeof firstName !== 'string') return null;
  const normalized = firstName.trim().toLowerCase().replace(/[^a-z'-]/g, '');
  if (normalized.length < 2) return null;

  for (const entry of nameData) {
    if (entry.canonical.toLowerCase() === normalized) return entry;
    if (entry.aliases.includes(normalized)) return entry;
  }
  return null;
}

function validateFirstName(value) {
  const trimmed = (value || '').trim();
  if (!trimmed) return { valid: true, error: null, cleaned: '' };
  if (/\s/.test(trimmed)) return { valid: false, error: 'First name only (no last name).', cleaned: trimmed };
  if (trimmed.length < 2) return { valid: false, error: 'Name must be at least 2 characters.', cleaned: trimmed };
  if (trimmed.length > 30) return { valid: false, error: 'Name must be 30 characters or fewer.', cleaned: trimmed };
  if (!/^[a-zA-Z\u0600-\u06FF'-]+$/.test(trimmed)) return { valid: false, error: 'Letters, hyphens, and apostrophes only.', cleaned: trimmed };
  return { valid: true, error: null, cleaned: trimmed };
}

// ---- Tests ----

let passed = 0;
let failed = 0;

function test(name, fn) {
  try {
    fn();
    passed++;
    console.log(`  PASS  ${name}`);
  } catch (e) {
    failed++;
    console.log(`  FAIL  ${name}`);
    console.log(`        ${e.message}`);
  }
}

console.log('\n=== getNameInfo ===\n');

test('"Ahmed" returns info', () => {
  const info = getNameInfo('Ahmed');
  assert.ok(info, 'Should return an entry');
  assert.strictEqual(info.canonical, 'Ahmad');
});

test('"Ahmad" and "Ahmet" map to same entry', () => {
  const a1 = getNameInfo('Ahmad');
  const a2 = getNameInfo('Ahmet');
  assert.ok(a1 && a2, 'Both should return entries');
  assert.strictEqual(a1.canonical, a2.canonical);
});

test('"ahmed" (lowercase) works', () => {
  const info = getNameInfo('ahmed');
  assert.ok(info);
  assert.strictEqual(info.canonical, 'Ahmad');
});

test('"AHMED" (uppercase) works', () => {
  const info = getNameInfo('AHMED');
  assert.ok(info);
  assert.strictEqual(info.canonical, 'Ahmad');
});

test('"Muhammad" returns info', () => {
  const info = getNameInfo('Muhammad');
  assert.ok(info);
  assert.strictEqual(info.canonical, 'Muhammad');
});

test('"Mohammad" alias works', () => {
  const info = getNameInfo('Mohammad');
  assert.ok(info);
  assert.strictEqual(info.canonical, 'Muhammad');
});

test('"Aisha" returns info (female name)', () => {
  const info = getNameInfo('Aisha');
  assert.ok(info);
  assert.strictEqual(info.canonical, 'Aisha');
});

test('"Ayesha" alias works', () => {
  const info = getNameInfo('Ayesha');
  assert.ok(info);
  assert.strictEqual(info.canonical, 'Aisha');
});

test('Unknown name returns null', () => {
  const info = getNameInfo('Xyzzyplugh');
  assert.strictEqual(info, null);
});

test('Empty string returns null', () => {
  assert.strictEqual(getNameInfo(''), null);
});

test('null returns null', () => {
  assert.strictEqual(getNameInfo(null), null);
});

test('undefined returns null', () => {
  assert.strictEqual(getNameInfo(undefined), null);
});

test('Single character returns null', () => {
  assert.strictEqual(getNameInfo('A'), null);
});

test('Number input returns null', () => {
  assert.strictEqual(getNameInfo(123), null);
});

test('Name with leading/trailing spaces is trimmed', () => {
  const info = getNameInfo('  Ahmed  ');
  assert.ok(info);
  assert.strictEqual(info.canonical, 'Ahmad');
});

console.log('\n=== validateFirstName ===\n');

test('Empty string is valid (optional field)', () => {
  const r = validateFirstName('');
  assert.strictEqual(r.valid, true);
  assert.strictEqual(r.error, null);
  assert.strictEqual(r.cleaned, '');
});

test('null input is valid (optional field)', () => {
  const r = validateFirstName(null);
  assert.strictEqual(r.valid, true);
});

test('Valid name "Ahmed" passes', () => {
  const r = validateFirstName('Ahmed');
  assert.strictEqual(r.valid, true);
  assert.strictEqual(r.cleaned, 'Ahmed');
});

test('Name with spaces rejected (no last name)', () => {
  const r = validateFirstName('John Smith');
  assert.strictEqual(r.valid, false);
  assert.ok(r.error.includes('First name only'));
});

test('Single character rejected', () => {
  const r = validateFirstName('A');
  assert.strictEqual(r.valid, false);
  assert.ok(r.error.includes('at least 2'));
});

test('31-character name rejected', () => {
  const r = validateFirstName('A'.repeat(31));
  assert.strictEqual(r.valid, false);
  assert.ok(r.error.includes('30 characters'));
});

test('30-character name accepted', () => {
  const r = validateFirstName('A'.repeat(30));
  assert.strictEqual(r.valid, true);
});

test('Hyphenated name accepted', () => {
  const r = validateFirstName("Abdul-Rahman");
  assert.strictEqual(r.valid, true);
});

test("Apostrophe name accepted", () => {
  const r = validateFirstName("O'Brien");
  assert.strictEqual(r.valid, true);
});

test('Numbers rejected', () => {
  const r = validateFirstName('Ahmed123');
  assert.strictEqual(r.valid, false);
  assert.ok(r.error.includes('Letters'));
});

test('Special characters rejected', () => {
  const r = validateFirstName('Ahmed@!');
  assert.strictEqual(r.valid, false);
});

test('Arabic characters accepted', () => {
  const r = validateFirstName('\u0623\u062d\u0645\u062f');
  assert.strictEqual(r.valid, true);
});

console.log('\n=== Data integrity ===\n');

test('All entries have required fields', () => {
  for (const entry of nameData) {
    assert.ok(entry.canonical, `Entry missing canonical: ${JSON.stringify(entry)}`);
    assert.ok(Array.isArray(entry.aliases), `Entry ${entry.canonical} missing aliases array`);
    assert.ok(entry.aliases.length > 0, `Entry ${entry.canonical} has empty aliases`);
    assert.ok(entry.short, `Entry ${entry.canonical} missing short description`);
    assert.ok(entry.long, `Entry ${entry.canonical} missing long description`);
    assert.ok(entry.language_origin, `Entry ${entry.canonical} missing language_origin`);
    assert.ok(entry.meaning, `Entry ${entry.canonical} missing meaning`);
    assert.ok('notes' in entry, `Entry ${entry.canonical} missing notes field`);
  }
});

test('All aliases are lowercase', () => {
  for (const entry of nameData) {
    for (const alias of entry.aliases) {
      assert.strictEqual(alias, alias.toLowerCase(), `Alias "${alias}" in ${entry.canonical} not lowercase`);
    }
  }
});

test('No duplicate aliases across entries', () => {
  const seen = new Map();
  for (const entry of nameData) {
    for (const alias of entry.aliases) {
      if (seen.has(alias)) {
        assert.fail(`Duplicate alias "${alias}" in ${entry.canonical} and ${seen.get(alias)}`);
      }
      seen.set(alias, entry.canonical);
    }
  }
});

test('At least 90 entries total', () => {
  assert.ok(nameData.length >= 90, `Only ${nameData.length} entries, expected >= 90`);
});

// ---- Summary ----
console.log(`\n${'='.repeat(40)}`);
console.log(`  ${passed} passed, ${failed} failed`);
console.log(`${'='.repeat(40)}\n`);

process.exit(failed > 0 ? 1 : 0);
