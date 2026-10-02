-- ==============================================================================
-- PROTOCOLOEDU / IMES - ESQUEMA DE BANCO DE DADOS & STORAGE PARA O SUPABASE
-- Aplicar apenas ao projeto próprio desta instalação independente.
-- Execute este script no SQL Editor do Supabase para criar as tabelas e o bucket.
-- ==============================================================================

-- 1. Habilita extensão UUID se necessário
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ==============================================================================
-- 2. TABELA DE DOSSIÊS ACADÊMICOS (STUDENT_DOSSIERS)
-- Prontuário central do aluno com status geral e metadados por instituição
-- ==============================================================================
CREATE TABLE IF NOT EXISTS public.student_dossiers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    institution_id TEXT NOT NULL,
    student_id TEXT NOT NULL,
    student_name TEXT NOT NULL,
    course_name TEXT DEFAULT 'Geral',
    cpf TEXT,
    status TEXT DEFAULT 'PENDENTE',
    documents_json JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT TIMEZONE('utc', NOW()),
    updated_at TIMESTAMPTZ DEFAULT TIMEZONE('utc', NOW()),
    CONSTRAINT uq_institution_student UNIQUE (institution_id, student_id)
);

-- Índices de alta performance
CREATE INDEX IF NOT EXISTS idx_student_dossiers_lookup 
    ON public.student_dossiers (institution_id, student_id);

CREATE INDEX IF NOT EXISTS idx_student_dossiers_status 
    ON public.student_dossiers (institution_id, status);

CREATE INDEX IF NOT EXISTS idx_student_dossiers_cpf 
    ON public.student_dossiers (cpf);

-- ==============================================================================
-- 3. TABELA DE AUDITORIAS DE DOCUMENTOS (DOCUMENT_AUDITS)
-- Registro detalhado de cada documento analisado pela IA e validado pelo MEC
-- ==============================================================================
CREATE TABLE IF NOT EXISTS public.document_audits (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    institution_id TEXT NOT NULL,
    student_id TEXT NOT NULL,
    document_id TEXT NOT NULL,
    display_name TEXT,
    status TEXT DEFAULT 'pending',
    reason TEXT,
    admin_diagnostic TEXT,
    system_error BOOLEAN DEFAULT FALSE,
    extracted_data JSONB DEFAULT '{}'::jsonb,
    file_name TEXT,
    storage_url TEXT,
    storage_path TEXT,
    sha256_hash TEXT,
    created_at TIMESTAMPTZ DEFAULT TIMEZONE('utc', NOW()),
    updated_at TIMESTAMPTZ DEFAULT TIMEZONE('utc', NOW()),
    CONSTRAINT uq_student_document UNIQUE (institution_id, student_id, document_id)
);

CREATE INDEX IF NOT EXISTS idx_document_audits_lookup 
    ON public.document_audits (institution_id, student_id);

CREATE INDEX IF NOT EXISTS idx_document_audits_hash 
    ON public.document_audits (sha256_hash);

-- ==============================================================================
-- 4. TABELA DE INSTITUIÇÕES / CONTRATANTES (INSTITUTIONS)
-- Suporte nativo ao White-Label, planos de franquia e isolamento multi-tenant
-- ==============================================================================
CREATE TABLE IF NOT EXISTS public.institutions (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    institution_type TEXT DEFAULT 'FACULDADE',
    branding JSONB DEFAULT '{}'::jsonb,
    storage JSONB DEFAULT '{}'::jsonb,
    subscription JSONB DEFAULT '{}'::jsonb,
    erp JSONB DEFAULT '{}'::jsonb,
    enabled_courses JSONB DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ DEFAULT TIMEZONE('utc', NOW()),
    updated_at TIMESTAMPTZ DEFAULT TIMEZONE('utc', NOW())
);

-- ==============================================================================
-- 5. CRIAÇÃO DO BUCKET DE ARQUIVOS PESSOAIS (SUPABASE STORAGE)
-- Bucket: 'documentos-alunos' (Privado por padrão para conformidade LGPD)
-- ==============================================================================
INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
VALUES (
    'documentos-alunos',
    'documentos-alunos',
    FALSE,
    52428800, -- Limite de 50MB por arquivo
    ARRAY[
        'application/pdf',
        'image/jpeg',
        'image/png',
        'image/heic',
        'image/webp'
    ]
)
ON CONFLICT (id) DO UPDATE SET
    public = FALSE,
    file_size_limit = EXCLUDED.file_size_limit,
    allowed_mime_types = EXCLUDED.allowed_mime_types;

-- ==============================================================================
-- 6. POLÍTICAS DE SEGURANÇA (ROW LEVEL SECURITY - RLS)
-- Garante que chaves de serviço (service_role) e scripts backend tenham acesso total
-- ==============================================================================
ALTER TABLE public.student_dossiers ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.document_audits ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.institutions ENABLE ROW LEVEL SECURITY;

-- Políticas permissivas para a Service Role (Backend ProtocoloEdu)
DROP POLICY IF EXISTS "Permitir acesso total para a Service Role em student_dossiers" ON public.student_dossiers;
CREATE POLICY "Permitir acesso total para a Service Role em student_dossiers"
    ON public.student_dossiers
    FOR ALL
    TO service_role
    USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "Permitir acesso total para a Service Role em document_audits" ON public.document_audits;
CREATE POLICY "Permitir acesso total para a Service Role em document_audits"
    ON public.document_audits
    FOR ALL
    TO service_role
    USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "Permitir acesso total para a Service Role em institutions" ON public.institutions;
CREATE POLICY "Permitir acesso total para a Service Role em institutions"
    ON public.institutions
    FOR ALL
    TO service_role
    USING (true) WITH CHECK (true);

-- Políticas de Storage para o Bucket 'documentos-alunos'
DROP POLICY IF EXISTS "Acesso backend total ao bucket documentos-alunos" ON storage.objects;
CREATE POLICY "Acesso backend total ao bucket documentos-alunos"
    ON storage.objects
    FOR ALL
    TO service_role
    USING (bucket_id = 'documentos-alunos') WITH CHECK (bucket_id = 'documentos-alunos');

-- ==============================================================================
-- 7. DADOS INICIAIS (SEED DA INSTITUIÇÃO PILOTO IMES)
-- ==============================================================================
INSERT INTO public.institutions (id, name, institution_type, branding, storage, subscription)
VALUES (
    'imes',
    'Faculdade IMES - Instituto Mineiro de Educação Superior',
    'FACULDADE',
    '{"primary_color": "#0a2351", "secondary_color": "#fdb913", "portal_title": "Portal de Envio de Documentos"}'::jsonb,
    '{"provider": "supabase", "root_folder_id": "documentos-alunos"}'::jsonb,
    '{"plan_tier": "PROFISSIONAL", "monthly_limit": 500, "is_active": true}'::jsonb
)
ON CONFLICT (id) DO UPDATE SET
    name = EXCLUDED.name,
    storage = EXCLUDED.storage;

REVOKE ALL ON public.student_dossiers, public.document_audits, public.institutions FROM anon, authenticated;
GRANT ALL ON public.student_dossiers, public.document_audits, public.institutions TO service_role;
