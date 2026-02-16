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
      <div style={{ height: 'calc(52px + env(safe-area-inset-bottom, 0px))' }} />

      <nav className="bottom-nav">
        <div className="bottom-nav-inner">
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
                <IconComponent size={22} strokeWidth={item.active ? 2.5 : 1.8} />
                <span className="nav-label">{item.label}</span>
              </button>
            );
          })}
        </div>

        <style jsx>{`
          .bottom-nav {
            position: fixed;
            bottom: 0;
            left: 0;
            right: 0;
            z-index: 1000;
            /* Background extends all the way to the bottom edge including safe area */
            background: rgba(255, 255, 255, 0.98);
            backdrop-filter: blur(20px);
            -webkit-backdrop-filter: blur(20px);
            border-top: 0.5px solid rgba(0, 0, 0, 0.12);
            /* Total height = nav + safe area. padding-bottom pushes the bg to the edge. */
            padding-bottom: env(safe-area-inset-bottom, 0px);
            -webkit-tap-highlight-color: transparent;
          }

          .bottom-nav-inner {
            display: flex;
            justify-content: space-around;
            align-items: stretch;
            height: 52px;
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
            padding: 0;
            cursor: pointer;
            color: #8e8e93;
            transition: color 0.15s ease;
            user-select: none;
            touch-action: manipulation;
            -webkit-tap-highlight-color: transparent;
          }

          .nav-item.active {
            color: #1a1a1a;
          }

          .nav-label {
            font-size: 10px;
            font-weight: 500;
            line-height: 1;
          }

          .nav-item.active .nav-label {
            font-weight: 600;
          }

          @media (prefers-color-scheme: dark) {
            .bottom-nav {
              background: rgba(0, 0, 0, 0.95);
              border-top-color: rgba(255, 255, 255, 0.1);
            }

            .nav-item {
              color: #636366;
            }

            .nav-item.active {
              color: #ffffff;
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
