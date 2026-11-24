"""Seed data API endpoint - loads initial data into Neo4j."""
import logging
import os
from fastapi import APIRouter, HTTPException

from app.core.database import neo4j_driver

logger = logging.getLogger(__name__)
router = APIRouter()

# Cypher statements for constraints/indexes that must exist
CONSTRAINT_STATEMENTS = [
    "CREATE CONSTRAINT developer_name IF NOT EXISTS FOR (d:Developer) REQUIRE d.name IS UNIQUE",
    "CREATE CONSTRAINT project_name IF NOT EXISTS FOR (p:Project) REQUIRE p.name IS UNIQUE",
    "CREATE CONSTRAINT technology_name IF NOT EXISTS FOR (t:Technology) REQUIRE t.name IS UNIQUE",
    "CREATE CONSTRAINT domain_name IF NOT EXISTS FOR (d:Domain) REQUIRE d.name IS UNIQUE",
    "CREATE CONSTRAINT location_name IF NOT EXISTS FOR (l:Location) REQUIRE l.name IS UNIQUE",
    "CREATE INDEX developer_project_count IF NOT EXISTS FOR (d:Developer) ON (d.project_count)",
    "CREATE CONSTRAINT feedback_id IF NOT EXISTS FOR (f:Feedback) REQUIRE f.id IS UNIQUE",
]


@router.post("/seed", summary="Seed Database")
async def seed_database(force: bool = False):
    """
    Seed the database with initial data.

    By default, skips seeding if graph data already exists.
    Set `force=true` to wipe graph nodes (preserving :Feedback) and re-seed.
    """
    try:
        # Count existing graph nodes (excluding :Feedback review nodes)
        check = neo4j_driver.execute_query(
            "MATCH (n) WHERE NOT n:Feedback RETURN count(n) as count"
        )
        existing_count = check[0].get("count", 0) if check else 0

        if existing_count > 0 and not force:
            return {
                "status": "skipped",
                "message": f"Database already has {existing_count} nodes. Use force=true to re-seed.",
                "node_count": existing_count,
            }

        # If force re-seed, clear existing graph data while preserving user feedback
        if force and existing_count > 0:
            logger.info(f"Force re-seeding: clearing {existing_count} existing graph nodes...")
            neo4j_driver.execute_write("MATCH (n) WHERE NOT n:Feedback DETACH DELETE n")
            logger.info("Graph data cleared (user feedback preserved).")

        # Ensure constraints exist first
        for stmt in CONSTRAINT_STATEMENTS:
            try:
                neo4j_driver.execute_write(stmt)
            except Exception as e:
                if "already exists" not in str(e).lower() and "equivalent" not in str(e).lower():
                    logger.warning(f"Constraint warning: {e}")

        # Locate seed file
        seed_file = _find_seed_file()

        if seed_file:
            logger.info(f"Loading seed data from: {seed_file}")
            return await _seed_from_file(seed_file)
        else:
            logger.warning("seed_data.cypher not found, using minimal inline seed.")
            return {
                "status": "partial",
                "message": "Created constraints/indexes only. Upload seed_data.cypher for full data.",
            }

    except Exception as e:
        logger.error(f"Seed failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/seed", summary="Clear Database")
async def clear_database(include_feedback: bool = False):
    """
    Remove nodes and relationships from the database.

    By default, preserves :Feedback review nodes unless `include_feedback=true`.
    ⚠️ This is irreversible. Use with caution.
    """
    try:
        where_clause = "" if include_feedback else "WHERE NOT n:Feedback"
        check = neo4j_driver.execute_query(
            f"MATCH (n) {where_clause} RETURN count(n) as count"
        )
        count_before = check[0].get("count", 0) if check else 0

        neo4j_driver.execute_write(f"MATCH (n) {where_clause} DETACH DELETE n")

        return {
            "status": "cleared",
            "message": f"Deleted {count_before} nodes and all relationships.",
            "deleted_count": count_before,
        }
    except Exception as e:
        logger.error(f"Clear database failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats", summary="Graph Statistics")
async def get_stats():
    """
    Get statistics about the knowledge graph.

    Returns node counts by type, relationship counts by type,
    and whether the database appears seeded.
    """
    try:
        stats = neo4j_driver.get_stats()

        # Exclude Feedback nodes from seeded heuristic count
        graph_nodes = {k: v for k, v in stats["nodes"].items() if k != "Feedback"}
        total_nodes = sum(graph_nodes.values())
        total_rels = sum(stats["relationships"].values())
        is_seeded = total_nodes >= 10  # Heuristic: seeded DB has many nodes

        return {
            "nodes": stats["nodes"],
            "relationships": stats["relationships"],
            "total_nodes": total_nodes,
            "total_relationships": total_rels,
            "is_seeded": is_seeded,
        }
    except Exception as e:
        logger.error(f"Stats query failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# --- Helpers ---

def _find_seed_file() -> str | None:
    """Locate the seed_data.cypher file in known locations."""
    candidates = [
        # Relative to backend app directory
        os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "..", "neo4j", "init", "seed_data.cypher"
        ),
        # Neo4j container import directory
        "/var/lib/neo4j/import/seed_data.cypher",
        # Current working directory
        "neo4j/init/seed_data.cypher",
    ]
    for path in candidates:
        normalized = os.path.normpath(path)
        if os.path.exists(normalized):
            return normalized
    return None


async def _seed_from_file(seed_file: str) -> dict:
    """Parse and execute a Cypher seed file."""
    with open(seed_file, "r") as f:
        content = f.read()

    statements = _parse_cypher_statements(content)
    logger.info(f"Executing {len(statements)} Cypher statements...")

    success_count = 0
    skip_count = 0
    error_count = 0

    for stmt in statements:
        stmt = stmt.strip()
        if not stmt:
            continue
        try:
            neo4j_driver.execute_write(stmt)
            success_count += 1
        except Exception as e:
            err_str = str(e).lower()
            if any(k in err_str for k in ("already exists", "equivalent", "constraint")):
                skip_count += 1
            else:
                logger.warning(f"Statement error (skipped): {e}\nStatement: {stmt[:100]}...")
                error_count += 1

    # Count result (excluding :Feedback nodes)
    count_result = neo4j_driver.execute_query(
        "MATCH (n) WHERE NOT n:Feedback RETURN count(n) as count"
    )
    final_count = count_result[0].get("count", 0) if count_result else 0

    logger.info(
        f"Seed complete: {final_count} nodes | "
        f"{success_count} ok, {skip_count} skipped, {error_count} errors"
    )

    return {
        "status": "success",
        "message": f"Database seeded with {final_count} nodes",
        "node_count": final_count,
        "statements_executed": success_count,
        "statements_skipped": skip_count,
        "statements_errored": error_count,
    }


def _parse_cypher_statements(content: str) -> list[str]:
    """
    Parse a Cypher file into individual executable statements.

    Handles:
    - Line comments (//)
    - Multi-statement CREATE blocks
    - Semicolon delimiters
    """
    statements = []
    current_lines = []

    for line in content.split("\n"):
        stripped = line.strip()

        # Skip empty lines and comments
        if not stripped or stripped.startswith("//"):
            continue

        current_lines.append(stripped)

        # Statement ends at semicolon
        if stripped.endswith(";"):
            stmt = " ".join(current_lines).rstrip(";").strip()
            if stmt:
                statements.append(stmt)
            current_lines = []

    # Flush remaining content without trailing semicolon
    if current_lines:
        stmt = " ".join(current_lines).rstrip(";").strip()
        if stmt:
            statements.append(stmt)

    return statements
