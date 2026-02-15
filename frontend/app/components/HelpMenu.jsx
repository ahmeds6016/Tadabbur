'use client';
import { useState, useEffect } from 'react';

const helpContent = {
  home: {
    title: 'Getting Started',
    sections: [
      {
        title: 'Browse Surahs',
        items: [
          {
            label: 'Surah Picker',
            description: 'Select any of the 114 surahs from the dropdown to explore its verses',
            tour: 'search'
          },
          {
            label: 'Verse Range',
            description: 'Pick a start and end verse — the app adjusts the max range based on commentary length',
            tour: 'search'
          },
          {
            label: 'Scholarly Commentary',
            description: 'Each response includes classical tafsir plus insights from 5 scholarly sources when relevant',
            tour: 'search'
          }
        ]
      },
      {
        title: 'Features',
        items: [
          {
            label: 'Add Reflections',
            description: 'Select any text in the results to add personal notes',
            tour: 'annotations'
          },
          {
            label: 'Save Answers',
            description: 'Bookmark important responses for later review',
            tour: 'save'
          },
          {
            label: 'Share',
            description: 'Generate shareable links for any answer',
            tour: 'share'
          }
        ]
      }
    ],
    shortcuts: [
      { keys: ['Ctrl', 'K'], action: 'Scroll to verse picker' },
      { keys: ['Esc'], action: 'Cancel request / clear results' },
      { keys: ['Alt', 'S'], action: 'Save current result' },
      { keys: ['Alt', 'H'], action: 'Open help menu' },
      { keys: ['Alt', 'N'], action: 'New search (clear and scroll up)' }
    ]
  },
  results: {
    title: 'Understanding Results',
    sections: [
      {
        title: 'Result Sections',
        items: [
          {
            label: 'Verses',
            description: 'Quranic verses with Arabic text and translation',
            tour: 'verses'
          },
          {
            label: 'Tafsir',
            description: 'Classical commentary from multiple scholars',
            tour: 'tafsir'
          },
          {
            label: 'Lessons',
            description: 'Practical applications for daily life',
            tour: 'lessons'
          },
          {
            label: 'Summary',
            description: 'Key takeaways from the response',
            tour: 'summary'
          }
        ]
      },
      {
        title: 'Actions',
        items: [
          {
            label: 'Annotate Text',
            description: 'Select any text to add your thoughts',
            tour: 'annotations'
          },
          {
            label: 'Save Answer',
            description: 'Keep this response for future reference',
            tour: 'save'
          },
          {
            label: 'Share',
            description: 'Generate a shareable link for this answer',
            tour: 'share'
          }
        ]
      }
    ],
    shortcuts: [
      { keys: ['Click + Drag'], action: 'Select text for annotation' },
      { keys: ['Tab'], action: 'Navigate between sections' },
      { keys: ['Space'], action: 'Scroll down' }
    ]
  },
  annotations: {
    title: 'Notes & Reflections',
    sections: [
      {
        title: 'Reflection Types',
        items: [
          { label: 'Insight', description: 'Personal understanding or revelation' },
          { label: 'Question', description: 'Something to explore further' },
          { label: 'Application', description: 'How to apply in daily life' },
          { label: "Du'a", description: 'Personal supplication or prayer' },
          { label: 'Connection', description: 'Link to other verses or concepts' },
          { label: 'Memorization', description: 'Verses to memorize' }
        ]
      },
      {
        title: 'Managing Reflections',
        items: [
          {
            label: 'Add Tags',
            description: 'Categorize your notes with custom tags for easy retrieval'
          },
          {
            label: 'View All Reflections',
            description: 'Access all your saved reflections from the Reflections tab in the sidebar'
          }
        ]
      }
    ],
    shortcuts: []
  }
};

