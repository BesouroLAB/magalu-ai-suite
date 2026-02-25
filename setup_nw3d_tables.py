import os
import sys
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

# SQL statements to create nw3d specific tables
# Note: Roteiros Ouro now points to the original nw_categorias to avoid duplicating the entire category list
# Persona is also shared because "Lu" is the same persona across both formats.

create_tables_sql = """
-- Tabela 2 (3D): Roteiros Ouro
create table if not exists nw3d_roteiros_ouro (
  id uuid default gen_random_uuid() primary key,
  criado_em timestamp with time zone default timezone('utc'::text, now()) not null,
  categoria_id int references nw_categorias(id),
  codigo_produto varchar(50),
  titulo_produto text not null,
  roteiro_original_ia text,
  roteiro_perfeito text not null,
  nota_percentual integer,
  aprendizado text
);

-- Tabela 5 (3D): Treinamento de Fonética
create table if not exists nw3d_treinamento_fonetica (
  id uuid default gen_random_uuid() primary key,
  criado_em timestamp with time zone default timezone('utc'::text, now()) not null,
  termo_errado text not null,
  termo_corrigido text not null,
  exemplo_no_roteiro text
);

-- Tabela 6 (3D): Treinamento de Estruturas
create table if not exists nw3d_treinamento_estruturas (
  id uuid default gen_random_uuid() primary key,
  criado_em timestamp with time zone default timezone('utc'::text, now()) not null,
  tipo_estrutura varchar(50) not null check (tipo_estrutura in ('Abertura (Gancho)', 'Fechamento (CTA)')),
  texto_ouro text not null
);

-- Tabela 7 (3D): Histórico
create table if not exists nw3d_historico_roteiros (
  id uuid default gen_random_uuid() primary key,
  criado_em timestamp with time zone default timezone('utc'::text, now()) not null,
  codigo_produto varchar(50),
  modo_trabalho varchar(100) default 'NW 3D',
  roteiro_gerado text not null,
  ficha_extraida text,
  status varchar(30) default 'gerado',
  modelo_llm varchar(50) default 'gemini-2.5-flash',
  tokens_entrada int,
  tokens_saida int,
  custo_estimado_brl numeric(10,6)
);

-- Tabela 8 (3D): Treinamento de Nuances
create table if not exists nw3d_treinamento_nuances (
  id uuid default gen_random_uuid() primary key,
  criado_em timestamp with time zone default timezone('utc'::text, now()) not null,
  frase_ia text not null,
  analise_critica text not null,
  exemplo_ouro text
);
"""

# Execute SQL via Postgres REST RPC if available, or print for direct execution
print("Since Supabase python client doesn't support raw DDL easily, we'll try to run via RPC or output the SQL.")
print("Run the following SQL in your Supabase SQL Editor:\n")
print(create_tables_sql)

# Try fetching via a simple ping to ensure connection works
try:
    res = supabase.table("nw_categorias").select("id").limit(1).execute()
    print("Connection tested successfully.")
except Exception as e:
    print(f"Error connecting to Supabase: {e}")
