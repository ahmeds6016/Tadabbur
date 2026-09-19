'use client';

import { useEffect, useRef, useState } from 'react';
import { BACKEND_URL } from '../lib/config';
import { THEME_QUICK_SELECTS } from './SurahVersePicker';

const curatedTopics = () => THEME_QUICK_SELECTS.map(theme => ({
  name: theme.label,
  verse_refs: (theme.verses ?? []).map(verse => verse.query),
  confidence: 0,
}));

export default function TopicExplorer({ text, user, onSelect }) {
  const [topics, setTopics] = useState(null);
  const [loading, setLoading] = useState(false);
  const [notice, setNotice] = useState('');
  const controllerRef = useRef(null);

  useEffect(() => () => controllerRef.current?.abort(), []);

  const explore = async () => {
    controllerRef.current?.abort();
    const controller = new AbortController();
    controllerRef.current = controller;
    const timeout = setTimeout(() => controller.abort(), 30000);
    setLoading(true);
    setNotice('');
    try {
      const headers = { 'Content-Type': 'application/json' };
      if (user?.getIdToken) headers.Authorization = `Bearer ${await user.getIdToken()}`;
      const response = await fetch(`${BACKEND_URL}/topics/resolve`, {
        method: 'POST', headers, body: JSON.stringify({ text }), signal: controller.signal,
      });
      const data = await response.json();
      const safeTopics = (Array.isArray(data?.topics) ? data.topics : []).filter(topic =>
        typeof topic?.name === 'string' && Array.isArray(topic?.verse_refs) &&
        topic.verse_refs.some(ref => typeof ref === 'string' && /^\d+:\d+$/.test(ref))
      );
      if (!response.ok || !safeTopics.length) {
        setTopics(curatedTopics());
        setNotice(response.status === 429
          ? 'Topic search is resting for a moment. You can still browse these themes.'
          : 'Try one of these themes to begin.');
      } else {
        setTopics(safeTopics);
        setNotice(safeTopics.every(topic => !(Number(topic?.confidence) > 0))
          ? 'No close match this time. You can explore one of these themes.'
          : 'Choose a verse to read its commentary.');
      }
    } catch {
      // Offline, malformed, and timed-out responses still offer local verse choices.
      setTopics(curatedTopics());
      setNotice('Topic search is unavailable right now. You can browse these themes.');
    } finally {
      clearTimeout(timeout);
      setLoading(false);
    }
  };

  return (
    <section aria-label="Topic discovery" className="topic-explorer">
      <h3>Find a verse for what is on your mind</h3>
      <p>Explore themes related to “{typeof text === 'string' ? text : ''}”.</p>
      <button type="button" onClick={explore} disabled={loading} className="explore-button">
        {loading ? 'Finding related themes…' : 'Explore as a topic'}
      </button>
      <div role="status" aria-live="polite" aria-busy={loading}>
        {notice && <p>{notice}</p>}
        {Array.isArray(topics) && topics.map((topic, index) => (
          <div className="topic" key={`${topic?.name ?? 'topic'}-${index}`}>
            <h4>{topic?.name ?? 'Suggested theme'}</h4>
            <div className="verse-chips">
              {(Array.isArray(topic?.verse_refs) ? topic.verse_refs : [])
                .filter(ref => typeof ref === 'string' && /^\d+:\d+$/.test(ref))
                .map(ref => (
                  <button type="button" key={ref} onClick={() => onSelect?.(ref)}
                    aria-label={`Read commentary for ${ref}`}>{ref}</button>
                ))}
            </div>
          </div>
        ))}
      </div>
      <style jsx>{`
        .topic-explorer { color: var(--foreground, #1f2937); margin-bottom: 20px; }
        h3 { margin: 0 0 8px; font-size: 1.1rem; }
        p { line-height: 1.5; font-size: .9rem; }
        button { padding: 10px 16px; border: 1px solid var(--primary-teal, #0d9488);
          border-radius: 20px; color: var(--primary-teal, #0d9488);
          background: var(--color-surface, white); cursor: pointer; font: inherit; }
        button:focus-visible { outline: 3px solid var(--primary-teal, #0d9488); outline-offset: 3px; }
        button:disabled { opacity: .65; cursor: wait; }
        .explore-button { background: var(--primary-teal, #0d9488); color: white; }
        h4 { margin: 16px 0 8px; }
        .verse-chips { display: flex; flex-wrap: wrap; gap: 8px; }
      `}</style>
    </section>
  );
}
