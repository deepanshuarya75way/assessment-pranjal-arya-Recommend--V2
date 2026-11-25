 import { useQuery } from '@tanstack/react-query';
import { graphAPI, type ShortestPathResponse } from '../services/api';
import { useRef, useCallback, useEffect, useState, useMemo } from 'react';
import { useSearchParams } from 'react-router-dom';
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

  
  const [sourceId, setSourceId] = useState<string>('');
  const [targetId, setTargetId] = useState<string>('');
  const [maxDepth, setMaxDepth] = useState<number>(4);
  const [weighted, setWeighted] = useState<boolean>(true);
  const [pathResult, setPathResult] = useState<ShortestPathResponse | null>(null);
  const [isFindingPath, setIsFindingPath] = useState<boolean>(false);
  const [pathError, setPathError] = useState<string | null>(null);
const [activeStepIndex, setActiveStepIndex] = useState<number>(0);

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

  // Add alongside your existing state declarations
const [monitoredHops, setMonitoredHops] = useState<Record<string, boolean>>({});
const [isDrawerOpen, setIsDrawerOpen] = useState<boolean>(true);

const toggleMonitorHop = (edgeKey: string) => {
  setMonitoredHops((prev) => ({
    ...prev,
    [edgeKey]: !prev[edgeKey],
  }));
};

