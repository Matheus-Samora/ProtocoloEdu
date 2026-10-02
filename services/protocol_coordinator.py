"""
Orquestrador Central do Protocolo e Secretaria Digital (Protocol Coordinator).
Conecta o Pipeline de Mídia, o Motor de Critérios, o Gemini 2.5 Flash,
o Storage Provider e o Repositório Central de Dossiês.
"""

import os
from security.isolation import initialize_runtime
initialize_runtime()
import json
from security.storage import atomic_write, production
from werkzeug.security import generate_password_hash
import logging
from typing import Dict, Any, List, Optional, Tuple

from core_institution_models import InstitutionProfile
from core_dossier_models import StudentDossier, DocumentAuditItem, DossierStatus
from core_criteria_models import DocumentSpecification
from criteria_engine import CriteriaCatalog
from media.pipeline import MediaPipeline
from ai_engine.gemini_service import GeminiDocumentAuditor
from adapters.storage.factory import StorageFactory
from adapters.storage.base import StorageProvider
from adapters.erp.factory import ERPFactory
from adapters.database.dossier_repository import DossierRepository
from export.engine import UniversalExportEngine
from mcp_services.pades_validator import PadesSignatureValidator, PadesVerificationReport
from mcp_services.notification_service import NotificationService, NotificationChannel, NotificationType, notification_service
from mcp_services.erp_connector import ErpConnector, ErpSyncResult, erp_connector
from mcp_services.telemetry_service import TelemetryService, telemetry_service
from agents.master_orchestrator import master_orchestrator, MasterOrchestratorAgent
import time

logger = logging.getLogger("PROTOCOL_COORDINATOR")


