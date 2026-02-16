'use client';
import { useState, useEffect, useMemo } from 'react';
import { Search } from 'lucide-react';
import { BACKEND_URL } from '../lib/config';
import BottomNav from '../components/BottomNav';
import { onAuthStateChanged } from 'firebase/auth';
import { auth } from '../lib/firebase';

export default function NamesPage() {
  const [user, setUser] = useState(null);
  const [names, setNames] = useState({ male: [], female: [] });
  const [origins, setOrigins] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [gender, setGender] = useState('male');
  const [search, setSearch] = useState('');
  const [originFilter, setOriginFilter] = useState(null);
  const [quranicOnly, setQuranicOnly] = useState(false);
  const [expandedName, setExpandedName] = useState(null);

  useEffect(() => {
    const unsubscribe = onAuthStateChanged(auth, (u) => setUser(u));
    return () => unsubscribe();
  }, []);

  useEffect(() => {
    async function fetchNames() {
      try {
        const res = await fetch(`${BACKEND_URL}/names`);
        if (res.ok) {
          const data = await res.json();
          setNames(data.names || { male: [], female: [] });
          setOrigins(data.origins || []);
        }
      } catch { /* non-critical */ }
      setIsLoading(false);
    }
    fetchNames();
  }, []);

  const filtered = useMemo(() => {
    let list = names[gender] || [];
    if (search) {
      const q = search.toLowerCase();
      list = list.filter(n => n.name.toLowerCase().includes(q) || n.meaning.toLowerCase().includes(q));
    }
    if (originFilter) {
      list = list.filter(n => n.origin === originFilter);
    }
    if (quranicOnly) {
      list = list.filter(n => n.quranic);
    }
    return list;
  }, [names, gender, search, originFilter, quranicOnly]);

  if (isLoading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '60vh' }}>
        <p style={{ color: '#6b7280' }}>Loading names...</p>
      </div>
    );
  }

  return (
    <>
      <div style={{ maxWidth: 800, margin: '0 auto', padding: '20px 16px 120px' }}>
        {/* Header */}
        <div style={{ marginBottom: 16 }}>
          <h1 style={{ fontSize: '1.3rem', fontWeight: 700, color: 'var(--deep-blue, #1e293b)', margin: '0 0 4px' }}>
            Muslim Name Dictionary
          </h1>
          <p style={{ fontSize: '0.82rem', color: '#6b7280', margin: 0 }}>
            {names.male.length} male and {names.female.length} female names with meanings and origins
          </p>
        </div>

        {/* Gender toggle */}
        <div style={{ display: 'flex', gap: 0, marginBottom: 12, borderRadius: 8, overflow: 'hidden', border: '1px solid var(--border-light, #e5e7eb)' }}>
          {['male', 'female'].map(g => (
            <button
              key={g}
              onClick={() => { setGender(g); setExpandedName(null); }}
              style={{
                flex: 1, padding: '10px', border: 'none',
                background: gender === g ? 'var(--primary-teal, #0d9488)' : 'white',
                color: gender === g ? 'white' : '#6b7280',
                fontSize: '0.85rem', fontWeight: 600, cursor: 'pointer',
              }}
            >
              {g === 'male' ? 'Male Names' : 'Female Names'}
            </button>
          ))}
        </div>

        {/* Search */}
        <div style={{ position: 'relative', marginBottom: 10 }}>
          <Search size={16} style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)', color: '#9ca3af' }} />
          <input
            type="text"
            placeholder="Search by name or meaning..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            style={{
              width: '100%', padding: '10px 12px 10px 36px',
              border: '1px solid var(--border-light, #e5e7eb)',
              borderRadius: 8, fontSize: '0.85rem',
              outline: 'none', background: 'white',
              boxSizing: 'border-box',
            }}
          />
        </div>

        {/* Filters */}
        <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginBottom: 12, alignItems: 'center' }}>
          <button
            onClick={() => setQuranicOnly(!quranicOnly)}
            style={{
              padding: '5px 10px', borderRadius: 14, fontSize: '0.75rem', fontWeight: 600,
              background: quranicOnly ? 'var(--primary-teal, #0d9488)' : 'white',
              color: quranicOnly ? 'white' : '#6b7280',
              border: `1px solid ${quranicOnly ? 'var(--primary-teal, #0d9488)' : 'var(--border-light, #e5e7eb)'}`,
              cursor: 'pointer',
            }}
          >
            Quranic Names
          </button>
          {originFilter && (
            <button
              onClick={() => setOriginFilter(null)}
              style={{
                padding: '5px 10px', borderRadius: 14, fontSize: '0.75rem', fontWeight: 600,
                background: 'var(--primary-teal, #0d9488)', color: 'white',
                border: '1px solid var(--primary-teal, #0d9488)', cursor: 'pointer',
              }}
            >
              {originFilter} ×
            </button>
          )}
          <span style={{ fontSize: '0.75rem', color: '#9ca3af' }}>
            {filtered.length} names
          </span>
        </div>

        {/* Names list */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
          {filtered.map((n) => (
            <div
              key={n.name}
              onClick={() => setExpandedName(expandedName === n.name ? null : n.name)}
              style={{
                padding: '12px 14px',
                background: 'white',
                borderBottom: '1px solid var(--border-light, #e5e7eb)',
                cursor: 'pointer',
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                  <span style={{ fontSize: '0.95rem', fontWeight: 600, color: 'var(--deep-blue, #1e293b)' }}>
                    {n.name}
                  </span>
                  <span style={{ fontSize: '1rem', color: '#6b7280', fontFamily: 'var(--font-amiri, serif)', direction: 'rtl' }}>
                    {n.arabic}
                  </span>
                </div>
                <div style={{ display: 'flex', gap: 4, alignItems: 'center' }}>
                  {n.quranic && (
                    <span style={{
                      fontSize: '0.65rem', fontWeight: 600,
                      background: 'rgba(13, 148, 136, 0.08)',
                      color: 'var(--primary-teal, #0d9488)',
                      padding: '2px 6px', borderRadius: 4,
                    }}>
                      Quran
                    </span>
                  )}
                </div>
              </div>
              <div style={{ fontSize: '0.82rem', color: '#6b7280', marginTop: 2 }}>
                {n.meaning}
              </div>

              {expandedName === n.name && (
                <div style={{ marginTop: 8, padding: '10px 12px', background: 'var(--cream, #faf6f0)', borderRadius: 8, fontSize: '0.8rem' }}>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                    <div>
                      <span style={{ fontWeight: 600, color: '#374151' }}>Origin: </span>
                      <button
                        onClick={(e) => { e.stopPropagation(); setOriginFilter(n.origin); }}
                        style={{
                          background: 'none', border: 'none', padding: 0,
                          color: 'var(--primary-teal, #0d9488)', cursor: 'pointer',
                          fontWeight: 500, fontSize: '0.8rem', textDecoration: 'underline',
                          textUnderlineOffset: 2,
                        }}
                      >
                        {n.origin}
                      </button>
                    </div>
                    {n.quranic && n.reference && (
                      <div>
                        <span style={{ fontWeight: 600, color: '#374151' }}>Quran Reference: </span>
                        <span style={{ color: 'var(--primary-teal, #0d9488)' }}>Surah {n.reference}</span>
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          ))}

          {filtered.length === 0 && (
            <div style={{ textAlign: 'center', padding: '40px 20px', color: '#6b7280' }}>
              <p style={{ fontSize: '1rem', marginBottom: 8 }}>No names found</p>
              <p style={{ fontSize: '0.85rem' }}>Try a different search or filter.</p>
            </div>
          )}
        </div>
      </div>

      <BottomNav user={user} />
    </>
  );
}
