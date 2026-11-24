import { useNavigate } from 'react-router-dom';
import type { Developer } from '../types';

interface DeveloperCardProps {
  developer: Developer;
  index?: number;
}

export default function DeveloperCard({ developer, index = 0 }: DeveloperCardProps) {
  const navigate = useNavigate();
  const initials = developer.name
    .split(' ')
    .slice(0, 2)
    .map(n => n[0])
    .join('');

  return (
    <div
      id={`developer-card-${developer.name.replace(/\s+/g, '-').toLowerCase()}`}
      onClick={() => navigate(`/developer/${encodeURIComponent(developer.name)}`)}
      className="fade-in"
      style={{
        background: 'var(--c-bg2)',
        border: '1px solid var(--c-bd)',
        borderRadius: 8,
        padding: '18px 20px',
        cursor: 'pointer',
        transition: 'border-color 0.15s, box-shadow 0.15s',
        animationDelay: `${index * 0.04}s`,
        display: 'flex',
        flexDirection: 'column',
        gap: 12,
      }}
      onMouseEnter={e => {
        e.currentTarget.style.borderColor = 'var(--c-bd2)';
        e.currentTarget.style.boxShadow = '0 4px 16px rgba(0,0,0,0.12)';
      }}
      onMouseLeave={e => {
        e.currentTarget.style.borderColor = 'var(--c-bd)';
        e.currentTarget.style.boxShadow = 'none';
      }}
    >
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
        {/* Avatar */}
        <div style={{
          width: 36,
          height: 36,
          borderRadius: 6,
          background: 'var(--c-bg3)',
          border: '1px solid var(--c-bd)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontSize: 12,
          fontWeight: 700,
          color: '#5b6cf9',
          flexShrink: 0,
          letterSpacing: '-0.01em',
        }}>
          {initials}
        </div>

        <div style={{ flex: 1, minWidth: 0 }}>
          <h3 style={{
            fontSize: 14,
            fontWeight: 600,
            color: 'var(--c-heading)',
            letterSpacing: '-0.01em',
          }}>
            {developer.name}
          </h3>
          {developer.bio && (
            <p style={{ fontSize: 12, color: 'var(--c-dim)', marginTop: 2 }}>
              {developer.bio.length > 60 ? developer.bio.slice(0, 60) + '…' : developer.bio}
            </p>
          )}
        </div>

        {developer.relevance_score > 0 && (
          <div style={{
            flexShrink: 0,
            fontSize: 11,
            fontWeight: 600,
            color: '#5b6cf9',
            background: 'rgba(91,108,249,0.1)',
            border: '1px solid rgba(91,108,249,0.2)',
            borderRadius: 4,
            padding: '2px 7px',
          }}>
            {developer.relevance_score.toFixed(0)}
          </div>
        )}
      </div>

      {/* Stats inline */}
      <div style={{ display: 'flex', gap: 16, fontSize: 12 }}>
        <span style={{ color: 'var(--c-dim)' }}>
          <span style={{ color: 'var(--c-heading)', fontWeight: 600 }}>{developer.project_count}</span>
          {' '}projects
        </span>
        <span style={{ color: 'var(--c-dim)' }}>
          <span style={{ color: 'var(--c-heading)', fontWeight: 600 }}>{developer.technologies.length}</span>
          {' '}technologies
        </span>
        <span style={{ color: 'var(--c-dim)' }}>
          <span style={{ color: 'var(--c-heading)', fontWeight: 600 }}>{developer.domains.length}</span>
          {' '}domains
        </span>
      </div>

      {/* Technologies */}
      {developer.technologies.length > 0 && (
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
          {developer.technologies.slice(0, 5).map(tech => (
            <span key={tech} className="tech-badge">{tech}</span>
          ))}
          {developer.technologies.length > 5 && (
            <span className="tech-badge" style={{ opacity: 0.5 }}>+{developer.technologies.length - 5}</span>
          )}
        </div>
      )}

      {/* Footer */}
      {(developer.domains.length > 0 || developer.locations.length > 0) && (
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: 8,
          paddingTop: 10,
          borderTop: '1px solid var(--c-bd)',
          flexWrap: 'wrap',
        }}>
          {developer.domains.slice(0, 2).map(d => (
            <span key={d} className="domain-badge">{d}</span>
          ))}
          {developer.locations.length > 0 && (
            <span style={{ fontSize: 11, color: 'var(--c-subtle)', marginLeft: 'auto' }}>
              {developer.locations[0]}
            </span>
          )}
        </div>
      )}
    </div>
  );
}
