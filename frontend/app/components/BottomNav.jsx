'use client';
import { usePathname, useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';

export default function BottomNav({ user }) {
  const pathname = usePathname();
  const router = useRouter();
  const [isMobile, setIsMobile] = useState(false);

  useEffect(() => {
    const checkMobile = () => {
      setIsMobile(window.innerWidth <= 768);
    };
    checkMobile();
    window.addEventListener('resize', checkMobile);
    return () => window.removeEventListener('resize', checkMobile);
  }, []);

  // Don't show on desktop
  if (!isMobile) return null;

  const navItems = [
    {
      label: 'Home',
      icon: '🏠',
      path: '/',
      active: pathname === '/'
    },
    {
      label: 'History',
      icon: '🕒',
      path: '/history',
      active: pathname === '/history'
    },
    {
      label: 'Saved',
      icon: '⭐',
      path: '/saved',
      active: pathname === '/saved'
    },
    user && {
      label: 'Notes',
      icon: '📝',
      path: '/annotations',
      active: pathname === '/annotations'
    }
  ].filter(Boolean);

  return (
    <>
      {/* Spacer to prevent content from being hidden behind bottom nav */}
      <div style={{ height: '60px' }} />

      <nav className="bottom-nav">
        {navItems.map((item) => (
          <button
            key={item.path}
            onClick={() => router.push(item.path)}
            className={`nav-item ${item.active ? 'active' : ''}`}
            aria-label={item.label}
            aria-current={item.active ? 'page' : undefined}
          >
            <span className="nav-icon">{item.icon}</span>
            <span className="nav-label">{item.label}</span>
          </button>
        ))}

        <style jsx>{`
          .bottom-nav {
            position: fixed;
            bottom: 0;
            left: 0;
            right: 0;
            background: linear-gradient(to top, rgba(255, 255, 255, 0.98), rgba(255, 255, 255, 0.95));
            backdrop-filter: blur(20px);
            -webkit-backdrop-filter: blur(20px);
            border-top: 3px solid #10b981;
            display: flex;
            justify-content: space-around;
            align-items: center;
            height: 60px;
            z-index: 1000;
            box-shadow: 0 -4px 20px rgba(0, 0, 0, 0.15),
                        0 -2px 6px rgba(16, 185, 129, 0.2);
            padding-bottom: env(safe-area-inset-bottom);
          }

          .bottom-nav::before {
            content: '';
            position: absolute;
            top: -3px;
            left: 0;
            right: 0;
            height: 3px;
            background: linear-gradient(90deg,
              #10b981 0%,
              #fbbf24 50%,
              #10b981 100%);
            box-shadow: 0 0 10px rgba(16, 185, 129, 0.5);
          }

          .nav-item {
            flex: 1;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            gap: 2px;
            background: none;
            border: none;
            padding: 8px;
            cursor: pointer;
            color: #6b7280;
            transition: all 0.2s;
            position: relative;
            min-height: 44px; /* iOS touch target size */
          }

          .nav-item:active {
            background: #f3f4f6;
          }

          .nav-item.active {
            color: #10b981;
          }

          .nav-item.active::before {
            content: '';
            position: absolute;
            top: 0;
            left: 50%;
            transform: translateX(-50%);
            width: 40px;
            height: 2px;
            background: #10b981;
            border-radius: 0 0 2px 2px;
          }

          .nav-icon {
            font-size: 1.25rem;
            line-height: 1;
          }

          .nav-label {
            font-size: 0.625rem;
            font-weight: 500;
            margin-top: 2px;
          }

          /* Haptic feedback simulation on touch */
          @media (hover: none) {
            .nav-item:active {
              transform: scale(0.95);
            }
          }

          /* Dark mode support */
          @media (prefers-color-scheme: dark) {
            .bottom-nav {
              background: #1f2937;
              border-top-color: #374151;
            }

            .nav-item {
              color: #9ca3af;
            }

            .nav-item.active {
              color: #10b981;
            }

            .nav-item:active {
              background: #374151;
            }
          }

          /* PWA standalone mode optimizations */
          @media all and (display-mode: standalone) {
            .bottom-nav {
              padding-bottom: calc(env(safe-area-inset-bottom) + 8px);
            }
          }
        `}</style>
      </nav>
    </>
  );
}