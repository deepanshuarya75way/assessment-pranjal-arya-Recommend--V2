"""Graph visualization API endpoints."""
import logging
from fastapi import APIRouter, HTTPException, Query
from app.models.schemas import GraphResponse
from app.services.graph_service import (
    get_full_graph,
    get_subgraph,
    find_shortest_path_dijkstra,
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/graph", response_model=GraphResponse, summary="Full or Filtered Knowledge Graph")
async def graph_data(q: str = Query(None, description="Optional search query to filter the graph")):
    """
    Get the knowledge graph for visualization, optionally filtered by a search query.

    Returns all nodes (Developers, Projects, Technologies, Domains, Locations)
    and their relationships, suitable for force-directed graph rendering.
    """
    try:
        return get_full_graph(query=q)
    except Exception as e:
        logger.error(f"Full graph query failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/graph/subgraph", response_model=GraphResponse, summary="Entity Subgraph")
async def entity_subgraph(
    entity_type: str = Query(..., pattern="^(developer|project)$"),
    name: str = Query(..., min_length=1),
):

    """
    Get the local graph context for a specific entity.

    Returns nodes and edges within 1-hop of the given developer or project.
    """
    try:
        return get_subgraph(entity_type, name)
    except Exception as e:
        logger.error(f"Subgraph query failed for {entity_type}='{name}': {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/graph/shortest-path", summary="Shortest Collaboration Path (Dijkstra)")
async def get_shortest_path(
    source_id: str = Query(..., description="Source node ID (e.g., dev_Alice)"),
    target_id: str = Query(..., description="Target node ID (e.g., dev_Bob)"),
    max_depth: int = Query(4, ge=2, le=6, description="Max search depth (2 to 6 hops)"),
    weighted: bool = Query(True, description="Use relationship weights for Dijkstra distance"),
):
    """
    Find the shortest path between two entities in the knowledge graph using Dijkstra's algorithm,
    constrained between 2 and 6 degrees of connection.
    """
    try:
        return find_shortest_path_dijkstra(
            source_id=source_id,
            target_id=target_id,
            max_depth=max_depth,
            weighted=weighted,
        )
    except Exception as e:
        logger.error(f"Shortest path query failed ({source_id} -> {target_id}): {e}")
        raise HTTPException(status_code=500, detail=str(e))
