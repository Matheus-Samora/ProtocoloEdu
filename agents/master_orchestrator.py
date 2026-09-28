# -*- coding: utf-8 -*-
"""
Agente Maestro Orquestrador Geral (MasterOrchestratorAgent).
O regente central do enxame de subagentes do ProtocoloEdu.
Coordena a coreografia assíncrona, delegação de tarefas, consolidação de pareceres,
gestão do ciclo de vida dos dossiês, acionamento do guardião de custódia e comunicação com a Secretaria e ERP.
"""

import uuid
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

from agents.models import (
    SubagentRole,
    WorkflowStage,
    AgentTask,
    AgentResult,
    SwarmExecutionTrace
)
from agents.registry import AgentRegistry, agent_registry
from core_institution_models import InstitutionProfile
from core_criteria_models import DocumentSpecification
from core_dossier_models import StudentDossier, DocumentAuditItem, DossierStatus
from criteria_engine import CriteriaCatalog

logger = logging.getLogger("MASTER_ORCHESTRATOR")


class MasterOrchestratorAgent:
    """Maestro central que coordena a execução e interação entre todos os subagentes especialistas."""

    def __init__(self, registry: AgentRegistry = None, criteria_catalog: CriteriaCatalog = None):
        self.registry = registry or agent_registry
        self.criteria_catalog = criteria_catalog or CriteriaCatalog()
        self.role = SubagentRole.MASTER_ORCHESTRATOR
        self.name = "Agente Maestro Orquestrador Geral"

    def orchestrate_document_audit(
        self,
        institution_profile: InstitutionProfile,
        student_id: str,
        student_name: str,
        course_name: str,
        doc_key: str,
        raw_files: List[Dict[str, Any]],
        spec: DocumentSpecification,
        dossier: StudentDossier,
        responsible_name: Optional[str] = None
    ) -> SwarmExecutionTrace:
        """
        Executa a coreografia completa de auditoria documental através dos Subagentes Especialistas.
        """
        task_prefix = f"{student_id}_{doc_key}_{uuid.uuid4().hex[:6]}"
        trace = SwarmExecutionTrace(
            document_id=doc_key,
            student_id=student_id,
            institution_id=institution_profile.id,
            current_stage=WorkflowStage.SUBMITTED
        )

        logger.info(f"[ORQUESTRADOR] Iniciando pipeline multi-agentes para '{doc_key}' do aluno '{student_name}'.")

        # ----------------------------------------------------------------------
        # ETAPA 1: SUBAGENTE DE PERÍCIA E HIGIENIZAÇÃO DE MÍDIA
        # ----------------------------------------------------------------------
        trace.current_stage = WorkflowStage.PREPROCESSED
        forensics_agent = self.registry.get(SubagentRole.MEDIA_FORENSICS)
        task_forensics = AgentTask(
            task_id=f"{task_prefix}_forensics",
            role=SubagentRole.MEDIA_FORENSICS,
            payload={"raw_files": raw_files, "spec": spec, "doc_key": doc_key}
        )
        res_forensics: AgentResult = forensics_agent.execute(task_forensics)
        trace.subagent_results[SubagentRole.MEDIA_FORENSICS.value] = res_forensics

        if not res_forensics.success:
            trace.current_stage = WorkflowStage.FAILED
            trace.final_reason = "Falha no processamento inicial da imagem/PDF enviado."
            trace.admin_diagnostic = res_forensics.diagnostics
            return trace

        sanitized_media_list = res_forensics.data.get("sanitized_media_list", [])

        # ----------------------------------------------------------------------
        # ETAPA 2: SUBAGENTE DE VISÃO COGNITIVA & OCR GEMINI
        # ----------------------------------------------------------------------
        trace.current_stage = WorkflowStage.OCR_EXTRACTED
        ocr_agent = self.registry.get(SubagentRole.COGNITIVE_OCR)
        task_ocr = AgentTask(
            task_id=f"{task_prefix}_ocr",
            role=SubagentRole.COGNITIVE_OCR,
            payload={
                "sanitized_media_list": sanitized_media_list,
                "spec": spec,
                "student_name": student_name
            }
        )
        res_ocr: AgentResult = ocr_agent.execute(task_ocr)
        trace.subagent_results[SubagentRole.COGNITIVE_OCR.value] = res_ocr

        ocr_data = res_ocr.data
        extracted_data = ocr_data.get("extracted_data", {})

        # Registra latência da IA no subagente de telemetria
        analytics_agent = self.registry.get(SubagentRole.TELEMETRY_ANALYTICS)
        if analytics_agent:
            analytics_agent.execute(AgentTask(
                task_id=f"{task_prefix}_telem_ai",
                role=SubagentRole.TELEMETRY_ANALYTICS,
                payload={
                    "action": "record_ai_latency",
                    "latency_ms": res_ocr.latency_ms,
                    "success": res_ocr.success,
                    "model_name": ocr_data.get("model_used", "gemini-2.5-flash")
                }
            ))

        # ----------------------------------------------------------------------
        # ETAPA 3: SUBAGENTE AUDITOR DE CONFORMIDADE MEC
        # ----------------------------------------------------------------------
        trace.current_stage = WorkflowStage.COMPLIANCE_EVALUATED
        mec_agent = self.registry.get(SubagentRole.MEC_COMPLIANCE)
        task_mec = AgentTask(
            task_id=f"{task_prefix}_mec",
            role=SubagentRole.MEC_COMPLIANCE,
            payload={
                "ocr_result": ocr_data,
                "spec": spec,
                "course_name": course_name,
                "student_name": student_name
            }
        )
        res_mec: AgentResult = mec_agent.execute(task_mec)
        trace.subagent_results[SubagentRole.MEC_COMPLIANCE.value] = res_mec

        # ----------------------------------------------------------------------
        # ETAPA 4: SUBAGENTE PERICIAL DE IDENTIDADE & ANTIFRAUDE
        # ----------------------------------------------------------------------
        trace.current_stage = WorkflowStage.IDENTITY_VERIFIED
        fraud_agent = self.registry.get(SubagentRole.IDENTITY_FRAUD)
        task_fraud = AgentTask(
            task_id=f"{task_prefix}_fraud",
            role=SubagentRole.IDENTITY_FRAUD,
            payload={
                "ocr_result": ocr_data,
                "sanitized_media_list": sanitized_media_list,
                "student_name": student_name,
                "student_cpf": student_id,
                "responsible_name": responsible_name
            }
        )
        res_fraud: AgentResult = fraud_agent.execute(task_fraud)
        trace.subagent_results[SubagentRole.IDENTITY_FRAUD.value] = res_fraud

        # ----------------------------------------------------------------------
        # ETAPA 5: CONSOLIDAÇÃO DO VEREDITO PELO MAESTRO
        # ----------------------------------------------------------------------
        trace.current_stage = WorkflowStage.DECISION_CONSOLIDATED

        is_ocr_approved = bool(ocr_data.get("is_approved") is True and ocr_data.get("status") == "approved")
        is_mec_compliant = bool(res_mec.data.get("is_compliant", True))
        is_identity_authentic = bool(res_fraud.data.get("is_authentic", True))

        is_globally_approved = is_ocr_approved and is_mec_compliant and is_identity_authentic

        rejection_reasons = []
        if not is_ocr_approved and ocr_data.get("reason"):
            rejection_reasons.append(ocr_data.get("reason"))

        if not is_identity_authentic:
            fraud_flags = res_fraud.data.get("fraud_flags", [])
            rejection_reasons.extend(fraud_flags)

        if not is_mec_compliant:
            mec_reasons = res_mec.data.get("regulatory_reasons", [])
            for mr in mec_reasons:
                if mr not in rejection_reasons:
                    rejection_reasons.append(mr)

        final_reason = " | ".join(rejection_reasons) if rejection_reasons else "Documento auditado e em plena conformidade institucional."
        trace.is_approved = is_globally_approved
        trace.final_reason = final_reason
        trace.admin_diagnostic = ocr_data.get("diagnostics")

        item_status = "approved" if is_globally_approved else "rejected"
        if ocr_data.get("system_error") or ocr_data.get("status") in ("in_review", "pending_review"):
            item_status = "in_review"

        # ----------------------------------------------------------------------
        # ETAPA 6: SUBAGENTE GUARDIÃO DE CUSTÓDIA E ARQUIVO A-Z
        # ----------------------------------------------------------------------
        trace.current_stage = WorkflowStage.CUSTODY_FINALIZED
        custody_agent = self.registry.get(SubagentRole.CUSTODY_ARCHIVAL)

        legacy_item = dossier.documents.get(doc_key)
        legacy_file = legacy_item.file_name if legacy_item else None

        task_custody = AgentTask(
            task_id=f"{task_prefix}_custody",
            role=SubagentRole.CUSTODY_ARCHIVAL,
            payload={
                "institution_profile": institution_profile,
                "student_name": student_name,
                "spec": spec,
                "media_list": sanitized_media_list,
                "is_globally_approved": is_globally_approved,
                "doc_key": doc_key,
                "legacy_file_name": legacy_file
            }
        )
        res_custody: AgentResult = custody_agent.execute(task_custody)
        trace.subagent_results[SubagentRole.CUSTODY_ARCHIVAL.value] = res_custody

        stored_file_name = res_custody.data.get("stored_file_name")
        storage_url = res_custody.data.get("storage_url")

        # ----------------------------------------------------------------------
        # ETAPA 7: ATUALIZAÇÃO DO DOSSIÊ E ESTADO DO ALUNO
        # ----------------------------------------------------------------------
        audit_item = DocumentAuditItem(
            document_id=spec.id,
            display_name=spec.display_name,
            status=item_status,
            reason=final_reason,
            admin_diagnostic=trace.admin_diagnostic,
            system_error=ocr_data.get("system_error", False),
            extracted_data=extracted_data,
            file_name=stored_file_name if is_globally_approved else None,
            storage_url=storage_url if is_globally_approved else None
        )
        dossier.documents[doc_key] = audit_item

        # Registra auditoria no subagente de telemetria
        if analytics_agent:
            analytics_agent.execute(AgentTask(
                task_id=f"{task_prefix}_telem_audit",
                role=SubagentRole.TELEMETRY_ANALYTICS,
                payload={
                    "action": "record_audit",
                    "institution_id": institution_profile.id,
                    "status": item_status,
                    "doc_name": spec.display_name,
                    "reason": final_reason
                }
            ))

        trace.finished_at = datetime.now(timezone.utc)
        logger.info(
            f"[ORQUESTRADOR] Auditoria de '{doc_key}' concluída pelo enxame. "
            f"Veredito={item_status.upper()} | Custódia={res_custody.data.get('gatekeeper_action')}"
        )
        return trace

    def review_document_workflow(
        self,
        institution_profile: InstitutionProfile,
        student_id: str,
        doc_id: str,
        new_status: str,
        admin_notes: str,
        dossier: StudentDossier
    ) -> Dict[str, Any]:
        """
        Orquestra a intervenção manual da Secretaria Acadêmica com purga de arquivos se rejeitado.
        """
        item = dossier.documents.get(doc_id)
        if not item:
            spec = self.criteria_catalog.get_document_spec(doc_id)
            disp_name = spec.display_name if spec else doc_id
            item = DocumentAuditItem(
                document_id=doc_id,
                display_name=disp_name,
                status=new_status,
                reason=admin_notes or ("Homologado manualmente pela Secretaria Acadêmica." if new_status == 'approved' else "Documento com pendência conforme apontamento da Secretaria.")
            )
            dossier.documents[doc_id] = item
        else:
            item.status = new_status
            item.system_error = False
            item.reason = admin_notes or ("Aprovado e homologado manualmente pela Secretaria Acadêmica." if new_status == 'approved' else "Documento em desconformidade. Providencie o reenvio.")
            item.updated_at = datetime.now(timezone.utc)

        # Se a Secretaria rejeitar, aciona o Guardião de Custódia para expurgar arquivo do disco
        if new_status == 'rejected' and item.file_name:
            custody_agent = self.registry.get(SubagentRole.CUSTODY_ARCHIVAL)
            if custody_agent:
                custody_agent.execute(AgentTask(
                    task_id=f"manual_purge_{student_id}_{doc_id}",
                    role=SubagentRole.CUSTODY_ARCHIVAL,
                    payload={
                        "institution_profile": institution_profile,
                        "student_name": dossier.student_name,
                        "is_globally_approved": False,
                        "doc_key": doc_id,
                        "legacy_file_name": item.file_name
                    }
                ))
            item.file_name = None
            item.storage_url = None

        return {
            "success": True,
            "doc_id": doc_id,
            "new_status": item.status,
            "reason": item.reason
        }

    def get_swarm_status(self) -> Dict[str, Any]:
        """Retorna a visão panorâmica e saúde operacional de todos os subagentes."""
        return self.registry.get_swarm_health()


# Instância singleton global do Maestro Orquestrador
master_orchestrator = MasterOrchestratorAgent()
