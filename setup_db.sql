-- ============================================================
-- BOLÃO COPA 2026 — Setup do Banco de Dados
-- Execute este SQL no Supabase > SQL Editor > New query
-- ============================================================

-- 1. Participantes do bolão
CREATE TABLE IF NOT EXISTS participantes (
    id         SERIAL PRIMARY KEY,
    nome       VARCHAR(100) NOT NULL UNIQUE,
    apelido    VARCHAR(60),
    criado_em  TIMESTAMP DEFAULT NOW()
);

-- 2. Resultados reais dos jogos (preenchido pelo admin)
CREATE TABLE IF NOT EXISTS resultados (
    id              SERIAL PRIMARY KEY,
    jogo_id         INTEGER NOT NULL UNIQUE,
    mandante        VARCHAR(100),
    visitante       VARCHAR(100),
    gols_mandante   INTEGER,
    gols_visitante  INTEGER,
    data_hora       TIMESTAMPTZ,
    atualizado_em   TIMESTAMP DEFAULT NOW()
);

-- Se a tabela ja existe sem essa coluna:
ALTER TABLE resultados ADD COLUMN IF NOT EXISTS data_hora TIMESTAMPTZ;

-- PIN para login e palpite do campeao na tabela participantes
ALTER TABLE participantes ADD COLUMN IF NOT EXISTS pin VARCHAR(10);
ALTER TABLE participantes ADD COLUMN IF NOT EXISTS palpite_campeao VARCHAR(100);

-- Tabela de configuracao (campeao oficial, etc)
CREATE TABLE IF NOT EXISTS configuracao (
    chave VARCHAR(50) PRIMARY KEY,
    valor TEXT,
    atualizado_em TIMESTAMP DEFAULT NOW()
);
ALTER TABLE configuracao DISABLE ROW LEVEL SECURITY;
GRANT ALL ON TABLE configuracao TO anon, authenticated, service_role;

-- 3. Palpites de cada participante
CREATE TABLE IF NOT EXISTS palpites (
    id              SERIAL PRIMARY KEY,
    participante_id INTEGER NOT NULL REFERENCES participantes(id) ON DELETE CASCADE,
    jogo_id         INTEGER NOT NULL,
    gols_mandante   INTEGER NOT NULL DEFAULT 0,
    gols_visitante  INTEGER NOT NULL DEFAULT 0,
    criado_em       TIMESTAMP DEFAULT NOW(),
    UNIQUE(participante_id, jogo_id)
);

-- ============================================================
-- Políticas de acesso (desabilitar RLS para uso simples)
-- ============================================================
ALTER TABLE participantes DISABLE ROW LEVEL SECURITY;
ALTER TABLE resultados    DISABLE ROW LEVEL SECURITY;
ALTER TABLE palpites      DISABLE ROW LEVEL SECURITY;

-- ============================================================
-- Índices para performance
-- ============================================================
CREATE INDEX IF NOT EXISTS idx_palpites_part ON palpites(participante_id);
CREATE INDEX IF NOT EXISTS idx_palpites_jogo ON palpites(jogo_id);
CREATE INDEX IF NOT EXISTS idx_resultados_jogo ON resultados(jogo_id);
