"""
Search Service - Converts parsed query filters into Cypher queries.

Handles all search logic for developers and projects, including
multi-filter support, relevance scoring, and pagination.
"""
import logging
from typing import List
from app.core.database import neo4j_driver
from app.models.schemas import (
    ParsedQuery, SearchRequest, SearchResponse, DeveloperResponse, ProjectResponse
)
from app.services.query_parser import get_parser

logger = logging.getLogger(__name__)


def search(query: str, limit: int = 25) -> SearchResponse:
    """Execute a natural language search against the knowledge graph."""
    from app.core.config import settings
    parser = get_parser(settings.query_parser)
    parsed = parser.parse(query)

    logger.info(f"Search query: '{query}' | Parsed: entity={parsed.entity}, "
                f"techs={parsed.technologies}, domain={parsed.domain}, "
                f"location={parsed.location}, min_projects={parsed.min_projects}")

    response = SearchResponse(
        query=query,
        entity_type=parsed.entity,
        parsed_filters=parsed.model_dump(exclude_none=True),
        limit=limit,
    )

    if parsed.entity in ("developer", "both"):
        response.developers = search_developers(parsed, limit)
    if parsed.entity in ("project", "both"):
        response.projects = search_projects(parsed, limit)

    response.total_results = len(response.developers) + len(response.projects)
    return response


def search_developers(parsed: ParsedQuery, limit: int = 25) -> List[DeveloperResponse]:
    """
    Search for developers based on parsed filters.

    Builds Cypher query dynamically from parsed filters and executes it.
    Uses subquery approach to avoid Cartesian product from multiple OPTIONAL MATCHes.
    """
    params: dict = {"limit": limit}
    where_clauses = []

    # Technology filter — join via project tech relationships
    if parsed.technologies:
        tech_conditions = []
        for i, tech in enumerate(parsed.technologies):
            params[f"tech_{i}"] = tech.lower()
            tech_conditions.append(f"toLower(t.name) CONTAINS $tech_{i}")
        tech_where = " OR ".join(tech_conditions)
        where_clauses.append(f"""EXISTS {{
            MATCH (d)-[:DEVELOPED]->(:Project)-[:USES_TECH]->(t:Technology)
            WHERE {tech_where}
        }}""")

    # Domain filter
    if parsed.domain:
        params["domain"] = parsed.domain.lower()
        where_clauses.append("""EXISTS {
            MATCH (d)-[:DEVELOPED]->(:Project)-[:BELONGS_TO]->(dom:Domain)
            WHERE toLower(dom.name) CONTAINS $domain
        }""")

    # Location filter
    if parsed.location:
        params["location"] = parsed.location.lower()
        where_clauses.append("""EXISTS {
            MATCH (d)-[:DEVELOPED]->(:Project)-[:LOCATED_IN]->(loc:Location)
            WHERE toLower(loc.name) = $location
        }""")

    # Minimum projects filter
    if parsed.min_projects:
        params["min_projects"] = parsed.min_projects
        where_clauses.append("d.project_count >= $min_projects")

    # Keyword / Name matching filter
    if parsed.keyword:
        params["keyword"] = parsed.keyword.lower()
        where_clauses.append("""(
            toLower(d.name) CONTAINS $keyword 
            OR toLower(d.bio) CONTAINS $keyword
            OR EXISTS {
                MATCH (d)-[:DEVELOPED]->(p:Project)
                WHERE toLower(p.name) CONTAINS $keyword
                   OR toLower(p.tagline) CONTAINS $keyword
                   OR toLower(p.description) CONTAINS $keyword
                   OR EXISTS {
                       MATCH (p)-[:USES_TECH]->(t:Technology)
                       WHERE toLower(t.name) CONTAINS $keyword
                   }
                   OR EXISTS {
                       MATCH (p)-[:BELONGS_TO]->(dom:Domain)
                       WHERE toLower(dom.name) CONTAINS $keyword
                   }
            }
        )""")

    # Build filtering query
    filter_query = "MATCH (d:Developer)"
    if where_clauses:
        filter_query += "\n    WHERE " + " AND ".join(where_clauses)

    # Collect full data
    # Collect full data
    full_query = filter_query + """
    RETURN
        d.name AS name,
        d.project_count AS project_count,
        d.bio AS bio,
        d.email AS email,
        d.phone AS phone,
        [(d)-[:DEVELOPED]->(proj:Project) | proj.name] AS projects,
        [(d)-[:DEVELOPED]->(:Project)-[:USES_TECH]->(tech:Technology) | tech.name] AS technologies,
        [(d)-[:DEVELOPED]->(:Project)-[:BELONGS_TO]->(domain:Domain) | domain.name] AS domains,
        [(d)-[:DEVELOPED]->(:Project)-[:LOCATED_IN]->(location:Location) | location.name] AS locations
    """

    try:
        results = neo4j_driver.execute_query(full_query, params)
    except Exception as e:
        logger.error(f"Developer search failed: {e}")
        return []

    devs = []
    for r in results:
        score = _dev_relevance(r, parsed)
        devs.append(DeveloperResponse(
            name=r.get("name", ""),
            project_count=r.get("project_count") or 0,
            bio=r.get("bio"),
            email=r.get("email"),
            phone=r.get("phone"),
            projects=list(set([p for p in r.get("projects", []) if p])),
            technologies=list(set([t for t in r.get("technologies", []) if t])),
            domains=list(set([d for d in r.get("domains", []) if d])),
            locations=list(set([l for l in r.get("locations", []) if l])),
            relevance_score=score,
        ))

    devs.sort(key=lambda d: d.relevance_score, reverse=True)
    return devs[:limit]


