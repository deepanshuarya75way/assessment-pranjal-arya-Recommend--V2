import SearchBar from '../components/SearchBar';

const STATS = [
  { label: 'Developers',   value: '55+'  },
  { label: 'Projects',     value: '89'   },
  { label: 'Technologies', value: '99+'  },
  { label: 'Domains',      value: '20'   },
];

const EXAMPLES = [
  { query: 'developers with python experience',         category: 'Skill search'    },
  { query: 'projects using react in Ahmedabad',         category: 'Location filter' },
  { query: 'AI and machine learning tools',             category: 'Domain search'   },
  { query: 'developers with more than 5 projects',      category: 'Experience'      },
  { query: 'seismic data management projects',          category: 'Domain'          },
  { query: 'projects using PHP and MySQL',              category: 'Multi-tech'      },
];

export default function HomePage() {
  return (
    <div style={{ minHeight: 'calc(100vh - 56px)' }}>

      {/* Hero */}
      <div style={{ maxWidth: 640, margin: '0 auto', padding: '80px 24px 52px', textAlign: 'center' }}>
        <div className="fade-in" style={{
          display: 'inline-block',
          fontSize: 11,
          fontWeight: 600,
          color: '#5b6cf9',
          background: 'var(--c-accent-dim, rgba(91,108,249,0.1))',
          border: '1px solid rgba(91,108,249,0.22)',
          borderRadius: 4,
          padding: '3px 10px',
          marginBottom: 24,
          letterSpacing: '0.06em',
          textTransform: 'uppercase',
        }}>
          Neo4j Knowledge Graph
        </div>

        <h1 className="fade-in-1" style={{
          fontSize: 'clamp(30px, 5vw, 50px)',
          fontWeight: 700,
          color: 'var(--c-heading)',
          letterSpacing: '-0.03em',
          lineHeight: 1.15,
          marginBottom: 16,
        }}>
          Discover Developers<br />& Projects
        </h1>

        <p className="fade-in-2" style={{
          fontSize: 15,
          color: 'var(--c-dim)',
          lineHeight: 1.7,
          marginBottom: 36,
          maxWidth: 400,
          margin: '0 auto 36px',
        }}>
          Search using natural language. Find projects by technology,
          domain, or developer expertise.
        </p>

        <div className="fade-in-3">
          <SearchBar />
        </div>
      </div>

      {/* Stats */}
      <div style={{ maxWidth: 640, margin: '0 auto', padding: '0 24px 44px' }}>
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(4, 1fr)',
          gap: 1,
          background: 'var(--c-bd)',
          border: '1px solid var(--c-bd)',
          borderRadius: 8,
          overflow: 'hidden',
        }}>
          {STATS.map((s) => (
            <div key={s.label} style={{ background: 'var(--c-bg)', padding: '18px 12px', textAlign: 'center' }}>
              <div style={{ fontSize: 20, fontWeight: 700, color: 'var(--c-heading)', letterSpacing: '-0.02em' }}>
                {s.value}
              </div>
              <div style={{ fontSize: 10, color: 'var(--c-subtle)', marginTop: 4, fontWeight: 500, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                {s.label}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Example queries */}
      <div style={{ maxWidth: 640, margin: '0 auto', padding: '0 24px 80px' }}>
        <div style={{ marginBottom: 16 }}>
          <h2 style={{ fontSize: 11, fontWeight: 600, color: 'var(--c-subtle)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
            Example searches
          </h2>
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(260px, 1fr))', gap: 8 }}>
          {EXAMPLES.map((ex, i) => (
            <a
              key={i}
              href={`/search?q=${encodeURIComponent(ex.query)}`}
              style={{
                display: 'block',
                padding: '12px 14px',
                background: 'var(--c-bg2)',
                border: '1px solid var(--c-bd)',
                borderRadius: 7,
                textDecoration: 'none',
                transition: 'border-color 0.15s',
              }}
              onMouseEnter={e => (e.currentTarget.style.borderColor = 'var(--c-bd2)')}
              onMouseLeave={e => (e.currentTarget.style.borderColor = 'var(--c-bd)')}
            >
              <div style={{ fontSize: 10, color: '#5b6cf9', fontWeight: 600, marginBottom: 4, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                {ex.category}
              </div>
              <div style={{ fontSize: 13, color: 'var(--c-dim)' }}>
                {ex.query}
              </div>
            </a>
          ))}
        </div>
      </div>

    </div>
  );
}
