# -*- coding: utf-8 -*-
"""
Provedor de Armazenamento em Nuvem no Supabase Storage (SupabaseStorageProvider).
Permite salvar e gerenciar arquivos e prontuários acadêmicos dos alunos diretamente
nos buckets do Supabase, com suporte a particionamento institucional A-Z, expurgo de recusados
e geração de URLs autenticadas.
"""

import os
import re
import logging
from typing import Optional, List, Dict, Any
import requests

from adapters.storage.base import StorageProvider, StoredFileInfo
from adapters.storage.local_storage import LocalDiskStorageProvider, normalize_initial_letter
from adapters.supabase_client import supabase_manager
from media.models import ProcessedMedia
from core_criteria_models import DocumentSpecification

logger = logging.getLogger("SUPABASE_STORAGE")


class SupabaseStorageProvider(StorageProvider):
    """
    Provedor de armazenamento integrado ao Supabase Storage.
    Garante custódia em nuvem com fallback transparente para disco local caso não configurado.
    """

    def __init__(
        self,
        bucket_name: str = "documentos-alunos",
        institution_id: str = "imes",
        fallback_local_dir: str = "storage"
    ):
        self.bucket_name = bucket_name
        self.institution_id = institution_id.lower().strip()
        self.manager = supabase_manager
        self.fallback_local = LocalDiskStorageProvider(base_directory=fallback_local_dir, institution_id=self.institution_id)

    def _build_storage_path(self, student_name: str, filename: str) -> str:
        """Constrói o caminho canônico do arquivo no bucket do Supabase."""
        letter = normalize_initial_letter(student_name)
        clean_name = re.sub(r'[/\\?%*:|"<>.]', '_', str(student_name)).strip()
        safe_filename = os.path.basename(filename)
        return f"{self.institution_id}/{letter}/{clean_name}/DOC/{safe_filename}"

    def store_document(
        self,
        student_name: str,
        spec: DocumentSpecification,
        media: ProcessedMedia,
        suffix: str = ""
    ) -> Optional[StoredFileInfo]:
        """
        Armazena um documento no Supabase Storage.
        Se a conexão não estiver ativa, salva no armazenamento local particionado como contingência.
        """
        # Monta nome oficial do arquivo padronizado
        clean_student = str(student_name).strip()
        ext = media.extension if media.extension.startswith('.') else f".{media.extension}"
        doc_label = spec.id.upper()
        if spec.target_filename_pattern and "{NOME_ALUNO}" in spec.target_filename_pattern:
            base_target = spec.target_filename_pattern.replace("{NOME_ALUNO}", clean_student).replace("{EXT}", "")
            final_filename = f"{base_target}{suffix}{ext}"
        else:
            final_filename = f"{clean_student} - {doc_label}{suffix}{ext}"

        safe_filename = re.sub(r'[/\\?%*:|"<> ]+', ' ', final_filename).strip()

        # Verifica se o Supabase está configurado com chave válida
        if not self.manager.is_configured:
            logger.info(f"Supabase não configurado. Salvando '{safe_filename}' no armazenamento local de contingência.")
            stored = self.fallback_local.store_document(student_name, spec, media, suffix=suffix)
            return stored

        storage_path = self._build_storage_path(student_name, safe_filename)

        try:
            # 1. Tenta usar o cliente oficial supabase-py se disponível
            if self.manager.client:
                # Garante bucket
                try:
                    self.manager.ensure_bucket_exists(self.bucket_name)
                except Exception:
                    pass

                storage_client = self.manager.client.storage.from_(self.bucket_name)
                res = storage_client.upload(
                    path=storage_path,
                    file=media.content_bytes,
                    file_options={"content-type": media.mime_type, "upsert": "true"}
                )

                storage_url = f"supabase://{self.bucket_name}/{storage_path}"

                logger.info(f"[SUPABASE STORAGE] Arquivo '{safe_filename}' enviado com sucesso para '{storage_path}'")
                return StoredFileInfo(
                    file_id=storage_path,
                    filename=safe_filename,
                    storage_url=storage_url,
                    provider="supabase",
                    size_bytes=len(media.content_bytes)
                )

            # 2. Fallback para chamada REST direta do Supabase Storage API
            upload_url = f"{self.manager.url}/storage/v1/object/{self.bucket_name}/{storage_path}"
            headers = {
                "apikey": self.manager.key,
                "Authorization": f"Bearer {self.manager.key}",
                "Content-Type": media.mime_type,
                "x-upsert": "true"
            }
            resp = requests.post(upload_url, headers=headers, data=media.content_bytes, timeout=15)

            if resp.status_code in (200, 201):
                storage_url = f"{self.manager.url}/storage/v1/object/authenticated/{self.bucket_name}/{storage_path}"
                logger.info(f"[SUPABASE REST] Arquivo gravado via REST: '{storage_path}'")
                return StoredFileInfo(
                    file_id=storage_path,
                    filename=safe_filename,
                    storage_url=storage_url,
                    provider="supabase",
                    size_bytes=len(media.content_bytes)
                )
            else:
                logger.warning(f"Falha ao enviar arquivo via REST para o Supabase (HTTP {resp.status_code}): {resp.text}")

        except Exception as e:
            logger.error(f"Erro ao salvar arquivo no Supabase Storage: {e}. Usando contingência local.", exc_info=True)

        # Fallback gracioso para local
        return self.fallback_local.store_document(student_name, spec, media, suffix=suffix)

    def list_student_documents(self, student_name: str) -> List[str]:
        """Lista os arquivos arquivados para o estudante no Supabase Storage."""
        if not self.manager.is_configured:
            return self.fallback_local.list_student_documents(student_name)

        letter = normalize_initial_letter(student_name)
        clean_name = re.sub(r'[/\\?%*:|"<>.]', '_', str(student_name)).strip()
        prefix = f"{self.institution_id}/{letter}/{clean_name}/DOC"

        try:
            if self.manager.client:
                files = self.manager.client.storage.from_(self.bucket_name).list(prefix)
                return [f.get("name") for f in files if isinstance(f, dict) and f.get("name")]

            # Via REST
            list_url = f"{self.manager.url}/storage/v1/object/list/{self.bucket_name}"
            headers = self.manager.get_auth_headers()
            payload = {"prefix": prefix, "limit": 100}
            resp = requests.post(list_url, headers=headers, json=payload, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                return [item.get("name") for item in data if isinstance(item, dict) and item.get("name")]
        except Exception as e:
            logger.warning(f"Erro ao listar documentos no Supabase Storage para '{student_name}': {e}")

        return self.fallback_local.list_student_documents(student_name)

    def delete_document(self, student_name: str, filename: str) -> bool:
        """
        Exclui fisicamente o arquivo do bucket do Supabase.
        Essencial para o Guardião de Custódia quando um documento for rejeitado ou substituído.
        """
        storage_path = self._build_storage_path(student_name, filename)

        # Remove localmente se existir versão local
        self.fallback_local.delete_document(student_name, filename)

        if not self.manager.is_configured:
            return True

        try:
            if self.manager.client:
                self.manager.client.storage.from_(self.bucket_name).remove([storage_path])
                logger.info(f"[SUPABASE PURGE] Arquivo '{storage_path}' expurgado do Supabase com sucesso.")
                return True

            del_url = f"{self.manager.url}/storage/v1/object/{self.bucket_name}"
            headers = self.manager.get_auth_headers()
            resp = requests.delete(del_url, headers=headers, json={"prefixes": [storage_path]}, timeout=10)
            return resp.status_code == 200
        except Exception as e:
            logger.error(f"Erro ao excluir documento do Supabase: {e}")
            return False

    def get_file_bytes(self, student_name: str, filename: str) -> Optional[bytes]:
        """Recupera os bytes do arquivo para geração de pacotes ZIP de exportação."""
        storage_path = self._build_storage_path(student_name, filename)

        if self.manager.is_configured:
            try:
                if self.manager.client:
                    data = self.manager.client.storage.from_(self.bucket_name).download(storage_path)
                    if data:
                        return data

                # Via REST
                down_url = f"{self.manager.url}/storage/v1/object/authenticated/{self.bucket_name}/{storage_path}"
                headers = self.manager.get_auth_headers()
                resp = requests.get(down_url, headers=headers, timeout=15)
                if resp.status_code == 200:
                    return resp.content
            except Exception as e:
                logger.warning(f"Falha ao baixar '{storage_path}' do Supabase: {e}")

        # Tenta no fallback local
        return self.fallback_local.get_file_bytes(student_name, filename)
