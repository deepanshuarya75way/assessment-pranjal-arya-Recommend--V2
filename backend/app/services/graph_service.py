"""
Graph Service - Provides graph visualization data.

Queries the Neo4j graph and returns a deduplicated set of
nodes and edges suitable for force-directed graph rendering.
"""
import logging
from app.core.database import neo4j_driver
from app.models.schemas import GraphResponse, GraphNode, GraphLink
import heapq
from typing import Optional


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

    
RELATIONSHIP_WEIGHTS = {
    "DEVELOPED": 1.0,
    "USES_TECH": 1.2,
    "BELONGS_TO": 1.5,
    "LOCATED_IN": 2.0,
}


def find_shortest_path_dijkstra(
    source_id: str,
    target_id: str,
    max_depth: int = 4,
    weighted: bool = True,
) -> dict:
    """
    Find the shortest path between source_id and target_id using Dijkstra's algorithm,
    constrained by max_depth (2 to 6 hops).
    """
    max_depth = max(2, min(6, max_depth))

    # Fetch ALL nodes and relationships directly from Neo4j
    node_query = """
    MATCH (n)
    WHERE n.name IS NOT NULL
    RETURN labels(n)[0] AS label_type, n.name AS name, properties(n) AS props
    """
    edge_query = """
    MATCH (a)-[r]->(b)
    WHERE a.name IS NOT NULL AND b.name IS NOT NULL
    RETURN labels(a)[0] AS src_type, a.name AS src_name,
           type(r) AS rel_type,
           labels(b)[0] AS dst_type, b.name AS dst_name
    """

    PREFIX_MAP = {
        "Developer": "dev",
        "Project": "proj",
        "Technology": "tech",
        "Domain": "dom",
        "Location": "loc",
    }

    try:
        node_rows = neo4j_driver.execute_query(node_query, {})
        edge_rows = neo4j_driver.execute_query(edge_query, {})
    except Exception as e:
        logger.error(f"Dijkstra graph fetch failed: {e}")
        return {"found": False, "message": f"Database query failed: {e}"}

    nodes_by_id: dict[str, GraphNode] = {}
    for row in node_rows:
        ntype = row.get("label_type")
        name = row.get("name")
        prefix = PREFIX_MAP.get(ntype)
        if not prefix or not name:
            continue
        nid = f"{prefix}_{name.strip()}"
        if nid not in nodes_by_id:
            nodes_by_id[nid] = GraphNode(
                id=nid,
                label=name.strip(),
                type=ntype,
                color=NODE_COLORS.get(ntype, "#94a3b8"),
                size=NODE_SIZES.get(ntype, 6),
                properties=row.get("props") or {},
            )

    clean_source = source_id.strip()
    clean_target = target_id.strip()

    if clean_source not in nodes_by_id or clean_target not in nodes_by_id:
        missing = [x for x in (clean_source, clean_target) if x not in nodes_by_id]
        return {
            "found": False,
            "message": f"Entity not found in Neo4j: {', '.join(missing)}",
        }

    if clean_source == clean_target:
        return {
            "found": True,
            "degrees": 0,
            "total_cost": 0.0,
            "nodes": [nodes_by_id[clean_source].model_dump()],
            "edges": [],
        }

    adj: dict[str, list[tuple[str, str, float]]] = {nid: [] for nid in nodes_by_id}
    for row in edge_rows:
        s_prefix = PREFIX_MAP.get(row.get("src_type"))
        t_prefix = PREFIX_MAP.get(row.get("dst_type"))
        s_name = row.get("src_name")
        t_name = row.get("dst_name")
        rel_type = row.get("rel_type")
        if not (s_prefix and t_prefix and s_name and t_name and rel_type):
            continue

        s_id = f"{s_prefix}_{s_name.strip()}"
        t_id = f"{t_prefix}_{t_name.strip()}"
        if s_id in adj and t_id in adj:
            cost = RELATIONSHIP_WEIGHTS.get(rel_type, 1.0) if weighted else 1.0
            adj[s_id].append((t_id, rel_type, cost))
            adj[t_id].append((s_id, rel_type, cost))

    pq = [(0.0, 0, clean_source, [clean_source], [])]
    best_cost: dict[tuple[str, int], float] = {(clean_source, 0): 0.0}

    while pq:
        cost, hops, curr_id, node_path, edge_path = heapq.heappop(pq)

        if curr_id == clean_target:
            return {
                "found": True,
                "degrees": hops,
                "total_cost": round(cost, 2),
                "nodes": [nodes_by_id[nid].model_dump() for nid in node_path],
                "edges": edge_path,
            }

        if hops >= max_depth:
            continue

        for neighbor_id, rel_type, edge_cost in adj.get(curr_id, []):
            if neighbor_id in node_path:
                continue
            new_hops = hops + 1
            new_cost = cost + edge_cost
            state = (neighbor_id, new_hops)

            if new_cost < best_cost.get(state, float("inf")):
                best_cost[state] = new_cost
                edge_obj = {
                    "source": curr_id,
                    "target": neighbor_id,
                    "type": rel_type,
                    "weight": edge_cost,
                }
                heapq.heappush(
                    pq,
                    (new_cost, new_hops, neighbor_id, node_path + [neighbor_id], edge_path + [edge_obj]),
                )

    return {
        "found": False,
        "degrees": None,
        "total_cost": None,
        "nodes": [],
        "edges": [],
        "message": f"No connection found between '{clean_source}' and '{clean_target}' within {max_depth} degrees.",
    }


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
