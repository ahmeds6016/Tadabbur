'use client';

import { useEffect, useState } from 'react';
import { BACKEND_URL } from '../lib/config';
import { THEME_QUICK_SELECTS } from './SurahVersePicker';

const curatedTopics = () => THEME_QUICK_SELECTS.map(theme => ({
  name: theme.label,
  verse_refs: (theme.verses ?? []).map(verse => verse.query),
  confidence: 0,
}));

export default function TopicExplorer({ text, user, onSelect }) {
  const [topics, setTopics] = useState(null);
  const [loading, setLoading] = useState(true);
  const [notice, setNotice] = useState('');
  useEffect(() => {
    let active = true;
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 30000);
    setLoading(true);
    setNotice('');
    const explore = async () => {
      try {
        const headers = { 'Content-Type': 'application/json' };
        if (user?.getIdToken) headers.Authorization = `Bearer ${await user.getIdToken()}`;
        const response = await fetch(`${BACKEND_URL}/topics/resolve`, {
          method: 'POST', headers, body: JSON.stringify({ text }), signal: controller.signal,
        });
        const data = await response.json();
        if (!active) return;
        const safeTopics = (Array.isArray(data?.topics) ? data.topics : []).filter(topic =>
          typeof topic?.name === 'string' && Array.isArray(topic?.verse_refs) &&
          topic.verse_refs.some(ref => typeof ref === 'string' && /^\d+:\d+$/.test(ref))
        );
        if (!response.ok || !safeTopics.length) {
          setTopics(curatedTopics());
          setNotice(response.status === 429
            ? 'Topic search is temporarily limited. Curated themes are listed below.'
            : 'Curated themes are listed below.');
        } else {
          setTopics(safeTopics);
          setNotice(safeTopics.every(topic => !(Number(topic?.confidence) > 0))
            ? 'No related theme was identified. Curated themes are listed below.'
            : 'Select a verse to read its commentary.');
        }
      } catch {
        if (!active) return;
        // Offline, malformed, and timed-out responses still offer local verse choices.
        setTopics(curatedTopics());
        setNotice('Topic search is unavailable. Curated themes are listed below.');
      } finally {
        clearTimeout(timeout);
        if (active) setLoading(false);
      }
    };
    explore();
    return () => {
      active = false;
      clearTimeout(timeout);
      controller.abort();
    };
  }, [text, user]);

  return (
    <section aria-label="Topic discovery" className="topic-explorer">
      <h3 className="lookup-heading">Related themes</h3>
      <p className="topic-query">{typeof text === 'string' ? text : ''}</p>
      <div role="status" aria-live="polite" aria-busy={loading}>
        {loading && <p className="topic-status">Identifying related themes…</p>}
        {notice && <p className="topic-status">{notice}</p>}
        {Array.isArray(topics) && topics.map((topic, index) => (
          <div className="topic-entry" key={`${topic?.name ?? 'topic'}-${index}`}>
            <h4>{topic?.name ?? 'Suggested theme'}</h4>
            <div className="topic-verses">
              {(Array.isArray(topic?.verse_refs) ? topic.verse_refs : [])
                .filter(ref => typeof ref === 'string' && /^\d+:\d+$/.test(ref))
                .map(ref => (
                  <button type="button" className="topic-verse" key={ref} onClick={() => onSelect?.(ref)}
                    aria-label={`Read commentary for ${ref}`}>{ref}</button>
                ))}
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
