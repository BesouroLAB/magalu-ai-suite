import os
from supabase import create_client, Client
from dotenv import load_dotenv
import pandas as pd

load_dotenv()
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
sp: Client = create_client(url, key)

try:
    res = sp.table("nw_historico_roteiros").select("modo_trabalho").eq("modo_trabalho", "SOCIAL").execute()
    df = pd.DataFrame(res.data)
    print(f"Count of 'SOCIAL' in nw_historico_roteiros: {len(df)}")
except Exception as e:
    print(f"Error: {e}")
