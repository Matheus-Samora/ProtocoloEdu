"""
Repositório de Persistência do Dossiê Central de Documentos.
Suporta Google Cloud Firestore (Produção) com fallback transparente para armazenamento local.
Garante o isolamento multi-tenant por 'institution_id'.
"""

import os
import re
import json
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone

from core_dossier_models import StudentDossier, DocumentAuditItem, DossierStatus
from adapters.database.supabase_dossier_repository import supabase_dossier_repo

logger = logging.getLogger("DOSSIER_REPOSITORY")

# Tenta carregar Firestore do Google Cloud
FIRESTORE_AVAILABLE = False
try:
    from google.cloud import firestore
    FIRESTORE_AVAILABLE = True
except ImportError:
    pass


class DossierRepository:
    """Gerenciador de leitura e gravação dos dossiês de alunos no banco de dados central (Supabase / Local)."""

    def __init__(self, local_storage_dir: str = "data_dossiers"):
        self.local_dir = os.path.abspath(local_storage_dir)
        os.makedirs(self.local_dir, exist_ok=True)
        self.db = None
        self.supabase = supabase_dossier_repo
        self._init_firestore()

    def _init_firestore(self):
        """Inicializa Firestore se houver credenciais ativas."""
        if FIRESTORE_AVAILABLE:
            try:
                # Conecta ao Firestore padrão da conta Google Cloud
                self.db = firestore.Client()
                logger.info("Repositório de Dossiês conectado com sucesso ao Google Cloud Firestore.")
            except Exception as e:
                logger.warning(f"Firestore não inicializado (usando persistência local): {e}")
                self.db = None

    def _get_local_file_path(self, institution_id: str, student_id: str) -> str:
        clean_inst = re.sub(r'[^a-zA-Z0-9_-]', '', str(institution_id)).strip() or "default"
        inst_dir = os.path.join(self.local_dir, clean_inst)
        os.makedirs(inst_dir, exist_ok=True)
        clean_id = re.sub(r'[^a-zA-Z0-9_-]', '', str(student_id)).strip() or "anon"
        return os.path.join(inst_dir, f"{clean_id}.json")

    def save_dossier(self, dossier: StudentDossier) -> bool:
        """Salva ou atualiza um dossiê no banco central (Supabase / Local)."""
        data = dossier.model_dump(mode='json')

        # 1. Tenta salvar no Supabase Database (PostgreSQL)
        if self.supabase.is_active:
            try:
                self.supabase.save_dossier(dossier)
            except Exception as e_sb:
                logger.warning(f"Aviso ao persistir dossiê no Supabase: {e_sb}")

        # 2. Tenta salvar no Firestore (se configurado)
        if self.db:
            try:
                collection_name = f"dossiers_{dossier.institution_id}"
                doc_ref = self.db.collection(collection_name).document(dossier.student_id)
                doc_ref.set(data, merge=True)
                logger.info(f"[FIRESTORE] Dossiê salvo para '{dossier.student_name}' na instituição '{dossier.institution_id}'.")
            except Exception as e:
                logger.error(f"Erro ao salvar no Firestore: {e}", exc_info=True)

        # 3. Persiste cópia local para redundância e desenvolvimento offline
        try:
            path = self._get_local_file_path(dossier.institution_id, dossier.student_id)
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            logger.error(f"Erro ao salvar dossiê em disco local: {e}")
            return False

    def get_dossier(self, institution_id: str, student_id: str) -> Optional[StudentDossier]:
        """Obtém o dossiê do estudante para a instituição especificada."""
        # 1. Tenta buscar no Supabase Database
        if self.supabase.is_active:
            try:
                sb_dossier = self.supabase.get_dossier(institution_id, student_id)
                if sb_dossier:
                    return sb_dossier
            except Exception as e_sb:
                logger.warning(f"Falha ao buscar no Supabase, tentando fallback: {e_sb}")

        # 2. Tenta buscar no Firestore
        if self.db:
            try:
                collection_name = f"dossiers_{institution_id}"
                doc = self.db.collection(collection_name).document(student_id).get()
                if doc.exists:
                    return StudentDossier(**doc.to_dict())
            except Exception as e:
                logger.warning(f"Falha ao buscar no Firestore, tentando armazenamento local: {e}")

        # 3. Busca local
        path = self._get_local_file_path(institution_id, student_id)
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return StudentDossier(**data)
            except Exception as e:
                logger.error(f"Erro ao ler dossiê local '{path}': {e}")

        return None

    def list_dossiers(
        self,
        institution_id: str,
        status: Optional[str] = None,
        course_name: Optional[str] = None
    ) -> List[StudentDossier]:
        """Lista todos os prontuários de uma instituição com filtros opcionais."""
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
                logger.warning(f"Falha ao listar no Supabase, tentando fallback: {e_sb}")

        # 2. Se Firestore estiver conectado
        if self.db:
            try:
                collection_name = f"dossiers_{institution_id}"
                query = self.db.collection(collection_name)
                if status:
                    query = query.where("status", "==", status)
                if course_name:
                    query = query.where("course_name", "==", course_name)

                for doc in query.stream():
                    dossiers.append(StudentDossier(**doc.to_dict()))
                return dossiers
            except Exception as e:
                logger.warning(f"Falha na listagem do Firestore: {e}. Usando cópia local.")

        # 2. Leitura local
        inst_dir = os.path.join(self.local_dir, institution_id)
        if not os.path.exists(inst_dir):
            return []

        for fname in os.listdir(inst_dir):
            if fname.endswith(".json"):
                try:
                    with open(os.path.join(inst_dir, fname), 'r', encoding='utf-8') as f:
                        d = StudentDossier(**json.load(f))
                        if status and d.status.value != status:
                            continue
                        if course_name and d.course_name != course_name:
                            continue
                        dossiers.append(d)
                except Exception:
                    continue

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
                logger.warning(f"Erro ao deletar dossiê no Supabase: {e_sb}")

        path = self._get_local_file_path(institution_id, student_id)
        if os.path.exists(path):
            try:
                os.remove(path)
                return True
            except Exception as e:
                logger.error(f"Erro ao remover arquivo local '{path}': {e}")
                return False
        return True


# Instância global singleton do repositório
dossier_repo = DossierRepository()
