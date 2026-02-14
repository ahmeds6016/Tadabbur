'use client';
import { usePathname, useRouter } from 'next/navigation';
import { Home, BookOpen, Star, FileText } from 'lucide-react';

export default function BottomNav({ user }) {
  const pathname = usePathname();
  const router = useRouter();

  const navItems = [
    {
      label: 'Home',
      icon: Home,
      path: '/',
      active: pathname === '/'
    },
    {
      label: 'Plans',
      icon: BookOpen,
      path: '/plans',
      active: pathname === '/plans'
    },
    {
      label: 'Saved',
      icon: Star,
      path: '/saved',
      active: pathname === '/saved'
    },
    user && {
      label: 'Reflections',
      icon: FileText,
      path: '/annotations',
      active: pathname === '/annotations'
    }
  ].filter(Boolean);

  return (
    <>
      {/* Spacer to prevent content from being hidden behind bottom nav */}
      <div style={{ height: 'var(--nav-height-with-safe, calc(72px + env(safe-area-inset-bottom)))' }} />

      <nav className="bottom-nav">
        {navItems.map((item) => {
          const IconComponent = item.icon;
          return (
            <button
              key={item.path}
              onClick={() => router.push(item.path)}
              className={`nav-item bottom-nav-item ${item.active ? 'active' : ''}`}
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
            left: 50%;
            transform: translateX(-50%);
            width: min(1200px, 100%);
            background: rgba(255, 255, 255, 0.98);
            backdrop-filter: blur(20px);
            -webkit-backdrop-filter: blur(20px);
            border-top: 1px solid var(--border-light, #e5e7eb);
            display: flex;
            justify-content: space-around;
            align-items: center;
            height: var(--nav-height, 72px);
            z-index: var(--z-fixed, 1000);
            box-shadow: 0 -2px 10px rgba(0, 0, 0, 0.05);
            padding-bottom: env(safe-area-inset-bottom);
            border-radius: 16px 16px 0 0;
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
            padding: 10px 8px;
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
              box-shadow: 0 -4px 16px rgba(0, 0, 0, 0.35);
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

          @media (min-width: 1024px) {
            .bottom-nav {
              display: none;
            }
          }
        `}</style>
      </nav>
    </>
  );
}