class ProtocolCoordinator:
    """Coordenador de fluxos de ponta a ponta do Protocolo Digital."""

    def __init__(
        self,
        institutions_catalog_file: str = "institutions_catalog.json",
        criteria_catalog: Optional[CriteriaCatalog] = None,
        dossier_repo: Optional[DossierRepository] = None
    ):
        self.institutions_file = institutions_catalog_file
        self.criteria_catalog = criteria_catalog or CriteriaCatalog()
        self.dossier_repo = dossier_repo or DossierRepository()
        self.media_pipeline = MediaPipeline()
        self.ai_auditor = GeminiDocumentAuditor()
        self.pades_validator = PadesSignatureValidator()
        self.notification_service = notification_service
        self.erp_connector = erp_connector
        self.telemetry = telemetry_service
        self.orchestrator = master_orchestrator
        self.institutions: Dict[str, InstitutionProfile] = {}
        self.load_institutions()

    def load_institutions(self):
        """Carrega perfis de instituições cadastradas."""
        if os.path.exists(self.institutions_file):
            try:
                with open(self.institutions_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for i_id, i_data in data.get("institutions", {}).items():
                        self.institutions[i_id] = InstitutionProfile(**i_data)
            except Exception as e:
                logger.error("Operation failed; inspect restricted security events")

    def save_institutions(self):
        """Persiste os perfis de instituições atualizados no catálogo JSON."""
        try:
            catalog_data = {
                "version": "2.1.0",
                "institutions": {i_id: inst.model_dump(mode="json") for i_id, inst in self.institutions.items()}
            }
            atomic_write(self.institutions_file,json.dumps(catalog_data,ensure_ascii=False).encode())
            logger.info("Catálogo de instituições e assinaturas atualizado com sucesso.")
        except Exception as e:
            logger.error("Operation failed; inspect restricted security events")

    def get_institution(self, institution_id: str) -> Optional[InstitutionProfile]:
        """Obtém o perfil da instituição."""
        if not institution_id:
            return self.institutions.get("imes")
        clean_id = institution_id.lower().strip()
        inst = self.institutions.get(clean_id)
        return inst

    def update_institution_subscription(
        self,
        institution_id: str,
        plan_tier: Optional[str] = None,
        plan_name: Optional[str] = None,
        monthly_limit: Optional[int] = None,
        is_active: Optional[bool] = None,
        admin_access_key: Optional[str] = None,
        billing_day: Optional[int] = None
    ) -> Optional[InstitutionProfile]:
        """Atualiza os parâmetros do plano e chave de acesso de um contratante."""
        inst = self.institutions.get(institution_id)
        if not inst:
            return None
        if plan_tier:
            inst.subscription.plan_tier = plan_tier
        if plan_name:
            inst.subscription.plan_name = plan_name
        if monthly_limit is not None:
            inst.subscription.monthly_limit = int(monthly_limit)
        if is_active is not None:
            inst.subscription.is_active = bool(is_active)
        if admin_access_key:
            inst.subscription.admin_access_key = generate_password_hash(str(admin_access_key)).strip()
        if billing_day is not None:
            inst.subscription.billing_day = int(billing_day)

        self.institutions[institution_id] = inst
        self.save_institutions()
        return inst

    def update_institution_branding(
        self,
        institution_id: str,
        logo_url: Optional[str] = None,
        primary_color: Optional[str] = None,
        secondary_color: Optional[str] = None,
        portal_title: Optional[str] = None
    ) -> Optional[InstitutionProfile]:
        """Atualiza a identidade visual (White-Label) do contratante."""
        inst = self.institutions.get(institution_id)
        if not inst:
            return None
        if logo_url is not None:
            inst.branding.logo_url = str(logo_url).strip()
        if primary_color is not None:
            inst.branding.primary_color = str(primary_color).strip()
        if secondary_color is not None:
            inst.branding.secondary_color = str(secondary_color).strip()
        if portal_title is not None:
            inst.branding.portal_title = str(portal_title).strip()

        self.institutions[institution_id] = inst
        self.save_institutions()
        return inst

    def reset_institution_usage(self, institution_id: str) -> Optional[InstitutionProfile]:
        """Zera o consumo de auditorias do mês (novo ciclo de faturamento)."""
        inst = self.institutions.get(institution_id)
        if not inst:
            return None
        inst.subscription.current_month_usage = 0
        self.institutions[institution_id] = inst
        self.save_institutions()
        return inst

    def increment_institution_usage(self, institution_id: str, count: int = 1):
        """Incrementa o contador de auditorias consumidas no ciclo."""
        inst = self.institutions.get(institution_id)
        if inst:
            inst.subscription.current_month_usage += count
            self.institutions[institution_id] = inst
            self.save_institutions()

    def create_or_update_institution(self, profile: InstitutionProfile):
        """Cadastra ou substitui uma instituição no catálogo central."""
        self.institutions[profile.id] = profile
        self.save_institutions()

    def get_student(self, institution_id: str, identifier: str) -> Optional[Dict[str, Any]]:
        """
        Busca o estudante: primeiro no banco central de dossiês da plataforma.
        Se for o primeiro acesso, consulta o ERP (Solis/Outro) e cria o dossiê inicial.
        """
        inst = self.get_institution(institution_id)
        if not inst: return None
        clean_id = str(identifier).replace('.', '').replace('-', '').strip()

        # 1. Verifica se já temos o dossiê registrado
        dossier = self.dossier_repo.get_dossier(inst.id, clean_id)
        if dossier:
            return {
                "id": dossier.student_id,
                "name": dossier.student_name,
                "cpf": dossier.cpf,
                "course": dossier.course_name,
                "status": dossier.status.value,
                "is_cached": True
            }

        # 2. Consulta conector de ERP da instituição
        erp_provider = ERPFactory.get_provider(inst)
        from adapters.erp.generic_rest_adapter import MockERPAdapter
        if isinstance(erp_provider, MockERPAdapter) and os.environ.get('PROTOCOL_DEMO_MODE', '').lower() != 'true':
            return None
        profile = erp_provider.search_student(clean_id)
        if not profile:
            return None

        # 3. Cria o dossiê inicial no banco central da plataforma
        new_dossier = StudentDossier(
            institution_id=inst.id,
            student_id=clean_id,
            student_name=profile.full_name,
            cpf=profile.cpf or clean_id,
            course_name=profile.course_name or inst.enabled_courses[0] if inst.enabled_courses else "Geral",
            status=DossierStatus.PENDENTE
        )
        self.dossier_repo.save_dossier(new_dossier)

        return {
            "id": new_dossier.student_id,
            "name": new_dossier.student_name,
            "cpf": new_dossier.cpf,
            "course": new_dossier.course_name,
            "status": new_dossier.status.value,
            "is_cached": False
        }

    def check_existing_documents(self, institution_id: str, student_id: str, course_name: str) -> Dict[str, Any]:
        """
        Verifica quais documentos já foram aprovados e arquivados no Storage ou Dossiê.
        """
        inst = self.get_institution(institution_id)
        clean_id = str(student_id).replace('.', '').replace('-', '').strip()
        dossier = self.dossier_repo.get_dossier(inst.id, clean_id)
        
        # Recupera lista de documentos exigidos para o curso
        required_groups = self.criteria_catalog.get_required_docs_for_course(course_name)
        result_docs = {}

        # 1. Primeiro verifica no banco de dados central da plataforma
        if dossier:
            for doc_k, item in dossier.documents.items():
                result_docs[doc_k] = {
                    "encontrado": item.status == "approved",
                    "status": item.status,
                    "nome_arquivo": item.file_name,
                    "reason": item.reason
                }

        return {
            "institution_id": inst.id,
            "institution_name": inst.name,
            "student_id": clean_id,
            "documentos": result_docs
        }

    def process_and_audit_uploads(
        self,
        institution_id: str,
        student_id: str,
        student_name: str,
        course_name: str,
        uploaded_files_map: Dict[str, List[Dict[str, Any]]]
    ) -> Dict[str, Any]:
        """
        Recebe os arquivos enviados pelo aluno, higieniza via MediaPipeline,
        submete à auditoria do Gemini, armazena os aprovados no Storage configurado
        e salva tudo no Dossiê Central.
        """
        inst = self.get_institution(institution_id)
        if not inst:
            raise ValueError(f"Instituição '{institution_id}' não localizada.")

        # Validação do status da assinatura e limites do plano contratado
        if hasattr(inst, "subscription"):
            if not inst.subscription.is_active:
                return {
                    "success": False,
                    "error": "O recebimento de documentos para esta instituição está temporariamente pausado pela administração.",
                    "code": "SUBSCRIPTION_INACTIVE"
                }
            if inst.subscription.monthly_limit > 0 and inst.subscription.current_month_usage >= inst.subscription.monthly_limit:
                return {
                    "success": False,
                    "error": "A cota mensal de análises desta instituição foi atingida para o ciclo atual. A secretaria já foi notificada.",
                    "code": "PLAN_QUOTA_EXCEEDED"
                }

        clean_id = str(student_id).replace('.', '').replace('-', '').strip()
        storage_provider = StorageFactory.get_provider(inst)

        # Carrega ou cria o dossiê no banco central
        dossier = self.dossier_repo.get_dossier(inst.id, clean_id)
        if not dossier:
            dossier = StudentDossier(
                institution_id=inst.id,
                student_id=clean_id,
                student_name=student_name,
                course_name=course_name,
                cpf=clean_id
            )

        results = {}

        for doc_key, files_list in uploaded_files_map.items():
            spec = self.criteria_catalog.get_document_spec(doc_key)
            if not spec:
                logger.warning(f"Documento '{doc_key}' não possui especificação cadastrada.")
                continue

            # Orquestração pelo Enxame Multi-Agentes (Mídia, OCR Gemini, MEC, Antifraude, Custódia)
            trace = self.orchestrator.orchestrate_document_audit(
                institution_profile=inst,
                student_id=clean_id,
                student_name=student_name,
                course_name=course_name,
                doc_key=doc_key,
                raw_files=files_list,
                spec=spec,
                dossier=dossier
            )

            # Contabiliza uso no plano mensal da instituição
            self.increment_institution_usage(inst.id, 1)

            ocr_res = trace.subagent_results.get("cognitive_ocr")
            ocr_data = ocr_res.data if ocr_res else {}

            item_status = "approved" if trace.is_approved else (
                "in_review" if ocr_data.get("system_error") or ocr_data.get("status") in ("in_review", "pending_review")
                else "rejected"
            )

            results[doc_key] = {
                "document_id": spec.id,
                "display_name": spec.display_name,
                "status": item_status,
                "is_approved": trace.is_approved,
                "system_error": ocr_data.get("system_error", False),
                "reason": trace.final_reason,
                "admin_diagnostic": trace.admin_diagnostic,
                "criteria_results": ocr_data.get("criteria_results", []),
                "extracted_data": ocr_data.get("extracted_data", {}),
                "swarm_trace": trace.to_dict()
            }


        # 5. Atualiza o status geral do dossiê e persiste no banco central
        # Busca a lista de documentos obrigatórios do curso
        groups = self.criteria_catalog.get_required_docs_for_course(course_name)
        mandatory_keys = []
        for g in groups:
            if g.get("type") in ("MANDATORY", "ONE_OF"):
                mandatory_keys.extend(g.get("options", []))

        old_status = dossier.status.value if hasattr(dossier, "status") else None
        dossier.update_status(mandatory_keys)
        self.telemetry.record_dossier_status(inst.id, old_status, dossier.status.value)
        if not self.dossier_repo.save_dossier(dossier):
            raise IOError("Persistência do dossiê não confirmada.")

        return {
            "success": True,
            "institution_id": inst.id,
            "student_id": clean_id,
            "dossier_status": dossier.status.value,
            "results": results
        }

    def verify_document_signature(
        self,
        pdf_input: Any,
        filename: str = "documento.pdf"
    ) -> PadesVerificationReport:
        """Valida assinaturas digitais ICP-Brasil / PAdES segundo a Portaria MEC 315/2018."""
        return self.pades_validator.verify_pdf(pdf_input, filename=filename)

    def notify_student(
        self,
        institution_id: str,
        student_id: str,
        notification_type: str = "pendency",
        channel: str = "whatsapp",
        recipient: Optional[str] = None,
        custom_message: Optional[str] = None,
        pending_docs: Optional[List[Dict[str, str]]] = None,
        course_name: Optional[str] = None,
        protocol_number: Optional[str] = None
    ) -> Any:
        """Dispara aviso institucional (WhatsApp, Webhook, E-mail)."""
        inst = self.get_institution(institution_id)
        inst_name = inst.name if inst else institution_id.upper()
        dossier = self.dossier_repo.get_dossier(institution_id, student_id)
        student_name = dossier.student_name if dossier else f"Estudante ({student_id})"
        target_recipient = recipient or (dossier.metadata.get("phone") if dossier else None) or ""
        if not target_recipient: raise ValueError("Destinatário não informado.")
        chan_enum = NotificationChannel(channel.lower())

        if notification_type == "pendency":
            if not pending_docs and dossier:
                pending_docs = [
                    {"display_name": item.display_name, "reason": item.reason or "Pendente de envio"}
                    for item in dossier.documents.values()
                    if item.status in ("rejected", "in_review")
                ]
            return self.notification_service.notify_pendencies(
                institution_id=institution_id,
                institution_name=inst_name,
                student_id=student_id,
                student_name=student_name,
                recipient_phone_or_email=target_recipient,
                pending_items=pending_docs or [],
                channel=chan_enum
            )
        elif notification_type == "homologation":
            c_name = course_name or (dossier.course_name if dossier else "Graduação")
            p_num = protocol_number or (f"PROT-{dossier.student_id}" if dossier else f"PROT-{student_id}")
            return self.notification_service.notify_homologation(
                institution_id=institution_id,
                institution_name=inst_name,
                student_id=student_id,
                student_name=student_name,
                course_name=c_name,
                protocol_number=p_num,
                recipient_phone_or_email=target_recipient,
                channel=chan_enum
            )
        else:
            return self.notification_service.notify_custom(
                institution_id=institution_id,
                institution_name=inst_name,
                student_id=student_id,
                student_name=student_name,
                recipient_phone_or_email=target_recipient,
                subject=f"[{inst_name}] Comunicado Acadêmico",
                custom_message=custom_message or "Aviso da Secretaria Acadêmica.",
                channel=chan_enum
            )

    def sync_dossier_to_erp(
        self,
        institution_id: str,
        student_id: str,
        force_sync: bool = False
    ) -> ErpSyncResult:
        """Sincroniza o dossiê com o ERP acadêmico configurado (Solis, TOTVS, Sophia)."""
        inst = self.get_institution(institution_id)
        if not inst:
            raise ValueError(f"Instituição '{institution_id}' não localizada.")
        dossier = self.dossier_repo.get_dossier(inst.id, student_id)
        if not dossier:
            raise ValueError(f"Dossiê do aluno '{student_id}' não encontrado.")

        res = self.erp_connector.sync_dossier_to_erp(inst, dossier, force_sync=force_sync)
        if res.success:
            self.dossier_repo.save_dossier(dossier)
        return res

    def get_telemetry_report(self) -> Dict[str, Any]:
        """Retorna telemetria do sistema, IA e taxas de conversão."""
        return self.telemetry.get_full_telemetry_report()


    def export_institution_dossiers(
        self,
        institution_id: str,
        export_format: str = "csv",
        status_filter: Optional[str] = None
    ) -> Any:
        """
        Exporta todos os dados e prontuários da instituição no formato solicitado.
        Formatos: 'csv', 'json', 'zip'.
        """
        inst = self.get_institution(institution_id)
        dossiers = self.dossier_repo.list_dossiers(inst.id, status=status_filter)

        if export_format == "json":
            return UniversalExportEngine.export_to_json(dossiers), "application/json", f"dossiers_{inst.id}.json"
        elif export_format == "zip":
            storage_provider = StorageFactory.get_provider(inst)
            def file_fetcher(dossier, doc_item):
                if hasattr(storage_provider, "get_file_bytes") and doc_item.file_name:
                    return storage_provider.get_file_bytes(dossier.student_name, doc_item.file_name)
                return None

            zip_bytes = UniversalExportEngine.create_batch_zip(dossiers, file_fetcher_fn=file_fetcher)
            return zip_bytes, "application/zip", f"pacote_documentos_{inst.id}.zip"

        # Padrão: CSV Excel
        csv_text = UniversalExportEngine.export_to_csv(dossiers)
        return csv_text, "text/csv; charset=utf-8-sig", f"relatorio_documental_{inst.id}.csv"

    def review_document(
        self,
        institution_id: str,
        student_id: str,
        doc_id: str,
        new_status: str,
        admin_notes: str = ""
    ) -> Dict[str, Any]:
        """Orquestra a intervenção manual da Secretaria através do Agente Maestro Orquestrador e Guardião de Custódia."""
        inst = self.get_institution(institution_id)
        if not inst:
            raise ValueError(f"Instituição '{institution_id}' não localizada.")
        clean_id = str(student_id).replace('.', '').replace('-', '').strip()
        dossier = self.dossier_repo.get_dossier(inst.id, clean_id)
        if not dossier:
            raise ValueError(f"Dossiê do estudante '{clean_id}' não localizado.")

        res = self.orchestrator.review_document_workflow(
            institution_profile=inst,
            student_id=clean_id,
            doc_id=doc_id,
            new_status=new_status,
            admin_notes=admin_notes,
            dossier=dossier
        )

        # Recalcula status geral do dossiê
        groups = self.criteria_catalog.get_required_docs_for_course(dossier.course_name)
        mandatory_keys = []
        for grp in groups:
            if grp.get("type") in ("MANDATORY", "ONE_OF"):
                mandatory_keys.extend(grp.get("options", []))
        dossier.update_status(mandatory_keys)
        self.dossier_repo.save_dossier(dossier)

        return res

    def get_swarm_status(self) -> Dict[str, Any]:
        """Retorna o status, saúde e telemetria operacional de todo o enxame de subagentes especialistas."""
        return self.orchestrator.get_swarm_status()