def search_projects(parsed: ParsedQuery, limit: int = 25) -> List[ProjectResponse]:
    """
    Search for projects based on parsed filters.

    Builds Cypher query dynamically from parsed filters and executes it.
    Uses subquery approach to avoid Cartesian product from multiple OPTIONAL MATCHes.
    """
    params: dict = {"limit": limit}
    where_clauses = []

    # Technology filter
    if parsed.technologies:
        tech_conditions = []
        for i, tech in enumerate(parsed.technologies):
            params[f"tech_{i}"] = tech.lower()
            tech_conditions.append(f"toLower(t.name) CONTAINS $tech_{i}")
        tech_where = " OR ".join(tech_conditions)
        where_clauses.append(f"""EXISTS {{
            MATCH (p)-[:USES_TECH]->(t:Technology)
            WHERE {tech_where}
        }}""")

    # Domain filter
    if parsed.domain:
        params["domain"] = parsed.domain.lower()
        where_clauses.append("""EXISTS {
            MATCH (p)-[:BELONGS_TO]->(dom:Domain)
            WHERE toLower(dom.name) CONTAINS $domain
        }""")

    # Location filter
    if parsed.location:
        params["location"] = parsed.location.lower()
        where_clauses.append("""EXISTS {
            MATCH (p)-[:LOCATED_IN]->(loc:Location)
            WHERE toLower(loc.name) = $location
        }""")

    # Year filter
    if parsed.developed_on:
        params["year"] = parsed.developed_on
        where_clauses.append("p.developed_on = $year")

    # Keyword / Name matching filter
    if parsed.keyword:
        params["keyword"] = parsed.keyword.lower()
        where_clauses.append("(toLower(p.name) CONTAINS $keyword OR toLower(p.tagline) CONTAINS $keyword OR toLower(p.description) CONTAINS $keyword)")

    # Build filtering query
    filter_query = "MATCH (p:Project)"
    if where_clauses:
        filter_query += "\n    WHERE " + " AND ".join(where_clauses)

    full_query = filter_query + """
    RETURN
        p.name AS name,
        p.description AS description,
        p.tagline AS tagline,
        p.developed_on AS developed_on,
        [(dev:Developer)-[:DEVELOPED]->(p) | dev.name] AS developers,
        [(p)-[:USES_TECH]->(tech:Technology) | tech.name] AS technologies,
        [(p)-[:BELONGS_TO]->(domain:Domain) | domain.name] AS domains,
        [(p)-[:LOCATED_IN]->(location:Location) | location.name] AS locations
    """

    try:
        results = neo4j_driver.execute_query(full_query, params)
    except Exception as e:
        logger.error(f"Project search failed: {e}")
        return []

    projects = []
    for r in results:
        score = _proj_relevance(r, parsed)
        projects.append(ProjectResponse(
            name=r.get("name", ""),
            description=r.get("description"),
            tagline=r.get("tagline"),
            developed_on=r.get("developed_on"),
            developers=list(set([d for d in r.get("developers", []) if d])),
            technologies=list(set([t for t in r.get("technologies", []) if t])),
            domains=list(set([d for d in r.get("domains", []) if d])),
            locations=list(set([l for l in r.get("locations", []) if l])),
            relevance_score=score,
        ))

    projects.sort(key=lambda p: p.relevance_score, reverse=True)
    return projects[:limit]


