const FAILURE_WINDOW_MS = 30_000;

let recentFailures = [];
let backendUnavailable = false;
const listeners = new Set();

function publish(nextValue) {
  if (backendUnavailable === nextValue) return;
  backendUnavailable = nextValue;
  listeners.forEach(listener => listener(backendUnavailable));
}

export function reportBackendFailure() {
  const now = Date.now();
  recentFailures = recentFailures.filter(timestamp => now - timestamp <= FAILURE_WINDOW_MS);
  recentFailures.push(now);
  if (recentFailures.length >= 2) publish(true);
}

export function reportBackendSuccess() {
  recentFailures = [];
  publish(false);
}

export function getBackendUnavailable() {
  return backendUnavailable;
}

export function subscribeBackendHealth(listener) {
  listeners.add(listener);
  listener(backendUnavailable);
  return () => listeners.delete(listener);
}
