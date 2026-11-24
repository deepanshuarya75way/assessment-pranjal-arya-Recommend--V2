import os
import re
from neo4j import GraphDatabase

# Locate environment configuration
env_path = "/home/pranjal_arya/Desktop/recommend/.env"
neo4j_uri = "bolt://localhost:7687"
neo4j_user = "neo4j"
neo4j_password = "recommend_neo4j_2024"

if os.path.exists(env_path):
    print("Reading configuration from .env file...")
    with open(env_path, "r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, val = line.split("=", 1)
                key = key.strip()
                val = val.strip()
                if key == "NEO4J_URI":
                    # If connecting from host, replace docker container name with localhost
                    neo4j_uri = val.replace("bolt://neo4j:", "bolt://localhost:")
                elif key == "NEO4J_USER":
                    neo4j_user = val
                elif key == "NEO4J_PASSWORD":
                    neo4j_password = val

print(f"Neo4j Connection Details:")
print(f"  URI:      {neo4j_uri}")
print(f"  User:     {neo4j_user}")
print(f"  Password: {'*' * len(neo4j_password)}")

# Verify the seed file exists
seed_file = "/home/pranjal_arya/Desktop/recommend/neo4j/init/seed_data.cypher"
if not os.path.exists(seed_file):
    print(f"ERROR: Seed file not found at {seed_file}")
    exit(1)

# Parse cypher statements
print("Parsing Cypher seed file...")
statements = []
current_lines = []

with open(seed_file, "r") as f:
    for line in f:
        stripped = line.strip()
        if not stripped or stripped.startswith("//"):
            continue
        current_lines.append(stripped)
        if stripped.endswith(";"):
            stmt = " ".join(current_lines).rstrip(";").strip()
            if stmt:
                statements.append(stmt)
            current_lines = []

if current_lines:
    stmt = " ".join(current_lines).rstrip(";").strip()
    if stmt:
        statements.append(stmt)

print(f"Parsed {len(statements)} statements.")

# Connect and execute
try:
    print("Connecting to Neo4j database...")
    driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
    driver.verify_connectivity()
    print("Connected successfully!")
    
    # Run constraints/indexes first if they are not in seed file
    print("Executing Cypher statements...")
    success_count = 0
    skipped_count = 0
    error_count = 0
    
    with driver.session() as session:
        # Clear existing data first
        print("Clearing existing nodes and relationships...")
        session.run("MATCH (n) DETACH DELETE n")
        
        for i, stmt in enumerate(statements, 1):
            try:
                session.run(stmt)
                success_count += 1
                if i % 100 == 0 or i == len(statements):
                    print(f"  Progress: {i}/{len(statements)} statements executed...")
            except Exception as e:
                err_str = str(e).lower()
                if any(k in err_str for k in ("already exists", "equivalent", "constraint")):
                    skipped_count += 1
                else:
                    print(f"  Error on statement {i}: {e}")
                    error_count += 1
                    
        # Verify counts
        result = session.run("MATCH (n) RETURN count(n) as count")
        nodes_count = result.single()["count"]
        
        result_rels = session.run("MATCH ()-[r]->() RETURN count(r) as count")
        rels_count = result_rels.single()["count"]
        
    print("\nIngestion Completed Summary:")
    print(f"  Total Nodes Created:         {nodes_count}")
    print(f"  Total Relationships Created: {rels_count}")
    print(f"  Successful Statements:       {success_count}")
    print(f"  Skipped (Existing) Statements: {skipped_count}")
    print(f"  Errored Statements:          {error_count}")
    
    driver.close()
    
except Exception as e:
    print(f"\nERROR: Failed to connect or execute queries: {e}")
    print("\nPlease ensure your Neo4j database is started and running.")
    print("If using Docker, run: sudo systemctl start docker && docker compose up -d")
