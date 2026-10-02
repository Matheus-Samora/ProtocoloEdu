"""
Repositório de Persistência do Dossiê Central de Documentos.
Persistência local cifrada e Supabase opcional, configurado para esta instalação.
Garante o isolamento multi-tenant por 'institution_id'.
"""

import os
import re
import json
import logging
from security.storage import production, component, contained, write_record, read_record
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone

from core_dossier_models import StudentDossier, DocumentAuditItem, DossierStatus
from adapters.database.supabase_dossier_repository import supabase_dossier_repo

logger = logging.getLogger("DOSSIER_REPOSITORY")

class DossierRepository:
    """Gerenciador de leitura e gravação dos dossiês de alunos no banco de dados central (Supabase / Local)."""

    def __init__(self, local_storage_dir: str = "data_dossiers"):
        self.local_dir = os.path.abspath(local_storage_dir)
        os.makedirs(self.local_dir, exist_ok=True)
        self.supabase = supabase_dossier_repo

    def _get_local_file_path(self, institution_id: str, student_id: str) -> str:
        tenant, student = component(institution_id), component(student_id)
        path = contained(self.local_dir, tenant, student + '.json')
        path.parent.mkdir(parents=True, exist_ok=True)
        return str(path)

    def save_dossier(self, dossier: StudentDossier) -> bool:
        """Salva ou atualiza um dossiê no banco central (Supabase / Local)."""
        component(dossier.institution_id);component(dossier.student_id)
        data = dossier.model_dump(mode='json')

        # 1. Tenta salvar no Supabase Database (PostgreSQL)
        if self.supabase.is_active:
            try:
                self.supabase.save_dossier(dossier)
            except Exception as e_sb:
                logger.warning("Operation failed; inspect restricted security events")

        # 3. Persiste cópia local para redundância e desenvolvimento offline
        try:
            path = self._get_local_file_path(dossier.institution_id, dossier.student_id)
            write_record(path, data, dossier.institution_id, dossier.student_id)
            return True
        except Exception as e:
            logger.error("Operation failed; inspect restricted security events")
            return False

    def get_or_create_dossier(self, institution_id, student_id, student_name, course_name, cpf=None):
        dossier = self.get_dossier(institution_id, student_id)
        if dossier is None:
            dossier = StudentDossier(institution_id=institution_id, student_id=student_id, student_name=student_name, course_name=course_name, cpf=cpf or None)
        else:
            dossier.student_name = student_name
            dossier.course_name = course_name
            dossier.cpf = cpf or dossier.cpf
        if not self.save_dossier(dossier): raise IOError("Cadastro não persistido.")
        return dossier

    def get_dossier(self, institution_id: str, student_id: str) -> Optional[StudentDossier]:
        """Obtém o dossiê do estudante para a instituição especificada."""
        component(institution_id);component(student_id)
        # 1. Tenta buscar no Supabase Database
        if self.supabase.is_active:
            try:
                sb_dossier = self.supabase.get_dossier(institution_id, student_id)
                if sb_dossier:
                    return sb_dossier
            except Exception as e_sb:
                logger.warning("Operation failed; inspect restricted security events")

        # 3. Busca local
        path = self._get_local_file_path(institution_id, student_id)
        if os.path.exists(path):
            try:
                return StudentDossier(**read_record(path, institution_id, student_id))
            except Exception as e:
                logger.error("Operation failed; inspect restricted security events")

        return None

    def list_dossiers(
        self,
        institution_id: str,
        status: Optional[str] = None,
        course_name: Optional[str] = None
    ) -> List[StudentDossier]:
        """Lista todos os prontuários de uma instituição com filtros opcionais."""
        component(institution_id)
        dossiers = []

        # 1. Se Supabase estiver conectado
        if self.supabase.is_active:
            try:
                sb_list = self.supabase.list_dossiers(institution_id, status=status)
                if sb_list:
                    if course_name:
                        return [d for d in sb_list if d.course_name == course_name]
                    return sb_list
            except Exception as e_sb:
                logger.warning("Operation failed; inspect restricted security events")

        # 2. Leitura local
        inst_dir = str(contained(self.local_dir, component(institution_id)))
        if not os.path.exists(inst_dir):
            return []

        for fname in os.listdir(inst_dir):
            if fname.endswith(".json"):
                try:
                    path = contained(self.local_dir, component(institution_id), fname)
                    d = StudentDossier(**read_record(path, institution_id, fname[:-5]))
                    if status and d.status.value != status:
                        continue
                    if course_name and d.course_name != course_name:
                        continue
                    dossiers.append(d)
                except Exception:
                    logger.warning("Dossier record unavailable: integrity or read failure")
                    if production():raise ValueError("Dossier integrity failure")

        return dossiers

    def mark_as_exported(self, institution_id: str, student_ids: List[str]) -> int:
        """Marca os dossiês como exportados com timestamp."""
        now = datetime.now(timezone.utc)
        count = 0
        for sid in student_ids:
            dossier = self.get_dossier(institution_id, sid)
            if dossier:
                dossier.exported_at = now
                self.save_dossier(dossier)
                count += 1
        return count

    def delete_dossier(self, institution_id: str, student_id: str) -> bool:
        """Exclui o registro do dossiê no banco central e local."""
        if self.supabase.is_active:
            try:
                self.supabase.delete_dossier(institution_id, student_id)
            except Exception as e_sb:
                logger.warning("Operation failed; inspect restricted security events")

        path = self._get_local_file_path(institution_id, student_id)
        if os.path.exists(path):
            try:
                os.remove(path)
                return True
            except Exception as e:
                logger.error("Operation failed; inspect restricted security events")
                return False
        return True


# Instância global singleton do repositório
dossier_repo = DossierRepository()
