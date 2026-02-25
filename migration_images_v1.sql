-- ==========================================
-- MIGRATION: TREINAMENTO DE IMAGENS (VISUAL CALIBRATION)
-- ==========================================

-- Tabela de Imagens para NW Standard
CREATE TABLE IF NOT EXISTS nw_treinamento_imagens (
  id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
  criado_em timestamp with time zone DEFAULT timezone('utc'::text, now()) NOT NULL,
  codigo_produto varchar(50),
  descricao_ia text NOT NULL,
  descricao_humano text NOT NULL,
  aprendizado text
);

-- Tabela de Imagens para NW 3D
CREATE TABLE IF NOT EXISTS nw3d_treinamento_imagens (
  id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
  criado_em timestamp with time zone DEFAULT timezone('utc'::text, now()) NOT NULL,
  codigo_produto varchar(50),
  descricao_ia text NOT NULL,
  descricao_humano text NOT NULL,
  aprendizado text
);

-- Ativar RLS
ALTER TABLE nw_treinamento_imagens ENABLE ROW LEVEL SECURITY;
ALTER TABLE nw3d_treinamento_imagens ENABLE ROW LEVEL SECURITY;

-- Políticas de Acesso
DO $$ 
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'Allow access' AND tablename = 'nw_treinamento_imagens') THEN
    CREATE POLICY "Allow access" ON nw_treinamento_imagens FOR ALL USING (true);
  END IF;
  
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'Allow access' AND tablename = 'nw3d_treinamento_imagens') THEN
    CREATE POLICY "Allow access" ON nw3d_treinamento_imagens FOR ALL USING (true);
  END IF;
END $$;
