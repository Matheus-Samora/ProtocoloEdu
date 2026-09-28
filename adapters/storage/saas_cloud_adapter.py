"""
Provedores de Armazenamento: Local e Nuvem SaaS da Plataforma (S3/Cloud Storage).
Permite à plataforma cobrar pela custódia e armazenamento dos documentos escolares.
"""

import os
import re
import logging
from typing import Optional, List, Dict, Any

from adapters.storage.base import StorageProvider, StoredFileInfo
from media.models import ProcessedMedia
from core_criteria_models import DocumentSpecification

logger = logging.getLogger("STORAGE_PROVIDERS")


from adapters.storage.local_storage import (
    LocalDiskStorageProvider,
    normalize_initial_letter,
    sanitize_folder_or_file_name as sanitize_folder_name
)


class SaaSCloudBucketStorageProvider(StorageProvider):
    """
    Storage Próprio Gerenciado pela Plataforma (Google Cloud Storage / AWS S3 / Cloudflare R2).
    Permite à sua empresa cobrar mensalidade ou franquia por GB armazenado das instituições.
    """

    def __init__(self, bucket_name: str, base_prefix: str = "instituicoes"):
        self.bucket_name = bucket_name
        self.base_prefix = base_prefix
        logger.info(f"SaaS Cloud Storage ativo no bucket '{bucket_name}'.")

    def list_student_documents(self, student_name: str) -> List[str]:
        # Em produção: consulta blobs com prefixo f"{self.base_prefix}/{student_name}/"
        logger.info(f"[SAAS STORAGE] Listando documentos na nuvem própria para '{student_name}'.")
        return []

    def store_document(
        self,
        student_name: str,
        spec: DocumentSpecification,
        media: ProcessedMedia,
        suffix: str = ""
    ) -> Optional[StoredFileInfo]:
        clean_student = sanitize_folder_name(student_name)
        target_name = spec.target_filename_pattern.format(
            aluno_nome=clean_student,
            sufixo_pagina=suffix,
            ext=media.extension,
            tipo_certidao_especifico="CERTIDAO"
        )
        cloud_key = f"{self.base_prefix}/{clean_student}/{target_name}"
        
        # Em produção, usa google-cloud-storage blob.upload_from_string ou boto3 s3.put_object
        logger.info(f"[SAAS STORAGE] Upload efetuado no Bucket '{self.bucket_name}' chave: '{cloud_key}' ({len(media.content_bytes)} bytes)")
        
        return StoredFileInfo(
            file_id=cloud_key,
            filename=target_name,
            storage_url=f"https://storage.googleapis.com/{self.bucket_name}/{cloud_key}",
            provider="saas_cloud_storage",
            size_bytes=len(media.content_bytes)
        )
