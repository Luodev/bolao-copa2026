-- ============================================================
-- BOLÃO COPA 2026 — Setup do Banco de Dados (Multi-Tenant)
-- Execute este SQL no Supabase > SQL Editor > New query
-- ============================================================

-- 0. Tabela de bolões (multi-tenant)
CREATE TABLE IF NOT EXISTS boloes (
    id              SERIAL PRIMARY KEY,
    slug            VARCHAR(50) NOT NULL UNIQUE,
    nome            VARCHAR(100) NOT NULL,
    admin_password  VARCHAR(100) DEFAULT 'copa2026admin',
    criado_em       TIMESTAMP DEFAULT NOW()
);
ALTER TABLE boloes DISABLE ROW LEVEL SECURITY;
GRANT ALL ON TABLE boloes TO anon, authenticated, service_role;
GRANT ALL ON SEQUENCE boloes_id_seq TO anon, authenticated, service_role;

-- Bolão padrão (preserva dados já existentes antes do multi-tenant)
INSERT INTO boloes (slug, nome, admin_password)
VALUES ('lucas', 'Bolão do Lucas', 'copa2026admin')
ON CONFLICT (slug) DO NOTHING;

-- ============================================================
-- 1. Participantes do bolão
-- ============================================================
CREATE TABLE IF NOT EXISTS participantes (
    id              SERIAL PRIMARY KEY,
    bolao_id        INTEGER REFERENCES boloes(id) DEFAULT 1,
    nome            VARCHAR(100) NOT NULL,
    apelido         VARCHAR(60),
    pin             VARCHAR(10),
    palpite_campeao VARCHAR(100),
    criado_em       TIMESTAMP DEFAULT NOW()
);

-- Migrar tabela existente (adiciona colunas se ainda não existem)
ALTER TABLE participantes ADD COLUMN IF NOT EXISTS bolao_id        INTEGER REFERENCES boloes(id) DEFAULT 1;
ALTER TABLE participantes ADD COLUMN IF NOT EXISTS pin             VARCHAR(10);
ALTER TABLE participantes ADD COLUMN IF NOT EXISTS palpite_campeao VARCHAR(100);

-- Remover UNIQUE simples (nome) e criar UNIQUE composto (bolao_id, nome)
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'participantes_nome_key') THEN
        ALTER TABLE participantes DROP CONSTRAINT participantes_nome_key;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'participantes_bolao_id_nome_key') THEN
        ALTER TABLE participantes ADD CONSTRAINT participantes_bolao_id_nome_key UNIQUE(bolao_id, nome);
    END IF;
END $$;

-- ============================================================
-- 2. Resultados reais dos jogos (um conjunto por bolão)
-- ============================================================
CREATE TABLE IF NOT EXISTS resultados (
    id              SERIAL PRIMARY KEY,
    bolao_id        INTEGER REFERENCES boloes(id) DEFAULT 1,
    jogo_id         INTEGER NOT NULL,
    mandante        VARCHAR(100),
    visitante       VARCHAR(100),
    gols_mandante   INTEGER,
    gols_visitante  INTEGER,
    data_hora       TIMESTAMPTZ,
    atualizado_em   TIMESTAMP DEFAULT NOW()
);

-- Migrar tabela existente
ALTER TABLE resultados ADD COLUMN IF NOT EXISTS bolao_id   INTEGER REFERENCES boloes(id) DEFAULT 1;
ALTER TABLE resultados ADD COLUMN IF NOT EXISTS data_hora  TIMESTAMPTZ;

-- Remover UNIQUE simples (jogo_id) e criar UNIQUE composto (bolao_id, jogo_id)
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'resultados_jogo_id_key') THEN
        ALTER TABLE resultados DROP CONSTRAINT resultados_jogo_id_key;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'resultados_bolao_id_jogo_id_key') THEN
        ALTER TABLE resultados ADD CONSTRAINT resultados_bolao_id_jogo_id_key UNIQUE(bolao_id, jogo_id);
    END IF;
END $$;

-- ============================================================
-- 3. Palpites de cada participante
-- ============================================================
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
-- 4. Configuração (campeão oficial, etc)
--    A chave é namespaceada no app como "bolao_id:chave"
-- ============================================================
CREATE TABLE IF NOT EXISTS configuracao (
    chave         VARCHAR(100) PRIMARY KEY,
    valor         TEXT,
    atualizado_em TIMESTAMP DEFAULT NOW()
);
ALTER TABLE configuracao DISABLE ROW LEVEL SECURITY;
GRANT ALL ON TABLE configuracao TO anon, authenticated, service_role;

-- ============================================================
-- Políticas de acesso (desabilitar RLS para uso simples)
-- ============================================================
ALTER TABLE participantes DISABLE ROW LEVEL SECURITY;
ALTER TABLE resultados    DISABLE ROW LEVEL SECURITY;
ALTER TABLE palpites      DISABLE ROW LEVEL SECURITY;

-- ============================================================
-- Permissões
-- ============================================================
GRANT ALL ON TABLE participantes TO anon, authenticated, service_role;
GRANT ALL ON TABLE resultados    TO anon, authenticated, service_role;
GRANT ALL ON TABLE palpites      TO anon, authenticated, service_role;
GRANT ALL ON SEQUENCE participantes_id_seq TO anon, authenticated, service_role;
GRANT ALL ON SEQUENCE resultados_id_seq    TO anon, authenticated, service_role;
GRANT ALL ON SEQUENCE palpites_id_seq      TO anon, authenticated, service_role;

-- ============================================================
-- Índices para performance
-- ============================================================
CREATE INDEX IF NOT EXISTS idx_participantes_bolao ON participantes(bolao_id);
CREATE INDEX IF NOT EXISTS idx_palpites_part       ON palpites(participante_id);
CREATE INDEX IF NOT EXISTS idx_palpites_jogo       ON palpites(jogo_id);
CREATE INDEX IF NOT EXISTS idx_resultados_bolao    ON resultados(bolao_id);
CREATE INDEX IF NOT EXISTS idx_resultados_jogo     ON resultados(jogo_id);
