import { useNavigate } from 'react-router-dom';
import type { Project } from '../types';

interface ProjectCardProps {
  project: Project;
  index?: number;
}

export default function ProjectCard({ project, index = 0 }: ProjectCardProps) {
  const navigate = useNavigate();

  return (
    <div
      id={`project-card-${project.name.replace(/\s+/g, '-').toLowerCase()}`}
      onClick={() => navigate(`/project/${encodeURIComponent(project.name)}`)}
      className="fade-in"
      style={{
        background: 'var(--c-bg2)',
        border: '1px solid var(--c-bd)',
        borderRadius: 8,
        padding: '16px 18px',
        cursor: 'pointer',
        transition: 'border-color 0.15s, box-shadow 0.15s',
        animationDelay: `${index * 0.04}s`,
        display: 'flex',
        flexDirection: 'column',
        gap: 10,
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
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 8 }}>
        <div style={{ flex: 1, minWidth: 0 }}>
          <h3 style={{
            fontSize: 13,
            fontWeight: 600,
            color: 'var(--c-heading)',
            letterSpacing: '-0.01em',
            lineHeight: 1.4,
            marginBottom: 3,
          }}>
            {project.name}
          </h3>
          {project.tagline && (
            <p style={{ fontSize: 12, color: 'var(--c-dim)', lineHeight: 1.5 }}>
              {project.tagline.length > 90 ? project.tagline.slice(0, 90) + '…' : project.tagline}
            </p>
          )}
        </div>
        {project.relevance_score > 0 && (
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
            {project.relevance_score.toFixed(0)}
          </div>
        )}
      </div>

      {/* Technologies */}
      {project.technologies.length > 0 && (
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
          {project.technologies.slice(0, 5).map(tech => (
            <span key={tech} className="tech-badge">{tech}</span>
          ))}
          {project.technologies.length > 5 && (
            <span className="tech-badge" style={{ opacity: 0.5 }}>+{project.technologies.length - 5}</span>
          )}
        </div>
      )}

      {/* Footer */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        paddingTop: 8,
        borderTop: '1px solid var(--c-bd)',
        gap: 8,
        flexWrap: 'wrap',
      }}>
        <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
          {project.domains.slice(0, 2).map(d => (
            <span key={d} className="domain-badge">{d}</span>
          ))}
        </div>
        <div style={{ display: 'flex', gap: 10, fontSize: 11, color: 'var(--c-subtle)' }}>
          {project.locations.length > 0 && <span>{project.locations[0]}</span>}
          {project.developers.length > 0 && (
            <span>
              {project.developers[0]}{project.developers.length > 1 && ` +${project.developers.length - 1}`}
            </span>
          )}
        </div>
      </div>
    </div>
  );
}
