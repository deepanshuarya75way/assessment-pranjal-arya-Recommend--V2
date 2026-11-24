import { useParams, useNavigate, Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { developersAPI } from '../services/api';
import RecommendationPanel from '../components/RecommendationPanel';
import ProjectCard from '../components/ProjectCard';

const SectionLabel = ({ children }: { children: React.ReactNode }) => (
  <h3 style={{
    fontSize: 11,
    fontWeight: 600,
    color: 'var(--c-subtle)',
    textTransform: 'uppercase',
    letterSpacing: '0.07em',
    marginBottom: 12,
  }}>
    {children}
  </h3>
);

const Section = ({ children }: { children: React.ReactNode }) => (
  <div style={{
    background: 'var(--c-bg2)',
    border: '1px solid var(--c-bd)',
    borderRadius: 8,
    padding: '16px 18px',
  }}>
    {children}
  </div>
);

export default function DeveloperDetailPage() {
  const { name } = useParams<{ name: string }>();
  const navigate = useNavigate();
  const devName = decodeURIComponent(name || '');

  const { data: developer, isLoading } = useQuery({
    queryKey: ['developer', devName],
    queryFn: () => developersAPI.get(devName),
    enabled: !!devName,
  });

  const { data: recommendations } = useQuery({
    queryKey: ['developer-rec', devName],
    queryFn: () => developersAPI.recommendations(devName),
    enabled: !!devName,
  });

  const { data: allProjects } = useQuery({
    queryKey: ['all-projects'],
    queryFn: () => import('../services/api').then(m => m.projectsAPI.list()),
  });

  if (isLoading) {
    return (
      <div style={{ maxWidth: 800, margin: '0 auto', padding: '32px 24px' }}>
        <div className="animate-shimmer" style={{ height: 200, borderRadius: 8, border: '1px solid var(--c-bd)' }} />
      </div>
    );
  }

  if (!developer) {
    return (
      <div style={{ maxWidth: 800, margin: '80px auto', padding: '0 24px', textAlign: 'center' }}>
        <p style={{ fontSize: 14, color: 'var(--c-dim)' }}>Developer not found.</p>
      </div>
    );
  }

  const initials = developer.name.split(' ').slice(0, 2).map((n: string) => n[0]).join('');
  const devProjects = allProjects?.filter((p: any) => developer.projects.includes(p.name)) || [];

  return (
    <div style={{ maxWidth: 800, margin: '0 auto', padding: '32px 24px' }} className="fade-in">

      {/* Back + Graph */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', paddingBottom: 20 }}>
        <button
          onClick={() => navigate(-1)}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 6,
            fontSize: 13,
            color: 'var(--c-dim)',
            background: 'none',
            border: 'none',
            cursor: 'pointer',
            padding: 0,
            transition: 'color 0.15s',
          }}
          onMouseEnter={e => (e.currentTarget.style.color = 'var(--c-heading)')}
          onMouseLeave={e => (e.currentTarget.style.color = 'var(--c-dim)')}
        >
          <svg width="14" height="14" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
          </svg>
          Back
        </button>

        <Link
          to={`/graph?q=${encodeURIComponent(developer.name)}`}
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: 6,
            fontSize: 12,
            fontWeight: 600,
            color: '#818cf8',
            background: 'rgba(99,102,241,0.1)',
            border: '1px solid rgba(99,102,241,0.3)',
            borderRadius: 7,
            padding: '5px 12px',
            textDecoration: 'none',
            transition: 'background 0.15s, border-color 0.15s',
          }}
          onMouseEnter={e => {
            (e.currentTarget as HTMLElement).style.background = 'rgba(99,102,241,0.2)';
            (e.currentTarget as HTMLElement).style.borderColor = 'rgba(99,102,241,0.55)';
          }}
          onMouseLeave={e => {
            (e.currentTarget as HTMLElement).style.background = 'rgba(99,102,241,0.1)';
            (e.currentTarget as HTMLElement).style.borderColor = 'rgba(99,102,241,0.3)';
          }}
        >
          <svg width="13" height="13" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth="2">
            <circle cx="5" cy="5" r="2"/>
            <circle cx="19" cy="5" r="2"/>
            <circle cx="12" cy="19" r="2"/>
            <path strokeLinecap="round" d="M5 7v4a7 7 0 007 7M19 7v4a7 7 0 01-7 7M5 5h14"/>
          </svg>
          View in Graph
        </Link>
      </div>

      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'flex-start', gap: 16, marginBottom: 28 }}>
        <div style={{
          width: 48,
          height: 48,
          borderRadius: 8,
          background: 'var(--c-bg3)',
          border: '1px solid var(--c-bd)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontSize: 15,
          fontWeight: 700,
          color: '#5b6cf9',
          flexShrink: 0,
        }}>
          {initials}
        </div>
        <div>
          <h1 style={{
            fontSize: 'clamp(20px, 3vw, 28px)',
            fontWeight: 700,
            color: 'var(--c-heading)',
            letterSpacing: '-0.025em',
            lineHeight: 1.3,
            marginBottom: 6,
          }}>
            {developer.name}
          </h1>
          {developer.bio && (
            <p style={{ fontSize: 13, color: 'var(--c-dim)', lineHeight: 1.6, marginBottom: 8 }}>
              {developer.bio}
            </p>
          )}

          {/* Email / Phone */}
          {(developer.email || developer.phone) && (
            <div style={{ display: 'flex', gap: 16, marginTop: 8, flexWrap: 'wrap' }}>
              {developer.email && (
                <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 12, color: 'var(--c-subtle)' }}>
                  <svg width="13" height="13" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth="2">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                  </svg>
                  <a href={`mailto:${developer.email}`} style={{ color: 'var(--c-dim)', textDecoration: 'none' }}
                     onMouseEnter={e => (e.currentTarget.style.color = '#5b6cf9')}
                     onMouseLeave={e => (e.currentTarget.style.color = 'var(--c-dim)')}>
                    {developer.email}
                  </a>
                </div>
              )}
              {developer.phone && (
                <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 12, color: 'var(--c-subtle)' }}>
                  <svg width="13" height="13" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth="2">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M3 5a2 2 0 012-2h3.28a1 1 0 01.94.725l.548 2.2a1 1 0 01-.321.988l-1.305.98a10.582 10.582 0 004.872 4.872l.98-1.305a1 1 0 01.988-.321l2.2.548a1 1 0 01.725.94V19a2 2 0 01-2 2h-1C9.716 21 3 14.284 3 6V5z" />
                  </svg>
                  <a href={`tel:${developer.phone}`} style={{ color: 'var(--c-dim)', textDecoration: 'none' }}
                     onMouseEnter={e => (e.currentTarget.style.color = '#5b6cf9')}
                     onMouseLeave={e => (e.currentTarget.style.color = 'var(--c-dim)')}>
                    {developer.phone}
                  </a>
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Stats row */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(4, 1fr)',
        gap: 1,
        background: 'var(--c-bd)',
        border: '1px solid var(--c-bd)',
        borderRadius: 8,
        overflow: 'hidden',
        marginBottom: 24,
      }}>
        {[
          { label: 'Projects',     value: developer.project_count },
          { label: 'Technologies', value: developer.technologies.length },
          { label: 'Domains',      value: developer.domains.length },
          { label: 'Locations',    value: developer.locations.length },
        ].map(s => (
          <div key={s.label} style={{ background: 'var(--c-bg)', padding: '16px 12px', textAlign: 'center' }}>
            <div style={{ fontSize: 20, fontWeight: 700, color: 'var(--c-heading)', letterSpacing: '-0.02em' }}>
              {s.value}
            </div>
            <div style={{ fontSize: 10, color: 'var(--c-subtle)', marginTop: 3, fontWeight: 500, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              {s.label}
            </div>
          </div>
        ))}
      </div>

      {/* Info grid */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10, marginBottom: 28 }}>

        {developer.technologies.length > 0 && (
          <Section>
            <SectionLabel>Technologies</SectionLabel>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 5 }}>
              {developer.technologies.map((tech: string) => (
                <span key={tech} className="tech-badge">{tech}</span>
              ))}
            </div>
          </Section>
        )}

        {developer.domains.length > 0 && (
          <Section>
            <SectionLabel>Domains</SectionLabel>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 5 }}>
              {developer.domains.map((d: string) => (
                <span key={d} className="domain-badge">{d}</span>
              ))}
            </div>
          </Section>
        )}

        {developer.locations.length > 0 && (
          <div style={{ gridColumn: '1 / -1' }}>
            <Section>
              <SectionLabel>Locations</SectionLabel>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 5 }}>
                {developer.locations.map((loc: string) => (
                  <span key={loc} className="location-badge">{loc}</span>
                ))}
              </div>
            </Section>
          </div>
        )}
      </div>

      {/* Projects */}
      {devProjects.length > 0 && (
        <div style={{ marginBottom: 28 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 14 }}>
            <h2 style={{ fontSize: 12, fontWeight: 600, color: 'var(--c-subtle)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
              Projects
            </h2>
            <span style={{ fontSize: 11, color: 'var(--c-muted)' }}>({devProjects.length})</span>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: 10 }}>
            {devProjects.map((p: any, i: number) => (
              <ProjectCard key={p.name} project={p} index={i} />
            ))}
          </div>
        </div>
      )}

      {/* Recommendations */}
      {recommendations && (
        <RecommendationPanel
          title="Similar Developers"
          developers={recommendations.recommended_developers}
        />
      )}
    </div>
  );
}
