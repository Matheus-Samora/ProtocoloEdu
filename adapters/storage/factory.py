"""
Fábrica de Provedores de Armazenamento (Storage Factory).
Instancia armazenamento local ou Supabase explicitamente configurado.
"""

import os
from typing import Optional, Any
from adapters.storage.base import StorageProvider
from adapters.storage.local_storage import LocalDiskStorageProvider
from core_institution_models import InstitutionProfile


class StorageFactory:
    """Entrega a instância de Storage configurada para a instituição, priorizando o armazenamento local A-Z ou Supabase."""

    @staticmethod
    def get_provider(institution_or_type: Any, institution_id: Optional[str] = None) -> StorageProvider:
        # Se for string direta, ex: "supabase" ou "local"
        if isinstance(institution_or_type, str):
            provider_type = institution_or_type.lower()
            inst_id = institution_id or "imes"
            base_dir = "storage"
            if provider_type in ("supabase", "supabase_storage"):
                from adapters.storage.supabase_storage import SupabaseStorageProvider
                return SupabaseStorageProvider(bucket_name="documentos-alunos", institution_id=inst_id)
            if provider_type != "local":raise ValueError("Configure local ou supabase")
            return LocalDiskStorageProvider(base_directory=base_dir, institution_id=inst_id)

        institution = institution_or_type
        storage_cfg = getattr(institution, "storage", None)
        inst_id = institution.id if institution and hasattr(institution, "id") else (institution_id or "imes")
        provider_type = (getattr(storage_cfg, "provider", None) or "local").lower()
        base_dir = getattr(storage_cfg, "base_path", "storage") or "storage"

        # Padrão ou Local: Armazenamento em disco com divisão A-Z, pastas por aluno, 'DOC' e 'Outros Docs'
        if provider_type == "local":
            return LocalDiskStorageProvider(base_directory=base_dir, institution_id=inst_id)

        # Supabase Storage (Nuvem com buckets gerenciados)
        if provider_type in ("supabase", "supabase_storage"):
            from adapters.storage.supabase_storage import SupabaseStorageProvider
            bucket = getattr(storage_cfg, "root_folder_id", "documentos-alunos") or "documentos-alunos"
            return SupabaseStorageProvider(bucket_name=bucket, institution_id=inst_id)

        raise ValueError("Provedor descontinuado nesta versão independente; configure local ou supabase")