export default function HelpMenu({ currentPage = 'home', isOpen, onClose, onReplayFeatureIntro }) {
  const [expandedSection, setExpandedSection] = useState(null);
  const [activeTab, setActiveTab] = useState('help');
  const content = helpContent[currentPage] || helpContent.home;

  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = '';
    }

    return () => {
      document.body.style.overflow = '';
    };
  }, [isOpen]);

  const handleReplayIntro = () => {
    onClose();
    if (onReplayFeatureIntro) {
      onReplayFeatureIntro();
    }
  };

  if (!isOpen) return null;

  return (
    <>
      {/* Overlay */}
      <div
        className="help-overlay"
        onClick={onClose}
        style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          background: 'rgba(0, 0, 0, 0.5)',
          zIndex: 999,
          animation: 'fadeIn 0.3s ease'
        }}
      />

      {/* Help Panel */}
      <div className={`help-panel ${isOpen ? 'open' : ''}`}>
        <div className="help-header">
          <h2>{content.title}</h2>
          <button onClick={onClose} className="help-close">
            ×
          </button>
        </div>

        {/* Tabs */}
        <div className="help-tabs">
          <button
            className={`help-tab ${activeTab === 'help' ? 'active' : ''}`}
            onClick={() => setActiveTab('help')}
          >
            Help
          </button>
          <button
            className={`help-tab ${activeTab === 'shortcuts' ? 'active' : ''}`}
            onClick={() => setActiveTab('shortcuts')}
          >
            Shortcuts
          </button>
          <button
            className={`help-tab ${activeTab === 'faq' ? 'active' : ''}`}
            onClick={() => setActiveTab('faq')}
          >
            FAQ
          </button>
        </div>

        <div className="help-content">
          {activeTab === 'help' && (
            <>
              {content.sections.map((section, idx) => (
                <div key={idx} className="help-section">
                  <h3
                    className="section-title"
                    onClick={() => setExpandedSection(expandedSection === idx ? null : idx)}
                  >
                    {section.title}
                    <span className="expand-icon">
                      {expandedSection === idx ? '−' : '+'}
                    </span>
                  </h3>

                  <div className={`section-content ${expandedSection === idx ? 'expanded' : ''}`}>
                    {section.items.map((item, itemIdx) => (
                      <div key={itemIdx} className="help-item">
                        <span className="item-icon">{item.icon}</span>
                        <div className="item-content">
                          <strong>{item.label}</strong>
                          <p>{item.description}</p>
                          {item.tour && onReplayFeatureIntro && (
                            <button
                              className="tour-link"
                              onClick={handleReplayIntro}
                            >
                              Show me how
                            </button>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              ))}

              <div className="help-cta">
                {onReplayFeatureIntro && (
                  <button
                    className="replay-intro-btn"
                    onClick={() => {
                      onClose();
                      onReplayFeatureIntro();
                    }}
                  >
                    Replay Feature Introduction
                  </button>
                )}
                <button
                  className="start-tour-btn"
                  onClick={handleReplayIntro}
                >
                  Replay Introduction
                </button>
              </div>
            </>
          )}

          {activeTab === 'shortcuts' && (
            <div className="shortcuts-list">
              <h3>Keyboard Shortcuts</h3>
              {content.shortcuts.length > 0 ? (
                <div className="shortcuts-grid">
                  {content.shortcuts.map((shortcut, idx) => (
                    <div key={idx} className="shortcut-item">
                      <div className="shortcut-keys">
                        {shortcut.keys.map((key, keyIdx) => (
                          <kbd key={keyIdx}>{key}</kbd>
                        ))}
                      </div>
                      <span className="shortcut-action">{shortcut.action}</span>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="no-shortcuts">No keyboard shortcuts available for this page.</p>
              )}
            </div>
          )}

          {activeTab === 'faq' && (
            <div className="faq-list">
              <h3>Frequently Asked Questions</h3>

              <div className="faq-item">
                <h4>What is Tafsir Simplified?</h4>
                <p>Tafsir Simplified helps you explore any verse of the Quran through the lens of classical scholarship. The AI synthesizes and presents content from authenticated sources — including Ibn Kathir, Al-Qurtubi, and five additional scholarly works — rather than generating its own interpretations. Every response is shaped by your chosen learning persona, so the commentary meets you at your level.</p>
              </div>

              <div className="faq-item">
                <h4>How do I select verses?</h4>
                <p>Use the surah dropdown to pick from all 114 surahs. Then choose a starting verse and an ending verse. The app automatically adjusts the maximum range based on how much commentary exists for those verses, so you always get complete, untruncated results.</p>
              </div>

              <div className="faq-item">
                <h4>Where do scholarly insights come from?</h4>
                <p>Five classical sources are matched automatically based on verse themes: Asbab Al-Nuzul (reasons of revelation), A Thematic Commentary on the Quran, Ihya Ulum Al-Din (Revival of Religious Sciences), Madarij Al-Salikin (Ranks of the Wayfarers), and Riyad-us-Saliheen (Gardens of the Righteous).</p>
              </div>

              <div className="faq-item">
                <h4>Why are some responses slow?</h4>
                <p>Each response involves multi-step generation: fetching verse data, matching scholarly sources, and generating commentary. This typically takes 10-20 seconds. Longer verse ranges or verses with more scholarly matches may take a bit longer.</p>
              </div>

              <div className="faq-item">
                <h4>How do I save my work?</h4>
                <p>Save any response to revisit later, select text to add personal reflections, and track your exploration across all 114 surahs. You can also follow reading plans, browse themed verse collections, and earn badges as you go — everything is accessible from the navigation bar.</p>
              </div>

              <div className="faq-item">
                <h4>Can I change my persona?</h4>
                <p>Yes! Click your persona badge in the header area to change your learning persona at any time. Your new persona takes effect on the next query.</p>
              </div>

              <div className="faq-item">
                <h4>What do personas do?</h4>
                <p>Your persona shapes how the same scholarship is presented to you. A New Revert receives patient, foundational guidance. A Curious Explorer gets reflective, open-ended interpretations. A Practicing Muslim receives balanced daily wisdom. A Student gets structured academic analysis. An Advanced Learner receives detailed classical commentary. Same sources, different depth.</p>
              </div>

              <div className="faq-item">
                <h4>Are my reflections private?</h4>
                <p>Yes — your personal reflections are encrypted and stored securely. They are only accessible to you when signed in. No one else — including us — can read your private reflections. When you share a response, only the scholarly commentary is shared, never your personal notes.</p>
              </div>
            </div>
          )}
        </div>

        <style jsx>{`
          @keyframes fadeIn {
            from { opacity: 0; }
            to { opacity: 1; }
          }

          .help-panel {
            position: fixed;
            right: 0;
            top: 0;
            bottom: 0;
            width: 450px;
            background: white;
            box-shadow: -4px 0 20px rgba(0, 0, 0, 0.1);
            z-index: 1000;
            transform: translateX(100%);
            transition: transform 0.3s ease;
            display: flex;
            flex-direction: column;
            overflow: hidden;
          }

          .help-panel.open {
            transform: translateX(0);
          }

          .help-header {
            padding: 24px;
            border-bottom: 2px solid var(--border-light);
            display: flex;
            justify-content: space-between;
            align-items: center;
            background: var(--gradient-manuscript);
          }

          .help-header h2 {
            margin: 0;
            color: var(--primary-teal);
            font-size: 1.5rem;
          }

          .help-close {
            width: 36px;
            height: 36px;
            border-radius: 50%;
            border: 2px solid var(--border-light);
            background: white;
            font-size: 1.5rem;
            cursor: pointer;
            transition: all 0.2s ease;
            display: flex;
            align-items: center;
            justify-content: center;
          }

          .help-close:hover {
            background: var(--cream);
            border-color: var(--primary-teal);
          }

          .help-tabs {
            display: flex;
            background: var(--cream);
            border-bottom: 1px solid var(--border-light);
          }

          .help-tab {
            flex: 1;
            padding: 12px;
            background: transparent;
            border: none;
            font-weight: 600;
            color: var(--deep-blue);
            cursor: pointer;
            transition: all 0.2s ease;
            border-bottom: 3px solid transparent;
          }

          .help-tab:hover {
            background: rgba(255, 255, 255, 0.5);
          }

          .help-tab.active {
            color: var(--primary-teal);
            border-bottom-color: var(--primary-teal);
            background: white;
          }

          .help-content {
            flex: 1;
            overflow-y: auto;
            padding: 24px;
          }

          .help-section {
            margin-bottom: 24px;
          }

          .section-title {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 12px 16px;
            background: var(--cream);
            border-radius: 12px;
            cursor: pointer;
            font-weight: 600;
            color: var(--deep-blue);
            margin-bottom: 12px;
            transition: all 0.2s ease;
          }

          .section-title:hover {
            background: linear-gradient(135deg, var(--cream) 0%, rgba(212, 175, 55, 0.1) 100%);
          }

          .expand-icon {
            font-size: 1.2rem;
            color: var(--primary-teal);
          }

          .section-content {
            max-height: 0;
            overflow: hidden;
            transition: max-height 0.3s ease;
          }

          .section-content.expanded {
            max-height: 1000px;
          }

          .help-item {
            display: flex;
            gap: 12px;
            padding: 12px;
            margin-bottom: 8px;
            border-radius: 8px;
            transition: background 0.2s ease;
          }

          .help-item:hover {
            background: var(--cream);
          }

          .item-icon {
            font-size: 1.5rem;
            flex-shrink: 0;
          }

          .item-content {
            flex: 1;
          }

          .item-content strong {
            display: block;
            color: var(--deep-blue);
            margin-bottom: 4px;
          }

          .item-content p {
            margin: 0;
            color: #666;
            font-size: 0.9rem;
          }

          .tour-link {
            margin-top: 8px;
            padding: 4px 12px;
            background: var(--primary-teal);
            color: white;
            border: none;
            border-radius: 6px;
            font-size: 0.85rem;
            cursor: pointer;
            transition: all 0.2s ease;
          }

          .tour-link:hover {
            background: var(--gold);
            transform: translateX(2px);
          }

          .help-cta {
            margin-top: 24px;
            padding: 20px;
            background: linear-gradient(135deg, var(--cream) 0%, rgba(212, 175, 55, 0.1) 100%);
            border-radius: 12px;
            text-align: center;
          }

          .start-tour-btn {
            padding: 12px 24px;
            background: linear-gradient(135deg, var(--primary-teal) 0%, var(--gold) 100%);
            color: white;
            border: none;
            border-radius: 12px;
            font-size: 1rem;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s ease;
          }

          .replay-intro-btn {
            padding: 12px 24px;
            background: white;
            color: var(--primary-teal, #10b981);
            border: 2px solid var(--primary-teal, #10b981);
            border-radius: 12px;
            font-size: 1rem;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s ease;
            margin-bottom: 10px;
            width: 100%;
          }

          .replay-intro-btn:hover {
            background: var(--cream, #faf6f0);
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(16, 185, 129, 0.2);
          }

          .start-tour-btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(16, 185, 129, 0.3);
          }

          .shortcuts-grid {
            display: flex;
            flex-direction: column;
            gap: 12px;
            margin-top: 16px;
          }

          .shortcut-item {
            display: flex;
            align-items: center;
            gap: 16px;
            padding: 12px;
            background: var(--cream);
            border-radius: 8px;
          }

          .shortcut-keys {
            display: flex;
            gap: 4px;
          }

          .shortcut-keys kbd {
            padding: 4px 8px;
            background: white;
            border: 1px solid var(--border-light);
            border-radius: 4px;
            font-family: monospace;
            font-size: 0.85rem;
            color: var(--deep-blue);
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
          }

          .shortcut-action {
            color: #666;
            font-size: 0.9rem;
          }

          .no-shortcuts {
            color: #999;
            font-style: italic;
            text-align: center;
            padding: 24px;
          }

          .faq-list {
            padding-top: 16px;
          }

          .faq-item {
            margin-bottom: 24px;
            padding-bottom: 24px;
            border-bottom: 1px solid var(--border-light);
          }

          .faq-item:last-child {
            border-bottom: none;
          }

          .faq-item h4 {
            color: var(--primary-teal);
            margin-bottom: 8px;
          }

          .faq-item p {
            color: #666;
            line-height: 1.6;
          }

          /* Mobile adjustments */
          @media (max-width: 768px) {
            .help-panel {
              width: 100%;
              max-width: 400px;
            }
          }
        `}</style>
      </div>
    </>
  );
}

// Floating Help Button Component
export function FloatingHelpButton({ onClick }) {
  const [isHovered, setIsHovered] = useState(false);

  return (
    <button
      className="floating-help-button"
      onClick={onClick}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      aria-label="Open help menu"
      title="Need help? (F1)"
    >
      ?

      <style jsx>{`
        .floating-help-button {
          position: fixed;
          bottom: 24px;
          right: 24px;
          width: 56px;
          height: 56px;
          border-radius: 50%;
          background: linear-gradient(135deg, var(--primary-teal) 0%, var(--gold) 100%);
          color: white;
          border: none;
          box-shadow: 0 4px 12px rgba(16, 185, 129, 0.3);
          cursor: pointer;
          z-index: 998;
          display: flex;
          align-items: center;
          justify-content: center;
          font-size: 1.5rem;
          transition: all 0.3s ease;
        }

        .floating-help-button:hover {
          transform: scale(1.1) rotate(10deg);
          box-shadow: 0 6px 20px rgba(16, 185, 129, 0.4);
        }

        /* Hide on mobile if bottom nav is present */
        @media (max-width: 768px) {
          .floating-help-button {
            bottom: 80px; /* Above bottom navigation */
          }
        }
      `}</style>
    </button>
  );
}