import os
from dotenv import load_dotenv
from supabase import create_client, Client

# Carrega as variáveis de ambiente (SUPABASE_URL e SUPABASE_KEY)
load_dotenv()

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")

if not url or not key:
    print("❌ ERRO: SUPABASE_URL ou SUPABASE_KEY não encontradas no arquivo .env!")
    exit(1)

supabase: Client = create_client(url, key)

# Lê o arquivo SQL puro
sql_file_path = "supabase_schema.sql"

try:
    with open(sql_file_path, "r", encoding="utf-8") as file:
        sql_script = file.read()

    print("⏳ Tentando criar as tabelas, isso pode não ser suportado diretamente via API REST Python dependendo das permissões do Postgres.")
    print("💡 A FORMA MAIS FÁCIL É: Copie o conteúdo do arquivo 'supabase_schema.sql' e cole no painel online do Supabase (Aba 'SQL Editor' -> 'New query' -> Colar -> 'Run')")

    # Supabase Client Python não tem um método genérico "execute raw SQL" muito robusto para DDL
    print("\nAbra o arquivo supabase_schema.sql gerado na pasta raiz e cole o conteúdo no Supabase!")

except FileNotFoundError:
    print(f"❌ Arquivo {sql_file_path} não encontrado.")
except Exception as e:
    print(f"❌ Ocorreu um erro: {e}")
