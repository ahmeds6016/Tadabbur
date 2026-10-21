/**
 * The single place that decides what a reader is told when something fails.
 *
 * Never render `err.message`: Firebase messages read "Firebase: Error (auth/...)", fetch
 * failures read "Failed to fetch", and many backend 500s carry raw exception text.
 */

const CONNECTION =
  "We couldn't reach Tadabbur. Please check your internet connection and try again.";

// Sign-in deliberately gives one answer whether the email is unknown or the password is
// wrong, so the form cannot be used to discover who has an account.
const BAD_CREDENTIALS =
  "That email and password don't match. Please check them and try again, or reset your password.";
const VERIFICATION =
  "We couldn't verify this request. Please refresh the page and try again.";

const AUTH_MESSAGES = {
  'auth/invalid-credential': BAD_CREDENTIALS,
  'auth/invalid-login-credentials': BAD_CREDENTIALS,
  'auth/wrong-password': BAD_CREDENTIALS,
  'auth/user-not-found': BAD_CREDENTIALS,
  'auth/invalid-email': 'Please enter a valid email address.',
  'auth/missing-email': 'Please enter your email address.',
  'auth/missing-password': 'Please enter your password.',
  'auth/email-already-in-use': 'An account with this email already exists. Please sign in instead.',
  'auth/weak-password': 'Please choose a stronger password of at least 6 characters.',
  'auth/password-does-not-meet-requirements':
    "That password doesn't meet the requirements. Please choose a longer, stronger password.",
  'auth/user-disabled': 'This account has been disabled.',
  'auth/too-many-requests':
    'Too many attempts. For your security, please wait a few minutes before trying again, or reset your password.',
  'auth/network-request-failed': CONNECTION,
  'auth/operation-not-allowed':
    'Signing in with email is unavailable at the moment. Please try again later.',
  'auth/requires-recent-login': 'For your security, please sign in again to continue.',
  'auth/captcha-check-failed': VERIFICATION,
  'auth/invalid-recaptcha-token': VERIFICATION,
  'auth/missing-recaptcha-token': VERIFICATION,
  'auth/invalid-recaptcha-action': VERIFICATION,
  'auth/invalid-recaptcha-version': VERIFICATION,
  'auth/recaptcha-not-enabled': VERIFICATION,
  'auth/missing-client-type': VERIFICATION,
};

const AUTH_FALLBACK = {
  signIn: "We couldn't sign you in just now. Please try again.",
  signUp: "We couldn't create your account just now. Please try again.",
  reset: "We couldn't send the reset email just now. Please try again.",
};

/** Plain-language message for a Firebase Auth error. `action`: signIn | signUp | reset. */
export function authErrorMessage(err, action = 'signIn') {
  return AUTH_MESSAGES[err?.code] || AUTH_FALLBACK[action] || AUTH_FALLBACK.signIn;
}

/** Password reset must not reveal whether an email has an account. */
export function isUnknownAccountError(err) {
  return err?.code === 'auth/user-not-found';
}

/** An HTTP failure carrying a message that is safe to show. */
export class RequestError extends Error {
  constructor(status, userMessage, errorType) {
    super(userMessage);
    this.name = 'RequestError';
    this.status = status;
    this.userMessage = userMessage;
    this.errorType = errorType;
  }
}

const TECHNICAL = /traceback|exception|errno|firestore|firebase|google|grpc|stack|undefined|null|nan\b|\binternal\b|https?:|projects\/|\.py\b|\.jsx?\b|[{}<>[\]]|\b[A-Z][a-z]+Error\b|\(\d{3}\)/i;

/** Server text is shown only if it reads like a sentence written for a reader. */
export function isSafeServerText(text) {
  if (typeof text !== 'string') return false;
  const value = text.trim();
  if (value.length < 8 || value.length > 400) return false;
  if (!/\s/.test(value)) return false; // bare codes such as "verse_range_too_large"
  return !TECHNICAL.test(value);
}

/**
 * Build a RequestError from a failed fetch Response.
 * `context.fallback` is what to say when the server gives nothing usable;
 * `context.notFound` and `context.messages[errorType]` override per screen.
 */
export async function requestErrorFrom(res, context = {}) {
  let body = null;
  try {
    body = await res.json();
  } catch {
    // Not JSON: fall through to status-based wording.
  }
  const errorType = body?.error_type || (typeof body?.error === 'string' && !/\s/.test(body.error) ? body.error : undefined);
  const fallback = context.fallback || 'Something went wrong. Please try again in a moment.';
  const byType = errorType && context.messages?.[errorType];
  if (byType) return new RequestError(res.status, byType, errorType);

  let message;
  if (res.status === 401) message = 'Your session has ended. Please sign in again.';
  else if (res.status === 403) message = "You don't have access to that.";
  else if (res.status === 404) message = context.notFound || fallback;
  else if (res.status === 429) message = 'You are sending requests faster than we can answer. Please wait a minute and try again.';
  else if (res.status === 503) message = 'Tadabbur is temporarily unavailable. Please try again in a moment.';
  else if (res.status >= 400 && res.status < 500) {
    // Prefer a written explanation over a code (e.g. verse_range_too_large carries `message`).
    message = [body?.message, body?.error].find(isSafeServerText) || fallback;
  } else message = fallback;
  return new RequestError(res.status, message, errorType);
}

/** The message to show for anything caught in a try/catch. Never returns raw error text. */
export function userMessage(err, fallback = 'Something went wrong. Please try again in a moment.') {
  if (err instanceof RequestError) return err.userMessage;
  if (err instanceof TypeError) return CONNECTION; // fetch() network failure
  if (err?.name === 'AbortError' || err?.name === 'TimeoutError') {
    return 'This is taking longer than expected. Please try again.';
  }
  if (typeof err?.code === 'string' && err.code.startsWith('auth/')) {
    return AUTH_MESSAGES[err.code] || fallback;
  }
  return fallback;
}
