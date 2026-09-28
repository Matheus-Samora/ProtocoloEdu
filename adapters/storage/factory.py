"""
Fábrica de Provedores de Armazenamento (Storage Factory).
Instancia Google Drive, Cloud Storage Próprio (SaaS) ou Local de acordo com a instituição.
"""

import os
from typing import Optional, Any
from adapters.storage.base import StorageProvider
from adapters.storage.local_storage import LocalDiskStorageProvider
from adapters.storage.saas_cloud_adapter import SaaSCloudBucketStorageProvider
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

        # Suporte legado caso configurado expressamente como cloud
        if provider_type in ("cloud_storage", "s3", "saas"):
            bucket = getattr(storage_cfg, "root_folder_id", "protocolo-documentos-instituicoes") or "protocolo-documentos-instituicoes"
            return SaaSCloudBucketStorageProvider(bucket_name=bucket)

        # Se for explicitamente google_drive mas não houver credenciais, faz fallback gracioso para local
        if provider_type == "google_drive" and os.path.exists("credentials.json"):
            try:
                from adapters.storage.drive_adapter import GoogleDriveStorageAdapter
                return GoogleDriveStorageAdapter(topology=storage_cfg)
            except Exception:
                pass

        return LocalDiskStorageProvider(base_directory=base_dir, institution_id=inst_id)
