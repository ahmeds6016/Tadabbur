'use client';
import { useState, useEffect, useCallback } from 'react';
import {
  Flame, Calendar, Star, Search, Brain, GraduationCap,
  Compass, Globe, PenLine, Heart, Crown, BookOpen, Trophy, Rocket,
} from 'lucide-react';
import { BACKEND_URL } from '../lib/config';

// Color palette for badge icons
const BADGE_COLORS = {
  fire: '#EF4444',
  calendar: '#2563EB',
  star: '#EAB308',
  search: '#8B5CF6',
  brain: '#EC4899',
  graduation: '#059669',
  compass: '#0891B2',
  globe: '#6366F1',
  pen: '#D97706',
  heart: '#F43F5E',
  crown: '#B45309',
  book: '#0D9488',
  trophy: '#D4AF37',
  rocket: '#7C3AED',
};

// Lucide icon mapping for each badge type
const BADGE_ICONS = {
  fire: Flame,
  calendar: Calendar,
  star: Star,
  search: Search,
  brain: Brain,
  graduation: GraduationCap,
  compass: Compass,
  globe: Globe,
  pen: PenLine,
  heart: Heart,
  crown: Crown,
  book: BookOpen,
  trophy: Trophy,
  rocket: Rocket,
};

/** Render a badge icon with translucent colored background */
function BadgeIcon({ iconKey, size = 40 }) {
  const color = BADGE_COLORS[iconKey] || BADGE_COLORS.trophy;
  const IconComponent = BADGE_ICONS[iconKey] || Trophy;
  const iconSize = Math.round(size * 0.5);
  return (
    <span style={{
      background: `${color}15`,
      width: size,
      height: size,
      borderRadius: size > 30 ? 12 : 6,
      display: 'inline-flex',
      alignItems: 'center',
      justifyContent: 'center',
      flexShrink: 0,
    }}>
      <IconComponent size={iconSize} color={color} strokeWidth={2.2} />
    </span>
  );
}

/** Toast-style popup shown when a badge is newly earned. */
export function BadgePopup({ badge, onClose }) {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    // Trigger enter animation on mount
    requestAnimationFrame(() => setVisible(true));
    const timer = setTimeout(() => {
      setVisible(false);
      setTimeout(onClose, 300);
    }, 5000);
    return () => clearTimeout(timer);
  }, [onClose]);

  return (
    <div className={`badge-popup ${visible ? 'badge-popup--visible' : ''}`}>
      <BadgeIcon iconKey={badge.icon} size={40} />
      <div className="badge-popup__body">
        <span className="badge-popup__title">Badge Earned!</span>
        <strong className="badge-popup__name">{badge.name}</strong>
        <span className="badge-popup__desc">{badge.description}</span>
      </div>
      <button className="badge-popup__close" onClick={() => { setVisible(false); setTimeout(onClose, 300); }} aria-label="Dismiss badge notification">
        x
      </button>

      <style jsx>{`
        .badge-popup {
          position: fixed;
          top: -100px;
          left: 50%;
          transform: translateX(-50%);
          z-index: 9999;
          display: flex;
          align-items: center;
          gap: 12px;
          padding: 14px 18px;
          background: var(--color-surface, white);
          border: 1px solid var(--gold, #d4a017);
          border-radius: 12px;
          box-shadow: 0 4px 16px rgba(0, 0, 0, 0.12);
          transition: top 0.35s cubic-bezier(0.34, 1.56, 0.64, 1);
          max-width: 380px;
          width: calc(100% - 32px);
        }
        .badge-popup--visible {
          top: 24px;
        }
        .badge-popup__icon {
          font-size: 2rem;
          flex-shrink: 0;
        }
        .badge-popup__body {
          display: flex;
          flex-direction: column;
          gap: 2px;
          min-width: 0;
        }
        .badge-popup__title {
          font-size: 0.7rem;
          text-transform: uppercase;
          letter-spacing: 0.05em;
          color: var(--gold, #d4a017);
          font-weight: 600;
        }
        .badge-popup__name {
          font-size: 0.95rem;
          color: var(--deep-blue, #1e293b);
        }
        .badge-popup__desc {
          font-size: 0.78rem;
          color: #666;
        }
        .badge-popup__close {
          position: absolute;
          top: 8px;
          right: 10px;
          background: none;
          border: none;
          font-size: 1rem;
          color: #aaa;
          cursor: pointer;
          line-height: 1;
          padding: 2px 4px;
        }
        .badge-popup__close:hover {
          color: #666;
        }
      `}</style>
    </div>
  );
}

