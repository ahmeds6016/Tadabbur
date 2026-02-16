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

      {/* Premium Islamic-themed Install Banner */}
      {isInstallable && !isInstalled && (
        <div className="fixed bottom-4 left-4 right-4 md:left-auto md:right-4 md:w-96
                        z-50 animate-slide-up"
             style={{
               background: 'linear-gradient(135deg, #0D9488 0%, #1E3A5F 100%)',
               boxShadow: '0 8px 32px rgba(30, 58, 95, 0.25)',
               borderRadius: '12px',
               border: '1px solid rgba(212, 175, 55, 0.2)'
             }}>

          {/* Gold accent line at top */}
          <div className="h-0.5 bg-gradient-to-r from-transparent via-[#D4AF37] to-transparent"></div>

          <div className="p-4">
            <div className="flex items-center justify-between">
              <div className="flex-1">
                <div className="flex items-center gap-2">
                  
                  <p className="font-semibold text-white">Install Tadabbur</p>
                </div>
                <p className="text-xs text-white/90 mt-1">
                  Quick access to Quranic commentary
                </p>
              </div>
              <div className="flex gap-2 ml-4">
                <button
                  onClick={handleInstallClick}
                  className="px-4 py-2 rounded-md text-sm font-medium
                           transition-all duration-200 transform hover:scale-105"
                  style={{
                    background: 'linear-gradient(135deg, #D4AF37 0%, #F4E4C1 100%)',
                    color: '#1E3A5F',
                    boxShadow: '0 2px 8px rgba(212, 175, 55, 0.3)'
                  }}
                >
                  Install
                </button>
                <button
                  onClick={() => setIsInstallable(false)}
                  className="text-white/80 hover:text-white p-2 transition-colors"
                  aria-label="Close"
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
            </div>

            {/* iOS Instructions with Islamic design */}
            {/iPhone|iPad|iPod/.test(navigator.userAgent) && (
              <div className="mt-3 pt-3 border-t border-[#D4AF37]/20 text-xs">
                <p className="text-white/90">
                  <span className="text-[#F4E4C1]">iOS Users:</span> Tap{' '}
                  <span className="inline-flex items-center mx-1">
                    <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 24 24">
                      <path d="M12 2L10.6985 3.20267L2 11.292V19.9651C2 20.5264 2.44689 20.9732 3.00761 20.9732H8.99239C9.55311 20.9732 10 20.5264 10 19.9651V14.9732H14V19.9651C14 20.5264 14.4469 20.9732 15.0076 20.9732H20.9924C21.5531 20.9732 22 20.5264 22 19.9651V11.292L13.3015 3.20267L12 2Z"/>
                    </svg>
                  </span>
                  then "Add to Home Screen"
                </p>
              </div>
            )}
          </div>
        </div>
      )}

    </>
  );
}