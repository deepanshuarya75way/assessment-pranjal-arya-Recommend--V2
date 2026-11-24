import { useSearchParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { searchAPI } from '../services/api';
import ProjectCard from '../components/ProjectCard';
import DeveloperCard from '../components/DeveloperCard';
import { useState, useEffect } from 'react';

type TabType = 'all' | 'projects' | 'developers';

export default function SearchResultsPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const query = searchParams.get('q') || '';
  const [activeTab, setActiveTab] = useState<TabType>((searchParams.get('type') as TabType) || 'all');

  useEffect(() => {
    const typeParam = searchParams.get('type') as TabType;
    if (typeParam && typeParam !== activeTab) {
      setActiveTab(typeParam);
    }
  }, [searchParams]);

  const handleTabChange = (tab: TabType) => {
    setActiveTab(tab);
    const newParams = new URLSearchParams(searchParams);
    newParams.set('type', tab);
    setSearchParams(newParams);
  };

  const { data, isLoading, error } = useQuery({
    queryKey: ['search', query],
    queryFn: () => searchAPI.search(query),
    enabled: !!query,
  });

  if (!query) {
    return (
      <div style={{ maxWidth: 720, margin: '80px auto', padding: '0 24px', textAlign: 'center' }}>
        <p style={{ color: 'var(--c-dim)', fontSize: 14 }}>Enter a search query to get started.</p>
      </div>
    );
  }

  const tabs: { key: TabType; label: string; count?: number }[] = [
    { key: 'all',        label: 'All',        count: data?.total_results },
    { key: 'projects',   label: 'Projects',   count: data?.projects.length },
    { key: 'developers', label: 'Developers', count: data?.developers.length },
  ];

  return (
    <div style={{ maxWidth: 960, margin: '0 auto', padding: '32px 24px' }}>

      {/* Query header */}
      <div style={{ marginBottom: 24 }}>
        <p style={{ fontSize: 12, color: 'var(--c-subtle)', marginBottom: 6 }}>Results for</p>
        <h1 style={{ fontSize: 22, fontWeight: 700, color: 'var(--c-heading)', letterSpacing: '-0.02em' }}>
          "{query}"
        </h1>

        {/* Parsed filters */}
        {data && data.parsed_filters && Object.keys(data.parsed_filters).length > 0 && (
          <div style={{ display: 'flex', gap: 6, marginTop: 10, flexWrap: 'wrap', alignItems: 'center' }}>
            <span style={{ fontSize: 11, color: 'var(--c-subtle)' }}>Parsed:</span>
            {data.parsed_filters.technology && (
              <span className="tech-badge">{String(data.parsed_filters.technology)}</span>
            )}
            {data.parsed_filters.domain && (
              <span className="domain-badge">{String(data.parsed_filters.domain)}</span>
            )}
            {data.parsed_filters.location && (
              <span className="location-badge">{String(data.parsed_filters.location)}</span>
            )}
            {data.parsed_filters.min_projects && (
              <span className="tech-badge">≥{String(data.parsed_filters.min_projects)} projects</span>
            )}
          </div>
        )}
      </div>

      {/* Tabs */}
      <div style={{
        display: 'flex',
        gap: 2,
        marginBottom: 24,
        background: 'var(--c-bg2)',
        border: '1px solid var(--c-bd)',
        borderRadius: 7,
        padding: 3,
        width: 'fit-content',
      }}>
        {tabs.map(tab => (
          <button
            key={tab.key}
            onClick={() => handleTabChange(tab.key)}
            style={{
              padding: '5px 14px',
              borderRadius: 5,
              fontSize: 13,
              fontWeight: 500,
              border: 'none',
              cursor: 'pointer',
              transition: 'background 0.15s, color 0.15s',
              background: activeTab === tab.key ? 'var(--c-bg3)' : 'transparent',
              color: activeTab === tab.key ? 'var(--c-heading)' : 'var(--c-dim)',
            }}
          >
            {tab.label}
            {tab.count !== undefined && tab.count > 0 && (
              <span style={{ marginLeft: 5, fontSize: 11, opacity: 0.6 }}>({tab.count})</span>
            )}
          </button>
        ))}
      </div>

      {/* Loading skeleton */}
      {isLoading && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: 10 }}>
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="animate-shimmer" style={{
              height: 140,
              borderRadius: 8,
              border: '1px solid var(--c-bd)',
            }} />
          ))}
        </div>
      )}

      {/* Error */}
      {error && (
        <div style={{
          padding: '24px',
          background: 'var(--c-bg2)',
          border: '1px solid var(--c-bd)',
          borderRadius: 8,
          textAlign: 'center',
        }}>
          <p style={{ fontSize: 13, color: 'var(--c-dim)' }}>
            Unable to connect to the server. Make sure the backend is running.
          </p>
        </div>
      )}

      {/* Results */}
      {data && !isLoading && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 32 }}>

          {/* Projects */}
          {(activeTab === 'all' || activeTab === 'projects') && data.projects.length > 0 && (
            <section>
              {activeTab === 'all' && (
                <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 14 }}>
                  <h2 style={{ fontSize: 12, fontWeight: 600, color: 'var(--c-subtle)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
                    Projects
                  </h2>
                  <span style={{ fontSize: 11, color: 'var(--c-muted)' }}>({data.projects.length})</span>
                </div>
              )}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: 10 }}>
                {data.projects.map((p, i) => (
                  <ProjectCard key={p.name} project={p} index={i} />
                ))}
              </div>
            </section>
          )}

          {/* Developers */}
          {(activeTab === 'all' || activeTab === 'developers') && data.developers.length > 0 && (
            <section>
              {activeTab === 'all' && (
                <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 14 }}>
                  <h2 style={{ fontSize: 12, fontWeight: 600, color: 'var(--c-subtle)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
                    Developers
                  </h2>
                  <span style={{ fontSize: 11, color: 'var(--c-muted)' }}>({data.developers.length})</span>
                </div>
              )}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: 10 }}>
                {data.developers.map((d, i) => (
                  <DeveloperCard key={d.name} developer={d} index={i} />
                ))}
              </div>
            </section>
          )}

          {/* Empty */}
          {data.total_results === 0 && (
            <div style={{
              padding: '48px 24px',
              background: 'var(--c-bg2)',
              border: '1px solid var(--c-bd)',
              borderRadius: 8,
              textAlign: 'center',
            }}>
              <p style={{ fontSize: 14, color: 'var(--c-heading)', marginBottom: 8 }}>No results found</p>
              <p style={{ fontSize: 13, color: 'var(--c-dim)' }}>
                Try different keywords, technologies, or domains.
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
