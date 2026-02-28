'use client';
import { useState, useEffect } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { Home, BookOpen as PlansIcon, Star, FileText, BarChart3, BookOpen, BookHeart, ChevronLeft, ChevronRight } from 'lucide-react';

export default function DesktopNav({ user, stats = {}, collapsed = false, onToggleCollapse }) {
  const pathname = usePathname();
  const [tooltipVisible, setTooltipVisible] = useState(null);

  const navItems = [
    {
      id: 'home',
      label: 'Home',
      icon: Home,
      href: '/',
      shortcut: 'Alt+H',
      description: 'Search and explore Tafsir'
    },
    {
      id: 'plans',
      label: 'Plans',
      icon: PlansIcon,
      href: '/plans',
      shortcut: 'Alt+R',
      description: 'Reading plans and progress'
    },
    {
      id: 'saved',
      label: 'Saved',
      icon: Star,
      href: '/saved',
      shortcut: 'Alt+S',
      description: `${stats.savedCount || 0} saved answers`,
      badge: stats.savedCount
    },
    {
      id: 'journal',
      label: 'Journal',
      icon: BookHeart,
      href: '/journal',
      shortcut: 'Alt+J',
      description: 'Spiritual journal & Iman Index'
    },
    {
      id: 'notes',
      label: 'Reflections',
      icon: FileText,
      href: '/annotations',
      shortcut: 'Alt+N',
      description: `${stats.annotationCount || 0} reflections`,
      badge: stats.annotationCount
    },
    {
      id: 'progress',
      label: 'Progress',
      icon: BarChart3,
      href: '/progress',
      shortcut: 'Alt+P',
      description: 'Your Quran journey'
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
            window.location.href = '/plans';
            break;
          case 's':
            e.preventDefault();
            window.location.href = '/saved';
            break;
          case 'j':
            e.preventDefault();
            window.location.href = '/journal';
            break;
          case 'n':
            e.preventDefault();
            window.location.href = '/annotations';
            break;
          case 'p':
            e.preventDefault();
            window.location.href = '/progress';
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
          {collapsed ? <ChevronRight size={16} /> : <ChevronLeft size={16} />}
        </button>
        {!collapsed && (
          <div className="nav-title">
            <span className="nav-logo">
              <BookOpen size={24} strokeWidth={2} />
            </span>
            <span className="nav-text">Tadabbur</span>
          </div>
        )}
      </div>

      <div className="nav-items">
        {navItems.map((item) => {
          const isActive = pathname === item.href;
          const IconComponent = item.icon;
          return (
            <Link
              key={item.id}
              href={item.href}
              className={`nav-item ${isActive ? 'active' : ''}`}
              onMouseEnter={() => setTooltipVisible(item.id)}
              onMouseLeave={() => setTooltipVisible(null)}
              title={collapsed ? `${item.label} - ${item.description}` : ''}
            >
              <span className="nav-icon">
                <IconComponent size={20} strokeWidth={isActive ? 2.5 : 2} />
              </span>
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
        </div>
      )}

      <style jsx>{`
        .desktop-nav {
          position: fixed;
          left: 0;
          top: 0;
          bottom: 0;
          width: 260px;
          background: var(--cream, #FAF6F0);
          border-right: 1px solid var(--border-light);
          display: flex;
          flex-direction: column;
          transition: width 0.3s ease;
          z-index: 100;
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
          background: var(--background, #FDFBF7);
          cursor: pointer;
          display: flex;
          align-items: center;
          justify-content: center;
          transition: all 0.2s ease;
          color: var(--text-muted, #6b7280);
        }

        .collapse-btn:hover {
          background: var(--primary-teal);
          color: white;
          border-color: var(--primary-teal);
        }

        .nav-title {
          display: flex;
          align-items: center;
          gap: 10px;
          flex: 1;
        }

        .nav-logo {
          color: var(--primary-teal);
          display: flex;
          align-items: center;
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
          background: rgba(13, 148, 136, 0.08);
        }

        .nav-item.active {
          background: var(--primary-teal);
          color: white;
          box-shadow: 0 2px 8px rgba(13, 148, 136, 0.25);
        }

        .nav-icon {
          width: 24px;
          display: flex;
          align-items: center;
          justify-content: center;
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
          background: var(--background, #FDFBF7);
        }

        .user-section {
          display: flex;
          align-items: center;
          gap: 12px;
        }

        .collapsed .user-section {
          justify-content: center;
        }

        .user-avatar {
          width: 36px;
          height: 36px;
          border-radius: 50%;
          background: var(--primary-teal);
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
          color: var(--text-muted, #6b7280);
          white-space: nowrap;
          overflow: hidden;
          text-overflow: ellipsis;
        }

        /* Hide on mobile */
        @media (max-width: 1024px) {
          .desktop-nav {
            display: none;
          }
        }
      `}</style>
    </nav>
  );
}