// Compute collaboration history & active hop details for the selected path
const pathStepsWithContext = useMemo(() => {
  if (!pathResult?.found || !pathResult.nodes.length) return [];
  return pathResult.nodes.map((node, index) => {
    const incomingEdge = index > 0 ? pathResult.edges[index - 1] : null;
    const outgoingEdge = index < pathResult.edges.length ? pathResult.edges[index] : null;
    const prevNode = index > 0 ? pathResult.nodes[index - 1] : null;
    const nextNode = index < pathResult.nodes.length - 1 ? pathResult.nodes[index + 1] : null;

    return {
      index,
      node,
      prevNode,
      nextNode,
      incomingEdge,
      outgoingEdge,
      hopKey: outgoingEdge ? `${outgoingEdge.source}__${outgoingEdge.target}__${outgoingEdge.type}` : null,
    };
  });
}, [pathResult]);


  useEffect(() => {
    const updateSize = () => {
      if (containerRef.current) {
        setDimensions({
          width: containerRef.current.offsetWidth,
          height: window.innerHeight - 240,
        });
      }
    };
    updateSize();
    window.addEventListener('resize', updateSize);
    return () => window.removeEventListener('resize', updateSize);
  }, []);

  const sortedEntities = useMemo(() => {
    if (!data?.nodes) return [];
    return [...data.nodes].sort((a, b) =>
      a.type === b.type ? a.label.localeCompare(b.label) : a.type.localeCompare(b.type)
    );
  }, [data]);

  const highlightedNodeIds = useMemo(() => {
    if (!pathResult?.found) return new Set<string>();
    return new Set(pathResult.nodes.map((n) => n.id));
  }, [pathResult]);

  const highlightedEdgePairs = useMemo(() => {
    if (!pathResult?.found) return new Set<string>();
    const pairs = new Set<string>();
    pathResult.edges.forEach((e) => {
      pairs.add(`${e.source}__${e.target}`);
      pairs.add(`${e.target}__${e.source}`);
    });
    return pairs;
  }, [pathResult]);

  const handleFindShortestPath = useCallback(async () => {
    if (!sourceId || !targetId) return;
    setIsFindingPath(true);
    setPathError(null);
    setSelectedType(null);

    try {
      const res = await graphAPI.shortestPath(sourceId, targetId, maxDepth, weighted);
      setPathResult(res);

      if (res.found && res.nodes.length > 0 && graphRef.current) {
        const pathIds = new Set(res.nodes.map((n) => n.id));
        setActiveStepIndex(0);
  focusPathStep(0, res.nodes);
        const liveNodes = (graphRef.current.graphData?.().nodes || []).filter(
          (n: any) => pathIds.has(n.id) && n.x !== undefined
        );
        if (liveNodes.length > 0) {
          const avgX = liveNodes.reduce((sum: number, n: any) => sum + n.x, 0) / liveNodes.length;
          const avgY = liveNodes.reduce((sum: number, n: any) => sum + n.y, 0) / liveNodes.length;
          graphRef.current.centerAt(avgX, avgY, 700);
          graphRef.current.zoom(2.4, 700);
        }
      }
    } catch (err: any) {
      setPathError(err?.message || 'Error computing shortest path.');
    } finally {
      setIsFindingPath(false);
    }
  }, [sourceId, targetId, maxDepth, weighted]);

  useEffect(() => {
    if (sourceId && targetId && pathResult !== null) {
      handleFindShortestPath();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [maxDepth, weighted]);

  const handleResetPath = () => {
    setSourceId('');
    setTargetId('');
    setPathResult(null);
    setPathError(null);
    setActiveStepIndex(0);

    if (graphRef.current) {
      graphRef.current.zoomToFit(500, 50);
    }
  };

  const handleSwapEndpoints = () => {
    setSourceId(targetId);
    setTargetId(sourceId);
  };

 const graphData = useMemo(() => {
    return data
      ? {
          nodes: data.nodes
            .filter((n) => !selectedType || n.type === selectedType)
            .map((n) => ({
              ...n,
              val: NODE_SIZES[n.type] || 5,
              color: NODE_COLORS[n.type] || '#94a3b8',
            })),
          links: data.links.filter((l) => {
            if (!selectedType) return true;
            const sId = typeof l.source === 'object' ? (l.source as any).id : l.source;
            const tId = typeof l.target === 'object' ? (l.target as any).id : l.target;
            const sourceNode = data.nodes.find((n) => n.id === sId);
            const targetNode = data.nodes.find((n) => n.id === tId);
            return sourceNode?.type === selectedType || targetNode?.type === selectedType;
          }),
        }
      : { nodes: [], links: [] };
  }, [data, selectedType]);
  const focusPathStep = useCallback(
  (index: number, nodesList = pathResult?.nodes) => {
    if (!nodesList || index < 0 || index >= nodesList.length) return;

    setActiveStepIndex(index);
    const stepNode = nodesList[index];
    const liveNode = graphData.nodes.find((n: any) => n.id === stepNode.id);

    if (liveNode) {
      setSelectedNode(liveNode);
      if (graphRef.current && liveNode.x !== undefined && liveNode.y !== undefined) {
        graphRef.current.centerAt(liveNode.x, liveNode.y, 600);
        graphRef.current.zoom(3.2, 600);
      }
    }
  },
  [pathResult, graphData.nodes]
);


  const handleNodeClick = useCallback((node: any) => {
    if (graphRef.current) {
      graphRef.current.centerAt(node.x, node.y, 500);
      graphRef.current.zoom(3, 500);
    }
    setSelectedNode(node);
  }, []);

  useEffect(() => {
    if (!focusName || autoFocusDone || !data || graphData.nodes.length === 0) return;
    const target =
      graphData.nodes.find((n: any) => n.label?.toLowerCase() === focusName.toLowerCase()) ||
      graphData.nodes.find((n: any) => n.label?.toLowerCase().includes(focusName.toLowerCase()));
    if (!target) return;

    const t = setTimeout(() => {
      if (graphRef.current && (target as any).x !== undefined) {
        graphRef.current.centerAt((target as any).x, (target as any).y, 800);
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
      const sourceIdVal = typeof link.source === 'object' ? link.source.id : link.source;
      const targetIdVal = typeof link.target === 'object' ? link.target.id : link.target;
      const selectedId = selectedNode.id;
      if (sourceIdVal === selectedId) {
        const targetNode = data.nodes.find((n: any) => n.id === targetIdVal);
        if (targetNode) connected.set(targetNode.id, targetNode);
      } else if (targetIdVal === selectedId) {
        const sourceNode = data.nodes.find((n: any) => n.id === sourceIdVal);
        if (sourceNode) connected.set(sourceNode.id, sourceNode);
      }
    });
    return Array.from(connected.values());
  }, [selectedNode, data]);

  const nodeCanvasObject = useCallback(
    (node: any, ctx: CanvasRenderingContext2D, globalScale: number) => {
      const label = node.label || '';
      const baseSize = node.val || 5;
      const isHovered = hoveredNode?.id === node.id;
      const isSelected = selectedNode?.id === node.id;

      const hasActivePath = highlightedNodeIds.size > 0;
      const isInPath = highlightedNodeIds.has(node.id);
      const isPathSource = hasActivePath && node.id === sourceId;
      const isPathTarget = hasActivePath && node.id === targetId;
      const isDimmed = hasActivePath && !isInPath && !isHovered && !isSelected;

      const sizeMultiplier =
        isPathSource || isPathTarget ? 1.6 : isInPath ? 1.35 : isHovered || isSelected ? 1.4 : 1;
      const radius = baseSize * sizeMultiplier;

      // Node circle
      ctx.beginPath();
      ctx.arc(node.x, node.y, radius, 0, 2 * Math.PI);
      ctx.fillStyle = node.color || '#94a3b8';
      ctx.globalAlpha = isDimmed ? 0.14 : isInPath || isHovered || isSelected ? 1 : 0.85;
      ctx.fill();
      ctx.globalAlpha = 1;

      // Glow effect
      if (isInPath || isHovered || isSelected) {
        ctx.beginPath();
        ctx.arc(node.x, node.y, radius * 1.9, 0, 2 * Math.PI);
        const glowColor = isPathSource
          ? '#22c55e'
          : isPathTarget
          ? '#ec4899'
          : isInPath
          ? '#38bdf8'
          : node.color || '#94a3b8';
        ctx.fillStyle = glowColor + '38';
        ctx.fill();
      }

      // Highlight ring border
      if (isPathSource || isPathTarget || isInPath || isSelected) {
        ctx.beginPath();
        ctx.arc(node.x, node.y, radius * 1.25, 0, 2 * Math.PI);
        ctx.strokeStyle = isPathSource
          ? '#22c55e'
          : isPathTarget
          ? '#ec4899'
          : isInPath
          ? '#38bdf8'
          : '#ffffff';
        ctx.lineWidth = (isPathSource || isPathTarget ? 2.5 : 1.8) / globalScale;
        ctx.stroke();
      }

      // Text label
      if (!isDimmed && (globalScale > 0.8 || isInPath || isHovered || isSelected)) {
        const fontSize = Math.max((isInPath ? 11 : 10) / globalScale, 2.2);
        ctx.font = `${isInPath || isHovered || isSelected ? 'bold ' : ''}${fontSize}px Inter, sans-serif`;
        ctx.textAlign = 'center';
        ctx.textBaseline = 'top';

        const textColor = isDark
          ? isInPath || isHovered || isSelected
            ? '#f8fafc'
            : '#94a3b8'
          : isInPath || isHovered || isSelected
          ? '#0f172a'
          : '#475569';

        ctx.fillStyle = textColor;
        ctx.fillText(label, node.x, node.y + radius + 3);
      }
    },
    [hoveredNode, selectedNode, isDark, highlightedNodeIds, sourceId, targetId]
  );

  const isLinkHighlighted = useCallback(
    (link: any) => {
      if (highlightedEdgePairs.size === 0) return false;
      const sId = typeof link.source === 'object' ? link.source.id : link.source;
      const tId = typeof link.target === 'object' ? link.target.id : link.target;
      return highlightedEdgePairs.has(`${sId}__${tId}`);
    },
    [highlightedEdgePairs]
  );

  const getLinkColor = useCallback(
    (link: any) => {
      if (highlightedEdgePairs.size === 0) {
        return isDark ? 'rgba(148, 163, 184, 0.22)' : 'rgba(100, 116, 139, 0.25)';
      }
      return isLinkHighlighted(link)
        ? '#38bdf8'
        : isDark
        ? 'rgba(148, 163, 184, 0.05)'
        : 'rgba(100, 116, 139, 0.06)';
    },
    [highlightedEdgePairs, isLinkHighlighted, isDark]
  );
    return (
    <div
      className={`min-h-[calc(100vh-4rem)] w-full transition-colors ${
        isDark ? 'bg-slate-950 text-slate-100' : 'bg-slate-50 text-slate-900'
      }`}
    >
      <div className="w-full px-4 sm:px-6 lg:px-8 py-4">
        {/* Full-Width Header */}
        <div className="flex flex-wrap items-center justify-between gap-4 mb-4">
          <div>
            <div className="flex items-center gap-3 flex-wrap">
              <h1
                className={`text-2xl font-bold ${
                  isDark ? 'text-slate-100' : 'text-slate-800'
                }`}
              >
                Knowledge Graph Explorer
              </h1>
              {focusName && (
                <span
                  className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold border ${
                    isDark
                      ? 'bg-indigo-500/15 text-indigo-300 border-indigo-500/35'
                      : 'bg-indigo-50 text-indigo-700 border-indigo-200'
                  }`}
                >
                  Focused: {focusName}
                </span>
              )}
            </div>
            <p className={`text-sm mt-0.5 ${isDark ? 'text-slate-400' : 'text-slate-600'}`}>
              Explore entity relationships or compute shortest Dijkstra collaboration paths (2–6 degrees)
            </p>
          </div>
          {data && (
            <div
              className={`flex items-center gap-3 text-sm font-medium ${
                isDark ? 'text-slate-400' : 'text-slate-600'
              }`}
            >
              <span>{data.nodes.length} nodes</span>
              <span>•</span>
              <span>{data.links.length} edges</span>
            </div>
          )}
        </div>

        {/* Shortest Path & Collaboration Distance Explorer Bar */}
        <div
          className={`mb-4 p-4 rounded-xl border shadow-sm transition-colors ${
            isDark
              ? 'border-slate-800 bg-slate-900/80'
              : 'border-slate-200 bg-white'
          }`}
        >
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-3 items-end">
            {/* Source Selector */}
            <div className="lg:col-span-3">
              <label
                className={`block text-xs font-semibold uppercase tracking-wider mb-1 ${
                  isDark ? 'text-emerald-400' : 'text-emerald-700'
                }`}
              >
                Source Entity
              </label>
              <select
                value={sourceId}
                onChange={(e) => setSourceId(e.target.value)}
                className={`w-full px-3 py-2 rounded-lg text-sm border focus:outline-none focus:ring-2 focus:ring-emerald-500/40 ${
                  isDark
                    ? 'bg-slate-800 border-slate-700 text-slate-100'
                    : 'bg-slate-50 border-slate-300 text-slate-900'
                }`}
              >
                <option value="">Select source node...</option>
                {sortedEntities.map((n) => (
                  <option key={n.id} value={n.id}>
                    [{n.type}] {n.label}
                  </option>
                ))}
              </select>
            </div>

            {/* Swap Button */}
            <div className="lg:col-span-1 flex justify-center">
              <button
                type="button"
                onClick={handleSwapEndpoints}
                disabled={!sourceId && !targetId}
                title="Swap Source & Destination"
                className={`px-3 py-2 rounded-lg border text-sm font-medium disabled:opacity-40 transition ${
                  isDark
                    ? 'bg-slate-800 hover:bg-slate-700 border-slate-700 text-slate-200'
                    : 'bg-slate-100 hover:bg-slate-200 border-slate-300 text-slate-700'
                }`}
              >
                ⇄
              </button>
            </div>

            {/* Destination Selector */}
            <div className="lg:col-span-3">
              <label
                className={`block text-xs font-semibold uppercase tracking-wider mb-1 ${
                  isDark ? 'text-pink-400' : 'text-pink-700'
                }`}
              >
                Destination Entity
              </label>
              <select
                value={targetId}
                onChange={(e) => setTargetId(e.target.value)}
                className={`w-full px-3 py-2 rounded-lg text-sm border focus:outline-none focus:ring-2 focus:ring-pink-500/40 ${
                  isDark
                    ? 'bg-slate-800 border-slate-700 text-slate-100'
                    : 'bg-slate-50 border-slate-300 text-slate-900'
                }`}
              >
                <option value="">Select destination node...</option>
                {sortedEntities.map((n) => (
                  <option key={n.id} value={n.id}>
                    [{n.type}] {n.label}
                  </option>
                ))}
              </select>
            </div>

            {/* Search Depth Slider (2 to 6) */}
            <div className="lg:col-span-2">
              <div
                className={`flex justify-between text-xs font-medium mb-1 ${
                  isDark ? 'text-slate-300' : 'text-slate-700'
                }`}
              >
                <span>Max Depth</span>
                <span className={isDark ? 'text-cyan-400 font-bold' : 'text-cyan-700 font-bold'}>
                  {maxDepth} degrees
                </span>
              </div>
              <input
                type="range"
                min={2}
                max={6}
                step={1}
                value={maxDepth}
                onChange={(e) => setMaxDepth(Number(e.target.value))}
                className="w-full accent-indigo-600 cursor-pointer"
              />
              <div className="flex justify-between text-[10px] text-slate-500 px-0.5">
                <span>2°</span>
                <span>3°</span>
                <span>4°</span>
                <span>5°</span>
                <span>6°</span>
              </div>
            </div>

            {/* Action Buttons */}
            <div className="lg:col-span-3 flex items-center gap-2">
              <button
                type="button"
                onClick={handleFindShortestPath}
                disabled={!sourceId || !targetId || isFindingPath}
                className="flex-1 px-4 py-2 rounded-lg text-sm font-semibold bg-indigo-600 hover:bg-indigo-500 disabled:opacity-40 text-white shadow-sm transition"
              >
                {isFindingPath ? 'Tracing...' : 'Find Shortest Path'}
              </button>
              {pathResult && (
                <button
                  type="button"
                  onClick={handleResetPath}
                  className={`px-3 py-2 rounded-lg text-sm font-medium border transition ${
                    isDark
                      ? 'bg-slate-800 hover:bg-slate-700 border-slate-700 text-slate-300'
                      : 'bg-slate-100 hover:bg-slate-200 border-slate-300 text-slate-700'
                  }`}
                >
                  Clear
                </button>
              )}
            </div>
          </div>
          {/* Weight Mode & Path Metrics */}
          <div
            className={`mt-3 pt-3 border-t flex flex-wrap items-center justify-between gap-3 ${
              isDark ? 'border-slate-800' : 'border-slate-200'
            }`}
          >
            <label
              className={`inline-flex items-center gap-2 text-xs cursor-pointer ${
                isDark ? 'text-slate-400' : 'text-slate-600'
              }`}
            >
              <input
                type="checkbox"
                checked={weighted}
                onChange={(e) => setWeighted(e.target.checked)}
                className="rounded border-slate-400 text-indigo-600 focus:ring-0"
              />
              <span>
                Use Dijkstra relationship weights (DEVELOPED=1.0, USES_TECH=1.2, BELONGS_TO=1.5, LOCATED_IN=2.0)
              </span>
            </label>

            {pathError && (
              <span className={`text-xs font-medium ${isDark ? 'text-red-400' : 'text-red-600'}`}>
                {pathError}
              </span>
            )}

            {pathResult && !pathResult.found && (
              <span className={`text-xs font-medium ${isDark ? 'text-amber-400' : 'text-amber-700'}`}>
                {pathResult.message || `No path found within ${maxDepth} degrees.`}
              </span>
            )}

            {pathResult?.found && (
              <div className="flex items-center gap-3 text-xs">
                <span
                  className={`px-2.5 py-1 rounded-full border font-semibold ${
                    isDark
                      ? 'bg-cyan-500/15 text-cyan-300 border-cyan-500/30'
                      : 'bg-cyan-50 text-cyan-800 border-cyan-200'
                  }`}
                >
                  {pathResult.degrees} {pathResult.degrees === 1 ? 'Degree' : 'Degrees'} of Separation
                </span>
                <span
                  className={`px-2.5 py-1 rounded-full border font-semibold ${
                    isDark
                      ? 'bg-indigo-500/15 text-indigo-300 border-indigo-500/30'
                      : 'bg-indigo-50 text-indigo-800 border-indigo-200'
                  }`}
                >
                  Dijkstra Cost: {pathResult.total_cost}
                </span>
              </div>
            )}
          </div>

          {/* Step-by-Step Collaboration Breadcrumb */}
                    {/* Part 2: Chain Traversal Controls */}
          {pathResult?.found && pathResult.nodes.length > 0 && (
            <div
              className={`mt-2.5 pt-2.5 border-t flex flex-wrap items-center justify-between gap-2 ${
                isDark ? 'border-slate-800' : 'border-slate-200'
              }`}
            >
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => focusPathStep(activeStepIndex - 1)}
                  disabled={activeStepIndex <= 0}
                  className={`px-3 py-1.5 rounded-lg text-xs font-semibold border transition disabled:opacity-40 ${
                    isDark
                      ? 'bg-slate-800 hover:bg-slate-700 border-slate-700 text-slate-200'
                      : 'bg-slate-100 hover:bg-slate-200 border-slate-300 text-slate-800'
                  }`}
                >
                  ← Prev Node
                </button>

                <span
                  className={`px-2.5 py-1 rounded-md text-xs font-mono font-semibold ${
                    isDark ? 'bg-slate-800 text-cyan-300' : 'bg-slate-100 text-cyan-800'
                  }`}
                >
                  Hop {activeStepIndex + 1} / {pathResult.nodes.length}
                </span>

                <button
                  type="button"
                  onClick={() => focusPathStep(activeStepIndex + 1)}
                  disabled={activeStepIndex >= pathResult.nodes.length - 1}
                  className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-indigo-600 hover:bg-indigo-500 text-white shadow-sm transition disabled:opacity-40"
                >
                  Next Node →
                </button>
              </div>

              <button
                type="button"
                onClick={() => setIsDrawerOpen((prev) => !prev)}
                className={`px-3 py-1.5 rounded-lg text-xs font-semibold border transition ${
                  isDark
                    ? 'bg-cyan-500/15 hover:bg-cyan-500/25 border-cyan-500/40 text-cyan-300'
                    : 'bg-cyan-50 hover:bg-cyan-100 border-cyan-300 text-cyan-800'
                }`}
              >
                {isDrawerOpen ? 'Hide Hop History' : 'Show Hop History'} (
                {Object.values(monitoredHops).filter(Boolean).length} Monitored)
              </button>
            </div>
          )}

          {pathResult?.found && pathResult.nodes.length > 0 && (
            <div
              className={`mt-3 pt-3 border-t flex items-center gap-2 overflow-x-auto pb-1 ${
                isDark ? 'border-slate-800' : 'border-slate-200'
              }`}
            >
              {pathResult.nodes.map((node, idx) => {
                const edge = pathResult.edges[idx];
                const isFirst = idx === 0;
                const isLast = idx === pathResult.nodes.length - 1;
                const chipStyle = isFirst
                  ? isDark
                    ? 'bg-emerald-500/15 border-emerald-500/40 text-emerald-300'
                    : 'bg-emerald-50 border-emerald-300 text-emerald-800'
                  : isLast
                  ? isDark
                    ? 'bg-pink-500/15 border-pink-500/40 text-pink-300'
                    : 'bg-pink-50 border-pink-300 text-pink-800'
                  : isDark
                  ? 'bg-sky-500/15 border-sky-500/40 text-sky-200'
                  : 'bg-sky-50 border-sky-300 text-sky-800';

                return (
                  <div key={node.id} className="flex items-center gap-2 shrink-0">
                    <button
                      type="button"
                      onClick={() => {
                        const live = (graphRef.current?.graphData?.().nodes || []).find(
                          (n: any) => n.id === node.id
                        );
                        if (live) handleNodeClick(live);
                      }}
                      className={`px-2.5 py-1 rounded-lg text-xs font-medium border flex items-center gap-1.5 transition hover:brightness-95 ${chipStyle}`}
                    >
                      <span
                        className="w-2 h-2 rounded-full"
                        style={{ backgroundColor: NODE_COLORS[node.type] || '#94a3b8' }}
                      />
                      <span>{node.label}</span>
                      <span className="opacity-70 text-[10px]">({node.type})</span>
                    </button>

                    {edge && (
                      <div
                        className={`flex flex-col items-center text-[10px] px-1 ${
                          isDark ? 'text-slate-400' : 'text-slate-500'
                        }`}
                      >
                        <span
                          className={`font-mono font-semibold ${
                            isDark ? 'text-cyan-400' : 'text-cyan-700'
                          }`}
                        >
                          {edge.type}
                        </span>
                        <span>──▶</span>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>

                  {/* Part 3: Collaboration History & Hop Monitoring Drawer */}
          {pathResult?.found && isDrawerOpen && (
            <div
              className={`absolute top-4 left-4 w-80 max-h-[calc(100%-2rem)] flex flex-col rounded-xl border shadow-xl backdrop-blur-md overflow-hidden ${
                isDark
                  ? 'bg-slate-900/95 border-slate-700 text-slate-100'
                  : 'bg-white/95 border-slate-200 text-slate-900'
              }`}
            >
              <div
                className={`p-3.5 border-b flex items-center justify-between ${
                  isDark ? 'border-slate-800 bg-slate-900' : 'border-slate-200 bg-slate-50'
                }`}
              >
                <div>
                  <h3 className="text-xs font-bold uppercase tracking-wider text-cyan-500">
                    Collaboration History & Hops
                  </h3>
                  <p className={`text-[11px] mt-0.5 ${isDark ? 'text-slate-400' : 'text-slate-500'}`}>
                    {pathResult.edges.length} hops • Total cost {pathResult.total_cost}
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => setIsDrawerOpen(false)}
                  className={`text-xs ${
                    isDark ? 'text-slate-400 hover:text-slate-200' : 'text-slate-500 hover:text-slate-800'
                  }`}
                >
                  ✕
                </button>
              </div>

              <div className="p-3 overflow-y-auto space-y-2.5 flex-1">
                {pathResult.nodes.map((node, idx) => {
                  const outgoingEdge = pathResult.edges[idx];
                  const nextNode = pathResult.nodes[idx + 1];
                  const hopKey = outgoingEdge
                    ? `${outgoingEdge.source}__${outgoingEdge.target}__${outgoingEdge.type}`
                    : null;
                  const isMonitored = hopKey ? !!monitoredHops[hopKey] : false;
                  const isCurrent = idx === activeStepIndex;

                  return (
                    <div
                      key={node.id}
                      onClick={() => focusPathStep(idx)}
                      className={`p-2.5 rounded-lg border cursor-pointer transition ${
                        isCurrent
                          ? isDark
                            ? 'bg-indigo-500/15 border-indigo-500/50'
                            : 'bg-indigo-50 border-indigo-300'
                          : isDark
                          ? 'bg-slate-800/50 border-slate-800 hover:border-slate-700'
                          : 'bg-slate-50 border-slate-200 hover:border-slate-300'
                      }`}
                    >
                      <div className="flex items-center justify-between gap-2">
                        <div className="flex items-center gap-1.5 min-w-0">
                          <span
                            className="w-2 h-2 rounded-full shrink-0"
                            style={{ backgroundColor: NODE_COLORS[node.type] || '#94a3b8' }}
                          />
                          <span className="text-xs font-bold truncate">{node.label}</span>
                        </div>
                        <span className="text-[10px] font-mono opacity-70">#{idx + 1}</span>
                      </div>

                      {outgoingEdge && nextNode && hopKey && (
                        <div
                          onClick={(e) => e.stopPropagation()}
                          className={`mt-2 pt-2 border-t text-[11px] ${
                            isDark ? 'border-slate-700/80' : 'border-slate-200'
                          }`}
                        >
                          <div className="flex items-center justify-between gap-1">
                            <span className="font-mono font-semibold text-cyan-500">
                              {outgoingEdge.type}
                            </span>
                            <button
                              type="button"
                              onClick={() =>
                                setMonitoredHops((prev) => ({
                                  ...prev,
                                  [hopKey]: !prev[hopKey],
                                }))
                              }
                              className={`px-2 py-0.5 rounded text-[10px] font-semibold border transition ${
                                isMonitored
                                  ? 'bg-emerald-500/20 border-emerald-500/50 text-emerald-400'
                                  : isDark
                                  ? 'bg-slate-800 border-slate-700 text-slate-400 hover:text-slate-200'
                                  : 'bg-white border-slate-300 text-slate-600 hover:text-slate-900'
                              }`}
                            >
                              {isMonitored ? '● Monitored' : '+ Monitor'}
                            </button>
                          </div>
                          <p className="mt-1 truncate opacity-90">
                            → <strong>{nextNode.label}</strong> ({nextNode.type})
                          </p>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          )}


        {/* Search & Type Filter Bar */}
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 mb-4">
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Filter graph by entity or keyword..."
            className={`w-full sm:w-80 px-3 py-1.5 rounded-lg text-sm border focus:outline-none focus:ring-2 focus:ring-indigo-500/40 ${
              isDark
                ? 'bg-slate-900 border-slate-700 text-slate-100 placeholder-slate-500'
                : 'bg-white border-slate-300 text-slate-900 placeholder-slate-400'
            }`}
          />
          <div className="flex flex-wrap items-center gap-2">
            <button
              onClick={() => setSelectedType(null)}
              className={`px-3 py-1 rounded-full text-xs font-medium border transition ${
                selectedType === null
                  ? isDark
                    ? 'bg-slate-100 text-slate-900 border-slate-100'
                    : 'bg-slate-900 text-white border-slate-900'
                  : isDark
                  ? 'border-slate-700 text-slate-400 hover:text-slate-200'
                  : 'border-slate-300 bg-white text-slate-600 hover:text-slate-900'
              }`}
            >
              All
            </button>
            {Object.entries(NODE_COLORS).map(([type, color]) => (
              <button
                key={type}
                onClick={() => setSelectedType(selectedType === type ? null : type)}
                className={`px-3 py-1 rounded-full text-xs font-medium border flex items-center gap-1.5 transition ${
                  selectedType === type
                    ? isDark
                      ? 'border-white text-white bg-slate-800'
                      : 'border-slate-900 text-slate-900 bg-slate-200/80'
                    : isDark
                    ? 'border-slate-700 text-slate-400 hover:text-slate-200'
                    : 'border-slate-300 bg-white text-slate-600 hover:text-slate-900'
                }`}
              >
                <span className="w-2 h-2 rounded-full" style={{ backgroundColor: color }} />
                {type}
              </button>
            ))}
          </div>
        </div>
        {/* Full-Width Graph Canvas + Selected Node Inspector */}
        <div
          className={`relative w-full rounded-xl border overflow-hidden shadow-sm transition-colors ${
            isDark ? 'border-slate-800 bg-slate-950' : 'border-slate-300 bg-white'
          }`}
          ref={containerRef}
        >
          {isLoading ? (
            <div className="flex items-center justify-center h-[600px] text-slate-500">
              Loading knowledge graph...
            </div>
          ) : error ? (
            <div className="flex items-center justify-center h-[600px] text-red-500">
              Failed to load graph data.
            </div>
          ) : (
            <ForceGraph2D
              ref={graphRef}
              width={dimensions.width}
              height={dimensions.height}
              backgroundColor={isDark ? '#020617' : '#f8fafc'}
              graphData={graphData}
              nodeCanvasObject={nodeCanvasObject}
              onNodeHover={setHoveredNode}
              onNodeClick={handleNodeClick}
              linkColor={getLinkColor}
              linkWidth={(link: any) => (isLinkHighlighted(link) ? 3.5 : 1)}
              linkDirectionalParticles={(link: any) => (isLinkHighlighted(link) ? 4 : 0)}
              linkDirectionalParticleWidth={3}
              linkDirectionalParticleColor={() => (isDark ? '#38bdf8' : '#0284c7')}
              cooldownTicks={100}
            />
          )}

          {/* Selected Node Detail Drawer */}
          {selectedNode && (
            <div
              className={`absolute top-4 right-4 w-72 p-4 rounded-xl border shadow-xl backdrop-blur-md ${
                isDark
                  ? 'bg-slate-900/95 border-slate-700 text-slate-100'
                  : 'bg-white/95 border-slate-200 text-slate-900'
              }`}
            >
              <div className="flex items-start justify-between gap-2">
                <div>
                  <span
                    className="inline-block px-2 py-0.5 rounded text-[10px] font-semibold uppercase tracking-wider mb-1"
                    style={{
                      backgroundColor: `${selectedNode.color}22`,
                      color: selectedNode.color,
                    }}
                  >
                    {selectedNode.type}
                  </span>
                  <h3
                    className={`text-sm font-bold ${
                      isDark ? 'text-slate-100' : 'text-slate-900'
                    }`}
                  >
                    {selectedNode.label}
                  </h3>
                </div>
                <button
                  onClick={() => setSelectedNode(null)}
                  className={`text-xs ${
                    isDark
                      ? 'text-slate-400 hover:text-slate-200'
                      : 'text-slate-500 hover:text-slate-800'
                  }`}
                >
                  ✕
                </button>
              </div>

              {/* Quick Set Source / Target Buttons */}
              <div className="mt-3 grid grid-cols-2 gap-2">
                <button
                  type="button"
                  onClick={() => setSourceId(selectedNode.id)}
                  className={`px-2 py-1.5 rounded text-xs font-medium border transition ${
                    isDark
                      ? 'bg-emerald-500/15 hover:bg-emerald-500/25 text-emerald-300 border-emerald-500/30'
                      : 'bg-emerald-50 hover:bg-emerald-100 text-emerald-800 border-emerald-300'
                  }`}
                >
                  Set as Source
                </button>
                <button
                  type="button"
                  onClick={() => setTargetId(selectedNode.id)}
                  className={`px-2 py-1.5 rounded text-xs font-medium border transition ${
                    isDark
                      ? 'bg-pink-500/15 hover:bg-pink-500/25 text-pink-300 border-pink-500/30'
                      : 'bg-pink-50 hover:bg-pink-100 text-pink-800 border-pink-300'
                  }`}
                >
                  Set as Target
                </button>
              </div>

              {connectedNodes.length > 0 && (
                <div
                  className={`mt-3 pt-3 border-t ${
                    isDark ? 'border-slate-800' : 'border-slate-200'
                  }`}
                >
                  <p
                    className={`text-xs font-semibold mb-1.5 ${
                      isDark ? 'text-slate-400' : 'text-slate-600'
                    }`}
                  >
                    Direct Connections ({connectedNodes.length})
                  </p>
                  <div className="max-h-36 overflow-y-auto space-y-1">
                    {connectedNodes.map((cn: any) => (
                      <div
                        key={cn.id}
                        className={`text-xs flex items-center gap-1.5 truncate ${
                          isDark ? 'text-slate-300' : 'text-slate-700'
                        }`}
                      >
                        <span
                          className="w-1.5 h-1.5 rounded-full shrink-0"
                          style={{ backgroundColor: NODE_COLORS[cn.type] || '#94a3b8' }}
                        />
                        <span className="truncate">{cn.label}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
