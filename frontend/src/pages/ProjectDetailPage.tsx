import { useParams, useNavigate, Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { projectsAPI } from '../services/api';
import RecommendationPanel from '../components/RecommendationPanel';

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

export default function ProjectDetailPage() {
  const { name } = useParams<{ name: string }>();
  const navigate = useNavigate();
  const projectName = decodeURIComponent(name || '');

  const { data: project, isLoading } = useQuery({
    queryKey: ['project', projectName],
    queryFn: () => projectsAPI.get(projectName),
    enabled: !!projectName,
  });

  const { data: recommendations } = useQuery({
    queryKey: ['project-rec', projectName],
    queryFn: () => projectsAPI.recommendations(projectName),
    enabled: !!projectName,
  });

  if (isLoading) {
    return (
      <div style={{ maxWidth: 800, margin: '0 auto', padding: '32px 24px' }}>
        <div className="animate-shimmer" style={{ height: 200, borderRadius: 8, border: '1px solid var(--c-bd)' }} />
      </div>
    );
  }

  if (!project) {
    return (
      <div style={{ maxWidth: 800, margin: '80px auto', padding: '0 24px', textAlign: 'center' }}>
        <p style={{ fontSize: 14, color: 'var(--c-dim)' }}>Project not found.</p>
      </div>
    );
  }

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
          to={`/graph?q=${encodeURIComponent(project.name)}`}
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: 6,
            fontSize: 12,
            fontWeight: 600,
            color: '#06b6d4',
            background: 'rgba(6,182,212,0.08)',
            border: '1px solid rgba(6,182,212,0.28)',
            borderRadius: 7,
            padding: '5px 12px',
            textDecoration: 'none',
            transition: 'background 0.15s, border-color 0.15s',
          }}
          onMouseEnter={e => {
            (e.currentTarget as HTMLElement).style.background = 'rgba(6,182,212,0.18)';
            (e.currentTarget as HTMLElement).style.borderColor = 'rgba(6,182,212,0.5)';
          }}
          onMouseLeave={e => {
            (e.currentTarget as HTMLElement).style.background = 'rgba(6,182,212,0.08)';
            (e.currentTarget as HTMLElement).style.borderColor = 'rgba(6,182,212,0.28)';
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
      <div style={{ marginBottom: 28 }}>
        <h1 style={{
          fontSize: 'clamp(22px, 3vw, 30px)',
          fontWeight: 700,
          color: 'var(--c-heading)',
          letterSpacing: '-0.025em',
          lineHeight: 1.3,
          marginBottom: 8,
        }}>
          {project.name}
        </h1>
        {project.tagline && (
          <p style={{ fontSize: 14, color: 'var(--c-dim)', lineHeight: 1.6 }}>
            {project.tagline}
          </p>
        )}
        {project.developed_on && (
          <p style={{ fontSize: 12, color: 'var(--c-muted)', marginTop: 6 }}>
            {project.developed_on}
          </p>
        )}
      </div>

      {/* Description */}
      {project.description && (
        <div style={{ marginBottom: 24 }}>
          <Section>
            <SectionLabel>About</SectionLabel>
            <p style={{ fontSize: 13, color: 'var(--c-body)', lineHeight: 1.75 }}>
              {project.description}
            </p>
          </Section>
        </div>
      )}

      {/* Info grid */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10, marginBottom: 24 }}>

        {/* Technologies */}
        {project.technologies.length > 0 && (
          <Section>
            <SectionLabel>Technologies</SectionLabel>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 5 }}>
              {project.technologies.map(tech => (
                <span key={tech} className="tech-badge">{tech}</span>
              ))}
            </div>
          </Section>
        )}

        {/* Domains */}
        {project.domains.length > 0 && (
          <Section>
            <SectionLabel>Domains</SectionLabel>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 5 }}>
              {project.domains.map(d => (
                <span key={d} className="domain-badge">{d}</span>
              ))}
            </div>
          </Section>
        )}

        {/* Developers */}
        {project.developers.length > 0 && (
          <Section>
            <SectionLabel>Developers</SectionLabel>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
              {project.developers.map(dev => (
                <button
                  key={dev}
                  onClick={() => navigate(`/developer/${encodeURIComponent(dev)}`)}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: 10,
                    padding: '6px 0',
                    background: 'none',
                    border: 'none',
                    cursor: 'pointer',
                    textAlign: 'left',
                  }}
                >
                  <div style={{
                    width: 28,
                    height: 28,
                    borderRadius: 5,
                    background: 'var(--c-bg3)',
                    border: '1px solid var(--c-bd)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    fontSize: 10,
                    fontWeight: 700,
                    color: '#5b6cf9',
                    flexShrink: 0,
                  }}>
                    {dev.split(' ').slice(0, 2).map(n => n[0]).join('')}
                  </div>
                  <span style={{ fontSize: 13, color: 'var(--c-dim)' }}
                    onMouseEnter={e => (e.currentTarget.style.color = 'var(--c-heading)')}
                    onMouseLeave={e => (e.currentTarget.style.color = 'var(--c-dim)')}
                  >{dev}</span>
                </button>
              ))}
            </div>
          </Section>
        )}

        {/* Locations */}
        {project.locations.length > 0 && (
          <Section>
            <SectionLabel>Locations</SectionLabel>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 5 }}>
              {project.locations.map(loc => (
                <span key={loc} className="location-badge">{loc}</span>
              ))}
            </div>
          </Section>
        )}
      </div>

      {/* Recommendations */}
      {recommendations && (
        <RecommendationPanel
          title="Similar Projects"
          projects={recommendations.recommended_projects}
        />
      )}
    </div>
  );
}
