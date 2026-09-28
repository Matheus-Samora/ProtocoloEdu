# -*- coding: utf-8 -*-
"""
Subagente Especialista 2: Agente de Visão Cognitiva & OCR Gemini (CognitiveOcrAgent).
Responsável pela transcrição ótica multimodal via API oficial do Google Gemini,
extração de campos estruturados (RG, CPF, nomes, filiação, datas, carimbos escolares e vistos).
"""

from typing import Dict, Any, List
from agents.base_agent import BaseSubagent
from agents.models import SubagentRole, AgentTask
from ai_engine.gemini_service import GeminiDocumentAuditor
from media.models import ProcessedMedia
from core_criteria_models import DocumentSpecification


class CognitiveOcrAgent(BaseSubagent):
    """Subagente responsável pela leitura OCR avançada e extração semântica com Google Gemini."""

    def __init__(self, gemini_auditor: GeminiDocumentAuditor = None):
        super().__init__(
            role=SubagentRole.COGNITIVE_OCR,
            name="Agente de Visão Cognitiva & OCR Gemini",
            description="Executa o OCR multimodal com Gemini 2.5 Flash / 3.5 Flash Lite para extração precisa de dados e carimbos."
        )
        self.auditor = gemini_auditor or GeminiDocumentAuditor()

    def _run(self, task: AgentTask) -> Dict[str, Any]:
        media_list: List[ProcessedMedia] = task.payload.get("sanitized_media_list", [])
        spec: DocumentSpecification = task.payload.get("spec")
        student_name: str = task.payload.get("student_name", "")

        if not media_list or not spec:
            raise ValueError(f"Parâmetros insuficientes para execução de {self.name}.")

        # Invoca a auditoria multimodal do Gemini (com failover e rotação de credenciais)
        verdict = self.auditor.audit_document(
            media_list=media_list,
            spec=spec,
            student_name=student_name
        )

        extracted_data = verdict.get("extracted_data", {})
        is_approved = verdict.get("is_approved", False)
        status = verdict.get("status", "rejected")
        reason = verdict.get("reason", "")
        system_error = verdict.get("system_error", False)
        admin_diag = verdict.get("admin_diagnostic")

        return {
            "success": not system_error,
            "is_approved": is_approved,
            "status": status,
            "reason": reason,
            "extracted_data": extracted_data,
            "criteria_results": verdict.get("criteria_results", []),
            "system_error": system_error,
            "diagnostics": admin_diag,
            "model_used": self.auditor.model_name,
            "summary": f"OCR Gemini concluído. Status={status.upper()} | Campos extraídos={len(extracted_data)}"
        }
