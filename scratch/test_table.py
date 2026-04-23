import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
sp: Client = create_client(url, key)

try:
    res = sp.table("social_historico_roteiros").select("count", count="exact").limit(1).execute()
    print(f"Table social_historico_roteiros exists. Count: {res.count}")
except Exception as e:
    print(f"Error: {e}")
