"""
Adaptador de Armazenamento para Google Drive da Instituição (BYOS - Bring Your Own Storage).
Utiliza a conta de serviço do Google Drive para upload e listagem de pastas do aluno.
"""

import os
import re
import logging
import unicodedata
from typing import Optional, List, Dict, Any, Tuple

from adapters.storage.base import StorageProvider, StoredFileInfo
from media.models import ProcessedMedia
from core_criteria_models import DocumentSpecification
from core_institution_models import StorageTopology

logger = logging.getLogger("DRIVE_STORAGE_ADAPTER")


def sanitize_name_for_drive(text: str) -> str:
    """Normaliza o nome do aluno para padrão maiúsculo e sem acentos."""
    if not text:
        return ""
    nfkd = unicodedata.normalize('NFKD', str(text).upper())
    only_ascii = nfkd.encode('ASCII', 'ignore').decode('utf-8')
    return re.sub(r'[^A-Z0-9\s-]', '', only_ascii).strip()


class GoogleDriveStorageAdapter(StorageProvider):
    """
    Provedor de armazenamento que envia arquivos diretamente para o Google Drive da instituição.
    """

    def __init__(self, topology: StorageTopology, credentials_file: str = "credentials.json"):
        self.topology = topology
        self.credentials_file = credentials_file
        self.drive_handler = None
        self._init_drive_handler()

    def _init_drive_handler(self):
        """Inicializa o manipulador do Google Drive com fallback gracioso."""
        try:
            from drive_handler import DriveHandler
            if os.path.exists(self.credentials_file):
                self.drive_handler = DriveHandler()
            else:
                logger.warning(f"Arquivo de credenciais do Drive '{self.credentials_file}' não encontrado.")
        except Exception as e:
            logger.error(f"Não foi possível inicializar o DriveHandler: {e}")

    def _resolve_partition(self, student_name: str) -> Tuple[Optional[str], Optional[str]]:
        """Resolve qual pasta raiz utilizar com base na regra de partição da instituição."""
        first_letter = student_name.strip().upper()[0] if student_name else "A"
        partitions = self.topology.partitions
        
        if self.topology.partitioning_mode == "ALPHABETICAL_SPLIT":
            target_key = "A-M" if 'A' <= first_letter <= 'M' else "N-Z"
            folder_id = partitions.get(target_key, self.topology.root_folder_id)
            return self.topology.drive_id, folder_id

        return self.topology.drive_id, self.topology.root_folder_id

    def list_student_documents(self, student_name: str) -> List[str]:
        if not self.drive_handler or not self.drive_handler.is_ready():
            return []
        try:
            drive_id, base_folder = self._resolve_partition(student_name)
            folders = self.drive_handler.find_folders_containing_name(student_name, drive_id)
            if not folders:
                return []
            student_folder_id = folders[0].get("id")
            items = self.drive_handler.list_all_items_in_folder(student_folder_id, drive_id)
            return [it.get("name") for it in (items or []) if it.get("mimeType") != "application/vnd.google-apps.folder"]
        except Exception as e:
            logger.error(f"Erro ao listar documentos no Drive: {e}")
            return []

    def store_document(
        self,
        student_name: str,
        spec: DocumentSpecification,
        media: ProcessedMedia,
        suffix: str = ""
    ) -> Optional[StoredFileInfo]:
        clean_student = sanitize_name_for_drive(student_name)
        target_name = spec.target_filename_pattern.format(
            aluno_nome=clean_student,
            sufixo_pagina=suffix,
            ext=media.extension,
            tipo_certidao_especifico="CERTIDAO"
        )

        if not self.drive_handler or not self.drive_handler.is_ready():
            logger.warning("[DRIVE MOCK] Credenciais ausentes. Simulando gravação com sucesso.")
            return StoredFileInfo(
                file_id=f"mock_drive_{spec.id}",
                filename=target_name,
                storage_url=f"https://drive.google.com/open?id=mock_{spec.id}",
                provider="google_drive",
                size_bytes=len(media.content_bytes)
            )

        try:
            drive_id, base_folder = self._resolve_partition(clean_student)
            
            # Localiza ou cria pasta do aluno
            student_folder_id = self.drive_handler.find_or_create_folder(
                clean_student,
                parent_id=base_folder,
                drive_id=drive_id
            )
            
            # Localiza ou cria subpasta DOC
            doc_folder_id = self.drive_handler.find_or_create_folder(
                spec.target_drive_folder,
                parent_id=student_folder_id,
                drive_id=drive_id
            )

            file_id = self.drive_handler.upload_file(
                folder_id=doc_folder_id,
                filename=target_name,
                file_content_bytes=media.content_bytes,
                mime_type=media.mime_type
            )

            if not file_id:
                return None

            return StoredFileInfo(
                file_id=file_id,
                filename=target_name,
                storage_url=f"https://drive.google.com/open?id={file_id}",
                provider="google_drive",
                size_bytes=len(media.content_bytes)
            )
        except Exception as e:
            logger.error(f"Erro ao fazer upload no Google Drive: {e}", exc_info=True)
            return None
