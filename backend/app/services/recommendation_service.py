"""
Recommendation Service - Find similar projects and developers.

Uses graph traversal over shared technologies, domains, and locations
to surface the most relevant recommendations.
"""
import logging
from typing import List
from app.core.database import neo4j_driver
from app.models.schemas import (
    DeveloperResponse, ProjectResponse, RecommendationResponse
)

logger = logging.getLogger(__name__)


def get_project_recommendations(project_name: str, limit: int = 6) -> RecommendationResponse:
    """
    Get recommendations for a given project.

    Finds similar projects by shared technologies, domains, and locations.
    Also recommends developers who work on similar projects.
    """
    # --- Similar Projects ---
    project_query = """
    MATCH (source:Project {name: $name})
    MATCH (similar:Project)
    WHERE similar <> source

    // Score by shared technologies
    OPTIONAL MATCH (source)-[:USES_TECH]->(t:Technology)<-[:USES_TECH]-(similar)
    WITH source, similar, COUNT(DISTINCT t) AS shared_techs

    // Score by shared domains
    OPTIONAL MATCH (source)-[:BELONGS_TO]->(d:Domain)<-[:BELONGS_TO]-(similar)
    WITH source, similar, shared_techs, COUNT(DISTINCT d) AS shared_domains

    // Score by shared locations
    OPTIONAL MATCH (source)-[:LOCATED_IN]->(l:Location)<-[:LOCATED_IN]-(similar)
    WITH similar, shared_techs, shared_domains, COUNT(DISTINCT l) AS shared_locs

    // Only return matches with at least one shared feature
    WHERE (shared_techs + shared_domains + shared_locs) > 0

    WITH similar, (shared_techs * 3 + shared_domains * 2 + shared_locs) AS score
    ORDER BY score DESC
    LIMIT $limit

    RETURN
        similar.name AS name,
        similar.description AS description,
        similar.tagline AS tagline,
        similar.developed_on AS developed_on,
        [(dev:Developer)-[:DEVELOPED]->(similar) | dev.name] AS developers,
        [(similar)-[:USES_TECH]->(tech:Technology) | tech.name] AS technologies,
        [(similar)-[:BELONGS_TO]->(domain:Domain) | domain.name] AS domains,
        [(similar)-[:LOCATED_IN]->(location:Location) | location.name] AS locations,
        score
    ORDER BY score DESC
    """

    # --- Recommended Developers (devs who work on similar tech/domain) ---
    developer_query = """
    MATCH (source:Project {name: $name})-[:USES_TECH]->(t:Technology)
    WITH source, COLLECT(DISTINCT t.name) AS source_techs

    MATCH (d:Developer)-[:DEVELOPED]->(p:Project)-[:USES_TECH]->(dt:Technology)
    WHERE dt.name IN source_techs
    AND NOT (d)-[:DEVELOPED]->(source)

    WITH d, COUNT(DISTINCT dt) AS shared_techs
    ORDER BY shared_techs DESC
    LIMIT $limit

    RETURN
        d.name AS name,
        d.project_count AS project_count,
        d.bio AS bio,
        [(d)-[:DEVELOPED]->(proj:Project) | proj.name] AS projects,
        [(d)-[:DEVELOPED]->(:Project)-[:USES_TECH]->(tech:Technology) | tech.name] AS technologies,
        [(d)-[:DEVELOPED]->(:Project)-[:BELONGS_TO]->(domain:Domain) | domain.name] AS domains,
        [(d)-[:DEVELOPED]->(:Project)-[:LOCATED_IN]->(location:Location) | location.name] AS locations,
        shared_techs AS score
    ORDER BY score DESC
    """

    params = {"name": project_name, "limit": limit}

    try:
        project_results = neo4j_driver.execute_query(project_query, params)
    except Exception as e:
        logger.error(f"Project recommendation query failed: {e}")
        project_results = []

    try:
        dev_results = neo4j_driver.execute_query(developer_query, params)
    except Exception as e:
        logger.error(f"Developer-from-project recommendation query failed: {e}")
        dev_results = []

    projects = [
        ProjectResponse(
            name=r.get("name", ""),
            description=r.get("description"),
            tagline=r.get("tagline"),
            developed_on=r.get("developed_on"),
            developers=list(set([d for d in r.get("developers", []) if d])),
            technologies=list(set([t for t in r.get("technologies", []) if t])),
            domains=list(set([d for d in r.get("domains", []) if d])),
            locations=list(set([l for l in r.get("locations", []) if l])),
            relevance_score=float(r.get("score", 0)),
        )
        for r in project_results
    ]

    developers = [
        DeveloperResponse(
            name=r.get("name", ""),
            project_count=r.get("project_count") or 0,
            bio=r.get("bio"),
            projects=list(set([p for p in r.get("projects", []) if p])),
            technologies=list(set([t for t in r.get("technologies", []) if t])),
            domains=list(set([d for d in r.get("domains", []) if d])),
            locations=list(set([l for l in r.get("locations", []) if l])),
            relevance_score=float(r.get("score", 0)),
        )
        for r in dev_results
    ]

    return RecommendationResponse(
        source=project_name,
        source_type="project",
        recommended_projects=projects,
        recommended_developers=developers,
    )


