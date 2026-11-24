import os
import csv
import re
from bs4 import BeautifulSoup

# Paths
base_dir = "/home/pranjal_arya/Desktop/recommend/Recommendation_System_Project"
index_path = os.path.join(base_dir, "index.html")
workcenter_path = os.path.join(base_dir, "index_workcenter.html")
child_dir = os.path.join(base_dir, "child")
output_csv = "/home/pranjal_arya/Desktop/recommend/software_knowledge_graph_data.csv"

# 1. Parse categories from index.html
print("Parsing categories from index.html...")
with open(index_path, 'r', encoding='utf-8') as f:
    index_soup = BeautifulSoup(f.read(), 'html.parser')

category_map = {}
filter_container = index_soup.find(class_="ongc-portfolio-isotope-filter")
if filter_container:
    for btn in filter_container.find_all('button'):
        data_filter = btn.get('data-filter', '')
        # extract class name e.g. ongc-portfolio-filter-tid-58
        match = re.search(r'\.(ongc-portfolio-filter-tid-\d+)', data_filter)
        if match:
            class_name = match.group(1)
            category_map[class_name] = btn.text.strip()

print(f"Mapped {len(category_map)} category IDs to category names.")

# Parse software items and their category classes from index.html
software_items = {}
grid = index_soup.find(class_="ongc-portfolio-isotope-grid")
if grid:
    for div in grid.find_all('div', class_='node-type-ongc-service-page'):
        classes = div.get('class', [])
        item_categories = []
        for cls in classes:
            if cls in category_map:
                item_categories.append(category_map[cls])
        
        link_tag = div.find('h2').find('a') if div.find('h2') else None
        if link_tag:
            href = link_tag.get('href', '').strip()
            name = link_tag.text.strip()
            
            content_div = div.find(class_='content')
            short_desc = ""
            if content_div:
                short_desc = content_div.text.strip()
                # Remove extra whitespace/newlines
                short_desc = re.sub(r'\s+', ' ', short_desc).strip()
            
            software_items[href] = {
                "name": name,
                "short_description": short_desc,
                "categories": item_categories,
                "workcenters": [],
                "child_file": href
            }

print(f"Found {len(software_items)} software items in index.html.")

# 2. Parse workcenters from index_workcenter.html
print("Parsing workcenters from index_workcenter.html...")
if os.path.exists(workcenter_path):
    with open(workcenter_path, 'r', encoding='utf-8') as f:
        wc_soup = BeautifulSoup(f.read(), 'html.parser')

    workcenter_map = {}
    wc_filter_container = wc_soup.find(class_="ongc-portfolio-isotope-filter")
    if wc_filter_container:
        for btn in wc_filter_container.find_all('button'):
            data_filter = btn.get('data-filter', '')
            match = re.search(r'\.(ongc-portfolio-filter-tid-\d+)', data_filter)
            if match:
                class_name = match.group(1)
                workcenter_map[class_name] = btn.text.strip()

    print(f"Mapped {len(workcenter_map)} workcenter IDs to workcenter names.")

    wc_grid = wc_soup.find(class_="ongc-portfolio-isotope-grid")
    if wc_grid:
        for div in wc_grid.find_all('div', class_='node-type-ongc-service-page'):
            classes = div.get('class', [])
            item_workcenters = []
            for cls in classes:
                if cls in workcenter_map:
                    item_workcenters.append(workcenter_map[cls])
            
            link_tag = div.find('h2').find('a') if div.find('h2') else None
            if link_tag:
                href = link_tag.get('href', '').strip()
                if href in software_items:
                    software_items[href]["workcenters"] = item_workcenters
                else:
                    name = link_tag.text.strip()
                    content_div = div.find(class_='content')
                    short_desc = re.sub(r'\s+', ' ', content_div.text.strip()) if content_div else ""
                    software_items[href] = {
                        "name": name,
                        "short_description": short_desc,
                        "categories": [],
                        "workcenters": item_workcenters,
                        "child_file": href
                    }
else:
    print(f"Warning: {workcenter_path} not found.")

