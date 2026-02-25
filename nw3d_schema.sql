-- ==========================================
-- NEW SCHEMA: NW 3D FORMAT
-- ==========================================
-- Execute this block in your Supabase SQL Editor

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
  aprendizado text,
  modelo_calibragem text default 'N/A'
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
  tipo_estrutura varchar(50) not null check (tipo_estrutura IN ('Abertura', 'Fechamento', 'Abertura (Gancho)', 'Fechamento (CTA)')),
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
