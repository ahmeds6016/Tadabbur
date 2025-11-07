/**
 * Tafsir Simplified - Minimal Service Worker for PWA Installation
 *
 * This minimal service worker enables PWA installation ("Add to Home Screen")
 * without offline functionality, since the app requires backend API access.
 */

const VERSION = 'v1.0.0';

// Install event - called when service worker is first installed
self.addEventListener('install', (event) => {
  console.log('[Tafsir PWA] Service Worker installed:', VERSION);
  // Activate immediately without waiting for open tabs to close
  self.skipWaiting();
});

// Activate event - called when service worker takes control
self.addEventListener('activate', (event) => {
  console.log('[Tafsir PWA] Service Worker activated:', VERSION);
  // Take control of all clients immediately
  event.waitUntil(clients.claim());
});

// Fetch event - handle network requests
self.addEventListener('fetch', (event) => {
  // Simply let all requests go through to the network
  // No caching strategy since app requires backend connection
  return;
});

// Optional: Handle messages from the app
self.addEventListener('message', (event) => {
  if (event.data && event.data.type === 'SKIP_WAITING') {
    self.skipWaiting();
  }
});