def get_developer_recommendations(developer_name: str, limit: int = 6) -> RecommendationResponse:
    """
    Get recommendations for a given developer.

    Finds similar developers by shared technologies and domains.
    Also recommends projects they might want to work on.
    """
    # --- Similar Developers ---
    developer_query = """
    MATCH (source:Developer {name: $name})-[:DEVELOPED]->(p:Project)-[:USES_TECH]->(t:Technology)
    WITH source, COLLECT(DISTINCT t.name) AS source_techs, COLLECT(DISTINCT p) AS source_projects

    MATCH (other:Developer)-[:DEVELOPED]->(op:Project)-[:USES_TECH]->(ot:Technology)
    WHERE other <> source AND ot.name IN source_techs

    WITH source, other, COUNT(DISTINCT ot) AS shared_techs
    ORDER BY shared_techs DESC
    LIMIT $limit

    RETURN
        other.name AS name,
        other.project_count AS project_count,
        other.bio AS bio,
        [(other)-[:DEVELOPED]->(proj:Project) | proj.name] AS projects,
        [(other)-[:DEVELOPED]->(:Project)-[:USES_TECH]->(tech:Technology) | tech.name] AS technologies,
        [(other)-[:DEVELOPED]->(:Project)-[:BELONGS_TO]->(domain:Domain) | domain.name] AS domains,
        [(other)-[:DEVELOPED]->(:Project)-[:LOCATED_IN]->(location:Location) | location.name] AS locations,
        shared_techs AS score
    ORDER BY score DESC
    """

    # --- Recommended Projects (projects using dev's known technologies, not yet built by them) ---
    project_query = """
    MATCH (source:Developer {name: $name})-[:DEVELOPED]->(p:Project)-[:USES_TECH]->(t:Technology)
    WITH source, COLLECT(DISTINCT t.name) AS source_techs, COLLECT(DISTINCT p) AS built_projects

    MATCH (rp:Project)-[:USES_TECH]->(rt:Technology)
    WHERE rt.name IN source_techs
    AND NOT rp IN built_projects

    WITH rp, COUNT(DISTINCT rt) AS shared_techs
    ORDER BY shared_techs DESC
    LIMIT $limit

    RETURN
        rp.name AS name,
        rp.description AS description,
        rp.tagline AS tagline,
        rp.developed_on AS developed_on,
        [(dev:Developer)-[:DEVELOPED]->(rp) | dev.name] AS developers,
        [(rp)-[:USES_TECH]->(tech:Technology) | tech.name] AS technologies,
        [(rp)-[:BELONGS_TO]->(domain:Domain) | domain.name] AS domains,
        [(rp)-[:LOCATED_IN]->(location:Location) | location.name] AS locations,
        shared_techs AS score
    ORDER BY score DESC
    """

    params = {"name": developer_name, "limit": limit}

    try:
        dev_results = neo4j_driver.execute_query(developer_query, params)
    except Exception as e:
        logger.error(f"Developer recommendation query failed: {e}")
        dev_results = []

    try:
        project_results = neo4j_driver.execute_query(project_query, params)
    except Exception as e:
        logger.error(f"Project-from-developer recommendation query failed: {e}")
        project_results = []

    developers = [
        DeveloperResponse(
            name=r.get("name", ""),
            project_count=r.get("project_count") or 0,
            bio=r.get("bio"),
            projects=list(set([p for p in r.get("projects", []) if p])),
            technologies=list(set([t for t in r.get("technologies", []) if t])),
            domains=list(set([d for d in r.get("domains", []) if d])),
            locations=list(set([l for l in r.get("locations", []) if l])),
            relevance_score=float(r.get("score", 0)),
        )
        for r in dev_results
    ]

    projects = [
        ProjectResponse(
            name=r.get("name", ""),
            description=r.get("description"),
            tagline=r.get("tagline"),
            developed_on=r.get("developed_on"),
            developers=list(set([d for d in r.get("developers", []) if d])),
            technologies=list(set([t for t in r.get("technologies", []) if t])),
            domains=list(set([d for d in r.get("domains", []) if d])),
            locations=list(set([l for l in r.get("locations", []) if l])),
            relevance_score=float(r.get("score", 0)),
        )
        for r in project_results
    ]

    return RecommendationResponse(
        source=developer_name,
        source_type="developer",
        recommended_developers=developers,
        recommended_projects=projects,
    )
