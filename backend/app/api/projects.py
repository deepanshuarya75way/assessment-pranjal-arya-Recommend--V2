"""Projects API endpoints."""
import logging
from fastapi import APIRouter, HTTPException, Query
from app.core.database import neo4j_driver
from app.models.schemas import ProjectResponse, RecommendationResponse, CreateProjectRequest
from app.services.recommendation_service import get_project_recommendations
from app.services.graph_service import get_subgraph
from typing import List

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/projects", response_model=List[ProjectResponse], summary="List All Projects")
async def list_projects(
    limit: int = Query(default=50, ge=1, le=200),
    domain: str = Query(default=None),
    technology: str = Query(default=None),
    location: str = Query(default=None),
):
    """
    List all projects with optional filters.

    Supports filtering by domain, technology, and location.
    """
    match_clauses = ["MATCH (p:Project)"]
    where_clauses = []
    params: dict = {"limit": limit}

    if technology:
        params["tech"] = technology.lower()
        match_clauses.append("EXISTS { MATCH (p)-[:USES_TECH]->(t:Technology) WHERE toLower(t.name) CONTAINS $tech }")
        where_clauses.append(
            "EXISTS { MATCH (p)-[:USES_TECH]->(t:Technology) WHERE toLower(t.name) CONTAINS $tech }"
        )

    if domain:
        params["domain"] = domain.lower()
        where_clauses.append(
            "EXISTS { MATCH (p)-[:BELONGS_TO]->(dom:Domain) WHERE toLower(dom.name) CONTAINS $domain }"
        )

    if location:
        params["location"] = location.lower()
        where_clauses.append(
            "EXISTS { MATCH (p)-[:LOCATED_IN]->(loc:Location) WHERE toLower(loc.name) = $location }"
        )

    query = "MATCH (p:Project)"
    if where_clauses:
        query += " WHERE " + " AND ".join(where_clauses)

    query += """
    WITH p
    OPTIONAL MATCH (dev:Developer)-[:DEVELOPED]->(p)
    OPTIONAL MATCH (p)-[:USES_TECH]->(tech:Technology)
    OPTIONAL MATCH (p)-[:BELONGS_TO]->(domain:Domain)
    OPTIONAL MATCH (p)-[:LOCATED_IN]->(location:Location)
    RETURN
        p.name AS name,
        p.description AS description,
        p.tagline AS tagline,
        p.developed_on AS developed_on,
        COLLECT(DISTINCT dev.name) AS developers,
        COLLECT(DISTINCT tech.name) AS technologies,
        COLLECT(DISTINCT domain.name) AS domains,
        COLLECT(DISTINCT location.name) AS locations
    ORDER BY p.name
    LIMIT $limit
    """

    try:
        results = neo4j_driver.execute_query(query, params)
        return [
            ProjectResponse(
                name=r.get("name", ""),
                description=r.get("description"),
                tagline=r.get("tagline"),
                developed_on=r.get("developed_on"),
                developers=[d for d in r.get("developers", []) if d],
                technologies=[t for t in r.get("technologies", []) if t],
                domains=[d for d in r.get("domains", []) if d],
                locations=[l for l in r.get("locations", []) if l],
            )
            for r in results
        ]
    except Exception as e:
        logger.error(f"List projects failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/projects/{project_name}", response_model=ProjectResponse, summary="Get Project Details")
async def get_project(project_name: str):
    """Get a specific project by name."""
    query = """
    MATCH (p:Project {name: $name})
    OPTIONAL MATCH (dev:Developer)-[:DEVELOPED]->(p)
    OPTIONAL MATCH (p)-[:USES_TECH]->(tech:Technology)
    OPTIONAL MATCH (p)-[:BELONGS_TO]->(domain:Domain)
    OPTIONAL MATCH (p)-[:LOCATED_IN]->(location:Location)
    RETURN
        p.name AS name,
        p.description AS description,
        p.tagline AS tagline,
        p.developed_on AS developed_on,
        COLLECT(DISTINCT dev.name) AS developers,
        COLLECT(DISTINCT tech.name) AS technologies,
        COLLECT(DISTINCT domain.name) AS domains,
        COLLECT(DISTINCT location.name) AS locations
    """
    try:
        results = neo4j_driver.execute_query(query, {"name": project_name})
    except Exception as e:
        logger.error(f"Get project '{project_name}' failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

    if not results:
        raise HTTPException(status_code=404, detail=f"Project '{project_name}' not found")

    r = results[0]
    return ProjectResponse(
        name=r.get("name", ""),
        description=r.get("description"),
        tagline=r.get("tagline"),
        developed_on=r.get("developed_on"),
        developers=[d for d in r.get("developers", []) if d],
        technologies=[t for t in r.get("technologies", []) if t],
        domains=[d for d in r.get("domains", []) if d],
        locations=[l for l in r.get("locations", []) if l],
    )


@router.get(
    "/projects/{project_name}/recommendations",
    response_model=RecommendationResponse,
    summary="Get Project Recommendations",
)
async def project_recommendations(
    project_name: str,
    limit: int = Query(default=6, ge=1, le=20),
):
    """Get similar project and developer recommendations for a project."""
    try:
        return get_project_recommendations(project_name, limit=limit)
    except Exception as e:
        logger.error(f"Project recommendations failed for '{project_name}': {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/projects/{project_name}/graph",
    summary="Get Project Subgraph",
)
async def project_subgraph(project_name: str):
    """Get the local knowledge graph context for a project."""
    try:
        return get_subgraph("project", project_name)
    except Exception as e:
        logger.error(f"Project subgraph failed for '{project_name}': {e}")
        raise HTTPException(status_code=500, detail=str(e))
