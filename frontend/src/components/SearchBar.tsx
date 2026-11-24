import { useState, useCallback, useEffect } from 'react';
import { useNavigate, useSearchParams, useLocation } from 'react-router-dom';

interface SearchBarProps {
  initialQuery?: string;
  compact?: boolean;
}



export default function SearchBar({ initialQuery = '', compact = false }: SearchBarProps) {
  const [searchParams] = useSearchParams();
  const location = useLocation();
  
  // Only use URL params if we are on the search page, otherwise use props/defaults
  const isSearchPage = location.pathname === '/search';
  const urlQuery = isSearchPage ? searchParams.get('q') || '' : '';
  const urlType = isSearchPage ? searchParams.get('type') || 'all' : 'all';

  const [query, setQuery] = useState(initialQuery || urlQuery);
  const [type, setType] = useState(urlType);

  const navigate = useNavigate();

  // Update state when URL changes
  useEffect(() => {
    if (isSearchPage) {
      setQuery(searchParams.get('q') || '');
      setType(searchParams.get('type') || 'all');
    }
  }, [searchParams, isSearchPage]);

  const handleSearch = useCallback((searchQuery?: string) => {
    const q = (searchQuery || query).trim();
    if (!q) return;
    navigate(`/search?q=${encodeURIComponent(q)}&type=${encodeURIComponent(type)}`);
  }, [query, type, navigate]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') handleSearch();
  };

  return (
    <div style={{ position: 'relative', width: '100%', maxWidth: compact ? '100%' : 540, margin: '0 auto' }}>
      <div style={{
        display: 'flex',
        alignItems: 'center',
        background: 'var(--c-bg2)',
        border: '1px solid var(--c-bd)',
        borderRadius: 8,
        overflow: 'hidden',
        transition: 'border-color 0.2s',
      }}>
        {/* Dropdown */}
        <div style={{ position: 'relative', display: 'flex', alignItems: 'center', background: 'var(--c-bg3)', borderRight: '1px solid var(--c-bd)', height: '100%' }}>
          <select
            value={type}
            onChange={(e) => setType(e.target.value)}
            style={{
              background: 'transparent',
              border: 'none',
              outline: 'none',
              padding: compact ? '9px 30px 9px 12px' : '12px 30px 12px 16px',
              color: 'var(--c-body)',
              fontSize: compact ? 13 : 14,
              cursor: 'pointer',
              appearance: 'none', // Remove default arrow
            }}
          >
            <option value="all">All Categories</option>
            <option value="projects">Projects</option>
            <option value="developers">Developers</option>
          </select>
          {/* Custom Dropdown Arrow */}
          <div style={{ position: 'absolute', right: compact ? 10 : 12, pointerEvents: 'none', color: 'var(--c-muted)', display: 'flex', alignItems: 'center' }}>
             <svg width="12" height="12" fill="none" stroke="currentColor" viewBox="0 0 24 24">
               <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
             </svg>
          </div>
        </div>

        <input
          id="search-input"
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}

          onKeyDown={handleKeyDown}
          placeholder="Search developers, projects, technologies..."
          style={{
            flex: 1,
            background: 'transparent',
            border: 'none',
            outline: 'none',
            color: 'var(--c-body)',
            fontSize: compact ? 13 : 14,
            padding: compact ? '9px 10px' : '12px 14px',
          }}
        />

        <button
          id="search-button"
          onClick={() => handleSearch()}
          style={{
            margin: '4px',
            padding: compact ? '5px 14px' : '7px 18px',
            background: '#5b6cf9',
            color: '#fff',
            border: 'none',
            borderRadius: 6,
            fontSize: 13,
            fontWeight: 600,
            cursor: 'pointer',
            transition: 'background 0.15s',
            whiteSpace: 'nowrap',
          }}
          onMouseEnter={e => (e.currentTarget.style.background = '#4a5af0')}
          onMouseLeave={e => (e.currentTarget.style.background = '#5b6cf9')}
        >
          Search
        </button>
      </div>


    </div>
  );
}
