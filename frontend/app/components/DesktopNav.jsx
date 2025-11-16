'use client';
import { useState, useEffect } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';

export default function DesktopNav({ user, stats = {}, collapsed = false, onToggleCollapse }) {
  const pathname = usePathname();
  const [tooltipVisible, setTooltipVisible] = useState(null);

  const navItems = [
    {
      id: 'home',
      label: 'Home',
      icon: '🏠',
      href: '/',
      shortcut: 'Alt+H',
      description: 'Search and explore Tafsir'
    },
    {
      id: 'history',
      label: 'History',
      icon: '📜',
      href: '/history',
      shortcut: 'Alt+R',
      description: `${stats.historyCount || 0} recent queries`,
      badge: stats.historyCount
    },
    {
      id: 'saved',
      label: 'Saved',
      icon: '⭐',
      href: '/saved',
      shortcut: 'Alt+S',
      description: `${stats.savedCount || 0} saved answers`,
      badge: stats.savedCount
    },
    {
      id: 'notes',
      label: 'Notes',
      icon: '📝',
      href: '/annotations',
      shortcut: 'Alt+N',
      description: `${stats.annotationCount || 0} reflections`,
      badge: stats.annotationCount
    }
  ];

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.altKey) {
        switch(e.key.toLowerCase()) {
          case 'h':
            e.preventDefault();
            window.location.href = '/';
            break;
          case 'r':
            e.preventDefault();
            window.location.href = '/history';
            break;
          case 's':
            e.preventDefault();
            window.location.href = '/saved';
            break;
          case 'n':
            e.preventDefault();
            window.location.href = '/annotations';
            break;
          case 'b':
            e.preventDefault();
            onToggleCollapse?.();
            break;
        }
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [onToggleCollapse]);

  return (
    <nav className={`desktop-nav ${collapsed ? 'collapsed' : ''}`}>
      <div className="nav-header">
        <button
          className="collapse-btn"
          onClick={onToggleCollapse}
          title={collapsed ? 'Expand sidebar (Alt+B)' : 'Collapse sidebar (Alt+B)'}
          aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
        >
          {collapsed ? '→' : '←'}
        </button>
        {!collapsed && (
          <div className="nav-title">
            <span className="nav-logo">📖</span>
            <span className="nav-text">Tafsir Simplified</span>
          </div>
        )}
      </div>

      <div className="nav-items">
        {navItems.map((item) => {
          const isActive = pathname === item.href;
          return (
            <Link
              key={item.id}
              href={item.href}
              className={`nav-item ${isActive ? 'active' : ''}`}
              onMouseEnter={() => setTooltipVisible(item.id)}
              onMouseLeave={() => setTooltipVisible(null)}
              title={collapsed ? `${item.label} - ${item.description}` : ''}
            >
              <span className="nav-icon">{item.icon}</span>
              {!collapsed && (
                <>
                  <span className="nav-label">{item.label}</span>
                  {item.badge > 0 && (
                    <span className="nav-badge">{item.badge > 99 ? '99+' : item.badge}</span>
                  )}
                </>
              )}
              {collapsed && tooltipVisible === item.id && (
                <div className="nav-tooltip">
                  <strong>{item.label}</strong>
                  <small>{item.description}</small>
                  <kbd>{item.shortcut}</kbd>
                </div>
              )}
            </Link>
          );
        })}
      </div>

      {user && (
        <div className="nav-footer">
          <div className="user-section">
            <div className="user-avatar">
              {user.photoURL ? (
                <img src={user.photoURL} alt={user.displayName || 'User'} />
              ) : (
                <span>{(user.displayName || user.email || 'U')[0].toUpperCase()}</span>
              )}
            </div>
            {!collapsed && (
              <div className="user-info">
                <div className="user-name">{user.displayName || 'User'}</div>
                <div className="user-email">{user.email}</div>
              </div>
            )}
          </div>
          {!collapsed && (
            <div className="nav-shortcuts">
              <div className="shortcut-title">Keyboard Shortcuts</div>
              <div className="shortcut-list">
                <div><kbd>Alt+H</kbd> Home</div>
                <div><kbd>Alt+S</kbd> Saved</div>
                <div><kbd>Alt+B</kbd> Toggle Sidebar</div>
                <div><kbd>Ctrl+K</kbd> Search</div>
                <div><kbd>Esc</kbd> Clear Results</div>
              </div>
            </div>
          )}
        </div>
      )}

      <style jsx>{`
        .desktop-nav {
          position: fixed;
          left: 0;
          top: 0;
          bottom: 0;
          width: 260px;
          background: linear-gradient(180deg, var(--cream) 0%, #faf6f0 100%);
          border-right: 2px solid var(--border-light);
          display: flex;
          flex-direction: column;
          transition: width 0.3s ease;
          z-index: 100;
          box-shadow: 2px 0 8px rgba(0, 0, 0, 0.05);
        }

        .desktop-nav.collapsed {
          width: 70px;
        }

        .nav-header {
          padding: 20px;
          border-bottom: 1px solid var(--border-light);
          display: flex;
          align-items: center;
          gap: 12px;
          min-height: 70px;
        }

        .collapse-btn {
          width: 30px;
          height: 30px;
          border-radius: 8px;
          border: 1px solid var(--border-light);
          background: white;
          cursor: pointer;
          display: flex;
          align-items: center;
          justify-content: center;
          font-size: 14px;
          transition: all 0.2s ease;
        }

        .collapse-btn:hover {
          background: var(--gold);
          color: white;
          border-color: var(--gold);
        }

        .nav-title {
          display: flex;
          align-items: center;
          gap: 10px;
          flex: 1;
        }

        .nav-logo {
          font-size: 1.5rem;
        }

        .nav-text {
          font-weight: 700;
          color: var(--primary-teal);
          font-size: 1.1rem;
        }

        .nav-items {
          flex: 1;
          padding: 20px 12px;
          overflow-y: auto;
        }

        .nav-item {
          display: flex;
          align-items: center;
          gap: 14px;
          padding: 12px 16px;
          border-radius: 12px;
          margin-bottom: 8px;
          text-decoration: none;
          color: var(--deep-blue);
          transition: all 0.2s ease;
          position: relative;
          cursor: pointer;
        }

        .collapsed .nav-item {
          justify-content: center;
          padding: 12px 8px;
        }

        .nav-item:hover {
          background: rgba(16, 185, 129, 0.1);
          transform: translateX(2px);
        }

        .nav-item.active {
          background: linear-gradient(135deg, var(--primary-teal), var(--gold));
          color: white;
          box-shadow: 0 4px 12px rgba(16, 185, 129, 0.3);
        }

        .nav-icon {
          font-size: 1.3rem;
          width: 24px;
          text-align: center;
        }

        .nav-label {
          flex: 1;
          font-weight: 500;
          font-size: 0.95rem;
        }

        .nav-badge {
          background: var(--gold);
          color: var(--deep-blue);
          padding: 2px 8px;
          border-radius: 12px;
          font-size: 0.75rem;
          font-weight: 600;
          min-width: 24px;
          text-align: center;
        }

        .nav-item.active .nav-badge {
          background: white;
          color: var(--primary-teal);
        }

        .nav-tooltip {
          position: absolute;
          left: calc(100% + 10px);
          top: 50%;
          transform: translateY(-50%);
          background: var(--deep-blue);
          color: white;
          padding: 8px 12px;
          border-radius: 8px;
          white-space: nowrap;
          z-index: 1000;
          box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
          font-size: 0.85rem;
          display: flex;
          flex-direction: column;
          gap: 4px;
        }

        .nav-tooltip strong {
          display: block;
          margin-bottom: 2px;
        }

        .nav-tooltip small {
          opacity: 0.9;
          font-size: 0.8rem;
        }

        .nav-tooltip kbd {
          background: rgba(255, 255, 255, 0.2);
          padding: 2px 4px;
          border-radius: 3px;
          font-family: monospace;
          font-size: 0.75rem;
          margin-top: 4px;
        }

        .nav-footer {
          border-top: 1px solid var(--border-light);
          padding: 16px;
          background: white;
        }

        .user-section {
          display: flex;
          align-items: center;
          gap: 12px;
          margin-bottom: 16px;
        }

        .collapsed .user-section {
          justify-content: center;
        }

        .user-avatar {
          width: 36px;
          height: 36px;
          border-radius: 50%;
          background: var(--gradient-teal-gold);
          display: flex;
          align-items: center;
          justify-content: center;
          color: white;
          font-weight: 600;
          overflow: hidden;
          flex-shrink: 0;
        }

        .user-avatar img {
          width: 100%;
          height: 100%;
          object-fit: cover;
        }

        .user-info {
          flex: 1;
          min-width: 0;
        }

        .user-name {
          font-weight: 600;
          font-size: 0.9rem;
          color: var(--deep-blue);
          white-space: nowrap;
          overflow: hidden;
          text-overflow: ellipsis;
        }

        .user-email {
          font-size: 0.75rem;
          color: #666;
          white-space: nowrap;
          overflow: hidden;
          text-overflow: ellipsis;
        }

        .nav-shortcuts {
          margin-top: 16px;
          padding-top: 16px;
          border-top: 1px solid var(--border-light);
        }

        .shortcut-title {
          font-size: 0.75rem;
          font-weight: 600;
          color: #999;
          text-transform: uppercase;
          margin-bottom: 8px;
        }

        .shortcut-list {
          display: flex;
          flex-direction: column;
          gap: 4px;
        }

        .shortcut-list div {
          font-size: 0.8rem;
          color: #666;
          display: flex;
          align-items: center;
          gap: 8px;
        }

        .shortcut-list kbd {
          background: var(--cream);
          padding: 2px 6px;
          border-radius: 4px;
          border: 1px solid var(--border-light);
          font-family: monospace;
          font-size: 0.7rem;
          color: var(--deep-blue);
          min-width: 40px;
          text-align: center;
        }

        /* Hide on mobile */
        @media (max-width: 768px) {
          .desktop-nav {
            display: none;
          }
        }
      `}</style>
    </nav>
  );
}