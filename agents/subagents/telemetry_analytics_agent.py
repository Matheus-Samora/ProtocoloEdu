# -*- coding: utf-8 -*-
"""
Subagente Especialista 8: Agente de Observabilidade & Inteligência Executiva (TelemetryAnalyticsAgent).
Responsável por monitorar a saúde do enxame de subagentes, telemetria da IA,
funil de conversão de matrículas, gargalos por documento e indicadores para a Reitoria e Mantenedora.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from agents.base_agent import BaseSubagent
from agents.models import SubagentRole, AgentTask
from mcp_services.telemetry_service import TelemetryService, telemetry_service


class TelemetryAnalyticsAgent(BaseSubagent):
    """Subagente responsável pela inteligência de dados, telemetria e observabilidade do sistema."""

    def __init__(self, service: TelemetryService = None):
        super().__init__(
            role=SubagentRole.TELEMETRY_ANALYTICS,
            name="Agente de Observabilidade & Inteligência Executiva",
            description="Coleta métricas em tempo real, monitora latência de IA e detecta gargalos de conversão de matrícula."
        )
        self.telemetry = service or telemetry_service

    def _run(self, task: AgentTask) -> Dict[str, Any]:
        action = task.payload.get("action", "get_report")
        institution_id = task.payload.get("institution_id")

        if action == "record_audit":
            status = task.payload.get("status", "in_review")
            doc_name = task.payload.get("doc_name", "Documento")
            reason = task.payload.get("reason")
            self.telemetry.record_document_audit(
                institution_id=institution_id or "imes",
                status=status,
                doc_name=doc_name,
                reason=reason
            )
            return {"success": True, "action": "audit_recorded"}

        elif action == "record_ai_latency":
            lat_ms = task.payload.get("latency_ms", 1000.0)
            success = task.payload.get("success", True)
            model_name = task.payload.get("model_name", "gemini-2.5-flash")
            self.telemetry.record_ai_call(latency_ms=lat_ms, success=success, model_name=model_name)
            return {"success": True, "action": "latency_recorded"}

        # Padrão: Gera relatório consolidado de saúde e inteligência
        full_report = self.telemetry.get_full_telemetry_report()

        # Análise diagnóstica inteligente de gargalos
        conversion_stats = full_report.get("conversion_funnel", {})
        total_docs = conversion_stats.get("total_documents_audited", 0)
        rejections = conversion_stats.get("rejected", 0)
        rejection_rate_pct = round((rejections / max(total_docs, 1)) * 100, 1)

        insights = []
        if rejection_rate_pct > 30:
            insights.append(
                f"Alerta de Gargalo: A taxa de recusa documental ({rejection_rate_pct}%) está elevada. "
                f"Recomenda-se reforçar a orientação de enquadramento de câmera e envio de verso no Portal do Aluno."
            )
        else:
            insights.append("Fluxo de Matrícula Saudável: Baixo índice de pendências e alta taxa de conversão.")

        return {
            "success": True,
            "telemetry_data": full_report,
            "rejection_rate_pct": rejection_rate_pct,
            "executive_insights": insights,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "summary": f"Observabilidade: Sistema Operacional ({full_report.get('status')}) | Taxa de Recusa: {rejection_rate_pct}%"
        }