def _dev_relevance(record: dict, parsed: ParsedQuery) -> float:
    """Calculate developer relevance score based on filter matches."""
    score = 0.0
    techs = [t.lower() for t in record.get("technologies", []) if t]
    domains = [d.lower() for d in record.get("domains", []) if d]
    locs = [l.lower() for l in record.get("locations", []) if l]

    # Technology match (most important signal)
    for tech in parsed.technologies:
        if any(tech.lower() in t for t in techs):
            score += 30.0

    # Domain match
    if parsed.domain and any(parsed.domain.lower() in d for d in domains):
        score += 25.0

    # Location match
    if parsed.location and parsed.location.lower() in locs:
        score += 20.0

    # Project count bonus (productivity signal)
    pc = record.get("project_count") or 0
    score += min(pc * 2, 20.0)

    # Min projects satisfied
    if parsed.min_projects and pc >= parsed.min_projects:
        score += 15.0

    # Keyword match bonus
    if parsed.keyword:
        kw = parsed.keyword.lower()
        if kw in record.get("name", "").lower():
            score += 25.0
        elif record.get("bio") and kw in record.get("bio", "").lower():
            score += 15.0
        elif any(kw in t.lower() for t in techs) or any(kw in d.lower() for d in domains) or any(kw in p.lower() for p in record.get("projects", [])):
            score += 10.0

    return round(score, 2)


def _proj_relevance(record: dict, parsed: ParsedQuery) -> float:
    """Calculate project relevance score based on filter matches."""
    score = 0.0
    techs = [t.lower() for t in record.get("technologies", []) if t]
    domains = [d.lower() for d in record.get("domains", []) if d]
    locs = [l.lower() for l in record.get("locations", []) if l]

    # Technology match
    for tech in parsed.technologies:
        if any(tech.lower() in t for t in techs):
            score += 30.0

    # Domain match
    if parsed.domain and any(parsed.domain.lower() in d for d in domains):
        score += 25.0

    # Location match
    if parsed.location and parsed.location.lower() in locs:
        score += 20.0

    # Year match
    if parsed.developed_on and record.get("developed_on") == parsed.developed_on:
        score += 10.0

    # Keyword match bonus
    if parsed.keyword:
        kw = parsed.keyword.lower()
        if kw in record.get("name", "").lower():
            score += 25.0
        elif record.get("tagline") and kw in record.get("tagline", "").lower():
            score += 15.0
        elif record.get("description") and kw in record.get("description", "").lower():
            score += 10.0
        elif any(kw in t.lower() for t in techs) or any(kw in d.lower() for d in domains):
            score += 10.0

    return round(score, 2)
