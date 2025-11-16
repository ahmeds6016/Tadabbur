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

  // Reset viewed sections when resetKey changes (new query)
  useEffect(() => {
    if (resetKey && typeof window !== 'undefined') {
      setViewedSections(new Set());
      localStorage.removeItem(`${storageKey}-viewed`);
    }
  }, [resetKey, storageKey]);

  // Filter out empty tabs (sections with no content)
  const validTabs = tabs.filter(tab => tab.content);

  // Don't use tabs on desktop - show all content
  if (!isMobile) {
    return <>{validTabs.map(tab => tab.content)}</>;
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
          overflow-x: auto;
          scrollbar-width: none;
          -webkit-overflow-scrolling: touch;
        }

        .tab-headers::-webkit-scrollbar {
          display: none;
        }

        .tab-header {
          flex: 1;
          min-width: 100px;
          padding: 12px 16px;
          background: none;
          border: none;
          border-bottom: 2px solid transparent;
          cursor: pointer;
          display: flex;
          flex-direction: column;
          align-items: center;
          gap: 4px;
          transition: all 0.2s;
          color: #6b7280;
          position: relative;
        }

        .tab-header:active {
          background: #f9fafb;
        }

        .tab-header.active {
          color: #10b981;
          border-bottom-color: #10b981;
          background: linear-gradient(to bottom, rgba(16, 185, 129, 0.05), transparent);
        }

        .tab-icon {
          font-size: 1.25rem;
        }

        .tab-label {
          font-size: 0.75rem;
          font-weight: 500;
        }

        .tab-count {
          position: absolute;
          top: 8px;
          right: 8px;
          background: linear-gradient(135deg, #fbbf24, #f59e0b);
          color: #7c2d12;
          font-size: 0.625rem;
          font-weight: 600;
          padding: 2px 6px;
          border-radius: 10px;
          min-width: 18px;
          text-align: center;
          box-shadow: 0 1px 2px rgba(251, 191, 36, 0.3);
        }

        .tab-header.active .tab-count {
          background: #10b981;
          color: white;
        }

        .tab-content {
          flex: 1;
          overflow-y: auto;
          padding: 16px;
          -webkit-overflow-scrolling: touch;
        }

        /* Swipe hint animation on first load */
        @keyframes swipeHint {
          0% { transform: translateX(0); }
          50% { transform: translateX(-20px); }
          100% { transform: translateX(0); }
        }

        .tab-headers.show-hint {
          animation: swipeHint 1s ease-in-out;
        }
      `}</style>
    </div>
  );
}