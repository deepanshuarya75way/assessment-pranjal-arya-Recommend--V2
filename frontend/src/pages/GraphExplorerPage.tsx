import { useQuery } from '@tanstack/react-query';
import { graphAPI } from '../services/api';
import { useRef, useCallback, useEffect, useState, useMemo } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { useTheme } from '../context/ThemeContext';
import ForceGraph2D from 'react-force-graph-2d';

const NODE_COLORS: Record<string, string> = {
  Developer: '#6366f1',
  Project: '#06b6d4',
  Technology: '#f59e0b',
  Domain: '#10b981',
  Location: '#ef4444',
};

const NODE_SIZES: Record<string, number> = {
  Developer: 8,
  Project: 6,
  Technology: 4,
  Domain: 5,
  Location: 4.5,
};

export default function GraphExplorerPage() {
  const { isDark } = useTheme();
  const [searchParams] = useSearchParams();
  const focusName = searchParams.get('q') || '';

  const [searchQuery, setSearchQuery] = useState(focusName);
  const [debouncedQuery, setDebouncedQuery] = useState(focusName);
  const [autoFocusDone, setAutoFocusDone] = useState(false);

  useEffect(() => {
    const timer = setTimeout(() => setDebouncedQuery(searchQuery), 500);
    return () => clearTimeout(timer);
  }, [searchQuery]);

  const { data, isLoading, error } = useQuery({
    queryKey: ['graph', debouncedQuery],
    queryFn: () => graphAPI.get(debouncedQuery || undefined),
  });

  const graphRef = useRef<any>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [dimensions, setDimensions] = useState({ width: 800, height: 600 });
  const [hoveredNode, setHoveredNode] = useState<any>(null);
  const [selectedNode, setSelectedNode] = useState<any>(null);
  const [selectedType, setSelectedType] = useState<string | null>(null);

  useEffect(() => {
    const updateSize = () => {
      if (containerRef.current) {
        setDimensions({
          width: containerRef.current.offsetWidth,
          height: window.innerHeight - 160,
        });
      }
    };
    updateSize();
    window.addEventListener('resize', updateSize);
    return () => window.removeEventListener('resize', updateSize);
  }, []);

  const graphData = useMemo(() => {
    return data ? {
      nodes: data.nodes
        .filter(n => !selectedType || n.type === selectedType)
        .map(n => ({
          ...n,
          val: NODE_SIZES[n.type] || 5,
          color: NODE_COLORS[n.type] || '#94a3b8',
        })),
      links: data.links.filter(l => {
        if (!selectedType) return true;
        const sourceNode = data.nodes.find(n => n.id === l.source);
        const targetNode = data.nodes.find(n => n.id === l.target);
        return sourceNode?.type === selectedType || targetNode?.type === selectedType;
      }),
    } : { nodes: [], links: [] };
  }, [data, selectedType]);

  const handleNodeClick = useCallback((node: any) => {
    if (graphRef.current) {
      graphRef.current.centerAt(node.x, node.y, 500);
      graphRef.current.zoom(3, 500);
    }
    setSelectedNode(node);
  }, []);

  // Auto-focus: after graph data loads and focusName is set, select + zoom to matching node
  useEffect(() => {
    if (!focusName || autoFocusDone || !data || graphData.nodes.length === 0) return;
    const target = graphData.nodes.find(
      (n: any) => n.label?.toLowerCase() === focusName.toLowerCase()
    ) || graphData.nodes.find(
      (n: any) => n.label?.toLowerCase().includes(focusName.toLowerCase())
    );
    if (!target) return;
    // Small delay to let force-graph settle its initial layout
    const t = setTimeout(() => {
      if (graphRef.current && target.x !== undefined) {
        graphRef.current.centerAt(target.x, target.y, 800);
        graphRef.current.zoom(4, 800);
      }
      setSelectedNode(target);
      setAutoFocusDone(true);
    }, 1200);
    return () => clearTimeout(t);
  }, [focusName, autoFocusDone, data, graphData]);

  const connectedNodes = useMemo(() => {
    if (!selectedNode || !data) return [];
    const connected = new Map<string, any>();
    data.links.forEach((link: any) => {
      const sourceId = typeof link.source === 'object' ? link.source.id : link.source;
      const targetId = typeof link.target === 'object' ? link.target.id : link.target;
      const selectedId = selectedNode.id;
      if (sourceId === selectedId) {
        const targetNode = data.nodes.find((n: any) => n.id === targetId);
        if (targetNode) connected.set(targetNode.id, targetNode);
      } else if (targetId === selectedId) {
        const sourceNode = data.nodes.find((n: any) => n.id === sourceId);
        if (sourceNode) connected.set(sourceNode.id, sourceNode);
      }
    });
    return Array.from(connected.values());
  }, [selectedNode, data]);

  const nodeCanvasObject = useCallback((node: any, ctx: CanvasRenderingContext2D, globalScale: number) => {
    const label = node.label || '';
    const size = node.val || 5;
    const isHovered = hoveredNode?.id === node.id;
    const isSelected = selectedNode?.id === node.id;

    // Node circle
    ctx.beginPath();
    ctx.arc(node.x, node.y, size * (isHovered || isSelected ? 1.4 : 1), 0, 2 * Math.PI);
    ctx.fillStyle = node.color || '#94a3b8';
    ctx.globalAlpha = isHovered || isSelected ? 1 : 0.85;
    ctx.fill();
    ctx.globalAlpha = 1;

    // Glow effect
    if (isHovered || isSelected) {
      ctx.beginPath();
      ctx.arc(node.x, node.y, size * 2.2, 0, 2 * Math.PI);
      ctx.fillStyle = (node.color || '#94a3b8') + (isSelected ? '45' : '22');
      ctx.fill();
    }

    // Selected border ring
    if (isSelected) {
      ctx.beginPath();
      ctx.arc(node.x, node.y, size * 1.6, 0, 2 * Math.PI);
      ctx.strokeStyle = '#ffffff';
      ctx.lineWidth = 2 / globalScale;
      ctx.stroke();
    }

    // Label (only show at sufficient zoom or when hovered/selected)
    if (globalScale > 0.8 || isHovered || isSelected) {
      const fontSize = Math.max(10 / globalScale, 2);
      ctx.font = `${isHovered || isSelected ? 'bold ' : ''}${fontSize}px Inter, sans-serif`;
      ctx.textAlign = 'center';
      ctx.textBaseline = 'top';
      
      const textColor = isDark
        ? (isHovered || isSelected ? '#f8fafc' : '#94a3b8')
        : (isHovered || isSelected ? '#0f172a' : '#475569');

      ctx.fillStyle = textColor;
      ctx.fillText(label, node.x, node.y + size + (isSelected ? 4 : 2));
    }
  }, [hoveredNode, selectedNode, isDark]);

  return (
    <div className="min-h-[calc(100vh-4rem)]">
      {/* Header */}
      <div className="px-4 sm:px-6 lg:px-8 py-6 max-w-7xl mx-auto">
        <div className="flex items-center justify-between mb-4">
          <div>
            <div className="flex items-center gap-3 flex-wrap">
              <h1 className="text-2xl font-bold text-surface-100">Knowledge Graph Explorer</h1>
              {focusName && (
                <span
                  className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold"
                  style={{
                    background: 'rgba(99,102,241,0.15)',
                    color: '#818cf8',
                    border: '1px solid rgba(99,102,241,0.35)',
                  }}
                >
                  <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <circle cx="11" cy="11" r="8" strokeWidth={2}/>
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-4.35-4.35"/>
                  </svg>
                  Focused: {focusName}
                </span>
              )}
            </div>
            <p className="text-sm text-surface-500 mt-1">
              {focusName
                ? `Showing graph filtered to "${focusName}" — zoom in to explore connections`
                : 'Interactive visualization of the project-developer-technology knowledge graph'}
            </p>
          </div>
          {data && (
            <div className="flex items-center gap-3 text-sm text-surface-500">
              <span>{data.nodes.length} nodes</span>
              <span>•</span>
              <span>{data.links.length} edges</span>
            </div>
          )}
        </div>

        {/* Search & Filters */}
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 mb-4">
          <div className="w-full sm:max-w-xs">
            <div className="relative">
              <input
                type="text"
                placeholder="Filter graph by keyword, tech, domain..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full bg-surface-800/50 border border-surface-700 rounded-lg py-2 pl-10 pr-4 text-sm text-surface-100 placeholder-surface-500 focus:outline-none focus:ring-2 focus:ring-primary-500"
              />
              <svg className="absolute left-3 top-2.5 h-4 w-4 text-surface-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
              </svg>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-2">
          <button
            onClick={() => setSelectedType(null)}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all
              ${!selectedType
                ? 'bg-surface-600/50 text-surface-100 border border-surface-500/30'
                : 'text-surface-400 hover:text-surface-200 border border-transparent'
              }
            `}
          >
            All
          </button>
          {Object.entries(NODE_COLORS).map(([type, color]) => (
            <button
              key={type}
              onClick={() => setSelectedType(selectedType === type ? null : type)}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all
                ${selectedType === type
                  ? 'bg-surface-700/50 text-surface-100 border border-surface-500/30'
                  : 'text-surface-400 hover:text-surface-200 border border-transparent'
                }
              `}
            >
              <span className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: color }} />
              {type}
            </button>
          ))}
          </div>
        </div>
      </div>

      {/* Graph Container */}
      <div ref={containerRef} className="relative border-t border-surface-800">
        {isLoading && (
          <div className="absolute inset-0 flex items-center justify-center bg-surface-950/80 z-10">
            <div className="text-center">
              <div className="w-12 h-12 border-4 border-primary-500/30 border-t-primary-500 rounded-full animate-spin mx-auto mb-4" />
              <p className="text-surface-400">Loading graph data...</p>
            </div>
          </div>
        )}

        {error && (
          <div className="absolute inset-0 flex items-center justify-center z-10" style={{ background: 'rgba(10,10,10,0.85)' }}>
            <div className="text-center">
              <p style={{ fontSize: 13, color: '#555' }}>Unable to load graph. Make sure the backend is running.</p>
            </div>
          </div>
        )}

        {data && (
          <ForceGraph2D
            ref={graphRef}
            graphData={graphData}
            width={dimensions.width}
            height={dimensions.height}
            backgroundColor="transparent"
            nodeCanvasObject={nodeCanvasObject}
            onNodeClick={handleNodeClick}
            onNodeHover={(node: any) => setHoveredNode(node)}
            linkColor={(link: any) => {
              const sourceId = typeof link.source === 'object' ? link.source.id : link.source;
              const targetId = typeof link.target === 'object' ? link.target.id : link.target;
              const isRelevant = 
                (hoveredNode && (sourceId === hoveredNode.id || targetId === hoveredNode.id)) ||
                (selectedNode && (sourceId === selectedNode.id || targetId === selectedNode.id));
              
              if (isRelevant) {
                return isDark ? 'rgba(99, 102, 241, 0.8)' : 'rgba(79, 70, 229, 0.85)';
              }
              return isDark ? 'rgba(148, 163, 184, 0.35)' : 'rgba(71, 85, 105, 0.3)';
            }}
            linkWidth={(link: any) => {
              const sourceId = typeof link.source === 'object' ? link.source.id : link.source;
              const targetId = typeof link.target === 'object' ? link.target.id : link.target;
              const isRelevant = 
                (hoveredNode && (sourceId === hoveredNode.id || targetId === hoveredNode.id)) ||
                (selectedNode && (sourceId === selectedNode.id || targetId === selectedNode.id));
              
              return isRelevant ? 2.0 : 0.8;
            }}
            linkDirectionalArrowLength={3}
            linkDirectionalArrowRelPos={1}
            d3AlphaDecay={0.02}
            d3VelocityDecay={0.3}
            cooldownTicks={100}
            enableZoomInteraction={true}
            enablePanInteraction={true}
          />
        )}

        {/* Hovered Node Info */}
        {hoveredNode && !selectedNode && (
          <div className="absolute bottom-4 left-4 glass rounded-xl px-4 py-3 z-20 max-w-xs pointer-events-none">
            <div className="flex items-center gap-2 mb-1">
              <span
                className="w-3 h-3 rounded-full"
                style={{ backgroundColor: NODE_COLORS[hoveredNode.type] }}
              />
              <span className="text-sm font-semibold text-[var(--c-heading)]">{hoveredNode.label}</span>
            </div>
            <span className="text-xs text-[var(--c-dim)]">{hoveredNode.type}</span>
          </div>
        )}

        {/* Selected Node Detail Panel */}
        {selectedNode && (
          <div className="absolute top-4 right-4 z-20 w-80 md:w-96 max-h-[calc(100%-2rem)] overflow-y-auto glass rounded-xl shadow-2xl p-5 border border-[var(--c-bd)] animate-fade-in-up">
            <div className="flex items-start justify-between mb-4">
              <div>
                <span
                  className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider mb-2"
                  style={{
                    backgroundColor: NODE_COLORS[selectedNode.type] + '20',
                    color: NODE_COLORS[selectedNode.type],
                    border: `1px solid ${NODE_COLORS[selectedNode.type]}40`,
                  }}
                >
                  {selectedNode.type}
                </span>
                <h3 className="text-lg font-bold text-[var(--c-heading)] leading-tight">{selectedNode.label}</h3>
              </div>
              <button
                onClick={() => setSelectedNode(null)}
                className="text-[var(--c-dim)] hover:text-[var(--c-heading)] p-1 rounded-lg hover:bg-[var(--c-bg3)] transition-colors"
                aria-label="Close panel"
              >
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            {/* Properties */}
            <div className="space-y-3 text-sm">
              {selectedNode.type === 'Developer' && (
                <>
                  <div className="bg-[var(--c-bg3)]/50 rounded-lg p-3 border border-[var(--c-bd)]">
                    <span className="text-[10px] text-[var(--c-dim)] block uppercase font-semibold">Biography</span>
                    <p className="text-[var(--c-body)] mt-1 text-xs leading-relaxed">
                      {selectedNode.properties?.bio || 'No biography available.'}
                    </p>
                  </div>
                  <div className="flex items-center justify-between py-1 border-b border-[var(--c-bd)]">
                    <span className="text-xs text-[var(--c-dim)]">Projects Contributed</span>
                    <span className="text-xs font-bold text-[var(--c-heading)]">{selectedNode.properties?.project_count || 0}</span>
                  </div>
                </>
              )}

              {selectedNode.type === 'Project' && (
                <>
                  <div className="bg-[var(--c-bg3)]/50 rounded-lg p-3 border border-[var(--c-bd)]">
                    <span className="text-[10px] text-[var(--c-dim)] block uppercase font-semibold">Description / Tagline</span>
                    <p className="text-[var(--c-body)] mt-1 text-xs leading-relaxed">
                      {selectedNode.properties?.tagline || 'No tagline or description available.'}
                    </p>
                  </div>
                  {selectedNode.properties?.developed_on && (
                    <div className="flex items-center justify-between py-1 border-b border-[var(--c-bd)]">
                      <span className="text-xs text-[var(--c-dim)]">Developed On</span>
                      <span className="text-xs font-bold text-[var(--c-heading)]">{selectedNode.properties.developed_on}</span>
                    </div>
                  )}
                </>
              )}

              {(selectedNode.type === 'Technology' || selectedNode.type === 'Domain' || selectedNode.type === 'Location') && (
                <p className="text-xs text-[var(--c-dim)] leading-relaxed italic">
                  Node representing the {selectedNode.type.toLowerCase()} "{selectedNode.label}". Connects projects with common traits.
                </p>
              )}
            </div>

            {/* Connected Nodes */}
            <div className="mt-5 pt-4 border-t border-[var(--c-bd)]">
              <h4 className="text-xs font-semibold text-[var(--c-dim)] uppercase tracking-wider mb-3">
                Connected Items ({connectedNodes.length})
              </h4>
              {connectedNodes.length > 0 ? (
                <div className="flex flex-wrap gap-2 max-h-48 overflow-y-auto pr-1">
                  {connectedNodes.map((node: any) => (
                    <button
                      key={node.id}
                      onClick={() => {
                        if (graphRef.current) {
                          // Center node coords or current spring coordinates
                          const x = node.x !== undefined ? node.x : 0;
                          const y = node.y !== undefined ? node.y : 0;
                          graphRef.current.centerAt(x, y, 500);
                          graphRef.current.zoom(3, 500);
                        }
                        setSelectedNode(node);
                      }}
                      className="inline-flex items-center gap-1.5 px-2 py-1 rounded bg-[var(--c-bg3)]/60 hover:bg-[var(--c-bg3)] border border-[var(--c-bd)] text-xs text-[var(--c-body)] transition-colors cursor-pointer"
                    >
                      <span className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: NODE_COLORS[node.type] }} />
                      <span className="font-medium text-[var(--c-heading)] max-w-[120px] truncate">{node.label}</span>
                      <span className="text-[9px] text-[var(--c-dim)]">({node.type})</span>
                    </button>
                  ))}
                </div>
              ) : (
                <p className="text-xs text-[var(--c-dim)] italic">No direct connections found in graph view.</p>
              )}
            </div>

            {/* Entity detail page link */}
            {(selectedNode.type === 'Developer' || selectedNode.type === 'Project') && (
              <div className="mt-5 pt-2">
                <Link
                  to={selectedNode.type === 'Developer' 
                    ? `/developer/${encodeURIComponent(selectedNode.label)}` 
                    : `/project/${encodeURIComponent(selectedNode.label)}`
                  }
                  className="flex items-center justify-center gap-1 w-full px-4 py-2 bg-primary-500 hover:bg-primary-600 text-white rounded-lg text-xs font-semibold transition-colors shadow-sm cursor-pointer"
                >
                  <span>Go to Profile Page</span>
                  <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                  </svg>
                </Link>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
