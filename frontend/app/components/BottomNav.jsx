'use client';
import { usePathname, useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';
import { Home, Clock, Star, FileText } from 'lucide-react';

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
      icon: Home,
      path: '/',
      active: pathname === '/'
    },
    {
      label: 'History',
      icon: Clock,
      path: '/history',
      active: pathname === '/history'
    },
    {
      label: 'Saved',
      icon: Star,
      path: '/saved',
      active: pathname === '/saved'
    },
    user && {
      label: 'Notes',
      icon: FileText,
      path: '/annotations',
      active: pathname === '/annotations'
    }
  ].filter(Boolean);

  return (
    <>
      {/* Spacer to prevent content from being hidden behind bottom nav */}
      <div style={{ height: '60px' }} />

      <nav className="bottom-nav">
        {navItems.map((item) => {
          const IconComponent = item.icon;
          return (
            <button
              key={item.path}
              onClick={() => router.push(item.path)}
              className={`nav-item ${item.active ? 'active' : ''}`}
              aria-label={item.label}
              aria-current={item.active ? 'page' : undefined}
            >
              <span className="nav-icon">
                <IconComponent size={22} strokeWidth={item.active ? 2.5 : 2} />
              </span>
              <span className="nav-label">{item.label}</span>
            </button>
          );
        })}

        <style jsx>{`
          .bottom-nav {
            position: fixed;
            bottom: 0;
            left: 0;
            right: 0;
            background: linear-gradient(to top, rgba(255, 255, 255, 0.98), rgba(255, 255, 255, 0.95));
            backdrop-filter: blur(20px);
            -webkit-backdrop-filter: blur(20px);
            border-top: 1px solid var(--border-light, #e5e7eb);
            display: flex;
            justify-content: space-around;
            align-items: center;
            height: 60px;
            z-index: 1000;
            box-shadow: 0 -2px 10px rgba(0, 0, 0, 0.05);
            padding-bottom: env(safe-area-inset-bottom);
          }

          .nav-item {
            flex: 1;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            gap: 4px;
            background: none;
            border: none;
            padding: 8px;
            cursor: pointer;
            color: var(--text-muted, #6b7280);
            transition: all 0.2s ease;
            position: relative;
            min-height: 44px;
          }

          .nav-item:active {
            background: var(--cream, #faf6f0);
          }

          .nav-item.active {
            color: var(--primary-teal, #0d9488);
          }

          .nav-item.active::before {
            content: '';
            position: absolute;
            top: 0;
            left: 50%;
            transform: translateX(-50%);
            width: 32px;
            height: 2px;
            background: var(--primary-teal, #0d9488);
            border-radius: 0 0 2px 2px;
          }

          .nav-icon {
            display: flex;
            align-items: center;
            justify-content: center;
            height: 24px;
          }

          .nav-label {
            font-size: 0.65rem;
            font-weight: 600;
            letter-spacing: 0.02em;
          }

          @media (hover: none) {
            .nav-item:active {
              transform: scale(0.95);
            }
          }

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
