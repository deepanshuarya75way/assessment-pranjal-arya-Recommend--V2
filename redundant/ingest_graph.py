"""
Neo4j Knowledge Graph Ingestion Script
=======================================
Reads software_knowledge_graph_data.csv and populates a Neo4j database with:

Nodes:
  (:Project)      – one per software row
  (:Developer)    – unique per developer name
  (:Technology)   – unique per technology token
  (:Domain)       – unique per category/domain
  (:Location)     – unique per workcenter / developer-group location

Relationships:
  (:Developer)-[:DEVELOPED]->(:Project)
  (:Project)-[:USES_TECH]->(:Technology)
  (:Project)-[:BELONGS_TO]->(:Domain)
  (:Project)-[:LOCATED_IN]->(:Location)
  (:Developer)-[:WORKS_AT]->(:Location)

Usage:
  python3 ingest_graph.py [--uri bolt://localhost:7687] [--user neo4j] [--password <pwd>] [--csv <path>]
"""

import csv
import argparse
import logging
import re
import os
import sys
from typing import Optional
from neo4j import GraphDatabase

# ─── Logging ────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("ingest")

# ─── Defaults (match config.py) ─────────────────────────────────────────────
DEFAULT_URI      = os.getenv("NEO4J_URI",      "bolt://localhost:7687")
DEFAULT_USER     = os.getenv("NEO4J_USER",     "neo4j")
DEFAULT_PASSWORD = os.getenv("NEO4J_PASSWORD", "recommend_neo4j_2024")
DEFAULT_DATABASE = os.getenv("NEO4J_DATABASE", "neo4j")
DEFAULT_CSV      = os.path.join(os.path.dirname(__file__), "software_knowledge_graph_data.csv")


# ─── Helpers ────────────────────────────────────────────────────────────────

def split_field(value: str) -> list[str]:
    """Split a comma-separated field, strip whitespace and drop empty tokens."""
    if not value or not value.strip():
        return []
    return [tok.strip() for tok in value.split(",") if tok.strip()]


def clean_str(value: Optional[str]) -> str:
    return (value or "").strip()


def extract_links(raw: str) -> list[dict]:
    """
    Parse 'Link text (url)' entries from the Links column.
    Returns a list of {"label": ..., "url": ...} dicts.
    """
    links = []
    for match in re.finditer(r'([^(]+?)\s*\(([^)]+)\)', raw or ""):
        label = match.group(1).strip().rstrip(",").strip()
        url   = match.group(2).strip()
        if url.startswith("http"):
            links.append({"label": label, "url": url})
    return links


# ─── Cypher helpers ─────────────────────────────────────────────────────────

CONSTRAINTS_CYPHER = [
    "CREATE CONSTRAINT project_name   IF NOT EXISTS FOR (p:Project)    REQUIRE p.name IS UNIQUE",
    "CREATE CONSTRAINT developer_name IF NOT EXISTS FOR (d:Developer)  REQUIRE d.name IS UNIQUE",
    "CREATE CONSTRAINT tech_name      IF NOT EXISTS FOR (t:Technology) REQUIRE t.name IS UNIQUE",
    "CREATE CONSTRAINT domain_name    IF NOT EXISTS FOR (dom:Domain)   REQUIRE dom.name IS UNIQUE",
    "CREATE CONSTRAINT location_name  IF NOT EXISTS FOR (loc:Location) REQUIRE loc.name IS UNIQUE",
]

MERGE_PROJECT = """
MERGE (p:Project {name: $name})
SET   p.short_description   = $short_desc,
      p.description         = $description,
      p.child_file          = $child_file,
      p.links               = $links,
      p.developer_group     = $developer_group
"""

MERGE_DEVELOPER = """
MERGE (d:Developer {name: $name})
ON CREATE SET d.email       = $email,
              d.phone       = $phone,
              d.bio         = $name,
              d.project_count = 1
ON MATCH  SET d.email       = CASE WHEN $email <> '' THEN $email ELSE d.email END,
              d.phone       = CASE WHEN $phone <> '' THEN $phone ELSE d.phone END,
              d.project_count = d.project_count + 1
"""

