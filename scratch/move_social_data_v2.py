import os
from supabase import create_client, Client
from dotenv import load_dotenv
import sys

# Forçar UTF-8 para evitar erros de encoding no Windows
if sys.stdout.encoding != 'utf-8':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

load_dotenv()
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
sp: Client = create_client(url, key)

try:
    # 1. Fetch from NW
    res = sp.table("nw_historico_roteiros").select("*").eq("modo_trabalho", "SOCIAL").execute()
    data = res.data
    if not data:
        print("No SOCIAL records found in nw_historico_roteiros.")
    else:
        print(f"Found {len(data)} SOCIAL records in nw_historico_roteiros. Moving...")
        for item in data:
            old_id = item.pop('id', None)
            try:
                # Insert into SOCIAL
                sp.table("social_historico_roteiros").insert(item).execute()
                # Delete from NW
                sp.table("nw_historico_roteiros").delete().eq("id", old_id).execute()
                print(f"OK: Moved SKU {item['codigo_produto']}")
            except Exception as e:
                print(f"FAIL: Error moving {old_id}: {e}")
except Exception as e:
    print(f"Global Error: {e}")
