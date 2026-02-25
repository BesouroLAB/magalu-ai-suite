-- ==========================================
-- DESATIVANDO RLS PARA TABELAS NW 3D
-- ==========================================
-- Execute isto no SQL Editor para garantir que as importações e o App funcionem

alter table nw3d_roteiros_ouro disable row level security;
alter table nw3d_treinamento_fonetica disable row level security;
alter table nw3d_treinamento_estruturas disable row level security;
alter table nw3d_historico_roteiros disable row level security;
alter table nw3d_treinamento_nuances disable row level security;

-- Alternativamente, se quiser manter RLS, habilite estas políticas:
create policy "Allow access" on nw3d_historico_roteiros for all using (true);
create policy "Allow access" on nw3d_roteiros_ouro for all using (true);
create policy "Allow access" on nw3d_treinamento_fonetica for all using (true);
create policy "Allow access" on nw3d_treinamento_estruturas for all using (true);
create policy "Allow access" on nw3d_treinamento_nuances for all using (true);