# 3. Parse child files
print("Parsing child pages...")
for href, item in software_items.items():
    child_path = os.path.join(base_dir, href)
    if not os.path.exists(child_path):
        print(f"Warning: child file {child_path} does not exist.")
        item["detailed_description"] = ""
        item["technologies"] = ""
        item["developer_group"] = ""
        item["developer_names"] = ""
        item["developer_mails"] = ""
        item["developer_phones"] = ""
        item["download_links"] = ""
        continue
    
    with open(child_path, 'r', encoding='utf-8') as f:
        child_soup = BeautifulSoup(f.read(), 'html.parser')
    
    # Title / Name
    title_tag = child_soup.find('h1', class_='title')
    title = title_tag.text.strip() if title_tag else item["name"]
    # Update title in case it differs slightly
    item["name"] = title
    
    # Detailed description
    detailed_desc = ""
    article = child_soup.find('article')
    if article:
        content_div = article.find(class_='content')
        if content_div:
            detailed_desc = content_div.text.strip()
        else:
            detailed_desc = article.text.strip()
    
    # Clean up whitespace
    detailed_desc = re.sub(r'\s+', ' ', detailed_desc).strip()
    
    # Summary Table: Technology used and Contact details
    tech_used = []
    dev_group = ""
    dev_names = []
    dev_mails = []
    dev_phones = []
    
    table = child_soup.find('table')
    if table:
        cells = table.find_all('td')
        for cell in cells:
            cell_text = cell.text.lower()
            if "technology used" in cell_text:
                lis = cell.find_all('li')
                if lis:
                    tech_used = [li.text.strip() for li in lis]
                else:
                    lines = [l.strip() for l in cell.text.split('\n') if l.strip()]
                    if len(lines) > 1:
                        tech_used = lines[1:]
            elif "get in contact" in cell_text or "contact" in cell_text:
                lis = cell.find_all('li')
                for li in lis:
                    text = li.text.strip()
                    if re.match(r'^(developer\s+group|group)\s*:', text, re.IGNORECASE):
                        dev_group = re.sub(r'^(developer\s+group|group)\s*:', '', text, flags=re.IGNORECASE).strip()
                    elif re.match(r'^(developer\s+name|developer\s+names|developer|name|names)\s*:', text, re.IGNORECASE):
                        names_str = re.sub(r'^(developer\s+name|developer\s+names|developer|name|names)\s*:', '', text, flags=re.IGNORECASE).strip()
                        dev_names = [n.strip() for n in re.split(r'[,;]', names_str) if n.strip()]
                    elif re.match(r'^(mail|email|emails)\s*:', text, re.IGNORECASE):
                        mails_str = re.sub(r'^(mail|email|emails)\s*:', '', text, flags=re.IGNORECASE).strip()
                        dev_mails = [m.strip() for m in re.split(r'[,;/\s]', mails_str) if m.strip()]
                    elif re.match(r'^(phone|phones|contact)\s*:', text, re.IGNORECASE):
                        phones_str = re.sub(r'^(phone|phones|contact)\s*:', '', text, flags=re.IGNORECASE).strip()
                        dev_phones = [p.strip() for p in re.split(r'[,;]', phones_str) if p.strip()]
    
    # Download / Other Links
    links = []
    for a in child_soup.find_all('a'):
        link_href = a.get('href', '')
        link_text = a.text.strip()
        # Filter out navigation links
        if link_href and not link_href.startswith('#') and 'index.html' not in link_href and 'default.aspx' not in link_href and link_href != '../index.html':
            links.append(f"{link_text} ({link_href})")
            
    item["detailed_description"] = detailed_desc
    item["technologies"] = ", ".join(tech_used)
    item["developer_group"] = dev_group
    item["developer_names"] = ", ".join(dev_names)
    item["developer_mails"] = ", ".join(dev_mails)
    item["developer_phones"] = ", ".join(dev_phones)
    item["download_links"] = "; ".join(links)

# Write to CSV
print(f"Writing to CSV: {output_csv}")
fields = [
    "Software Name", "Short Description", "Detailed Description", 
    "Categories", "Workcenters", "Technologies", 
    "Developer Group", "Developer Names", "Developer Mails", "Developer Phones", 
    "Links", "Child File"
]

with open(output_csv, 'w', newline='', encoding='utf-8') as f:
    writer = csv.writer(f)
    writer.writerow(fields)
    for href, item in sorted(software_items.items(), key=lambda x: x[1]['name']):
        writer.writerow([
            item["name"],
            item["short_description"],
            item["detailed_description"],
            ", ".join(item["categories"]),
            ", ".join(item["workcenters"]),
            item["technologies"],
            item["developer_group"],
            item["developer_names"],
            item["developer_mails"],
            item["developer_phones"],
            item["download_links"],
            item["child_file"]
        ])

print("CSV conversion completed successfully!")
