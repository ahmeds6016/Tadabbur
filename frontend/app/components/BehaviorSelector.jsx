'use client';
import { useState } from 'react';
import { Landmark, Shield, BookOpen, Star, Heart, Activity, ChevronDown } from 'lucide-react';

const CATEGORY_ICONS = {
  fard: Landmark,
  tawbah: Shield,
  quran: BookOpen,
  nafl: Star,
  character: Heart,
  stewardship: Activity,
};

const INPUT_TYPE_LABELS = {
  binary: 'Yes / No',
  scale_5: 'Scale 1-5',
  minutes: 'Minutes',
  hours: 'Hours',
  count: 'Count',
  count_inv: 'Count',
};

/**
 * Group an array of behaviors by practice_group, preserving catalog order.
 */
function groupByPractice(behaviors) {
  const groups = [];
  const seen = new Set();
  for (const b of behaviors) {
    const gid = b.practice_group || b.id;
    if (!seen.has(gid)) {
      seen.add(gid);
      groups.push({
        id: gid,
        behaviors: behaviors.filter((x) => (x.practice_group || x.id) === gid),
      });
    }
  }
  return groups;
}

export default function BehaviorSelector({
  categories = [],
  behaviors = [],
  selectedIds = [],
  onChange,
  maxSelections = 15,
  minSelections = 3,
}) {
  const [expandedCats, setExpandedCats] = useState(() => {
    const initial = {};
    categories.forEach((c) => { initial[c.id] = true; });
    return initial;
  });

  const selectedSet = new Set(selectedIds);
  const atMax = selectedIds.length >= maxSelections;

  const toggleCategory = (catId) => {
    setExpandedCats((prev) => ({ ...prev, [catId]: !prev[catId] }));
  };

  const toggleBehavior = (bid) => {
    if (selectedSet.has(bid)) {
      onChange(selectedIds.filter((id) => id !== bid));
    } else if (!atMax) {
      onChange([...selectedIds, bid]);
    }
  };

  // Group behaviors by category, then by practice_group within each
  const groupedByCategory = {};
  for (const cat of categories) {
    const catBehaviors = behaviors.filter((b) => b.category === cat.id);
    groupedByCategory[cat.id] = {
      behaviors: catBehaviors,
      practiceGroups: groupByPractice(catBehaviors),
    };
  }

  const count = selectedIds.length;
  const countColor = count < minSelections ? '#dc2626' : count <= 10 ? '#059669' : '#d97706';

  return (
    <div className="behavior-selector">
      {categories.map((cat) => {
        const { behaviors: catBehaviors, practiceGroups } = groupedByCategory[cat.id] || { behaviors: [], practiceGroups: [] };
        if (catBehaviors.length === 0) return null;
        const catSelected = catBehaviors.filter((b) => selectedSet.has(b.id)).length;
        const Icon = CATEGORY_ICONS[cat.id] || Star;
        const expanded = expandedCats[cat.id];

        return (
          <div key={cat.id} className="bs-category">
            <button
              className="bs-cat-header"
              onClick={() => toggleCategory(cat.id)}
              aria-expanded={expanded}
            >
              <div className="bs-cat-left">
                <Icon size={16} style={{ color: cat.color }} />
                <span className="bs-cat-label">{cat.label}</span>
                <span className="bs-cat-count" style={{ color: cat.color }}>
                  {catSelected}/{catBehaviors.length}
                </span>
              </div>
              <ChevronDown
                size={16}
                className={`bs-chevron ${expanded ? 'expanded' : ''}`}
              />
            </button>

            {expanded && (
              <div className="bs-cat-body">
                {practiceGroups.map((group) => (
                  <div key={group.id} className="bs-practice-group">
                    {group.behaviors.length > 1 && (
                      <div className="bs-pg-header">
                        <span className="bs-pg-label">
                          {group.id.replace(/_/g, ' ')}
                        </span>
                      </div>
                    )}
                    {group.behaviors.map((b) => {
                      const checked = selectedSet.has(b.id);
                      const disabled = !checked && atMax;
                      return (
                        <label
                          key={b.id}
                          className={`bs-behavior ${checked ? 'checked' : ''} ${disabled ? 'disabled' : ''}`}
                        >
                          <input
                            type="checkbox"
                            checked={checked}
                            disabled={disabled}
                            onChange={() => toggleBehavior(b.id)}
                            className="bs-checkbox"
                          />
                          <span className="bs-b-label">{b.label}</span>
                          <span className="bs-b-type">{INPUT_TYPE_LABELS[b.input_type] || b.input_type}</span>
                        </label>
                      );
                    })}
                  </div>
                ))}
              </div>
            )}
          </div>
        );
      })}

      <div className="bs-footer">
        <span className="bs-total" style={{ color: countColor }}>
          {count} of {maxSelections} selected
        </span>
        {count < minSelections && (
          <span className="bs-warning">Select at least {minSelections} behaviors</span>
        )}
        {count > 10 && count <= maxSelections && (
          <span className="bs-hint">Consider fewer behaviors for clearer insights</span>
        )}
      </div>

      <style jsx>{`
        .behavior-selector {
          display: flex;
          flex-direction: column;
          gap: 0;
          border: 1px solid var(--color-border, #e5e7eb);
          border-radius: 12px;
          overflow: hidden;
          background: var(--color-surface, white);
        }
        .bs-category {
          border-bottom: 1px solid var(--border-light, #e5e7eb);
        }
        .bs-category:last-child {
          border-bottom: none;
        }
        .bs-cat-header {
          width: 100%;
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 12px 14px;
          background: var(--color-surface-muted, #fafaf8);
          border: none;
          cursor: pointer;
        }
        .bs-cat-left {
          display: flex;
          align-items: center;
          gap: 8px;
        }
        .bs-cat-label {
          font-size: 0.85rem;
          font-weight: 600;
          color: var(--foreground, #1e293b);
        }
        .bs-cat-count {
          font-size: 0.7rem;
          font-weight: 500;
        }
        .bs-chevron {
          color: #9ca3af;
          transition: transform 0.2s ease;
        }
        .bs-chevron.expanded {
          transform: rotate(180deg);
        }
        .bs-cat-body {
          padding: 4px 0;
        }

        /* Practice group sub-headings */
        .bs-practice-group {
          margin-bottom: 2px;
        }
        .bs-pg-header {
          padding: 8px 14px 2px 38px;
        }
        .bs-pg-label {
          font-size: 0.65rem;
          font-weight: 600;
          color: #9ca3af;
          text-transform: uppercase;
          letter-spacing: 0.4px;
        }

        .bs-behavior {
          display: flex;
          align-items: center;
          gap: 10px;
          padding: 10px 14px 10px 38px;
          cursor: pointer;
          transition: background 0.1s ease;
          user-select: none;
        }
        .bs-behavior:hover:not(.disabled) {
          background: var(--color-surface-muted, #f8fafc);
        }
        .bs-behavior.disabled {
          opacity: 0.4;
          cursor: not-allowed;
        }
        .bs-checkbox {
          width: 18px;
          height: 18px;
          accent-color: var(--primary-teal, #0d9488);
          cursor: inherit;
          flex-shrink: 0;
        }
        .bs-b-label {
          flex: 1;
          font-size: 0.85rem;
          color: var(--foreground, #374151);
        }
        .bs-behavior.checked .bs-b-label {
          color: var(--foreground, #1e293b);
          font-weight: 500;
        }
        .bs-b-type {
          font-size: 0.65rem;
          color: var(--color-text-secondary, #9ca3af);
          padding: 2px 6px;
          background: var(--color-surface-muted, #f3f4f6);
          border-radius: 4px;
          flex-shrink: 0;
        }
        .bs-footer {
          padding: 10px 14px;
          display: flex;
          flex-direction: column;
          gap: 2px;
          background: var(--color-surface-muted, #fafaf8);
          border-top: 1px solid var(--color-border, #e5e7eb);
        }
        .bs-total {
          font-size: 0.8rem;
          font-weight: 600;
        }
        .bs-warning {
          font-size: 0.75rem;
          color: #dc2626;
        }
        .bs-hint {
          font-size: 0.75rem;
          color: #d97706;
        }
      `}</style>
    </div>
  );
}
