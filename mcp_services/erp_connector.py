"""
Conector Bidirecional de ERPs Acadêmicos do ProtocoloEdu.
Integração com SolisGE, TOTVS Educacional (Linha RM), SophiA e ERPs REST genéricos.
Permite consulta cadastral e exportação de dossiês aprovados com protocolos de deferimento.
"""

import os
import uuid
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from pydantic import BaseModel, Field

from core_institution_models import InstitutionProfile
from core_dossier_models import StudentDossier, DossierStatus
from adapters.erp.base import StudentProfile, StudentDataProvider
from adapters.erp.factory import ERPFactory
from adapters.erp.totvs_adapter import TotvsEducacionalAdapter
from adapters.erp.sophia_adapter import SophiaERPAdapter
from adapters.erp.solis_adapter import SolisERPAdapter

logger = logging.getLogger("ERP_CONNECTOR")


class ErpSyncResult(BaseModel):
    """Resultado da operação de sincronização de dossiê com o ERP institucional."""
    success: bool
    student_id: str
    institution_id: str
    erp_type: str
    erp_protocol: str
    dossier_status: str
    documents_synced_count: int
    synced_fields: List[str] = Field(default_factory=list)
    message: str
    error_details: Optional[str] = None
    synced_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class ErpConnector:
    """
    Controlador unificado de sincronização bidirecional entre o ProtocoloEdu e ERPs.
    """

    def __init__(self):
        self.logger = logger

    def search_student(self, institution: InstitutionProfile, identifier: str) -> Optional[StudentProfile]:
        """Busca estudante na base cadastral do ERP conectado."""
        provider = ERPFactory.get_provider(institution)
        return provider.search_student(identifier)

    def sync_dossier_to_erp(
        self,
        institution: InstitutionProfile,
        dossier: StudentDossier,
        force_sync: bool = False
    ) -> ErpSyncResult:
        """
        Exporta o dossiê aprovado e seus documentos auditados para o ERP acadêmico da instituição.
        
        Args:
            institution: Perfil e configurações de integração da instituição.
            dossier: Prontuário do estudante com documentos auditados.
            force_sync: Permite sincronizar mesmo se o dossiê estiver com pendências.
        """
        erp_type = (institution.erp.erp_type or "mock").lower()
        provider = ERPFactory.get_provider(institution)

        is_homologated = (dossier.status == DossierStatus.COMPLETO) or (str(getattr(dossier.status, 'value', dossier.status)) in ("COMPLETO", "HOMOLOGADO"))
        if not is_homologated and not force_sync:
            return ErpSyncResult(
                success=False,
                student_id=dossier.student_id,
                institution_id=institution.id,
                erp_type=erp_type,
                erp_protocol="",
                dossier_status=getattr(dossier.status, 'value', str(dossier.status)),
                documents_synced_count=0,
                message=f"Dossiê em estado '{getattr(dossier.status, 'value', str(dossier.status))}'. Apenas dossiês homologados/completos podem ser enviados ao ERP (use force_sync=True para contornar)."
            )

        from adapters.erp.generic_rest_adapter import MockERPAdapter
        simulated = isinstance(provider, MockERPAdapter)
        if simulated: erp_type = "mock"

        # Monta dados cadastrais extraídos da auditoria com IA para atualizar no ERP
        fields_to_update: Dict[str, Any] = {
            "status_matricula": "DEFERIDO",
            "protocolo_digital": getattr(dossier, "dossier_id", f"PROT-{dossier.student_id}"),
            "data_homologacao": datetime.now(timezone.utc).isoformat()
        }
        synced_fields = ["status_matricula", "protocolo_digital", "data_homologacao"]

        # Agrega dados extraídos de documentos (ex: RG, Certidão de Nascimento, Histórico)
        for doc_k, item in dossier.documents.items():
            if item.status == "approved" and item.extracted_data:
                for k, v in item.extracted_data.items():
                    clean_k = f"doc_{doc_k}_{k}"
                    fields_to_update[clean_k] = v
                    synced_fields.append(clean_k)

        # Gera identificador local da tentativa de sincronização
        erp_protocol = f"ERP-{erp_type.upper()}-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"

        try:
            # 1. Envio específico por tipo de ERP
            if isinstance(provider, TotvsEducacionalAdapter):
                if not provider.update_student_data(dossier.student_id, fields_to_update):
                    raise RuntimeError("ERP não confirmou a atualização.")
                if not provider.sync_matricula_status(dossier.student_id, True, erp_protocol):
                    raise RuntimeError("ERP não confirmou a matrícula.")
            elif isinstance(provider, SophiaERPAdapter):
                if not provider.update_student_data(dossier.student_id, fields_to_update):
                    raise RuntimeError("ERP não confirmou a atualização.")
                for doc_k, item in dossier.documents.items():
                    if item.status == "approved":
                        confirmed = provider.sync_document_delivery(
                            student_id=dossier.student_id,
                            document_name=item.display_name or doc_k,
                            status=item.status,
                            url=item.storage_url or ""
                        )
                        if not confirmed: raise RuntimeError("ERP não confirmou o documento.")
            elif isinstance(provider, SolisERPAdapter):
                if not provider.update_student_data(dossier.student_id, fields_to_update):
                    raise RuntimeError("ERP não confirmou a atualização.")
            else:
                # Provedor Mock ou Genérico
                if not provider.update_student_data(dossier.student_id, fields_to_update):
                    raise RuntimeError("ERP não confirmou a atualização.")

            # 2. Atualiza metadados do dossiê
            approved_count = sum(1 for item in dossier.documents.values() if item.status == "approved")
            dossier.exported_at = datetime.now(timezone.utc)
            dossier.metadata["erp_synced"] = not simulated
            dossier.metadata["erp_simulated"] = simulated
            dossier.metadata["erp_type"] = erp_type
            dossier.metadata["erp_protocol"] = erp_protocol
            dossier.metadata["erp_synced_at"] = datetime.now(timezone.utc).isoformat()

            return ErpSyncResult(
                success=True,
                student_id=dossier.student_id,
                institution_id=institution.id,
                erp_type=erp_type,
                erp_protocol=erp_protocol,
                dossier_status=getattr(dossier.status, 'value', str(dossier.status)),
                documents_synced_count=approved_count,
                synced_fields=synced_fields,
                message=f"Dossiê e {approved_count} documentos sincronizados com sucesso no ERP {erp_type.upper()}."
            )


        except Exception as e:
            logger.error(f"Falha ao sincronizar dossiê {dossier.student_id} no ERP {erp_type}: {e}", exc_info=True)
            return ErpSyncResult(
                success=False,
                student_id=dossier.student_id,
                institution_id=institution.id,
                erp_type=erp_type,
                erp_protocol="",
                dossier_status=dossier.status.value,
                documents_synced_count=0,
                message="Falha de comunicação com o servidor de ERP acadêmico.",
                error_details=str(e)
            )

    def test_connection(self, institution: InstitutionProfile) -> Dict[str, Any]:
        """Testa conectividade e resposta do endpoint do ERP."""
        erp_type = (institution.erp.erp_type or "mock").lower()
        provider = ERPFactory.get_provider(institution)
        try:
            # Consulta estudante de teste para checar conexão
            test_id = "00000000000"
            res = provider.search_student(test_id)
            return {
                "success": True,
                "erp_type": erp_type,
                "status": "connected",
                "message": f"Conexão com o ERP {erp_type.upper()} operando normalmente."
            }
        except Exception as e:
            return {
                "success": False,
                "erp_type": erp_type,
                "status": "error",
                "error": str(e)
            }


# Instância global compartilhada
erp_connector = ErpConnector()
