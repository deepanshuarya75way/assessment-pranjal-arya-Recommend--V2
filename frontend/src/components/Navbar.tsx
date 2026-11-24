import { Link, useLocation } from 'react-router-dom';
import SearchBar from './SearchBar';
import { useTheme } from '../context/ThemeContext';

function SunIcon() {
  return (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="5"/>
      <line x1="12" y1="1"  x2="12" y2="3"/>
      <line x1="12" y1="21" x2="12" y2="23"/>
      <line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/>
      <line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/>
      <line x1="1" y1="12" x2="3" y2="12"/>
      <line x1="21" y1="12" x2="23" y2="12"/>
      <line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/>
      <line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/>
    </svg>
  );
}

function MoonIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>
    </svg>
  );
}

export default function Navbar() {
  const location = useLocation();
  const isHome = location.pathname === '/';
  const currentQuery = new URLSearchParams(location.search).get('q') || '';
  const { isDark, toggle } = useTheme();

  return (
    <nav style={{
      position: 'sticky',
      top: 0,
      zIndex: 50,
      background: 'var(--c-nav-bg)',
      borderBottom: '1px solid var(--c-bd)',
      backdropFilter: 'blur(12px)',
      transition: 'background 0.2s, border-color 0.2s',
    }}>
      <div style={{ maxWidth: 1024, margin: '0 auto', padding: '0 20px' }}>
        <div style={{ display: 'flex', alignItems: 'center', height: 56, gap: 20 }}>

          {/* Logo */}
          <Link to="/" style={{ display: 'flex', alignItems: 'center', gap: 8, textDecoration: 'none', flexShrink: 0 }}>
            <div style={{
              width: 26,
              height: 26,
              borderRadius: 6,
              background: '#5b6cf9',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}>
              <svg width="12" height="12" fill="none" stroke="white" viewBox="0 0 24 24" strokeWidth="2.5">
                <circle cx="12" cy="12" r="3"/>
                <path strokeLinecap="round" d="M12 3v3M12 18v3M3 12h3M18 12h3"/>
              </svg>
            </div>
            <span style={{ fontSize: 14, fontWeight: 600, color: 'var(--c-heading)', letterSpacing: '-0.01em' }}>
              KGraph
            </span>
          </Link>

          {/* Compact search on non-home pages */}
          {!isHome && (
            <div style={{ flex: 1, maxWidth: 480 }}>
              <SearchBar initialQuery={currentQuery} compact />
            </div>
          )}

          {/* Right side — nav links + theme toggle */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 4, marginLeft: 'auto' }}>
            {[
              { to: '/',        label: 'Home'    },
              { to: '/graph',   label: 'Graph'   },
              { to: '/chat',    label: 'Chat'    },
              { to: '/reviews', label: 'Reviews' },
            ].map(({ to, label }) => {
              const active = location.pathname === to;
              return (
                <Link
                  key={to}
                  to={to}
                  style={{
                    padding: '5px 12px',
                    borderRadius: 6,
                    fontSize: 13,
                    fontWeight: 500,
                    textDecoration: 'none',
                    color: active ? 'var(--c-heading)' : 'var(--c-subtle)',
                    background: active ? 'var(--c-bg3)' : 'transparent',
                    transition: 'color 0.15s, background 0.15s',
                  }}
                >
                  {label}
                </Link>
              );
            })}

            {/* Theme toggle */}
            <button
              id="theme-toggle"
              onClick={toggle}
              title={isDark ? 'Switch to light mode' : 'Switch to dark mode'}
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                width: 32,
                height: 32,
                borderRadius: 6,
                border: '1px solid var(--c-bd)',
                background: 'var(--c-bg3)',
                color: 'var(--c-dim)',
                cursor: 'pointer',
                marginLeft: 6,
                transition: 'background 0.15s, color 0.15s, border-color 0.15s',
                flexShrink: 0,
              }}
              onMouseEnter={e => {
                e.currentTarget.style.color = 'var(--c-heading)';
                e.currentTarget.style.borderColor = 'var(--c-bd2)';
              }}
              onMouseLeave={e => {
                e.currentTarget.style.color = 'var(--c-dim)';
                e.currentTarget.style.borderColor = 'var(--c-bd)';
              }}
            >
              {isDark ? <SunIcon /> : <MoonIcon />}
            </button>
          </div>
        </div>
      </div>
    </nav>
  );
}