MERGE_TECH = "MERGE (:Technology {name: $name})"
MERGE_DOMAIN = "MERGE (:Domain {name: $name})"
MERGE_LOCATION = "MERGE (:Location {name: $name})"

REL_DEVELOPED = """
MATCH (d:Developer {name: $dev_name}), (p:Project {name: $proj_name})
MERGE (d)-[:DEVELOPED]->(p)
"""

REL_USES_TECH = """
MATCH (p:Project {name: $proj_name}), (t:Technology {name: $tech_name})
MERGE (p)-[:USES_TECH]->(t)
"""

REL_BELONGS_TO = """
MATCH (p:Project {name: $proj_name}), (dom:Domain {name: $dom_name})
MERGE (p)-[:BELONGS_TO]->(dom)
"""

REL_LOCATED_IN = """
MATCH (p:Project {name: $proj_name}), (loc:Location {name: $loc_name})
MERGE (p)-[:LOCATED_IN]->(loc)
"""

REL_WORKS_AT = """
MATCH (d:Developer {name: $dev_name}), (loc:Location {name: $loc_name})
MERGE (d)-[:WORKS_AT]->(loc)
"""


# ─── Location extraction ────────────────────────────────────────────────────

def extract_location(workcenter_raw: str, developer_group_raw: str) -> Optional[str]:
    """
    Derive the best Location name from Workcenters + Developer Group columns.
    Strategy: prefer the developer group string if it contains a known city/office,
    otherwise fall back to the workcenter.
    """
    combined = f"{workcenter_raw}, {developer_group_raw}".strip(", ")
    # Use workcenter as the primary location (it is more concise)
    if workcenter_raw.strip():
        return workcenter_raw.strip()
    if developer_group_raw.strip():
        return developer_group_raw.strip()
    return None


# ─── Main ingestion logic ────────────────────────────────────────────────────

