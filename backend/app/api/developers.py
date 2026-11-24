"""Developers API endpoints."""
import logging
from fastapi import APIRouter, HTTPException, Query
from app.core.database import neo4j_driver
from app.models.schemas import DeveloperResponse, RecommendationResponse
from app.services.recommendation_service import get_developer_recommendations
from app.services.graph_service import get_subgraph
from typing import List

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/developers", response_model=List[DeveloperResponse], summary="List All Developers")
async def list_developers(
    limit: int = Query(default=50, ge=1, le=200),
    technology: str = Query(default=None),
    domain: str = Query(default=None),
    location: str = Query(default=None),
    min_projects: int = Query(default=None, ge=0),
):
    """
    List all developers with optional filters.

    Supports filtering by technology, domain, location, and minimum project count.
    """
    where_clauses = []
    params: dict = {"limit": limit}

    if technology:
        params["tech"] = technology.lower()
        where_clauses.append(
            "EXISTS { MATCH (d)-[:DEVELOPED]->(:Project)-[:USES_TECH]->(t:Technology) WHERE toLower(t.name) CONTAINS $tech }"
        )

    if domain:
        params["domain"] = domain.lower()
        where_clauses.append(
            "EXISTS { MATCH (d)-[:DEVELOPED]->(:Project)-[:BELONGS_TO]->(dom:Domain) WHERE toLower(dom.name) CONTAINS $domain }"
        )

    if location:
        params["location"] = location.lower()
        where_clauses.append(
            "EXISTS { MATCH (d)-[:DEVELOPED]->(:Project)-[:LOCATED_IN]->(loc:Location) WHERE toLower(loc.name) = $location }"
        )

    if min_projects is not None:
        params["min_projects"] = min_projects
        where_clauses.append("d.project_count >= $min_projects")

    query = "MATCH (d:Developer)"
    if where_clauses:
        query += " WHERE " + " AND ".join(where_clauses)

    query += """
    WITH d
    OPTIONAL MATCH (d)-[:DEVELOPED]->(proj:Project)
    OPTIONAL MATCH (proj)-[:USES_TECH]->(tech:Technology)
    OPTIONAL MATCH (proj)-[:BELONGS_TO]->(domain:Domain)
    OPTIONAL MATCH (proj)-[:LOCATED_IN]->(location:Location)
    RETURN
        d.name AS name,
        d.project_count AS project_count,
        d.bio AS bio,
        d.email AS email,
        d.phone AS phone,
        COLLECT(DISTINCT proj.name) AS projects,
        COLLECT(DISTINCT tech.name) AS technologies,
        COLLECT(DISTINCT domain.name) AS domains,
        COLLECT(DISTINCT location.name) AS locations
    ORDER BY d.project_count DESC
    LIMIT $limit
    """

    try:
        results = neo4j_driver.execute_query(query, params)
        return [
            DeveloperResponse(
                name=r.get("name", ""),
                project_count=r.get("project_count") or 0,
                bio=r.get("bio"),
                email=r.get("email"),
                phone=r.get("phone"),
                projects=[p for p in r.get("projects", []) if p],
                technologies=[t for t in r.get("technologies", []) if t],
                domains=[d for d in r.get("domains", []) if d],
                locations=[l for l in r.get("locations", []) if l],
            )
            for r in results
        ]
    except Exception as e:
        logger.error(f"List developers failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/developers/{developer_name}",
    response_model=DeveloperResponse,
    summary="Get Developer Details",
)
async def get_developer(developer_name: str):
    """Get a specific developer by name."""
    query = """
    MATCH (d:Developer {name: $name})
    OPTIONAL MATCH (d)-[:DEVELOPED]->(proj:Project)
    OPTIONAL MATCH (proj)-[:USES_TECH]->(tech:Technology)
    OPTIONAL MATCH (proj)-[:BELONGS_TO]->(domain:Domain)
    OPTIONAL MATCH (proj)-[:LOCATED_IN]->(location:Location)
    RETURN
        d.name AS name,
        d.project_count AS project_count,
        d.bio AS bio,
        d.email AS email,
        d.phone AS phone,
        COLLECT(DISTINCT proj.name) AS projects,
        COLLECT(DISTINCT tech.name) AS technologies,
        COLLECT(DISTINCT domain.name) AS domains,
        COLLECT(DISTINCT location.name) AS locations
    """
    try:
        results = neo4j_driver.execute_query(query, {"name": developer_name})
    except Exception as e:
        logger.error(f"Get developer '{developer_name}' failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

    if not results:
        raise HTTPException(status_code=404, detail=f"Developer '{developer_name}' not found")

    r = results[0]
    return DeveloperResponse(
        name=r.get("name", ""),
        project_count=r.get("project_count") or 0,
        bio=r.get("bio"),
        email=r.get("email"),
        phone=r.get("phone"),
        projects=[p for p in r.get("projects", []) if p],
        technologies=[t for t in r.get("technologies", []) if t],
        domains=[d for d in r.get("domains", []) if d],
        locations=[l for l in r.get("locations", []) if l],
    )


@router.get(
    "/developers/{developer_name}/recommendations",
    response_model=RecommendationResponse,
    summary="Get Developer Recommendations",
)
async def developer_recommendations(
    developer_name: str,
    limit: int = Query(default=6, ge=1, le=20),
):
    """Get similar developer and project recommendations for a developer."""
    try:
        return get_developer_recommendations(developer_name, limit=limit)
    except Exception as e:
        logger.error(f"Developer recommendations failed for '{developer_name}': {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/developers/{developer_name}/graph",
    summary="Get Developer Subgraph",
)
async def developer_subgraph(developer_name: str):
    """Get the local knowledge graph context for a developer."""
    try:
        return get_subgraph("developer", developer_name)
    except Exception as e:
        logger.error(f"Developer subgraph failed for '{developer_name}': {e}")
        raise HTTPException(status_code=500, detail=str(e))
