'use client';
import { useState, useEffect } from 'react';

export default function TabNavigation({
  children,
  tabs = [],
  defaultTab = 0,
  storageKey = 'selected-tab',
  resetKey = null  // Add reset key prop
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

  // Don't use tabs on desktop - show all content with section labels
  if (!isMobile) {
    return (
      <div className="desktop-sections">
        {validTabs.map((tab, index) => (
          <section key={index} className="desktop-section" aria-label={tab.label}>
            <header className="desktop-section-header">
              <span className="tab-icon">{tab.icon}</span>
              <h2 className="tab-label">{tab.label}{tab.count !== undefined ? ` (${tab.count})` : ''}</h2>
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
