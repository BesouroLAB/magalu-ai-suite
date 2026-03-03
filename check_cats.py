import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
sp: Client = create_client(url, key)

res = sp.table("nw_categorias").select("*").execute()
for c in res.data:
    print(f"{c['id']}: {c['nome']}")
