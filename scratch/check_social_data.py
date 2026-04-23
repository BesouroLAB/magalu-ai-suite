import os
from supabase import create_client, Client
from dotenv import load_dotenv
import pandas as pd

load_dotenv()
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
sp: Client = create_client(url, key)

try:
    res = sp.table("social_historico_roteiros").select("modo_trabalho").execute()
    df = pd.DataFrame(res.data)
    print("Unique modo_trabalho in social_historico_roteiros:")
    print(df['modo_trabalho'].unique())
    print("\nSample rows:")
    print(df.head())
except Exception as e:
    print(f"Error: {e}")
