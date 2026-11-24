import { useState, useRef, useEffect } from 'react';
import { chatAPI } from '../services/api';
import type { ChatMessage } from '../services/api';

type Mode = 'llm' | 'rag';

interface MessageEntry {
  role: string;
  content: string;
  user_query?: string;
  response_mode?: Mode;
  requested_mode?: Mode;
  feedback?: 'useful' | 'not_useful' | null;
}

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export default function ChatPage() {
  const [messages, setMessages] = useState<MessageEntry[]>([
    {
      role: 'assistant',
      content: 'Hello! I am your local AI expert powered by a 1B LLM and KGraph. Ask me anything about the software projects, developers, technologies, or workcenters!\n\nUse the toggle above to switch between LLM mode (Ollama synthesises an answer) and RAG mode (structured results directly from the database).',
      response_mode: 'llm',
    }
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [mode, setMode] = useState<Mode>('llm');
  const [sources, setSources] = useState<any[]>([]);
  const [expandedSources, setExpandedSources] = useState(false);

  const [commentingIdx, setCommentingIdx] = useState<number | null>(null);
  const [commentText, setCommentText] = useState('');
  const [submittingFeedback, setSubmittingFeedback] = useState<number | null>(null);

  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, loading]);

  const handleSend = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || loading) return;

    const userQuery = input.trim();
    const currentMode = mode;
    setMessages(prev => [...prev, { role: 'user', content: userQuery }]);
    setInput('');
    setLoading(true);
    setExpandedSources(false);

    try {
      const res = await chatAPI.chat({
        messages: messages.filter(m => m.role !== 'system').map(m => ({ role: m.role, content: m.content } as ChatMessage)),
        query: userQuery,
        mode: currentMode,
      });
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: res.answer,
        user_query: userQuery,
        response_mode: res.response_mode ?? currentMode,
        requested_mode: currentMode,
        feedback: null,
      }]);
      if (res.sources && res.sources.length > 0) {
        setSources(res.sources);
      }
    } catch (err: any) {
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: '⚠️ Sorry, I encountered an error connecting to the backend or local LLM server.',
        user_query: userQuery,
        response_mode: 'rag',
        requested_mode: currentMode,
        feedback: null,
      }]);
    } finally {
      setLoading(false);
    }
  };

  const handleFeedback = async (idx: number, isUseful: boolean, comment?: string) => {
    const msg = messages[idx];
    const queryText = msg?.user_query || (idx > 0 ? messages[idx - 1]?.content : 'User Query');
    if (!msg || submittingFeedback === idx) return;

    setSubmittingFeedback(idx);
    try {
      const res = await fetch(`${API_BASE}/api/feedback`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query: queryText,
          response: msg.content,
          mode: msg.response_mode || 'rag',
          is_useful: isUseful,
          comment: comment?.trim() || null,
        }),
      });

      if (res.ok) {
        setMessages(prev =>
          prev.map((m, i) =>
            i === idx ? { ...m, feedback: isUseful ? 'useful' : 'not_useful' } : m
          )
        );
        if (commentingIdx === idx) {
          setCommentingIdx(null);
          setCommentText('');
        }
      }
    } catch (err) {
      console.error('Failed to submit feedback:', err);
    } finally {
      setSubmittingFeedback(null);
    }
  };

  const toggleBase: React.CSSProperties = {
    padding: '6px 16px',
    borderRadius: 20,
    fontSize: 12,
    fontWeight: 600,
    cursor: 'pointer',
    border: 'none',
    transition: 'background 0.2s, color 0.2s',
  };
  const activeStyle: React.CSSProperties = {
    background: '#5b6cf9',
    color: '#fff',
    boxShadow: '0 2px 8px rgba(91,108,249,0.35)',
  };
  const inactiveStyle: React.CSSProperties = {
    background: 'var(--c-bg3)',
    color: 'var(--c-subtle)',
  };

  const badgeStyle = (msg: MessageEntry): React.CSSProperties => {
    const fell_back = msg.requested_mode && msg.response_mode !== msg.requested_mode;
    return {
      display: 'inline-flex',
      alignItems: 'center',
      gap: 4,
      fontSize: 10,
      fontWeight: 700,
      padding: '2px 8px',
      borderRadius: 10,
      letterSpacing: '0.05em',
      textTransform: 'uppercase',
      background: fell_back ? 'rgba(234,179,8,0.12)' : msg.response_mode === 'llm' ? 'rgba(91,108,249,0.12)' : 'rgba(16,185,129,0.12)',
      color: fell_back ? '#ca8a04' : msg.response_mode === 'llm' ? '#5b6cf9' : '#10B981',
      border: `1px solid ${fell_back ? 'rgba(202,138,4,0.25)' : msg.response_mode === 'llm' ? 'rgba(91,108,249,0.25)' : 'rgba(16,185,129,0.25)'}`,
    };
  };

  return (
    <div style={{
      maxWidth: 900,
      margin: '0 auto',
      padding: '24px 20px',
      display: 'flex',
      flexDirection: 'column',
      height: 'calc(100vh - 56px)',
    }}>
      <style>{`
        @keyframes pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.4; }
        }
      `}</style>

      {/* Header */}
      <div style={{
        marginBottom: 20,
        padding: '16px 24px',
        borderRadius: 16,
        background: 'var(--c-bg2)',
        border: '1px solid var(--c-bd)',
        boxShadow: '0 4px 20px rgba(0,0,0,0.05)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        flexWrap: 'wrap',
        gap: 12,
      }}>
        <div>
          <h1 style={{ fontSize: 20, fontWeight: 700, color: 'var(--c-heading)', margin: 0, display: 'flex', alignItems: 'center', gap: 8 }}>
            <span style={{ display: 'inline-block', width: 10, height: 10, borderRadius: '50%', background: '#10B981' }}></span>
            Local AI Chat Assistant
          </h1>
          <p style={{ fontSize: 13, color: 'var(--c-subtle)', margin: '4px 0 0 0' }}>
            Powered by local 1B LLM + software_knowledge_graph_data.csv (RAG)
          </p>
        </div>
        {/* Mode toggle */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{ fontSize: 11, color: 'var(--c-subtle)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            Mode
          </span>
          <div style={{
            display: 'flex',
            background: 'var(--c-bg3)',
            border: '1px solid var(--c-bd)',
            borderRadius: 24,
            padding: 3,
            gap: 2,
          }}>
            <button
              id="mode-llm-btn"
              onClick={() => setMode('llm')}
              style={{ ...toggleBase, ...(mode === 'llm' ? activeStyle : inactiveStyle) }}
              title="LLM mode: Ollama synthesises a natural language answer from the RAG context. Falls back to RAG if Ollama is unavailable."
            >
              LLM -LOCAL
            </button>
            <button
              id="mode-rag-btn"
              onClick={() => setMode('rag')}
              style={{ ...toggleBase, ...(mode === 'rag' ? { background: '#10B981', color: '#fff', boxShadow: '0 2px 8px rgba(16,185,129,0.35)' } : inactiveStyle) }}
              title="RAG mode: Returns structured results directly from the database without calling the LLM."
            >
              RAG
            </button>
          </div>
          <div style={{
            fontSize: 11,
            fontWeight: 600,
            background: mode === 'llm' ? 'rgba(91,108,249,0.1)' : 'rgba(16,185,129,0.1)',
            color: mode === 'llm' ? '#5b6cf9' : '#10B981',
            padding: '4px 10px',
            borderRadius: 20,
            border: `1px solid ${mode === 'llm' ? 'rgba(91,108,249,0.2)' : 'rgba(16,185,129,0.2)'}`,
          }}>
            {mode === 'llm' ? '1B Local Engine' : 'Direct DB Lookup'}
          </div>
        </div>
      </div>

      {/* Chat Messages Panel */}
      <div style={{
        flex: 1,
        overflowY: 'auto',
        padding: '20px 24px',
        borderRadius: 16,
        background: 'var(--c-bg2)',
        border: '1px solid var(--c-bd)',
        boxShadow: 'inset 0 2px 4px rgba(0,0,0,0.02)',
        display: 'flex',
        flexDirection: 'column',
        gap: 16,
        marginBottom: 20,
      }}>
        {messages.map((msg, idx) => {
          const isUser = msg.role === 'user';
          const fellBack = !isUser && msg.requested_mode && msg.response_mode !== msg.requested_mode;

          return (
            <div key={idx} style={{
              display: 'flex',
              flexDirection: 'column',
              alignItems: isUser ? 'flex-end' : 'flex-start',
            }}>
              <div style={{
                fontSize: 12,
                fontWeight: 600,
                color: 'var(--c-subtle)',
                marginBottom: 4,
                padding: '0 4px',
              }}>
                {isUser ? 'You' : 'AI Assistant'}
              </div>

              <div style={{
                maxWidth: '85%',
                padding: '14px 18px',
                borderRadius: isUser ? '16px 16px 4px 16px' : '16px 16px 16px 4px',
                background: isUser ? '#5b6cf9' : 'var(--c-bg3)',
                color: isUser ? '#ffffff' : 'var(--c-heading)',
                fontSize: 14,
                lineHeight: 1.6,
                boxShadow: isUser ? '0 4px 12px rgba(91, 108, 249, 0.25)' : '0 2px 8px rgba(0,0,0,0.05)',
                border: isUser ? 'none' : '1px solid var(--c-bd)',
                whiteSpace: 'pre-wrap',
              }}>
                {msg.content}
              </div>

              {/* Response mode badge + Useful / Not Useful feedback buttons */}
              {!isUser && (
                <div style={{
                  display: 'flex',
                  alignItems: 'center',
                  flexWrap: 'wrap',
                  gap: 8,
                  marginTop: 6,
                  maxWidth: '85%',
                }}>
                  {msg.response_mode && (
                    <div style={badgeStyle(msg)}>
                      {msg.response_mode === 'llm' ? '🤖' : '🗄️'}
                      {msg.response_mode.toUpperCase()}
                      {fellBack && ' · auto-fallback'}
                    </div>
                  )}

                  {idx > 0 && (
                    <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                      {msg.feedback ? (
                        <span style={{
                          fontSize: 11,
                          fontWeight: 600,
                          color: msg.feedback === 'useful' ? '#10B981' : '#f43f5e',
                        }}>
                          {msg.feedback === 'useful' ? '✓ Marked Useful' : '✕ Marked Not Useful'}
                        </span>
                      ) : (
                        <>
                          <span style={{ fontSize: 11, color: 'var(--c-dim)' }}>Helpful?</span>
                          <button
                            type="button"
                            disabled={submittingFeedback === idx}
                            onClick={() => handleFeedback(idx, true)}
                            style={{
                              padding: '3px 9px',
                              borderRadius: 6,
                              fontSize: 11,
                              fontWeight: 600,
                              cursor: 'pointer',
                              border: '1px solid rgba(16,185,129,0.35)',
                              background: 'rgba(16,185,129,0.1)',
                              color: '#10B981',
                            }}
                          >
                            👍 Useful
                          </button>
                          <button
                            type="button"
                            disabled={submittingFeedback === idx}
                            onClick={() => {
                              setCommentingIdx(commentingIdx === idx ? null : idx);
                              setCommentText('');
                            }}
                            style={{
                              padding: '3px 9px',
                              borderRadius: 6,
                              fontSize: 11,
                              fontWeight: 600,
                              cursor: 'pointer',
                              border: '1px solid rgba(244,63,94,0.35)',
                              background: 'rgba(244,63,94,0.1)',
                              color: '#f43f5e',
                            }}
                          >
                            👎 Not Useful
                          </button>
                        </>
                      )}
                    </div>
                  )}
                </div>
              )}
              {/* Optional Feedback Comment Box when "Not Useful" is clicked */}
              {!isUser && commentingIdx === idx && !msg.feedback && (
                <div style={{
                  marginTop: 8,
                  padding: 10,
                  borderRadius: 10,
                  background: 'var(--c-bg3)',
                  border: '1px solid var(--c-bd)',
                  width: '100%',
                  maxWidth: '85%',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: 8,
                }}>
                  <input
                    type="text"
                    value={commentText}
                    onChange={e => setCommentText(e.target.value)}
                    placeholder="Optional: What was missing or inaccurate?"
                    style={{
                      width: '100%',
                      padding: '6px 10px',
                      borderRadius: 6,
                      border: '1px solid var(--c-bd)',
                      background: 'var(--c-bg)',
                      color: 'var(--c-heading)',
                      fontSize: 12,
                      outline: 'none',
                    }}
                  />
                  <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 6 }}>
                    <button
                      type="button"
                      onClick={() => setCommentingIdx(null)}
                      style={{
                        padding: '4px 10px',
                        borderRadius: 6,
                        fontSize: 11,
                        background: 'transparent',
                        border: '1px solid var(--c-bd)',
                        color: 'var(--c-subtle)',
                        cursor: 'pointer',
                      }}
                    >
                      Cancel
                    </button>
                    <button
                      type="button"
                      disabled={submittingFeedback === idx}
                      onClick={() => handleFeedback(idx, false, commentText)}
                      style={{
                        padding: '4px 10px',
                        borderRadius: 6,
                        fontSize: 11,
                        fontWeight: 600,
                        background: '#f43f5e',
                        border: 'none',
                        color: '#fff',
                        cursor: 'pointer',
                      }}
                    >
                      {submittingFeedback === idx ? 'Saving...' : 'Submit Review'}
                    </button>
                  </div>
                </div>
              )}

              {/* RAG sources accordion on the latest AI response */}
              {!isUser && idx === messages.length - 1 && sources.length > 0 && (
                <div style={{ marginTop: 12, width: '100%', maxWidth: '85%' }}>
                  <button
                    onClick={() => setExpandedSources(!expandedSources)}
                    style={{
                      background: 'var(--c-bg3)',
                      border: '1px solid var(--c-bd)',
                      color: 'var(--c-subtle)',
                      padding: '8px 14px',
                      borderRadius: 8,
                      fontSize: 12,
                      fontWeight: 600,
                      cursor: 'pointer',
                      display: 'flex',
                      alignItems: 'center',
                      gap: 6,
                      transition: 'color 0.15s, border-color 0.15s'
                    }}
                    onMouseEnter={e => { e.currentTarget.style.color = 'var(--c-heading)'; e.currentTarget.style.borderColor = 'var(--c-bd2)'; }}
                    onMouseLeave={e => { e.currentTarget.style.color = 'var(--c-subtle)'; e.currentTarget.style.borderColor = 'var(--c-bd)'; }}
                  >
                    <svg width="14" height="14" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    {expandedSources ? 'Hide RAG Context Sources' : `View RAG Context Sources (${sources.length})`}
                  </button>

                  {expandedSources && (
                    <div style={{
                      marginTop: 8,
                      padding: 16,
                      borderRadius: 12,
                      background: 'var(--c-bg)',
                      border: '1px solid var(--c-bd)',
                      display: 'flex',
                      flexDirection: 'column',
                      gap: 12,
                    }}>
                      {sources.map((src, sIdx) => (
                        <div key={sIdx} style={{ padding: 12, borderRadius: 8, background: 'var(--c-bg2)', border: '1px solid var(--c-bd)' }}>
                          <div style={{ fontSize: 14, fontWeight: 700, color: 'var(--c-heading)', marginBottom: 4 }}>
                            {src['Software Name'] || 'Unnamed Software'}
                          </div>
                          <div style={{ fontSize: 13, color: 'var(--c-subtle)', marginBottom: 8 }}>
                            {src['Short Description'] || src['Detailed Description']}
                          </div>
                          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                            {src['Categories'] && (
                              <span style={{ fontSize: 11, background: 'var(--c-bg3)', color: '#10B981', padding: '2px 8px', borderRadius: 4, border: '1px solid var(--c-bd)' }}>
                                {src['Categories']}
                              </span>
                            )}
                            {src['Technologies'] && (
                              <span style={{ fontSize: 11, background: 'var(--c-bg3)', color: '#3B82F6', padding: '2px 8px', borderRadius: 4, border: '1px solid var(--c-bd)' }}>
                                {src['Technologies']}
                              </span>
                            )}
                            {src['Developer Names'] && (
                              <span style={{ fontSize: 11, background: 'var(--c-bg3)', color: '#8B5CF6', padding: '2px 8px', borderRadius: 4, border: '1px solid var(--c-bd)' }}>
                                By: {src['Developer Names']}
                              </span>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>
          );
        })}

        {loading && (
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, color: 'var(--c-subtle)', fontSize: 13, padding: '10px 14px', background: 'var(--c-bg3)', borderRadius: '18px 18px 18px 4px', width: 'fit-content', border: '1px solid var(--c-bd)' }}>
            <span style={{ animation: 'pulse 1.5s infinite ease-in-out', width: 8, height: 8, borderRadius: '50%', background: mode === 'llm' ? '#5b6cf9' : '#10B981' }}></span>
            {mode === 'llm' ? 'AI is thinking & searching database...' : 'Searching database...'}
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input Bar */}
      <form onSubmit={handleSend} style={{
        display: 'flex',
        gap: 12,
        padding: '10px 14px',
        borderRadius: 16,
        background: 'var(--c-bg2)',
        border: `1px solid ${mode === 'llm' ? 'var(--c-bd)' : 'rgba(16,185,129,0.25)'}`,
        boxShadow: '0 4px 20px rgba(0,0,0,0.05)',
        transition: 'border-color 0.2s',
      }}>
        <input
          type="text"
          value={input}
          onChange={e => setInput(e.target.value)}
          placeholder={mode === 'llm'
            ? 'Ask about any software project, developer, technology, or location...'
            : 'Query the database directly (e.g. "python projects in Delhi")...'
          }
          style={{
            flex: 1,
            background: 'transparent',
            border: 'none',
            outline: 'none',
            color: 'var(--c-heading)',
            fontSize: 15,
            padding: '4px 8px',
          }}
        />
        <button
          type="submit"
          disabled={loading || !input.trim()}
          style={{
            background: loading || !input.trim()
              ? 'var(--c-bg3)'
              : mode === 'llm' ? '#5b6cf9' : '#10B981',
            color: loading || !input.trim() ? 'var(--c-dim)' : '#ffffff',
            border: loading || !input.trim() ? '1px solid var(--c-bd)' : 'none',
            padding: '10px 22px',
            borderRadius: 12,
            fontSize: 14,
            fontWeight: 600,
            cursor: loading || !input.trim() ? 'not-allowed' : 'pointer',
            transition: 'background 0.2s, color 0.2s',
          }}
        >
          Send
        </button>
      </form>
    </div>
  );
}
