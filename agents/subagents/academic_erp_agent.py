# -*- coding: utf-8 -*-
"""
Subagente Especialista 7: Agente de Integração & Sincronização com ERPs (AcademicErpAgent).
Responsável por conectar o ProtocoloEdu aos sistemas legados e ERPs acadêmicos
(SolisGE, TOTVS Educacional RM, Sophia Educacional, Lyceum Techne).
Atualiza a situação da matrícula para 'DEFERIDO' e persiste as URLs de custódia digital.
"""

from typing import Dict, Any, Optional
from agents.base_agent import BaseSubagent
from agents.models import SubagentRole, AgentTask
from mcp_services.erp_connector import ErpConnector, ErpSyncResult, erp_connector
from core_institution_models import InstitutionProfile
from core_dossier_models import StudentDossier


class AcademicErpAgent(BaseSubagent):
    """Subagente responsável pela interoperabilidade e atualização de cadastros nos ERPs acadêmicos."""

    def __init__(self, connector: ErpConnector = None):
        super().__init__(
            role=SubagentRole.ACADEMIC_ERP,
            name="Agente de Integração & Sincronização com ERPs",
            description="Comunica com SolisGE, TOTVS RM e Sophia para deferimento de matrículas e registro de prontuários."
        )
        self.erp_connector = connector or erp_connector

    def _run(self, task: AgentTask) -> Dict[str, Any]:
        institution_profile: Optional[InstitutionProfile] = task.payload.get("institution_profile")
        dossier: Optional[StudentDossier] = task.payload.get("dossier")
        force_sync: bool = task.payload.get("force_sync", False)

        if not institution_profile or not dossier:
            raise ValueError(f"Parâmetros institucionais ou dossiê ausentes para {self.name}.")

        # Invoca o conector adaptativo de ERP
        res: ErpSyncResult = self.erp_connector.sync_dossier_to_erp(
            institution=institution_profile,
            dossier=dossier,
            force_sync=force_sync
        )

        erp_type_str = res.erp_type if isinstance(res.erp_type, str) else getattr(res.erp_type, 'value', str(res.erp_type))
        return {
            "success": res.success,
            "target_erp": erp_type_str,
            "transaction_id": res.erp_protocol,
            "error_detail": res.error_details,
            "synced_at": res.synced_at if isinstance(res.synced_at, str) else str(res.synced_at),
            "message": res.message,
            "summary": f"Sincronização ERP [{erp_type_str.upper()}]: {'SUCESSO' if res.success else 'PENDENTE/FALHA'}"
        }
