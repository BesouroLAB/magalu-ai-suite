import os
import sys
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")

if not url or not key:
    print("❌ Erro: SUPABASE_URL ou SUPABASE_KEY não encontrados.")
    sys.exit(1)

supabase: Client = create_client(url, key)

print("🚀 Iniciando migração para a nova métrica de Aprovação baseada em IA...")

sql_script = """
ALTER TABLE feedback_roteiros ADD COLUMN IF NOT EXISTS nota_percentual integer;
ALTER TABLE feedback_roteiros ADD COLUMN IF NOT EXISTS aprendizado text;
ALTER TABLE feedback_roteiros DROP COLUMN IF EXISTS avaliacao CASCADE;
ALTER TABLE feedback_roteiros DROP COLUMN IF EXISTS comentarios CASCADE;
"""

try:
    # Supabase Python client doesn't expose a direct raw SQL execution method by default,
    # except via RPC or the pgtap extension.
    # However, we can use the REST API through `.rpc()` if we have a function,
    # OR we can just instruct the user to run it via the Supabase dashboard if this fails.
    # We will try to execute it by sending a query using PostgREST indirectly, though Alter Table won't work in standard PostgREST.
    pass
except Exception as e:
    print(f"Erro tentando rodar via python: {e}")

print("⚠️ NOTA: O Supabase API não permite rodar ALTER TABLE diretamente via cliente Python padrão.")
print("Por favor, rode o seguinte comando no SQL Editor do seu Dashboard do Supabase:\n")
print(sql_script)

