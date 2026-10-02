'use client';

import { useEffect, useState } from 'react';

export default function PWAProvider({ children }) {
  const [isInstallable, setIsInstallable] = useState(false);
  const [deferredPrompt, setDeferredPrompt] = useState(null);
  const [isInstalled, setIsInstalled] = useState(false);

  useEffect(() => {
    // Register service worker
    if ('serviceWorker' in navigator && typeof window !== 'undefined') {
      window.addEventListener('load', () => {
        navigator.serviceWorker
          .register('/sw.js')
          .catch(() => {
            // Service worker registration failed silently
          });
      });
    }

    // Check if already installed
    if (window.matchMedia('(display-mode: standalone)').matches) {
      setIsInstalled(true);
    }

    // Listen for install prompt
    const handleBeforeInstallPrompt = (e) => {
      e.preventDefault();
      setDeferredPrompt(e);
      setIsInstallable(true);
    };

    window.addEventListener('beforeinstallprompt', handleBeforeInstallPrompt);

    // Check if app was just installed
    window.addEventListener('appinstalled', () => {
      setIsInstalled(true);
      setIsInstallable(false);
      setDeferredPrompt(null);
    });

    return () => {
      window.removeEventListener('beforeinstallprompt', handleBeforeInstallPrompt);
    };
  }, []);

  const handleInstallClick = async () => {
    if (!deferredPrompt) return;

    // Show the install prompt
    deferredPrompt.prompt();

    // Wait for the user to respond
    await deferredPrompt.userChoice;

    // Clean up
    setDeferredPrompt(null);
    setIsInstallable(false);
  };

  return (
    <>
      {children}

      {isInstallable && !isInstalled && (
        <aside className="install-banner" aria-label="Install Tadabbur">
          <div className="install-banner-text">
            <p className="install-banner-title">Install Tadabbur</p>
            <p className="install-banner-subtitle">Open the commentary directly from your home screen.</p>
          </div>
          <div className="install-banner-actions">
            <button type="button" className="install-banner-install" onClick={handleInstallClick}>
              Install
            </button>
            <button type="button" className="install-banner-dismiss" onClick={() => setIsInstallable(false)}>
              Not now
            </button>
          </div>
        </aside>
      )}
    </>
  );
}