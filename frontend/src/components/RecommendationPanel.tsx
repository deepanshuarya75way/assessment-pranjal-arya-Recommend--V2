import ProjectCard from './ProjectCard';
import DeveloperCard from './DeveloperCard';
import type { Project, Developer } from '../types';

interface RecommendationPanelProps {
  title: string;
  projects?: Project[];
  developers?: Developer[];
}

export default function RecommendationPanel({ title, projects, developers }: RecommendationPanelProps) {
  const hasContent = (projects && projects.length > 0) || (developers && developers.length > 0);

  if (!hasContent) return null;

  return (
    <div style={{ marginTop: 40 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 14 }}>
        <h2 style={{ fontSize: 12, fontWeight: 600, color: 'var(--c-subtle)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
          {title}
        </h2>
      </div>

      {projects && projects.length > 0 && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: 10 }}>
          {projects.map((p, i) => (
            <ProjectCard key={p.name} project={p} index={i} />
          ))}
        </div>
      )}

      {developers && developers.length > 0 && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: 10 }}>
          {developers.map((d, i) => (
            <DeveloperCard key={d.name} developer={d} index={i} />
          ))}
        </div>
      )}
    </div>
  );
}