def run_ingestion(uri: str, user: str, password: str, database: str, csv_path: str):
    log.info(f"Connecting to Neo4j at {uri} (db={database}) …")
    driver = GraphDatabase.driver(uri, auth=(user, password))
    try:
        driver.verify_connectivity()
    except Exception as exc:
        log.error(f"Cannot connect to Neo4j: {exc}")
        log.error("Make sure Neo4j is running and the credentials in config.py are correct.")
        sys.exit(1)

    log.info("Connected ✓")

    # ── Step 1: constraints ──────────────────────────────────────────────────
    with driver.session(database=database) as session:
        for cypher in CONSTRAINTS_CYPHER:
            try:
                session.run(cypher)
            except Exception as e:
                log.warning(f"Constraint skipped ({e})")
    log.info("Constraints created ✓")

    # ── Step 2: read CSV ─────────────────────────────────────────────────────
    if not os.path.exists(csv_path):
        log.error(f"CSV not found: {csv_path}")
        sys.exit(1)

    with open(csv_path, newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        rows = [row for row in reader if row.get("Software Name", "").strip()]

    log.info(f"Loaded {len(rows)} software rows from CSV")

    # ── Step 3: ingest ───────────────────────────────────────────────────────
    stats = {
        "projects": 0, "developers": 0, "technologies": 0,
        "domains": 0, "locations": 0, "relationships": 0,
    }

    with driver.session(database=database) as session:
        for i, row in enumerate(rows, 1):
            proj_name    = clean_str(row.get("Software Name", ""))
            short_desc   = clean_str(row.get("Short Description", ""))
            description  = clean_str(row.get("Detailed Description", ""))
            categories   = split_field(row.get("Categories", ""))
            workcenter   = clean_str(row.get("Workcenters", ""))
            technologies = split_field(row.get("Technologies", ""))
            dev_group    = clean_str(row.get("Developer Group", ""))
            dev_names    = split_field(row.get("Developer Names", ""))
            dev_mails    = split_field(row.get("Developer Mails", ""))
            dev_phones   = split_field(row.get("Developer Phones", ""))
            links_raw    = clean_str(row.get("Links", ""))
            child_file   = clean_str(row.get("Child File", ""))
            location     = extract_location(workcenter, dev_group)

            if not proj_name:
                continue

            # ── Project node ─────────────────────────────────────────────────
            session.run(MERGE_PROJECT, {
                "name":             proj_name,
                "short_desc":       short_desc,
                "description":      description,
                "child_file":       child_file,
                "links":            links_raw,
                "developer_group":  dev_group,
            })
            stats["projects"] += 1

            # ── Technology nodes + relationships ─────────────────────────────
            for tech in technologies:
                session.run(MERGE_TECH, {"name": tech})
                session.run(REL_USES_TECH, {"proj_name": proj_name, "tech_name": tech})
                stats["technologies"] += 1
                stats["relationships"] += 1

            # ── Domain nodes + relationships ─────────────────────────────────
            for cat in categories:
                session.run(MERGE_DOMAIN, {"name": cat})
                session.run(REL_BELONGS_TO, {"proj_name": proj_name, "dom_name": cat})
                stats["domains"] += 1
                stats["relationships"] += 1

            # ── Location node + project relationship ─────────────────────────
            if location:
                session.run(MERGE_LOCATION, {"name": location})
                session.run(REL_LOCATED_IN, {"proj_name": proj_name, "loc_name": location})
                stats["locations"] += 1
                stats["relationships"] += 1

            # ── Developer nodes + relationships ──────────────────────────────
            for j, dev_name in enumerate(dev_names):
                if not dev_name or dev_name in ("-", "---"):
                    continue
                email = dev_mails[j] if j < len(dev_mails) else ""
                phone = dev_phones[j] if j < len(dev_phones) else ""
                # Sanitise placeholder values
                email = email if "@" in email else ""
                phone = phone if phone not in ("-", "---", "") else ""

                session.run(MERGE_DEVELOPER, {
                    "name":  dev_name,
                    "email": email,
                    "phone": phone,
                })
                stats["developers"] += 1

                # Developer → Project
                session.run(REL_DEVELOPED, {"dev_name": dev_name, "proj_name": proj_name})
                stats["relationships"] += 1

                # Developer → Location
                if location:
                    session.run(REL_WORKS_AT, {"dev_name": dev_name, "loc_name": location})
                    stats["relationships"] += 1

            if i % 10 == 0 or i == len(rows):
                log.info(f"  [{i:3d}/{len(rows)}] ingested: {proj_name}")

    # ── Step 4: summary ──────────────────────────────────────────────────────
    log.info("─" * 60)
    log.info("Ingestion complete!")
    log.info(f"  Projects     : {stats['projects']}")
    log.info(f"  Technologies : unique merges ~ {stats['technologies']} ops")
    log.info(f"  Domains      : unique merges ~ {stats['domains']} ops")
    log.info(f"  Locations    : unique merges ~ {stats['locations']} ops")
    log.info(f"  Developer ops: {stats['developers']}")
    log.info(f"  Relationships: {stats['relationships']}")

    # ── Step 5: verify counts ─────────────────────────────────────────────────
    with driver.session(database=database) as session:
        for label in ["Project", "Developer", "Technology", "Domain", "Location"]:
            count = session.run(f"MATCH (n:{label}) RETURN count(n) AS c").single()["c"]
            log.info(f"  DB :{label:12s}  →  {count} nodes")
        for rel_type in ["DEVELOPED", "USES_TECH", "BELONGS_TO", "LOCATED_IN", "WORKS_AT"]:
            count = session.run(f"MATCH ()-[r:{rel_type}]->() RETURN count(r) AS c").single()["c"]
            log.info(f"  DB :{rel_type:12s}  →  {count} relationships")

    driver.close()
    log.info("Done ✓")


# ─── Entry point ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingest CSV into Neo4j knowledge graph")
    parser.add_argument("--uri",      default=DEFAULT_URI,      help="Neo4j Bolt URI")
    parser.add_argument("--user",     default=DEFAULT_USER,     help="Neo4j username")
    parser.add_argument("--password", default=DEFAULT_PASSWORD, help="Neo4j password")
    parser.add_argument("--database", default=DEFAULT_DATABASE, help="Neo4j database name")
    parser.add_argument("--csv",      default=DEFAULT_CSV,      help="Path to CSV file")
    args = parser.parse_args()

    run_ingestion(args.uri, args.user, args.password, args.database, args.csv)
