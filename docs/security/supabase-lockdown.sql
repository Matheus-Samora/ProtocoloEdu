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

UPDATE storage.buckets SET public=false WHERE id='documentos-alunos';
REVOKE ALL ON public.student_dossiers,public.document_audits,public.institutions FROM anon,authenticated;
