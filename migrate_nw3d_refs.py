import os
import sys
import re
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client, Client

# Load environment variables
load_dotenv()
url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")

if not url or not key:
    print("Error: SUPABASE_URL or SUPABASE_KEY not found in .env")
    sys.exit(1)

supabase: Client = create_client(url, key)
KB_DIR = "kb/nw-3d"

def parse_filename(filename):
    """
    Extracts SKU and title from filenames like:
    'NW 3D FEV  234470600 234470700 235718000 Armário de Cozinha Compacta Demóbile Select com Balcão Nicho para Micro-ondas.md'
    or 'NW 3D JAN 240441500 Geladeira_Refrigerador Electrolux Frost Free Inverse Inox Look 400L Efficient IB6S  (1).md'
    """
    basename = os.path.splitext(filename)[0]
    
    # Extract month
    mes = "FEV"
    if "JAN" in basename: mes = "JAN"
    elif "MAR" in basename: mes = "MAR"
    elif "FEV" in basename: mes = "FEV"
    
    # Extract all 9-digit numbers (SKUs)
    skus = re.findall(r'\b\d{9}\b', basename)
    primary_sku = skus[0] if skus else "000000000"
    
    # Find where the text starts after the numbers
    match = re.search(r'\b\d{9}\b\s+(.*)', basename)
    if match:
        title = match.group(1).replace(" (1)", "").replace("_", " ").strip()
    else:
        title = basename
        
    return primary_sku, title, mes

def migrate():
    if not os.path.exists(KB_DIR):
        print(f"Directory {KB_DIR} not found.")
        return

    files = [f for f in os.listdir(KB_DIR) if f.endswith('.md')]
    print(f"Found {len(files)} markdown files in {KB_DIR}.")
    
    success_count = 0
    for filename in files:
        filepath = os.path.join(KB_DIR, filename)
        
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            
        sku, title, mes = parse_filename(filename)
        
        # Prepare the record
        record = {
            "codigo_produto": sku,
            "modo_trabalho": "NW 3D",
            "roteiro_gerado": content,
            "ficha_extraida": f"MIGRATED_FROM_KB: {title}",
            "status": "gerado",
            "modelo_llm": "kb-import",
            "tokens_entrada": 0,
            "tokens_saida": len(content.split()),
            "custo_estimado_brl": 0.0
        }
        
        try:
            supabase.table("nw3d_historico_roteiros").insert(record).execute()
            print(f"[OK] Imported: {sku} - {title[:30]}...")
            success_count += 1
        except Exception as e:
            print(f"[ERROR] Failed to import {filename}: {e}")
            
    print(f"\nMigration complete. Inserted {success_count} out of {len(files)} records.")

if __name__ == "__main__":
    migrate()
