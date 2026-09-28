// Follow this setup guide to integrate the Deno language server with your editor:
// https://deno.land/manual/getting_started/setup_your_environment
// This code runs on Supabase Edge Functions (Deno / TypeScript)

import { serve } from "https://deno.land/std@0.168.0/http/server.ts";
import { createClient } from "https://esm.sh/@supabase/supabase-js@2.39.0";

const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
  "Access-Control-Allow-Methods": "POST, OPTIONS",
};

serve(async (req) => {
  // Trata preflight CORS
  if (req.method === "OPTIONS") {
    return new Response("ok", { headers: corsHeaders });
  }

  try {
    const supabaseUrl = Deno.env.get("SUPABASE_URL") || "https://phipudvmceitxcajggus.supabase.co";
    const supabaseServiceKey = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY") || "sb_secret_Rt3beKTkAzVUrvRGWZagpg_3TvWoV6y";
    const geminiApiKey = Deno.env.get("GEMINI_API_KEY") || "AIzaSyBbxXALaM60hn-Es-kjKY0yopJ4qaDXF-s";

    const supabase = createClient(supabaseUrl, supabaseServiceKey);

    const body = await req.json();
    const {
      institution_id = "imes",
      student_id,
      student_name,
      document_id = "rg_cnh",
      display_name = "Documento de Identidade (RG/CNH)",
      file_path,
      file_base64,
      mime_type = "application/pdf"
    } = body;

    if (!student_id || !file_path) {
      return new Response(
        JSON.stringify({ error: "Parâmetros obrigatórios: student_id e file_path" }),
        { status: 400, headers: { ...corsHeaders, "Content-Type": "application/json" } }
      );
    }

    // 1. Obtém os bytes do documento do bucket 'documentos-alunos'
    let base64Data = file_base64;
    let actualMime = mime_type;

    if (!base64Data) {
      const { data: fileBlob, error: downloadError } = await supabase.storage
        .from("documentos-alunos")
        .download(file_path);

      if (downloadError || !fileBlob) {
        throw new Error(`Erro ao baixar arquivo do bucket: ${downloadError?.message}`);
      }

      actualMime = fileBlob.type || mime_type;
      const arrayBuffer = await fileBlob.arrayBuffer();
      const uint8Array = new Uint8Array(arrayBuffer);
      let binary = "";
      for (let i = 0; i < uint8Array.byteLength; i++) {
        binary += String.fromCharCode(uint8Array[i]);
      }
      base64Data = btoa(binary);
    }

    // 2. Monta o Prompt Forense de Auditoria Regulatória MEC (Portaria 315/2018)
    const systemPrompt = `Você é o Auditor Acadêmico Oficial de Inteligência Artificial do ProtocoloEdu para validação de documentos de matrícula segundo a Portaria MEC nº 315/2018 e diretrizes do CNE.
Analise detalhadamente o arquivo enviado para o estudante "${student_name}".
Tipo de documento esperado: "${display_name}" (ID: ${document_id}).

Regras de Aceitação:
1. DOC_TYPE: O arquivo é de fato o tipo esperado (${display_name})?
2. HOLDER_MATCH: O titular indicado no documento corresponde a "${student_name}"? Aceite variações de solteiro/casado e abreviações comuns.
3. COMPLETENESS: O documento possui frente e verso (se aplicável), sem cortes em assinaturas ou carimbos?
4. QUALITY_CHECK: O texto está legível e sem reflexos que ocultem dados críticos (CPF, RG, Data de Nascimento)?
5. ANTIFRAUD: Há sinais evidentes de montagem digital, adulteração de fontes ou rasuras?

Responda ESTRITAMENTE em formato JSON com o seguinte schema:
{
  "status": "approved" OU "rejected",
  "reason": "Justificativa clara e humanizada em português para o aluno",
  "admin_diagnostic": "Diagnóstico técnico detalhado para a secretaria",
  "extracted_data": {
    "nome_titular": "Nome lido no documento",
    "cpf": "CPF encontrado ou null",
    "rg": "RG encontrado ou null",
    "data_nascimento": "Data ou null",
    "orgao_emissor": "Órgão expedidor ou null"
  },
  "confidence_score": 0.95
}`;

    // 3. Executa chamada direta à API do Google Gemini Flash
    const geminiEndpoint = `https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key=${geminiApiKey}`;
    const geminiPayload = {
      contents: [
        {
          parts: [
            { text: systemPrompt },
            {
              inline_data: {
                mime_type: actualMime,
                data: base64Data
              }
            }
          ]
        }
      ],
      generationConfig: {
        response_mime_type: "application/json",
        temperature: 0.1
      }
    };

    const geminiResp = await fetch(geminiEndpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(geminiPayload)
    });

    if (!geminiResp.ok) {
      const errText = await geminiResp.text();
      throw new Error(`Erro na API Gemini: ${geminiResp.status} - ${errText}`);
    }

    const geminiJson = await geminiResp.json();
    const rawText = geminiJson.candidates?.[0]?.content?.parts?.[0]?.text || "{}";
    const auditResult = JSON.parse(rawText);

    // 4. Grava na tabela 'document_audits' do Supabase
    const fileName = file_path.split("/").pop() || "documento.pdf";
    const storageUrl = `${supabaseUrl}/storage/v1/object/authenticated/documentos-alunos/${file_path}`;

    const auditRecord = {
      institution_id,
      student_id,
      document_id,
      display_name,
      status: auditResult.status || "rejected",
      reason: auditResult.reason || "Documento analisado.",
      admin_diagnostic: auditResult.admin_diagnostic || "Auditoria automatizada via Gemini Flash.",
      system_error: false,
      extracted_data: auditResult.extracted_data || {},
      file_name: fileName,
      storage_url: storageUrl,
      updated_at: new Date().toISOString()
    };

    await supabase.from("document_audits").upsert(auditRecord, {
      onConflict: "institution_id,student_id,document_id"
    });

    // 5. Atualiza o dossiê central 'student_dossiers'
    const { data: currentDossier } = await supabase
      .from("student_dossiers")
      .select("documents_json")
      .eq("institution_id", institution_id)
      .eq("student_id", student_id)
      .maybeSingle();

    const docsMap = currentDossier?.documents_json || {};
    docsMap[document_id] = auditRecord;

    // Se todos estiverem aprovados, marca dossiê como CONCLUIDO
    const allApproved = Object.values(docsMap).every((d: any) => d.status === "approved");
    const dossierStatus = allApproved ? "CONCLUIDO" : "PENDENTE";

    await supabase.from("student_dossiers").upsert(
      {
        institution_id,
        student_id,
        student_name,
        status: dossierStatus,
        documents_json: docsMap,
        updated_at: new Date().toISOString()
      },
      { onConflict: "institution_id,student_id" }
    );

    return new Response(
      JSON.stringify({
        success: true,
        audit: auditRecord,
        dossier_status: dossierStatus
      }),
      { status: 200, headers: { ...corsHeaders, "Content-Type": "application/json" } }
    );

  } catch (err: any) {
    return new Response(
      JSON.stringify({ success: false, error: err?.message || String(err) }),
      { status: 500, headers: { ...corsHeaders, "Content-Type": "application/json" } }
    );
  }
});
