// Run: node frontend/tests/errors.test.mjs
import assert from 'node:assert/strict';
import { test } from 'node:test';
import {
  authErrorMessage, isUnknownAccountError, isSafeServerText,
  RequestError, requestErrorFrom, userMessage,
} from '../app/lib/errors.js';

const authError = (code) => Object.assign(new Error(`Firebase: Error (${code}).`), { code });
const response = (status, body) => ({
  status,
  json: async () => {
    if (body === undefined) throw new SyntaxError('Unexpected token < in JSON');
    return body;
  },
});
const LEAKY = /firebase|auth\/|error \(|exception|traceback|google|\{|\}/i;

test('wrong password and unknown email read identically, so accounts cannot be probed', () => {
  const codes = ['auth/invalid-credential', 'auth/wrong-password', 'auth/user-not-found', 'auth/invalid-login-credentials'];
  const messages = new Set(codes.map((code) => authErrorMessage(authError(code), 'signIn')));
  assert.equal(messages.size, 1);
  const [message] = messages;
  assert.match(message, /email and password don't match/);
  assert.doesNotMatch(message, LEAKY);
});

test('every auth outcome is plain language, including unknown codes', () => {
  for (const [code, action] of [
    ['auth/email-already-in-use', 'signUp'], ['auth/weak-password', 'signUp'],
    ['auth/too-many-requests', 'signIn'], ['auth/network-request-failed', 'signIn'],
    ['auth/invalid-recaptcha-token', 'signIn'], ['auth/some-future-code', 'signIn'],
    ['auth/some-future-code', 'signUp'], ['auth/some-future-code', 'reset'], [undefined, 'signIn'],
  ]) {
    const message = authErrorMessage(code ? authError(code) : new Error('boom'), action);
    assert.ok(message.length > 10, `${code}/${action}`);
    assert.doesNotMatch(message, LEAKY, `${code}/${action}`);
    assert.doesNotMatch(message, /!/, `${code}/${action}`);
  }
  assert.ok(isUnknownAccountError(authError('auth/user-not-found')));
  assert.ok(!isUnknownAccountError(authError('auth/invalid-email')));
});

test('server exception text never reaches the reader', async () => {
  const fallback = "We couldn't prepare this commentary just now. Please try again in a moment.";
  for (const [status, body] of [
    [500, { error: "403 Missing or insufficient permissions. google.api_core.exceptions.PermissionDenied" }],
    [500, { error: 'Internal server error' }],
    [400, { error: "KeyError: 'query'" }],
    [400, { error: "Invalid input: {'verse': None}" }],
    [502, undefined],
  ]) {
    const err = await requestErrorFrom(response(status, body), { fallback });
    assert.ok(err instanceof RequestError);
    assert.equal(err.userMessage, fallback, JSON.stringify(body));
  }
});

test('helpful server explanations are kept, and codes are never shown', async () => {
  const range = await requestErrorFrom(response(400, {
    error: 'verse_range_too_large',
    message: 'The verses 2:1-50 contain extensive commentary that exceeds response limits.\n\nPlease narrow your range to 12 verses or fewer from this starting point.',
  }), { fallback: 'fallback' });
  assert.match(range.userMessage, /narrow your range to 12 verses/);
  assert.doesNotMatch(range.userMessage, /verse_range_too_large/);

  const bareCode = await requestErrorFrom(response(400, { error: 'verse_range_too_large' }), { fallback: 'fallback text here' });
  assert.equal(bareCode.userMessage, 'fallback text here');

  const typed = await requestErrorFrom(response(400, { error: 'The AI could not generate a response.', error_type: 'content_blocked' }),
    { fallback: 'f', messages: { content_blocked: 'Please try rephrasing it.' } });
  assert.equal(typed.userMessage, 'Please try rephrasing it.');
});

test('status-based wording for session, permission, missing and rate limits', async () => {
  assert.match((await requestErrorFrom(response(401, { error: 'Invalid or expired token', details: 'x' }))).userMessage, /sign in again/);
  assert.match((await requestErrorFrom(response(403, {}))).userMessage, /access/);
  assert.equal((await requestErrorFrom(response(404, { error: 'Verse 2:300 not found' }), { notFound: 'Not here.' })).userMessage, 'Not here.');
  assert.match((await requestErrorFrom(response(429, {}))).userMessage, /wait a minute/);
});

test('userMessage never returns raw error text', () => {
  assert.match(userMessage(new TypeError('Failed to fetch')), /internet connection/);
  assert.equal(userMessage(new RequestError(500, 'Safe text.')), 'Safe text.');
  assert.equal(userMessage(new Error('Firebase: Error (auth/x).'), 'Fallback.'), 'Fallback.');
  assert.equal(userMessage(new Error('Cannot read properties of undefined'), 'Fallback.'), 'Fallback.');
  assert.match(userMessage(Object.assign(new Error('x'), { name: 'AbortError' })), /longer than expected/);
  assert.match(userMessage(authError('auth/network-request-failed'), 'f'), /internet connection/);
  assert.equal(userMessage(null, 'Fallback.'), 'Fallback.');
});

test('isSafeServerText rejects codes, stack traces and markup', () => {
  assert.ok(isSafeServerText('Please narrow your range to 5 verses.'));
  for (const bad of ['verse_range_too_large', 'ValueError: bad', 'see https://x.io', '<b>hi there</b>', 'x'.repeat(401), '', null]) {
    assert.ok(!isSafeServerText(bad), String(bad).slice(0, 30));
  }
});


test('503 has stable retry copy without exposing dependency details', async () => {
  for (const body of [undefined, { error: 'Firestore PermissionDenied projects/private', retry: true }]) {
    const error = await requestErrorFrom(response(503, body), { fallback: 'Other failure.' });
    assert.equal(userMessage(error), 'Tadabbur is temporarily unavailable. Please try again in a moment.');
    assert.doesNotMatch(error.userMessage, LEAKY);
  }
});
