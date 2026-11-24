import os
import csv
import re
import shutil

csv_path = "/home/pranjal_arya/Desktop/recommend/software_knowledge_graph_data.csv"
cypher_path = "/home/pranjal_arya/Desktop/recommend/neo4j/init/seed_data.cypher"
backup_path = "/home/pranjal_arya/Desktop/recommend/neo4j/init/seed_data_backup.cypher"

print("Starting Cypher seed generation...")

# Backup original seed file if backup doesn't exist
if os.path.exists(cypher_path) and not os.path.exists(backup_path):
    shutil.copy(cypher_path, backup_path)
    print(f"Backed up original seed file to {backup_path}")

# Load CSV data
rows = []
if not os.path.exists(csv_path):
    print(f"Error: CSV file not found at {csv_path}")
    exit(1)

with open(csv_path, 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        rows.append(row)

# Collect unique technologies, domains, locations, and developers
technologies = set()
domains = set()
locations = set()
developers = {} # name -> { 'group': group, 'projects_count': 0 }

for row in rows:
    # Categories -> Domain
    if row["Categories"]:
        for d in row["Categories"].split(","):
            domains.add(d.strip())
            
    # Workcenters -> Location
    if row["Workcenters"]:
        for l in row["Workcenters"].split(","):
            locations.add(l.strip())
            
    # Technologies -> Technology
    if row["Technologies"]:
        for t in row["Technologies"].split(","):
            technologies.add(t.strip())
            
    # Developer Names -> Developer
    if row["Developer Names"]:
        dev_names = [d.strip() for d in row["Developer Names"].split(",") if d.strip()]
        dev_mails = [m.strip() for m in row.get("Developer Mails", "").split(",") if m.strip()]
        dev_phones = [p.strip() for p in row.get("Developer Phones", "").split(",") if p.strip()]
        for i, dev_name in enumerate(dev_names):
            email = dev_mails[i] if i < len(dev_mails) else ""
            phone = dev_phones[i] if i < len(dev_phones) else ""
            if dev_name not in developers:
                developers[dev_name] = {
                    "group": row["Developer Group"],
                    "projects_count": 0,
                    "email": email,
                    "phone": phone
                }
            else:
                if not developers[dev_name]["email"] and email:
                    developers[dev_name]["email"] = email
                if not developers[dev_name]["phone"] and phone:
                    developers[dev_name]["phone"] = phone
            developers[dev_name]["projects_count"] += 1

# Start writing Cypher queries
cypher_lines = []
cypher_lines.append("// ============================================")
cypher_lines.append("// Knowledge Graph Seed Data (Real Extracted Data)")
cypher_lines.append("// ============================================\n")

cypher_lines.append("// --- Create Constraints ---")
cypher_lines.append("CREATE CONSTRAINT developer_name IF NOT EXISTS FOR (d:Developer) REQUIRE d.name IS UNIQUE;")
cypher_lines.append("CREATE CONSTRAINT project_name IF NOT EXISTS FOR (p:Project) REQUIRE p.name IS UNIQUE;")
cypher_lines.append("CREATE CONSTRAINT technology_name IF NOT EXISTS FOR (t:Technology) REQUIRE t.name IS UNIQUE;")
cypher_lines.append("CREATE CONSTRAINT domain_name IF NOT EXISTS FOR (d:Domain) REQUIRE d.name IS UNIQUE;")
cypher_lines.append("CREATE CONSTRAINT location_name IF NOT EXISTS FOR (l:Location) REQUIRE l.name IS UNIQUE;\n")

cypher_lines.append("// --- Create Indexes ---")
cypher_lines.append("CREATE INDEX developer_project_count IF NOT EXISTS FOR (d:Developer) ON (d.project_count);")
cypher_lines.append("CREATE FULLTEXT INDEX project_search IF NOT EXISTS FOR (p:Project) ON EACH [p.name, p.description, p.tagline];")
cypher_lines.append("CREATE FULLTEXT INDEX developer_search IF NOT EXISTS FOR (d:Developer) ON EACH [d.name];\n")

# Helper to escape strings for Cypher
def escape(s):
    if not s:
        return ""
    # Escape backslashes first, then single quotes
    return s.replace('\\', '\\\\').replace("'", "\\'")

# Create Technology Nodes
cypher_lines.append("// --- Technology Nodes ---")
for idx, tech in enumerate(sorted(technologies), 1):
    cypher_lines.append(f"MERGE (t{idx}:Technology {{name: '{escape(tech)}'}});")
cypher_lines.append("")

# Create Domain Nodes
cypher_lines.append("// --- Domain Nodes ---")
for idx, dom in enumerate(sorted(domains), 1):
    cypher_lines.append(f"MERGE (d{idx}:Domain {{name: '{escape(dom)}'}});")
cypher_lines.append("")

# Create Location Nodes
cypher_lines.append("// --- Location Nodes ---")
for idx, loc in enumerate(sorted(locations), 1):
    cypher_lines.append(f"MERGE (l{idx}:Location {{name: '{escape(loc)}'}});")
cypher_lines.append("")

# Create Developer Nodes
cypher_lines.append("// --- Developer Nodes ---")
for idx, (dev_name, dev_info) in enumerate(sorted(developers.items()), 1):
    bio = f"Developer at {dev_info['group']}" if dev_info['group'] else "Developer"
    email_prop = f", email: '{escape(dev_info['email'])}'" if dev_info.get('email') else ""
    phone_prop = f", phone: '{escape(dev_info['phone'])}'" if dev_info.get('phone') else ""
    cypher_lines.append(f"MERGE (dev{idx}:Developer {{name: '{escape(dev_name)}', project_count: {dev_info['projects_count']}, bio: '{escape(bio)}'{email_prop}{phone_prop}}});")
cypher_lines.append("")

# Create Project Nodes and Relationships
cypher_lines.append("// --- Project Nodes and Relationships ---")
for idx, row in enumerate(rows, 1):
    p_name = row["Software Name"]
    p_desc = row["Detailed Description"] or row["Short Description"]
    p_tagline = row["Short Description"]
    
    # Try to extract year from text, default to 2024
    developed_on = "2024"
    year_match = re.search(r'\b(20\d{2})\b', p_desc)
    if year_match:
        developed_on = year_match.group(1)
        
    cypher_lines.append(f"MERGE (p{idx}:Project {{name: '{escape(p_name)}', description: '{escape(p_desc)}', tagline: '{escape(p_tagline)}', developed_on: '{escape(developed_on)}'}});")
    
    # Relationships: Project -> Domain
    if row["Categories"]:
        for dom in row["Categories"].split(","):
            cypher_lines.append(f"MATCH (p:Project {{name: '{escape(p_name)}'}}), (d:Domain {{name: '{escape(dom.strip())}'}}) MERGE (p)-[:BELONGS_TO]->(d);")
            
    # Relationships: Project -> Location
    if row["Workcenters"]:
        for loc in row["Workcenters"].split(","):
            cypher_lines.append(f"MATCH (p:Project {{name: '{escape(p_name)}'}}), (l:Location {{name: '{escape(loc.strip())}'}}) MERGE (p)-[:LOCATED_IN]->(l);")
            
    # Relationships: Project -> Technology
    if row["Technologies"]:
        for tech in row["Technologies"].split(","):
            cypher_lines.append(f"MATCH (p:Project {{name: '{escape(p_name)}'}}), (t:Technology {{name: '{escape(tech.strip())}'}}) MERGE (p)-[:USES_TECH]->(t);")
            
    # Relationships: Developer -> Project
    if row["Developer Names"]:
        for dev in row["Developer Names"].split(","):
            dev_name = dev.strip()
            if dev_name:
                cypher_lines.append(f"MATCH (dev:Developer {{name: '{escape(dev_name)}'}}), (p:Project {{name: '{escape(p_name)}'}}) MERGE (dev)-[:DEVELOPED]->(p);")
    cypher_lines.append("")

# Write to file
with open(cypher_path, 'w', encoding='utf-8') as f:
    f.write("\n".join(cypher_lines))

print(f"Successfully generated Cypher seed file with real data: {cypher_path}")
