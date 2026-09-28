# -*- coding: utf-8 -*-
"""
Repositório de Dossiês Integrado ao Supabase (PostgreSQL / PostgREST).
Grava prontuários de alunos, status de matrícula e documentos auditados
nas tabelas 'student_dossiers' e 'document_audits' do Supabase.
"""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
import requests

from core_dossier_models import StudentDossier, DocumentAuditItem, DossierStatus
from adapters.supabase_client import supabase_manager

logger = logging.getLogger("SUPABASE_DOSSIER_REPO")


class SupabaseDossierRepository:
    """
    Persistência de prontuários acadêmicos e auditorias no Supabase Database.
    Utiliza o cliente oficial supabase-py ou PostgREST direto (/rest/v1/).
    """

    def __init__(self):
        self.manager = supabase_manager

    @property
    def is_active(self) -> bool:
        return self.manager.is_configured

    def save_dossier(self, dossier: StudentDossier) -> bool:
        """Salva ou atualiza um prontuário estudantil no Supabase."""
        if not self.is_active:
            return False

        # Prepara registro do dossiê
        dossier_dict = {
            "institution_id": dossier.institution_id,
            "student_id": dossier.student_id,
            "student_name": dossier.student_name,
            "course_name": dossier.course_name,
            "cpf": dossier.cpf,
            "status": dossier.status.value if hasattr(dossier.status, "value") else str(dossier.status),
            "documents_json": {k: v.model_dump(mode="json") for k, v in dossier.documents.items()},
            "updated_at": datetime.now(timezone.utc).isoformat()
        }

        try:
            # 1. Via supabase-py
            if self.manager.client:
                # Upsert em student_dossiers
                self.manager.client.table("student_dossiers").upsert(
                    dossier_dict,
                    on_conflict="institution_id,student_id"
                ).execute()

                # Upsert de cada documento individual em document_audits
                for doc_id, doc_item in dossier.documents.items():
                    audit_record = {
                        "institution_id": dossier.institution_id,
                        "student_id": dossier.student_id,
                        "document_id": doc_id,
                        "display_name": doc_item.display_name,
                        "status": doc_item.status,
                        "reason": doc_item.reason,
                        "admin_diagnostic": doc_item.admin_diagnostic,
                        "system_error": doc_item.system_error,
                        "extracted_data": doc_item.extracted_data,
                        "file_name": doc_item.file_name,
                        "storage_url": doc_item.storage_url,
                        "updated_at": datetime.now(timezone.utc).isoformat()
                    }
                    try:
                        self.manager.client.table("document_audits").upsert(
                            audit_record,
                            on_conflict="institution_id,student_id,document_id"
                        ).execute()
                    except Exception as e_audit:
                        logger.warning(f"Aviso ao persistir documento '{doc_id}' em 'document_audits': {e_audit}")

                logger.info(f"[SUPABASE DB] Dossiê de '{dossier.student_name}' ({dossier.student_id}) sincronizado.")
                return True

            # 2. Via PostgREST REST API
            rest_url = f"{self.manager.url}/rest/v1/student_dossiers"
            headers = self.manager.get_auth_headers()
            headers["Prefer"] = "resolution=merge-duplicates,return=representation"
            resp = requests.post(rest_url, headers=headers, json=dossier_dict, timeout=10)

            if resp.status_code in (200, 201):
                logger.info(f"[SUPABASE REST] Dossiê '{dossier.student_id}' salvo via PostgREST.")
                return True
            else:
                logger.warning(f"Erro ao salvar dossiê via PostgREST (HTTP {resp.status_code}): {resp.text}")

        except Exception as e:
            logger.error(f"Erro na sincronização do dossiê com Supabase: {e}", exc_info=True)

        return False

    def get_dossier(self, institution_id: str, student_id: str) -> Optional[StudentDossier]:
        """Recupera o dossiê do estudante no Supabase."""
        if not self.is_active:
            return None

        clean_inst = str(institution_id).strip()
        clean_id = str(student_id).strip()

        try:
            # 1. Via supabase-py
            if self.manager.client:
                res = self.manager.client.table("student_dossiers") \
                    .select("*") \
                    .eq("institution_id", clean_inst) \
                    .eq("student_id", clean_id) \
                    .execute()

                rows = res.data if hasattr(res, "data") else []
                if rows:
                    return self._row_to_dossier(rows[0])

            # 2. Via PostgREST
            rest_url = f"{self.manager.url}/rest/v1/student_dossiers?institution_id=eq.{clean_inst}&student_id=eq.{clean_id}&select=*"
            headers = self.manager.get_auth_headers()
            resp = requests.get(rest_url, headers=headers, timeout=10)
            if resp.status_code == 200:
                rows = resp.json()
                if rows and isinstance(rows, list):
                    return self._row_to_dossier(rows[0])

        except Exception as e:
            logger.warning(f"Erro ao buscar dossiê no Supabase para '{student_id}': {e}")

        return None

    def list_dossiers(self, institution_id: str, status: Optional[str] = None) -> List[StudentDossier]:
        """Lista os dossiês cadastrados de uma instituição no Supabase."""
        if not self.is_active:
            return []

        clean_inst = str(institution_id).strip()
        dossiers = []

        try:
            if self.manager.client:
                query = self.manager.client.table("student_dossiers").select("*").eq("institution_id", clean_inst)
                if status:
                    query = query.eq("status", status)
                res = query.execute()
                for row in res.data or []:
                    d = self._row_to_dossier(row)
                    if d:
                        dossiers.append(d)
                return dossiers

            # Via REST
            rest_url = f"{self.manager.url}/rest/v1/student_dossiers?institution_id=eq.{clean_inst}"
            if status:
                rest_url += f"&status=eq.{status}"
            rest_url += "&select=*&order=updated_at.desc"
            headers = self.manager.get_auth_headers()
            resp = requests.get(rest_url, headers=headers, timeout=10)
            if resp.status_code == 200:
                for row in resp.json():
                    d = self._row_to_dossier(row)
                    if d:
                        dossiers.append(d)
        except Exception as e:
            logger.warning(f"Erro ao listar dossiês no Supabase: {e}")

        return dossiers

    def delete_dossier(self, institution_id: str, student_id: str) -> bool:
        """Exclui o registro do dossiê no Supabase."""
        if not self.is_active:
            return False

        clean_inst = str(institution_id).strip()
        clean_id = str(student_id).strip()

        try:
            if self.manager.client:
                self.manager.client.table("document_audits") \
                    .delete() \
                    .eq("institution_id", clean_inst) \
                    .eq("student_id", clean_id) \
                    .execute()

                self.manager.client.table("student_dossiers") \
                    .delete() \
                    .eq("institution_id", clean_inst) \
                    .eq("student_id", clean_id) \
                    .execute()
                return True

            # Via REST
            headers = self.manager.get_auth_headers()
            requests.delete(
                f"{self.manager.url}/rest/v1/document_audits?institution_id=eq.{clean_inst}&student_id=eq.{clean_id}",
                headers=headers, timeout=5
            )
            resp = requests.delete(
                f"{self.manager.url}/rest/v1/student_dossiers?institution_id=eq.{clean_inst}&student_id=eq.{clean_id}",
                headers=headers, timeout=5
            )
            return resp.status_code in (200, 204)
        except Exception as e:
            logger.error(f"Erro ao deletar dossiê no Supabase: {e}")
            return False

    def _row_to_dossier(self, row: Dict[str, Any]) -> Optional[StudentDossier]:
        """Converte uma linha da tabela do Supabase em instância de StudentDossier."""
        try:
            status_str = row.get("status", "PENDENTE")
            try:
                status_enum = DossierStatus(status_str)
            except Exception:
                status_enum = DossierStatus.PENDENTE

            docs_dict = {}
            raw_docs = row.get("documents_json") or {}
            for doc_k, item_data in raw_docs.items():
                if isinstance(item_data, dict):
                    docs_dict[doc_k] = DocumentAuditItem(**item_data)

            return StudentDossier(
                institution_id=row.get("institution_id", "imes"),
                student_id=row.get("student_id", ""),
                student_name=row.get("student_name", ""),
                course_name=row.get("course_name", "Geral"),
                cpf=row.get("cpf"),
                status=status_enum,
                documents=docs_dict
            )
        except Exception as e:
            logger.error(f"Erro ao deserializar dossiê do Supabase: {e}")
            return None


# Instância global singleton
supabase_dossier_repo = SupabaseDossierRepository()
