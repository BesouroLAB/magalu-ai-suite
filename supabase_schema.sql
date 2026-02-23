-- Tabela 0: Roteiros Aprovados (Original)
create table if not exists roteiros_aprovados (
  id uuid default gen_random_uuid() primary key,
  criado_em timestamp with time zone default timezone('utc'::text, now()) not null,
  ficha_tecnica text not null,
  roteiro_original_ia text not null,
  roteiro_editado_humano text not null
);

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
  ficha_tecnica text not null,
  roteiro_original_ia text not null,
  roteiro_final_humano text not null,
  avaliacao int, -- 1 para Bom (👍), -1 para Ruim (👎)
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

-- Tabela 6: Treinamento de Estruturas (Aberturas e Fechamentos/CTAs)
create table if not exists treinamento_estruturas (
  id uuid default gen_random_uuid() primary key,
  criado_em timestamp with time zone default timezone('utc'::text, now()) not null,
  tipo_estrutura varchar(50) not null check (tipo_estrutura in ('Abertura (Gancho)', 'Fechamento (CTA)')),
  texto_ouro text not null
);

-- Tabela 7: Histórico de Roteiros Gerados
create table if not exists historico_roteiros (
  id uuid default gen_random_uuid() primary key,
  criado_em timestamp with time zone default timezone('utc'::text, now()) not null,
  codigo_produto varchar(50),
  modo_trabalho varchar(100) default 'NW (NewWeb)',
  roteiro_gerado text not null,
  ficha_extraida text,
  status varchar(30) default 'gerado'
);
-- Ativando RLS para proteção base em todas as tabelas
alter table roteiros_aprovados enable row level security;
alter table categorias enable row level security;
alter table feedback_roteiros enable row level security;
alter table roteiros_ouro enable row level security;
alter table treinamento_persona_lu enable row level security;
alter table treinamento_fonetica enable row level security;
alter table treinamento_estruturas enable row level security;
alter table historico_roteiros enable row level security;

-- Política simples: Permite acesso total apenas para chaves autenticadas (authenticated context) ou service_role.
-- Como você está alimentando o app Python com as keys direto no .env, isso já barra "visitantes anônimos da internet"
-- caso usem uma chamada de navegador não assinada. 
create policy "Allow full access for authenticated requests"
on roteiros_aprovados for all using (true);

create policy "Allow full access for authenticated requests"
on categorias for all using (true);

create policy "Allow full access for authenticated requests"
on feedback_roteiros for all using (true);

create policy "Allow full access for authenticated requests"
on roteiros_ouro for all using (true);

create policy "Allow full access for authenticated requests"
on treinamento_persona_lu for all using (true);

create policy "Allow full access for authenticated requests"
on treinamento_fonetica for all using (true);

create policy "Allow full access for authenticated requests"
on treinamento_estruturas for all using (true);

create policy "Allow full access for authenticated requests"
on historico_roteiros for all using (true);
