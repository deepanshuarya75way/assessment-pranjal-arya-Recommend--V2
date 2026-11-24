import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';

interface ReviewItem {
  id: string;
  query: string;
  response: string;
  mode: string;
  is_useful: boolean;
  comment?: string | null;
  created_at: string;
}

interface FeedbackResponse {
  summary: {
    total: number;
    useful: number;
    not_useful: number;
    approval_rate: number;
  };
  reviews: ReviewItem[];
}

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export default function ReviewsPage() {
  const [filter, setFilter] = useState<'all' | 'useful' | 'not_useful'>('all');

  const { data, isLoading, isError, refetch } = useQuery<FeedbackResponse>({
    queryKey: ['feedback', filter],
    queryFn: async () => {
      const params = new URLSearchParams();
      if (filter === 'useful') params.set('useful', 'true');
      if (filter === 'not_useful') params.set('useful', 'false');

      const queryString = params.toString();
      const url = `${API_BASE}/api/feedback${queryString ? `?${queryString}` : ''}`;

      const res = await fetch(url);
      if (!res.ok) throw new Error('Failed to load reviews');
      return res.json();
    },
  });

  const summary = data?.summary;
  const reviews = data?.reviews ?? [];

  return (
    <div style={{ maxWidth: 1024, margin: '0 auto', padding: '32px 20px' }}>
      
      <div style={{
        display: 'flex',
        flexWrap: 'wrap',
        alignItems: 'center',
        justifyContent: 'space-between',
        gap: 16,
        marginBottom: 24,
        marginTop: 12,
      }}>
        <div>
          <h1 style={{ fontSize: 20, fontWeight: 600, color: 'var(--c-heading)', margin: 0 }}>
            Response Quality Reviews
          </h1>
          <p style={{ fontSize: 13, color: 'var(--c-subtle)', marginTop: 4 }}>
            User ratings on AI chat and knowledge graph search responses
          </p>
        </div>

        <div style={{ display: 'flex', gap: 6 }}>
          {([
            { id: 'all', label: 'All-Reviews' },
            { id: 'useful', label: 'Useful' },
            { id: 'not_useful', label: 'Not Useful' },
          ] as const).map((tab) => {
            const active = filter === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setFilter(tab.id)}
                style={{
                  padding: '6px 14px',
                  borderRadius: 6,
                  fontSize: 13,
                  fontWeight: 500,
                  cursor: 'pointer',
                  border: `1px solid ${active ? '#5b6cf9' : 'var(--c-bd)'}`,
                  background: active ? '#5b6cf9' : 'var(--c-bg3)',
                  color: active ? '#ffffff' : 'var(--c-subtle)',
                  transition: 'all 0.15s',
                }}
              >
                {tab.label}
              </button>
            );
          })}
        </div>
      </div>

      
      {summary && (
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
          gap: 12,
          marginBottom: 24,
        }}>
          {[
            { label: 'Total Reviews', value: summary.total, color: 'var(--c-heading)' },
            { label: 'Useful', value: summary.useful, color: '#10b981' },
            { label: 'Not Useful', value: summary.not_useful, color: '#f43f5e' },
            { label: 'Approval Rate', value: `${summary.approval_rate}%`, color: '#5b6cf9' },
          ].map((stat) => (
            <div
              key={stat.label}
              style={{
                padding: 16,
                borderRadius: 8,
                background: 'var(--c-bg2, var(--c-bg3))',
                border: '1px solid var(--c-bd)',
              }}
            >
              <div style={{ fontSize: 11, fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.04em', color: 'var(--c-dim)' }}>
                {stat.label}
              </div>
              <div style={{ fontSize: 24, fontWeight: 700, color: stat.color, marginTop: 4 }}>
                {stat.value}
              </div>
            </div>
          ))}
        </div>
      )}

      
      {isLoading ? (
        <div style={{ padding: 48, textAlign: 'center', fontSize: 13, color: 'var(--c-subtle)' }}>
          Loading user reviews...
        </div>
      ) : isError ? (
        <div style={{
          padding: 16,
          borderRadius: 8,
          background: 'rgba(244, 63, 94, 0.1)',
          border: '1px solid rgba(244, 63, 94, 0.3)',
          color: '#f43f5e',
          fontSize: 13,
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
        }}>
          <span>Could not fetch reviews from the backend.</span>
          <button
            onClick={() => refetch()}
            style={{ background: 'none', border: 'none', color: '#f43f5e', textDecoration: 'underline', cursor: 'pointer' }}
          >
            Retry
          </button>
        </div>
      ) : reviews.length === 0 ? (
        <div style={{
          padding: 48,
          textAlign: 'center',
          borderRadius: 8,
          border: '1px dashed var(--c-bd)',
          color: 'var(--c-subtle)',
          fontSize: 13,
        }}>
          No reviews recorded for this filter yet.
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          {reviews.map((item) => (
            <div
              key={item.id}
              style={{
                padding: 18,
                borderRadius: 8,
                background: 'var(--c-bg2, var(--c-bg3))',
                border: '1px solid var(--c-bd)',
                display: 'flex',
                flexDirection: 'column',
                gap: 12,
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 8 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <span style={{
                    padding: '2px 10px',
                    borderRadius: 999,
                    fontSize: 12,
                    fontWeight: 600,
                    background: item.is_useful ? 'rgba(16, 185, 129, 0.15)' : 'rgba(244, 63, 94, 0.15)',
                    color: item.is_useful ? '#10b981' : '#f43f5e',
                  }}>
                    {item.is_useful ? 'Useful' : 'Not Useful'}
                  </span>
                  <span style={{
                    padding: '2px 8px',
                    borderRadius: 4,
                    fontSize: 11,
                    fontFamily: 'monospace',
                    textTransform: 'uppercase',
                    background: 'var(--c-bg3)',
                    border: '1px solid var(--c-bd)',
                    color: 'var(--c-dim)',
                  }}>
                    {item.mode}
                  </span>
                </div>
                <span style={{ fontSize: 12, color: 'var(--c-dim)' }}>
                  {new Date(item.created_at).toLocaleString()}
                </span>
              </div>

              <div>
                <div style={{ fontSize: 11, fontWeight: 600, textTransform: 'uppercase', color: 'var(--c-dim)', marginBottom: 4 }}>
                  User Query
                </div>
                <div style={{ fontSize: 14, fontWeight: 500, color: 'var(--c-heading)' }}>
                  {item.query}
                </div>
              </div>

              <div>
                <div style={{ fontSize: 11, fontWeight: 600, textTransform: 'uppercase', color: 'var(--c-dim)', marginBottom: 4 }}>
                  System Response
                </div>
                <div style={{
                  fontSize: 13,
                  lineHeight: 1.5,
                  padding: 12,
                  borderRadius: 6,
                  background: 'var(--c-bg)',
                  border: '1px solid var(--c-bd)',
                  color: 'var(--c-subtle)',
                  whiteSpace: 'pre-wrap',
                }}>
                  {item.response}
                </div>
              </div>

              {item.comment && (
                <div>
                  <div style={{ fontSize: 11, fontWeight: 600, textTransform: 'uppercase', color: 'var(--c-dim)', marginBottom: 2 }}>
                    User Note
                  </div>
                  <div style={{ fontSize: 13, fontStyle: 'italic', color: 'var(--c-subtle)' }}>
                    "{item.comment}"
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
