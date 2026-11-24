"""Search API endpoint."""
import logging
from fastapi import APIRouter, HTTPException, Query
from app.models.schemas import SearchRequest, SearchResponse
from app.services.search_service import search

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/search", response_model=SearchResponse, summary="Natural Language Search")
async def search_endpoint(request: SearchRequest):
    """
    Natural language search endpoint.

    Accepts a natural language query and returns matching
    developers and/or projects from the knowledge graph.

    **Example queries:**
    - `developers with Python experience and more than 5 projects`
    - `healthcare projects in Delhi using React`
    - `show AI developers from Bangalore`
    - `e-commerce projects using FastAPI`
    """
    try:
        result = search(request.query, limit=request.limit)
        return result
    except Exception as e:
        logger.error(f"Search failed for query '{request.query}': {e}")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@router.get("/search/suggestions", summary="Search Suggestions")
async def search_suggestions(q: str = Query(..., min_length=1, max_length=100)):
    """
    Get autocomplete suggestions for a partial search query.
    Returns matching developer names, project names, technologies, domains.
    """
    from app.core.database import neo4j_driver

    q_lower = q.lower()
    try:
        results = neo4j_driver.execute_query("""
            CALL {
                MATCH (d:Developer)
                WHERE toLower(d.name) CONTAINS $q
                RETURN d.name AS suggestion, 'developer' AS type
                LIMIT 5
                UNION
                MATCH (p:Project)
                WHERE toLower(p.name) CONTAINS $q OR toLower(p.tagline) CONTAINS $q
                RETURN p.name AS suggestion, 'project' AS type
                LIMIT 5
                UNION
                MATCH (t:Technology)
                WHERE toLower(t.name) CONTAINS $q
                RETURN t.name AS suggestion, 'technology' AS type
                LIMIT 5
                UNION
                MATCH (dom:Domain)
                WHERE toLower(dom.name) CONTAINS $q
                RETURN dom.name AS suggestion, 'domain' AS type
                LIMIT 3
                UNION
                MATCH (l:Location)
                WHERE toLower(l.name) CONTAINS $q
                RETURN l.name AS suggestion, 'location' AS type
                LIMIT 3
            }
            RETURN suggestion, type
            ORDER BY type, suggestion
            LIMIT 15
        """, {"q": q_lower})
        return {"query": q, "suggestions": results}
    except Exception as e:
        logger.error(f"Suggestions failed: {e}")
        return {"query": q, "suggestions": []}
