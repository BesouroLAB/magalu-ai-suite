import os
from supabase import create_client, Client
from dotenv import load_dotenv
import pandas as pd

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
        print(f"Moving {len(data)} records...")
        for item in data:
            # Remove ID to avoid conflict or if it's auto-generated
            old_id = item.pop('id', None)
            try:
                # Insert into SOCIAL
                sp.table("social_historico_roteiros").insert(item).execute()
                # Delete from NW
                sp.table("nw_historico_roteiros").delete().eq("id", old_id).execute()
                print(f"✅ Moved SKU {item['codigo_produto']}")
            except Exception as e:
                print(f"❌ Error moving {old_id}: {e}")
except Exception as e:
    print(f"Error: {e}")
