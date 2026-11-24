"""
Graph Service - Provides graph visualization data.

Queries the Neo4j graph and returns a deduplicated set of
nodes and edges suitable for force-directed graph rendering.
"""
import logging
from app.core.database import neo4j_driver
from app.models.schemas import GraphResponse, GraphNode, GraphLink

logger = logging.getLogger(__name__)

# Node type colors (matches frontend palette)
NODE_COLORS = {
    "Developer": "#6366f1",   # Indigo
    "Project":   "#06b6d4",   # Cyan
    "Technology": "#f59e0b",  # Amber
    "Domain":    "#10b981",   # Emerald
    "Location":  "#ef4444",   # Red
}

NODE_SIZES = {
    "Developer": 12,
    "Project":   10,
    "Technology": 6,
    "Domain":     8,
    "Location":   7,
}


def get_full_graph(query: str = None) -> GraphResponse:
    """
    Get the knowledge graph for visualization.
    If query is provided, it filters the graph to nodes relevant to the search.
    """
    params = {}
    where_clause = ""
    
    if query:
        from app.services.search_service import search
        search_res = search(query, limit=50)
        dev_names = [d.name for d in search_res.developers]
        proj_names = [p.name for p in search_res.projects]
        
        if not dev_names and not proj_names:
            return GraphResponse() # No matches
            
        where_clause = "WHERE d.name IN $dev_names OR p.name IN $proj_names"
        params = {"dev_names": dev_names, "proj_names": proj_names}

    cypher_query = f"""
    MATCH (d:Developer)-[r1:DEVELOPED]->(p:Project)
    {where_clause}
    OPTIONAL MATCH (p)-[r2:USES_TECH]->(t:Technology)
    OPTIONAL MATCH (p)-[r3:BELONGS_TO]->(dom:Domain)
    OPTIONAL MATCH (p)-[r4:LOCATED_IN]->(loc:Location)
    RETURN
        d.name AS dev_name, d.project_count AS dev_project_count, d.bio AS dev_bio,
        p.name AS proj_name, p.tagline AS proj_tagline, p.developed_on AS proj_year,
        t.name AS tech_name,
        dom.name AS dom_name,
        loc.name AS loc_name
    """

    try:
        results = neo4j_driver.execute_query(cypher_query, params)
    except Exception as e:
        logger.error(f"Graph query failed: {e}")
        return GraphResponse()

    nodes_map: dict[str, GraphNode] = {}
    links_set: set[tuple] = set()
    link_list: list[GraphLink] = []

    for record in results:
        dev_name = record.get("dev_name")
        proj_name = record.get("proj_name")
        tech_name = record.get("tech_name")
        dom_name = record.get("dom_name")
        loc_name = record.get("loc_name")

        # --- Developer node ---
        if dev_name:
            dev_id = f"dev_{dev_name}"
            if dev_id not in nodes_map:
                nodes_map[dev_id] = GraphNode(
                    id=dev_id,
                    label=dev_name,
                    type="Developer",
                    color=NODE_COLORS["Developer"],
                    size=NODE_SIZES["Developer"],
                    properties={
                        "project_count": record.get("dev_project_count", 0),
                        "bio": record.get("dev_bio", ""),
                    },
                )

        # --- Project node ---
        if proj_name:
            proj_id = f"proj_{proj_name}"
            if proj_id not in nodes_map:
                nodes_map[proj_id] = GraphNode(
                    id=proj_id,
                    label=proj_name,
                    type="Project",
                    color=NODE_COLORS["Project"],
                    size=NODE_SIZES["Project"],
                    properties={
                        "tagline": record.get("proj_tagline", ""),
                        "developed_on": record.get("proj_year", ""),
                    },
                )

            # Developer -> Project link
            if dev_name:
                dev_id = f"dev_{dev_name}"
                key = (dev_id, proj_id, "DEVELOPED")
                if key not in links_set:
                    links_set.add(key)
                    link_list.append(GraphLink(source=dev_id, target=proj_id, type="DEVELOPED"))

        # --- Technology node ---
        if tech_name:
            tech_id = f"tech_{tech_name}"
            if tech_id not in nodes_map:
                nodes_map[tech_id] = GraphNode(
                    id=tech_id,
                    label=tech_name,
                    type="Technology",
                    color=NODE_COLORS["Technology"],
                    size=NODE_SIZES["Technology"],
                )
            if proj_name:
                proj_id = f"proj_{proj_name}"
                key = (proj_id, tech_id, "USES_TECH")
                if key not in links_set:
                    links_set.add(key)
                    link_list.append(GraphLink(source=proj_id, target=tech_id, type="USES_TECH"))

        # --- Domain node ---
        if dom_name:
            dom_id = f"dom_{dom_name}"
            if dom_id not in nodes_map:
                nodes_map[dom_id] = GraphNode(
                    id=dom_id,
                    label=dom_name,
                    type="Domain",
                    color=NODE_COLORS["Domain"],
                    size=NODE_SIZES["Domain"],
                )
            if proj_name:
                proj_id = f"proj_{proj_name}"
                key = (proj_id, dom_id, "BELONGS_TO")
                if key not in links_set:
                    links_set.add(key)
                    link_list.append(GraphLink(source=proj_id, target=dom_id, type="BELONGS_TO"))

        # --- Location node ---
        if loc_name:
            loc_id = f"loc_{loc_name}"
            if loc_id not in nodes_map:
                nodes_map[loc_id] = GraphNode(
                    id=loc_id,
                    label=loc_name,
                    type="Location",
                    color=NODE_COLORS["Location"],
                    size=NODE_SIZES["Location"],
                )
            if proj_name:
                proj_id = f"proj_{proj_name}"
                key = (proj_id, loc_id, "LOCATED_IN")
                if key not in links_set:
                    links_set.add(key)
                    link_list.append(GraphLink(source=proj_id, target=loc_id, type="LOCATED_IN"))

    # Compute node type counts for stats
    type_counts: dict[str, int] = {}
    for node in nodes_map.values():
        type_counts[node.type] = type_counts.get(node.type, 0) + 1

    logger.info(
        f"Graph built: {len(nodes_map)} nodes, {len(link_list)} links | "
        + ", ".join(f"{k}={v}" for k, v in type_counts.items())
    )

    return GraphResponse(
        nodes=list(nodes_map.values()),
        links=link_list,
        stats=type_counts,
    )


