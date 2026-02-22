import csv
import os
import re

# Paths
CLUSTERS_CSV = r'c:\Users\Tiago\Desktop\PROJETOS\guia-de-geladeira\pesquisas\geladeira-para-caminhão_clusters_2026-01-19.csv'
CONTENT_DIR = r'c:\Users\Tiago\Desktop\PROJETOS\guia-de-geladeira\content\reviews'

# 1. Get existing content topics (normalized)
existing_topics = set()
try:
    for filename in os.listdir(CONTENT_DIR):
        if filename.endswith('.mdx'):
            # Extract topic from filename (e.g., '101-melhores-geladeiras' -> 'melhores geladeiras')
            clean_name = re.sub(r'^\d+-', '', filename)
            clean_name = clean_name.replace('.mdx', '').replace('-', ' ')
            existing_topics.add(clean_name)
    # Add manual topics known to be covered
    existing_topics.update(['solar', 'painel solar', 'bateria', 'consumo', 'instalar', 'instalação', 'defeito', 'conserto', 'resfriar', 'elber', 'maxiclima'])
except FileNotFoundError:
    print(f"Directory not found: {CONTENT_DIR}")

# 2. Process CSV
opportunities = []

try:
    with open(CLUSTERS_CSV, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            keyword = row.get('Keyword', '').lower().strip()
            volume = int(row.get('Volume', 0))
            difficulty = int(row.get('Keyword Difficulty', 100))
            intent = row.get('Intent', '')
            
            # Filters:
            # 1. Volume > 50 (ignoring tiny long tails for top 100)
            # 2. Difficulty < 60 (realistic targets)
            if volume >= 50 and difficulty < 60:
                is_covered = False
                for topic in existing_topics:
                    if topic in keyword: # Simple match
                        is_covered = True
                        break
                
                # Check for "geladeira para caminhão" generic terms which we already rank for or cover in home
                if keyword in ['geladeira para caminhão', 'geladeira de caminhão']:
                    is_covered = True

                if not is_covered:
                    opportunities.append({
                        'keyword': keyword,
                        'volume': volume,
                        'difficulty': difficulty,
                        'intent': intent
                    })

    # Sort by Volume (descending) then Difficulty (ascending)
    opportunities.sort(key=lambda x: (-x['volume'], x['difficulty']))

    # Print top 100
    print(f"Found {len(opportunities)} potential keywords. Showing top 100:")
    print("Keyword | Volume | KD | Intent")
    print("-" * 50)
    for opp in opportunities[:100]:
        print(f"{opp['keyword']} | {opp['volume']} | {opp['difficulty']} | {opp['intent']}")

except FileNotFoundError:
    print(f"CSV not found: {CLUSTERS_CSV}")
except Exception as e:
    print(f"Error: {e}")
