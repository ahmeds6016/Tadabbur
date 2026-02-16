'use client';
import { useState, useEffect, useRef } from 'react';

export default function TabNavigation({
  children,
  tabs = [],
  defaultTab = 0,
  storageKey = 'selected-tab',
  resetKey = null,
  onReflect = null,       // (sectionName) => void — reflect on current section
  onReflectAll = null,    // () => void — reflect on entire response
}) {
  const [activeTab, setActiveTab] = useState(() => {
    if (typeof window === 'undefined') return defaultTab;
    const saved = localStorage.getItem(storageKey);
    return saved !== null ? parseInt(saved) : defaultTab;
  });

  // Track viewed sections
  const [viewedSections, setViewedSections] = useState(() => {
    if (typeof window === 'undefined') return new Set();
    const saved = localStorage.getItem(`${storageKey}-viewed`);
    return saved ? new Set(JSON.parse(saved)) : new Set();
  });

  // Overflow menu state for reflect
  const [showReflectMenu, setShowReflectMenu] = useState(false);
  const menuRef = useRef(null);

  // Close overflow menu on outside click
  useEffect(() => {
    if (!showReflectMenu) return;
    const handler = (e) => {
      if (menuRef.current && !menuRef.current.contains(e.target)) {
        setShowReflectMenu(false);
      }
    };
    document.addEventListener('mousedown', handler);
    document.addEventListener('touchstart', handler);
    return () => {
      document.removeEventListener('mousedown', handler);
      document.removeEventListener('touchstart', handler);
    };
  }, [showReflectMenu]);

  // Check if we're on mobile
  const [isMobile, setIsMobile] = useState(false);
  useEffect(() => {
    const checkMobile = () => {
      setIsMobile(window.innerWidth <= 768);
    };
    checkMobile();
    window.addEventListener('resize', checkMobile);
    return () => window.removeEventListener('resize', checkMobile);
  }, []);

  // Save active tab to localStorage
  useEffect(() => {
    if (typeof window !== 'undefined') {
      localStorage.setItem(storageKey, activeTab.toString());
    }
  }, [activeTab, storageKey]);

  // Reset viewed sections AND active tab when resetKey changes (new query)
  useEffect(() => {
    if (resetKey && typeof window !== 'undefined') {
      setViewedSections(new Set());
      localStorage.removeItem(`${storageKey}-viewed`);
      // Reset to first tab (verses first)
      setActiveTab(0);
      localStorage.setItem(storageKey, '0');
    }
  }, [resetKey, storageKey]);

  // Filter out empty tabs (sections with no content)
  const validTabs = tabs.filter(tab => tab.content);

  // Get current section name for reflect
  const currentSectionName = validTabs[activeTab]?.sectionName || validTabs[activeTab]?.label || '';

  // Three-dot icon for overflow menu
  const dotsIcon = (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
      <circle cx="12" cy="5" r="2"/>
      <circle cx="12" cy="12" r="2"/>
      <circle cx="12" cy="19" r="2"/>
    </svg>
  );

  // Track which desktop section has its menu open
  const [openDesktopMenu, setOpenDesktopMenu] = useState(null);
  const desktopMenuRef = useRef(null);

  // Close desktop overflow menu on outside click
  useEffect(() => {
    if (openDesktopMenu === null) return;
    const handler = (e) => {
      if (desktopMenuRef.current && !desktopMenuRef.current.contains(e.target)) {
        setOpenDesktopMenu(null);
      }
    };
    document.addEventListener('mousedown', handler);
    document.addEventListener('touchstart', handler);
    return () => {
      document.removeEventListener('mousedown', handler);
      document.removeEventListener('touchstart', handler);
    };
  }, [openDesktopMenu]);

  // Don't use tabs on desktop - show all content with section labels
  if (!isMobile) {
    return (
      <div className="desktop-sections">
        {validTabs.map((tab, index) => (
          <section key={index} className="desktop-section" aria-label={tab.label}>
            <header className="desktop-section-header">
              <div style={{ display: 'flex', alignItems: 'center', gap: 10, flex: 1 }}>
                <span className="tab-icon">{tab.icon}</span>
                <h2 className="tab-label">{tab.label}</h2>
              </div>
              {onReflect && tab.sectionName && (
                <div className="section-dots-area" ref={openDesktopMenu === index ? desktopMenuRef : null}>
                  <button
                    className="section-dots-btn"
                    onClick={() => setOpenDesktopMenu(openDesktopMenu === index ? null : index)}
                    title="More options"
                    aria-label="More options"
                  >
                    {dotsIcon}
                  </button>
                  {openDesktopMenu === index && (
                    <div className="section-dots-menu">
                      <button
                        className="section-dots-menu-item"
                        onClick={() => {
                          setOpenDesktopMenu(null);
                          onReflect(tab.sectionName);
                        }}
                      >
                        Reflect on {tab.label}
                      </button>
                      {onReflectAll && (
                        <button
                          className="section-dots-menu-item"
                          onClick={() => {
                            setOpenDesktopMenu(null);
                            onReflectAll();
                          }}
                        >
                          Reflect on entire response
                        </button>
                      )}
                    </div>
                  )}
                </div>
              )}
            </header>
            <div className="desktop-section-body">
              {tab.content}
            </div>
          </section>
        ))}

        <style jsx>{`
          .desktop-sections {
            display: flex;
            flex-direction: column;
            gap: 24px;
          }

          .desktop-section {
            background: white;
            border: 1px solid #e5e7eb;
            border-radius: 16px;
            box-shadow: 0 1px 4px rgba(0, 0, 0, 0.06);
            padding: 20px 24px;
          }

          .desktop-section-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 10px;
            margin-bottom: 12px;
          }

          .desktop-section-header .tab-icon {
            font-size: 1.4rem;
          }

          .desktop-section-header .tab-label {
            font-size: 1.1rem;
            font-weight: 700;
            color: #065f46;
            margin: 0;
          }

          .section-dots-area {
            position: relative;
          }

          .section-dots-btn {
            display: flex;
            align-items: center;
            justify-content: center;
            width: 32px;
            height: 32px;
            background: #f3f4f6;
            border: 1px solid #e5e7eb;
            border-radius: 8px;
            color: #6b7280;
            cursor: pointer;
            transition: all 0.15s ease;
          }

          .section-dots-btn:hover {
            background: #e5e7eb;
            color: #374151;
          }

          .section-dots-menu {
            position: absolute;
            top: 100%;
            right: 0;
            margin-top: 4px;
            background: white;
            border: 1px solid #e5e7eb;
            border-radius: 10px;
            box-shadow: 0 4px 16px rgba(0, 0, 0, 0.12);
            min-width: 200px;
            z-index: 100;
            overflow: hidden;
          }

          .section-dots-menu-item {
            display: block;
            width: 100%;
            padding: 10px 16px;
            background: none;
            border: none;
            text-align: left;
            cursor: pointer;
            transition: background 0.15s ease;
            font-size: 0.82rem;
            color: #374151;
            font-weight: 500;
          }

          .section-dots-menu-item:hover {
            background: #f5f3ff;
            color: #7c3aed;
          }

          .section-dots-menu-item + .section-dots-menu-item {
            border-top: 1px solid #f3f4f6;
          }

          .desktop-section-body {
            margin-top: 8px;
          }
        `}</style>
      </div>
    );
  }

  // Mobile tab interface
  return (
    <div className="tab-navigation">
      {/* Tab Headers */}
      <div className="tab-header-container">
        <div className="tab-headers">
          {validTabs.map((tab, index) => (
            <button
              key={index}
              className={`tab-header ${activeTab === index ? 'active' : ''}`}
              onClick={() => {
                setActiveTab(index);
                // Mark section as viewed
                const sectionKey = `${storageKey}-${index}`;
                if (!viewedSections.has(sectionKey)) {
                  const newViewed = new Set(viewedSections);
                  newViewed.add(sectionKey);
                  setViewedSections(newViewed);
                  if (typeof window !== 'undefined') {
                    localStorage.setItem(`${storageKey}-viewed`, JSON.stringify([...newViewed]));
                  }
                }
              }}
              aria-selected={activeTab === index}
              role="tab"
            >
              <span className="tab-icon">{tab.icon}</span>
              <span className="tab-label">{tab.label}</span>
              {tab.count !== undefined && tab.count > 0 && !viewedSections.has(`${storageKey}-${index}`) && (
                <span className="tab-count">{tab.count}</span>
              )}
            </button>
          ))}

          {/* Three-dot overflow menu for reflect */}
          {onReflect && (currentSectionName || onReflectAll) && (
            <div className="tab-dots-area" ref={menuRef}>
              <button
                className="tab-dots-btn"
                onClick={() => {
                  if (currentSectionName && onReflectAll) {
                    setShowReflectMenu(!showReflectMenu);
                  } else if (currentSectionName) {
                    onReflect(currentSectionName);
                  } else if (onReflectAll) {
                    onReflectAll();
                  }
                }}
                title="More options"
                aria-label="More options"
              >
                {dotsIcon}
              </button>

              {showReflectMenu && (
                <div className="reflect-menu">
                  {currentSectionName && (
                    <button
                      className="reflect-menu-item"
                      onClick={() => {
                        setShowReflectMenu(false);
                        onReflect(currentSectionName);
                      }}
                    >
                      <span className="reflect-menu-label">Reflect on {validTabs[activeTab]?.label || 'section'}</span>
                    </button>
                  )}
                  {onReflectAll && (
                    <button
                      className="reflect-menu-item"
                      onClick={() => {
                        setShowReflectMenu(false);
                        onReflectAll();
                      }}
                    >
                      <span className="reflect-menu-label">Reflect on entire response</span>
                    </button>
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Tab Content */}
      <div className="tab-content">
        {validTabs[activeTab]?.content}
      </div>

      <style jsx>{`
        .tab-navigation {
          display: flex;
          flex-direction: column;
          height: 100%;
        }

        .tab-header-container {
          position: sticky;
          top: 0;
          background: white;
          z-index: 50;
          border-bottom: 1px solid #e5e7eb;
          box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
        }

        .tab-headers {
          display: flex;
          width: 100%;
          align-items: center;
        }

        .tab-header {
          flex: 1;
          padding: 8px 4px;
          background: none;
          border: none;
          border-bottom: 2px solid transparent;
          cursor: pointer;
          display: flex;
          flex-direction: column;
          align-items: center;
          gap: 2px;
          transition: all 0.2s;
          color: #6b7280;
          position: relative;
        }

        .tab-header:active {
          background: #f9fafb;
        }

        .tab-header.active {
          color: var(--primary-teal, #0d9488);
          border-bottom-color: var(--primary-teal, #0d9488);
        }

        .tab-icon {
          font-size: 1rem;
          display: none;
        }

        .tab-label {
          font-size: 0.7rem;
          font-weight: 600;
          white-space: nowrap;
        }

        .tab-count {
          position: absolute;
          top: 2px;
          right: 2px;
          background: var(--gold, #d97706);
          color: white;
          font-size: 0.55rem;
          font-weight: 600;
          padding: 1px 4px;
          border-radius: 8px;
          min-width: 14px;
          text-align: center;
        }

        .tab-header.active .tab-count {
          background: var(--primary-teal, #0d9488);
        }

        /* Three-dot button in tab bar */
        .tab-dots-area {
          position: relative;
          display: flex;
          align-items: center;
          padding: 0 8px;
          flex-shrink: 0;
        }

        .tab-dots-btn {
          display: flex;
          align-items: center;
          justify-content: center;
          width: 32px;
          height: 32px;
          background: #f3f4f6;
          border: 1px solid #e5e7eb;
          border-radius: 8px;
          color: #6b7280;
          cursor: pointer;
          transition: all 0.15s ease;
        }

        .tab-dots-btn:active {
          background: #e5e7eb;
          color: #374151;
        }

        /* Overflow menu */
        .reflect-menu {
          position: absolute;
          top: 100%;
          right: 0;
          margin-top: 4px;
          background: white;
          border: 1px solid #e5e7eb;
          border-radius: 10px;
          box-shadow: 0 4px 16px rgba(0, 0, 0, 0.12);
          min-width: 200px;
          z-index: 100;
          overflow: hidden;
        }

        .reflect-menu-item {
          display: block;
          width: 100%;
          padding: 12px 16px;
          background: none;
          border: none;
          text-align: left;
          cursor: pointer;
          transition: background 0.15s ease;
          font-size: 0.82rem;
          color: #374151;
        }

        .reflect-menu-item:hover,
        .reflect-menu-item:active {
          background: #f5f3ff;
        }

        .reflect-menu-item + .reflect-menu-item {
          border-top: 1px solid #f3f4f6;
        }

        .reflect-menu-label {
          font-weight: 500;
        }

        .tab-content {
          flex: 1;
          overflow-y: auto;
          padding: 12px;
          -webkit-overflow-scrolling: touch;
        }
      `}</style>
    </div>
  );
}