/** Full badge grid or compact summary. */
export default function BadgeDisplay({ user, compact = false }) {
  const [badges, setBadges] = useState([]);
  const [totalEarned, setTotalEarned] = useState(0);
  const [totalAvailable, setTotalAvailable] = useState(13);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchBadges = useCallback(async () => {
    if (!user) return;
    setLoading(true);
    setError(null);
    try {
      const token = await user.getIdToken();
      const res = await fetch(`${BACKEND_URL}/badges`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error(`Failed to load badges (${res.status})`);
      const data = await res.json();
      setBadges(data.badges || []);
      setTotalEarned(data.total_earned ?? 0);
      setTotalAvailable(data.total_available ?? 13);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [user]);

  useEffect(() => { fetchBadges(); }, [fetchBadges]);

  if (loading) {
    return (
      <div className="badge-loading">
        <span>Loading badges...</span>
        <style jsx>{`
          .badge-loading {
            text-align: center;
            padding: 24px;
            color: #999;
            font-size: 0.85rem;
          }
        `}</style>
      </div>
    );
  }

  if (error) {
    return (
      <div className="badge-error">
        <span>{error}</span>
        <button onClick={fetchBadges}>Retry</button>
        <style jsx>{`
          .badge-error {
            text-align: center;
            padding: 16px;
            color: #b91c1c;
            font-size: 0.85rem;
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 8px;
          }
          .badge-error button {
            padding: 6px 14px;
            border: 1px solid var(--border-light, #e5e7eb);
            border-radius: 6px;
            background: var(--color-surface, white);
            cursor: pointer;
            font-size: 0.8rem;
          }
        `}</style>
      </div>
    );
  }

  /* ---------- Compact mode ---------- */
  if (compact) {
    const earned = badges.filter((b) => b.earned);
    return (
      <div className="badge-compact">
        <span className="badge-compact__count">{totalEarned}/{totalAvailable} badges earned</span>
        <div className="badge-compact__icons">
          {earned.map((b) => (
            <span key={b.id} title={b.name}>
              <BadgeIcon iconKey={b.icon} size={24} />
            </span>
          ))}
        </div>
        <style jsx>{`
          .badge-compact {
            display: flex;
            align-items: center;
            gap: 10px;
            flex-wrap: wrap;
          }
          .badge-compact__count {
            font-size: 0.85rem;
            font-weight: 600;
            color: var(--deep-blue, #1e293b);
          }
          .badge-compact__icons {
            display: flex;
            gap: 4px;
            flex-wrap: wrap;
          }
          .badge-compact__icon {
            font-size: 1.1rem;
          }
        `}</style>
      </div>
    );
  }

  /* ---------- Full grid mode ---------- */
  return (
    <div className="badge-grid-wrap">
      <div className="badge-grid-header">
        <span className="badge-grid-header__title">Badges</span>
        <span className="badge-grid-header__count">{totalEarned} / {totalAvailable}</span>
      </div>
      <div className="badge-grid">
        {badges.map((b) => {
          const earned = b.earned;
          return (
            <div key={b.id} className={`badge-card ${earned ? 'badge-card--earned' : 'badge-card--locked'}`}>
              <BadgeIcon iconKey={b.icon} size={44} />
              <strong className="badge-card__title">{b.name}</strong>
              <span className="badge-card__desc">{b.description}</span>
              {earned && b.earned_at && (
                <span className="badge-card__date">
                  {new Date(b.earned_at).toLocaleDateString()}
                </span>
              )}
              {!earned && b.threshold != null && (
                <span className="badge-card__progress">
                  Reach {b.threshold} to unlock
                </span>
              )}
            </div>
          );
        })}
      </div>

      <style jsx>{`
        .badge-grid-wrap {
          width: 100%;
        }
        .badge-grid-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 16px;
        }
        .badge-grid-header__title {
          font-size: 1.1rem;
          font-weight: 700;
          color: var(--deep-blue, #1e293b);
        }
        .badge-grid-header__count {
          font-size: 0.85rem;
          font-weight: 600;
          color: var(--primary-teal, #0d9488);
          background: var(--cream, #faf6f0);
          padding: 4px 10px;
          border-radius: 10px;
        }
        .badge-grid {
          display: grid;
          grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
          gap: 12px;
        }
        .badge-card {
          display: flex;
          flex-direction: column;
          align-items: center;
          text-align: center;
          gap: 6px;
          padding: 14px 10px;
          border-radius: 10px;
          border: 1px solid var(--border-light, #e5e7eb);
          background: var(--color-surface, white);
        }
        .badge-card--earned {
          border-color: var(--gold, #d4a017);
        }
        .badge-card--locked {
          filter: grayscale(1);
          opacity: 0.55;
        }
        .badge-card__icon {
          font-size: 2rem;
        }
        .badge-card__title {
          font-size: 0.82rem;
          color: var(--deep-blue, #1e293b);
          line-height: 1.2;
        }
        .badge-card__desc {
          font-size: 0.72rem;
          color: #888;
          line-height: 1.3;
        }
        .badge-card__date {
          font-size: 0.68rem;
          color: var(--gold, #d4a017);
          font-weight: 500;
          margin-top: 2px;
        }
        .badge-card__progress {
          font-size: 0.68rem;
          color: #aaa;
          font-style: italic;
          margin-top: 2px;
        }
        @media (max-width: 480px) {
          .badge-grid {
            grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
            gap: 8px;
          }
          .badge-card {
            padding: 12px 8px;
          }
        }
      `}</style>
    </div>
  );
}
