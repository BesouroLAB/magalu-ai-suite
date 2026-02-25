-- ==========================================
-- DESATIVANDO RLS PARA TABELAS NW PADRÃO (STANDART)
-- ==========================================
-- Execute isto no SQL Editor se encontrar erros de permissão ou 42501 no App

alter table nw_historico_roteiros disable row level security;
alter table nw_roteiros_ouro disable row level security;
alter table nw_categorias disable row level security;
alter table nw_treinamento_fonetica disable row level security;
alter table nw_treinamento_estruturas disable row level security;
alter table nw_treinamento_nuances disable row level security;
alter table nw_treinamento_persona_lu disable row level security;

-- Caso não queira desativar o RLS mas sim abrir para todos:
-- create policy "Allow all standard" on nw_historico_roteiros for all using (true);
-- (repetir para as outras)