def get_subgraph(entity_type: str, entity_name: str) -> GraphResponse:
    """
    Get a subgraph centered on a specific entity.

    Useful for detail pages that need to show local graph context.
    """
    if entity_type == "developer":
        query = """
        MATCH (d:Developer {name: $name})-[:DEVELOPED]->(p:Project)
        OPTIONAL MATCH (p)-[:USES_TECH]->(t:Technology)
        OPTIONAL MATCH (p)-[:BELONGS_TO]->(dom:Domain)
        OPTIONAL MATCH (p)-[:LOCATED_IN]->(loc:Location)
        RETURN
            d.name AS dev_name, d.project_count AS dev_project_count, d.bio AS dev_bio,
            p.name AS proj_name, p.tagline AS proj_tagline, p.developed_on AS proj_year,
            t.name AS tech_name,
            dom.name AS dom_name,
            loc.name AS loc_name
        """
    elif entity_type == "project":
        query = """
        MATCH (p:Project {name: $name})
        OPTIONAL MATCH (d:Developer)-[:DEVELOPED]->(p)
        OPTIONAL MATCH (p)-[:USES_TECH]->(t:Technology)
        OPTIONAL MATCH (p)-[:BELONGS_TO]->(dom:Domain)
        OPTIONAL MATCH (p)-[:LOCATED_IN]->(loc:Location)
        RETURN
            d.name AS dev_name, d.project_count AS dev_project_count, d.bio AS dev_bio,
            p.name AS proj_name, p.tagline AS proj_tagline, p.developed_on AS proj_year,
            t.name AS tech_name,
            dom.name AS dom_name,
            loc.name AS loc_name
        """
    else:
        return GraphResponse()

    try:
        results = neo4j_driver.execute_query(query, {"name": entity_name})
    except Exception as e:
        logger.error(f"Subgraph query failed: {e}")
        return GraphResponse()

    # Reuse full graph builder logic on the filtered results
    nodes_map: dict[str, GraphNode] = {}
    links_set: set[tuple] = set()
    link_list: list[GraphLink] = []

    for record in results:
        dev_name = record.get("dev_name")
        proj_name = record.get("proj_name")
        tech_name = record.get("tech_name")
        dom_name = record.get("dom_name")
        loc_name = record.get("loc_name")

        if dev_name:
            dev_id = f"dev_{dev_name}"
            if dev_id not in nodes_map:
                nodes_map[dev_id] = GraphNode(
                    id=dev_id, label=dev_name, type="Developer",
                    color=NODE_COLORS["Developer"], size=NODE_SIZES["Developer"],
                    properties={"project_count": record.get("dev_project_count", 0), "bio": record.get("dev_bio", "")},
                )

        if proj_name:
            proj_id = f"proj_{proj_name}"
            if proj_id not in nodes_map:
                nodes_map[proj_id] = GraphNode(
                    id=proj_id, label=proj_name, type="Project",
                    color=NODE_COLORS["Project"], size=NODE_SIZES["Project"],
                    properties={"tagline": record.get("proj_tagline", ""), "developed_on": record.get("proj_year", "")},
                )
            if dev_name:
                dev_id = f"dev_{dev_name}"
                key = (dev_id, proj_id, "DEVELOPED")
                if key not in links_set:
                    links_set.add(key)
                    link_list.append(GraphLink(source=dev_id, target=proj_id, type="DEVELOPED"))

        if tech_name and proj_name:
            tech_id = f"tech_{tech_name}"
            proj_id = f"proj_{proj_name}"
            if tech_id not in nodes_map:
                nodes_map[tech_id] = GraphNode(
                    id=tech_id, label=tech_name, type="Technology",
                    color=NODE_COLORS["Technology"], size=NODE_SIZES["Technology"],
                )
            key = (proj_id, tech_id, "USES_TECH")
            if key not in links_set:
                links_set.add(key)
                link_list.append(GraphLink(source=proj_id, target=tech_id, type="USES_TECH"))

        if dom_name and proj_name:
            dom_id = f"dom_{dom_name}"
            proj_id = f"proj_{proj_name}"
            if dom_id not in nodes_map:
                nodes_map[dom_id] = GraphNode(
                    id=dom_id, label=dom_name, type="Domain",
                    color=NODE_COLORS["Domain"], size=NODE_SIZES["Domain"],
                )
            key = (proj_id, dom_id, "BELONGS_TO")
            if key not in links_set:
                links_set.add(key)
                link_list.append(GraphLink(source=proj_id, target=dom_id, type="BELONGS_TO"))

        if loc_name and proj_name:
            loc_id = f"loc_{loc_name}"
            proj_id = f"proj_{proj_name}"
            if loc_id not in nodes_map:
                nodes_map[loc_id] = GraphNode(
                    id=loc_id, label=loc_name, type="Location",
                    color=NODE_COLORS["Location"], size=NODE_SIZES["Location"],
                )
            key = (proj_id, loc_id, "LOCATED_IN")
            if key not in links_set:
                links_set.add(key)
                link_list.append(GraphLink(source=proj_id, target=loc_id, type="LOCATED_IN"))

    type_counts = {}
    for node in nodes_map.values():
        type_counts[node.type] = type_counts.get(node.type, 0) + 1

    return GraphResponse(
        nodes=list(nodes_map.values()),
        links=link_list,
        stats=type_counts,
    )
