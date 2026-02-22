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
