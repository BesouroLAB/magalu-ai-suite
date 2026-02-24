-- ==========================================
-- MAGALU AI SUITE - SCHEMA CONSOLIDADO V2.0
-- ==========================================
-- Changelog V2.0:
--   + Adicionado codigo_produto em roteiros_ouro (SKU p/ JSON-LD)
--   + Migration script ao final do arquivo

-- Tabela 1: Categorias (Organiza o Cérebro da IA)
create table if not exists nw_categorias (
  id serial primary key,
  nome text unique not null,
  tom_de_voz text
);

-- Popular categorias baseadas no Guia de Contexto Brasileiro (KB Magalu):
insert into nw_categorias (nome, tom_de_voz) values 
('Móveis', 'Lar como Refúgio; Foco em segurança no transporte e facilidade de montagem.'),
('Eletrodomésticos', 'Saúde e Economia Doméstica; Foco em eficiência energética e praticidade.'),
('Eletroportáteis', 'Praticidade e Estilo de Vida; Foco na facilidade de uso, design funcional e como o produto melhora o dia a dia.'),
('Celulares e Informática', 'Ferramenta de Trabalho/Status; Descomplicar termos técnicos e focar no desempenho.'),
('Saúde e Bem-estar', 'Vida Saudável Democratizada; Foco na prática e fácil integração à rotina.'),
('Beleza e Perfumaria', 'Autocuidado e Autoestima; Foco nos resultados, sensações e bem-estar. Linguagem sofisticada e acolhedora.'),
('Brinquedos', 'Mundo da Imaginação; Foco na segurança, desenvolvimento pedagógico e diversão em família. Linguagem lúdica.'),
('TV e Vídeo', 'Cinema em Casa; Foco em imersão sonora e visual, tecnologias de tela e entretenimento familiar.'),
('Esporte e Lazer', 'Vida em Movimento; Foco na performance, durabilidade e incentivo à prática de exercícios.'),
('Automotivo', 'Segurança e Praticidade; Foco na confiança, manutenção e utilidade técnica acessível.'),
('Genérico', 'Otimismo prudente, didatismo amigável, padrão Lu do Magalu.')
ON CONFLICT (nome) DO NOTHING;

-- Tabela 2: Roteiros Ouro (O 'Few-Shot' Premium + JSON-LD Ready + Memória de Calibração)
create table if not exists nw_roteiros_ouro (
  id uuid default gen_random_uuid() primary key,
  criado_em timestamp with time zone default timezone('utc'::text, now()) not null,
  categoria_id int references nw_categorias(id),
  codigo_produto varchar(50),  -- SKU Magalu (ex: 240304700) para JSON-LD
  titulo_produto text not null,
  roteiro_original_ia text, -- Qual era a versão da IA antes da edição
  roteiro_perfeito text not null,
  nota_percentual integer, -- % de similaridade aprovada (0 a 100)
  aprendizado text -- Lição extraída pela IA (o que o humano mudou e por que)
);

-- Tabela 4: Treinamento de Persona (A Alma da Lu)
create table if not exists nw_treinamento_persona_lu (
  id uuid default gen_random_uuid() primary key,
  criado_em timestamp with time zone default timezone('utc'::text, now()) not null,
  pilar_persona varchar(50) not null,
  texto_gerado_ia text not null,
  texto_corrigido_humano text not null,
  lexico_sugerido text,
  erro_cometido text
);

-- Tabela 5: Treinamento de Fonética (Regras de Áudio)
create table if not exists nw_treinamento_fonetica (
  id uuid default gen_random_uuid() primary key,
  criado_em timestamp with time zone default timezone('utc'::text, now()) not null,
  termo_errado text not null,
  termo_corrigido text not null,
  exemplo_no_roteiro text
);

-- Tabela 6: Treinamento de Estruturas (Hooks & CTAs)
create table if not exists nw_treinamento_estruturas (
  id uuid default gen_random_uuid() primary key,
  criado_em timestamp with time zone default timezone('utc'::text, now()) not null,
  tipo_estrutura varchar(50) not null check (tipo_estrutura in ('Abertura (Gancho)', 'Fechamento (CTA)')),
  texto_ouro text not null
);

-- Tabela 7: Histórico de Roteiros Gerados (Log Automático)
create table if not exists nw_historico_roteiros (
  id uuid default gen_random_uuid() primary key,
  criado_em timestamp with time zone default timezone('utc'::text, now()) not null,
  codigo_produto varchar(50),
  modo_trabalho varchar(100) default 'NW (NewWeb)',
  roteiro_gerado text not null,
  ficha_extraida text,
  status varchar(30) default 'gerado',
  modelo_llm varchar(50) default 'gemini-2.5-flash',
  tokens_entrada int,
  tokens_saida int,
  custo_estimado_brl numeric(10,6)
);

