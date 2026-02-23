-- ==========================================
-- MAGALU AI SUITE - SCHEMA CONSOLIDADO V1.5
-- ==========================================

-- Tabela 1: Categorias (Organiza o Cérebro da IA)
create table if not exists categorias (
  id serial primary key,
  nome text unique not null,
  tom_de_voz text
);

-- Popular categorias baseadas no Guia de Contexto Brasileiro (KB Magalu):
insert into categorias (nome, tom_de_voz) values 
('Móveis', 'Lar como Refúgio; Foco em segurança no transporte e facilidade de montagem.'),
('Eletrodomésticos', 'Saúde e Economia Doméstica; Foco em eficiência energética e praticidade.'),
('Celulares e Informática', 'Ferramenta de Trabalho/Status; Descomplicar termos técnicos e focar no desempenho.'),
('Saúde e Bem-estar', 'Vida Saudável Democratizada; Foco na prática e fácil integração à rotina.'),
('Genérico', 'Otimismo prudente, didatismo amigável, padrão Lu do Magalu.')
ON CONFLICT (nome) DO NOTHING;

-- Tabela 2: Aprendizado Contínuo (Feedback Diário e Ajustes)
create table if not exists feedback_roteiros (
  id uuid default gen_random_uuid() primary key,
  criado_em timestamp with time zone default timezone('utc'::text, now()) not null,
  categoria_id int references categorias(id),
  roteiro_original_ia text not null,
  roteiro_final_humano text not null,
  avaliacao varchar(50), -- Ruim, Regular, Bom, Ótimo
  comentarios text
);

-- Tabela 3: Roteiros Ouro (O 'Few-Shot' Premium)
create table if not exists roteiros_ouro (
  id uuid default gen_random_uuid() primary key,
  criado_em timestamp with time zone default timezone('utc'::text, now()) not null,
  categoria_id int references categorias(id),
  titulo_produto text not null,
  roteiro_perfeito text not null
);

-- Tabela 4: Treinamento de Persona (A Alma da Lu)
create table if not exists treinamento_persona_lu (
  id uuid default gen_random_uuid() primary key,
  criado_em timestamp with time zone default timezone('utc'::text, now()) not null,
  pilar_persona varchar(50) not null,
  texto_gerado_ia text not null,
  texto_corrigido_humano text not null,
  lexico_sugerido text,
  erro_cometido text
);

-- Tabela 5: Treinamento de Fonética (Regras de Áudio)
create table if not exists treinamento_fonetica (
  id uuid default gen_random_uuid() primary key,
  criado_em timestamp with time zone default timezone('utc'::text, now()) not null,
  termo_errado text not null,
  termo_corrigido text not null,
  exemplo_no_roteiro text
);

-- Tabela 6: Treinamento de Estruturas (Hooks & CTAs)
create table if not exists treinamento_estruturas (
  id uuid default gen_random_uuid() primary key,
  criado_em timestamp with time zone default timezone('utc'::text, now()) not null,
  tipo_estrutura varchar(50) not null check (tipo_estrutura in ('Abertura (Gancho)', 'Fechamento (CTA)')),
  texto_ouro text not null
);

-- Tabela 7: Histórico de Roteiros Gerados (Log Automático)
create table if not exists historico_roteiros (
  id uuid default gen_random_uuid() primary key,
  criado_em timestamp with time zone default timezone('utc'::text, now()) not null,
  codigo_produto varchar(50),
  modo_trabalho varchar(100) default 'NW (NewWeb)',
  roteiro_gerado text not null,
  ficha_extraida text,
  status varchar(30) default 'gerado'
);

-- ==========================================
-- ATIVANDO ROW LEVEL SECURITY (RLS)
-- ==========================================

alter table categorias enable row level security;
alter table feedback_roteiros enable row level security;
alter table roteiros_ouro enable row level security;
alter table treinamento_persona_lu enable row level security;
alter table treinamento_fonetica enable row level security;
alter table treinamento_estruturas enable row level security;
alter table historico_roteiros enable row level security;

-- ==========================================
-- POLÍTICAS DE ACESSO (PERMISSIO TOTAL PARA AUTENTICADOS)
-- ==========================================

-- Como criamos as políticas pelo SQL Editor, garantimos que apenas quem tem a Service Key/Anon Key do app acesse.

do $$ 
begin
  -- Categorias
  if not exists (select 1 from pg_policies where policyname = 'Allow access' and tablename = 'categorias') then
    create policy "Allow access" on categorias for all using (true);
  end if;
  
  -- Feedback
  if not exists (select 1 from pg_policies where policyname = 'Allow access' and tablename = 'feedback_roteiros') then
    create policy "Allow access" on feedback_roteiros for all using (true);
  end if;

  -- Roteiros Ouro
  if not exists (select 1 from pg_policies where policyname = 'Allow access' and tablename = 'roteiros_ouro') then
    create policy "Allow access" on roteiros_ouro for all using (true);
  end if;

  -- Persona
  if not exists (select 1 from pg_policies where policyname = 'Allow access' and tablename = 'treinamento_persona_lu') then
    create policy "Allow access" on treinamento_persona_lu for all using (true);
  end if;

  -- Fonetica
  if not exists (select 1 from pg_policies where policyname = 'Allow access' and tablename = 'treinamento_fonetica') then
    create policy "Allow access" on treinamento_fonetica for all using (true);
  end if;

  -- Estruturas
  if not exists (select 1 from pg_policies where policyname = 'Allow access' and tablename = 'treinamento_estruturas') then
    create policy "Allow access" on treinamento_estruturas for all using (true);
  end if;

  -- Histórico
  if not exists (select 1 from pg_policies where policyname = 'Allow access' and tablename = 'historico_roteiros') then
    create policy "Allow access" on historico_roteiros for all using (true);
  end if;
end $$;