-- Tabela 8: Treinamento de Nuances e Construção (Linguagem Viva)
create table if not exists nw_treinamento_nuances (
  id uuid default gen_random_uuid() primary key,
  criado_em timestamp with time zone default timezone('utc'::text, now()) not null,
  frase_ia text not null,
  analise_critica text not null,
  exemplo_ouro text
);


-- ==========================================
-- ATIVANDO ROW LEVEL SECURITY (RLS)
-- ==========================================

alter table nw_categorias enable row level security;
alter table feedback_roteiros enable row level security;
alter table nw_roteiros_ouro enable row level security;
alter table nw_treinamento_persona_lu enable row level security;
alter table nw_treinamento_fonetica enable row level security;
alter table nw_treinamento_estruturas enable row level security;
alter table nw_historico_roteiros enable row level security;
alter table nw_treinamento_nuances enable row level security;


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

  -- Nuances
  if not exists (select 1 from pg_policies where policyname = 'Allow access' and tablename = 'treinamento_nuances') then
    create policy "Allow access" on treinamento_nuances for all using (true);
  end if;

end $$;

-- ==========================================
-- MIGRATION V1.5 -> V2.0
-- ==========================================
-- Execute este bloco no SQL Editor do Supabase para atualizar schemas existentes.
-- É seguro rodar múltiplas vezes (idempotente).

DO $$
BEGIN
  -- Adiciona codigo_produto em nw_roteiros_ouro se não existir
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns 
    WHERE table_name = 'nw_roteiros_ouro' AND column_name = 'codigo_produto'
  ) THEN
    ALTER TABLE nw_roteiros_ouro ADD COLUMN codigo_produto varchar(50);
    RAISE NOTICE 'Coluna codigo_produto adicionada em nw_roteiros_ouro.';
  END IF;
END $$;

-- ==========================================
-- MIGRATION V2.0 -> V2.5 (LLM Tracking)
-- ==========================================
-- Adiciona colunas de rastreamento de modelo e custo ao histórico.
-- É seguro rodar múltiplas vezes (idempotente).

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns 
    WHERE table_name = 'nw_historico_roteiros' AND column_name = 'modelo_llm'
  ) THEN
    ALTER TABLE nw_historico_roteiros ADD COLUMN modelo_llm varchar(50) DEFAULT 'gemini-2.5-flash';
    ALTER TABLE nw_historico_roteiros ADD COLUMN tokens_entrada int;
    ALTER TABLE nw_historico_roteiros ADD COLUMN tokens_saida int;
    ALTER TABLE nw_historico_roteiros ADD COLUMN custo_estimado_brl numeric(10,6);
    RAISE NOTICE 'Colunas de tracking LLM adicionadas em nw_historico_roteiros.';
  END IF;
END $$;

-- ==========================================
-- MIGRATION V2.5 -> V3.0 (Calibragem Inteligente)
-- ==========================================
-- Adiciona coluna modelo_calibragem em roteiros_ouro.
-- Relaxa CHECK de tipo_estrutura para aceitar valores simplificados.
-- É seguro rodar múltiplas vezes (idempotente).

DO $$
BEGIN
  -- 1. modelo_calibragem em roteiros_ouro
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns 
    WHERE table_name = 'nw_roteiros_ouro' AND column_name = 'modelo_calibragem'
  ) THEN
    ALTER TABLE nw_roteiros_ouro ADD COLUMN modelo_calibragem text DEFAULT 'N/A';
    RAISE NOTICE 'Coluna modelo_calibragem adicionada em nw_roteiros_ouro.';
  END IF;

  -- 2. Relaxa CHECK em tipo_estrutura para aceitar 'Abertura' e 'Fechamento' também
  IF EXISTS (
    SELECT 1 FROM information_schema.check_constraints 
    WHERE constraint_name LIKE '%tipo_estrutura%'
  ) THEN
    ALTER TABLE nw_treinamento_estruturas DROP CONSTRAINT IF EXISTS nw_treinamento_estruturas_tipo_estrutura_check;
    ALTER TABLE nw_treinamento_estruturas ADD CONSTRAINT nw_treinamento_estruturas_tipo_estrutura_check 
      CHECK (tipo_estrutura IN ('Abertura', 'Fechamento', 'Abertura (Gancho)', 'Fechamento (CTA)'));
    RAISE NOTICE 'CHECK de tipo_estrutura atualizado para aceitar valores simplificados.';
  END IF;
END $$;
