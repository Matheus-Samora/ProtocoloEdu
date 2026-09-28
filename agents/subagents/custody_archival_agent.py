# -*- coding: utf-8 -*-
"""
Subagente Especialista 5: Agente Guardião de Custódia & Arquivo A-Z (CustodyArchivalAgent).
Implementa a governança de armazenamento local em disco:
Apenas documentos 100% aprovados e autenticados são gravados em disco.
Documentos rejeitados são barrados e têm quaisquer versões legadas expurgadas imediatamente.
Calcula e anexa o hash criptográfico SHA-256 de cada documento para a trilha de auditoria do MEC.
"""

import os
import hashlib
from typing import Dict, Any, List, Optional
from agents.base_agent import BaseSubagent
from agents.models import SubagentRole, AgentTask
from adapters.storage.factory import StorageFactory
from adapters.storage.local_storage import LocalDiskStorageProvider
from core_institution_models import InstitutionProfile
from core_criteria_models import DocumentSpecification
from media.models import ProcessedMedia


class CustodyArchivalAgent(BaseSubagent):
    """Subagente responsável pela integridade física do acervo documental no disco do servidor."""

    def __init__(self):
        super().__init__(
            role=SubagentRole.CUSTODY_ARCHIVAL,
            name="Agente Guardião de Custódia & Arquivo A-Z",
            description="Custodia no repositório A-Z estritamente arquivos válidos e homologados, com hash SHA-256 e expurgo de rejeitados."
        )

    def _run(self, task: AgentTask) -> Dict[str, Any]:
        institution_profile: Optional[InstitutionProfile] = task.payload.get("institution_profile")
        student_name: str = task.payload.get("student_name", "")
        spec: DocumentSpecification = task.payload.get("spec")
        media_list: List[ProcessedMedia] = task.payload.get("sanitized_media_list") or task.payload.get("media_list", [])
        is_globally_approved: bool = task.payload.get("is_globally_approved", False)
        doc_key: str = task.payload.get("doc_key", "DOC")
        legacy_file_name: Optional[str] = task.payload.get("legacy_file_name")

        storage_provider = StorageFactory.get_provider(institution_profile) if institution_profile else LocalDiskStorageProvider()

        # GUARDIÃO DE CUSTÓDIA: Se o documento NÃO foi aprovado por todas as etapas periciais
        if not is_globally_approved:
            # Expurgar qualquer arquivo que possa ter sido salvo anteriormente para este documento
            if legacy_file_name and hasattr(storage_provider, "delete_document"):
                storage_provider.delete_document(student_name, legacy_file_name)

            self.logger.warning(
                f"[CUSTÓDIA BLOQUEADA]: Documento '{doc_key}' para '{student_name}' REPROVADO. "
                f"Gravação em disco barrada com sucesso."
            )
            return {
                "success": True,
                "gatekeeper_action": "BLOCKED_AND_PURGED",
                "stored_file_name": None,
                "storage_url": None,
                "sha256_hash": None,
                "file_size_bytes": 0,
                "summary": f"Guardião de Custódia: Documento '{doc_key}' recusado. Arquivo descartado da custódia oficial."
            }

        # SE FOI APROVADO: Grava no disco particionado com política de nomes institucional
        stored_file_name = None
        storage_url = None
        sha256_hash = None
        total_size = 0

        for i, media in enumerate(media_list):
            suffix = ""
            if len(media_list) > 1:
                suffix = " FRENTE" if i == 0 else " VERSO" if i == 1 else f" PAG {i+1}"

            stored_info = storage_provider.store_document(
                student_name=student_name,
                spec=spec,
                media=media,
                suffix=suffix
            )
            if stored_info:
                stored_file_name = stored_info.filename
                storage_url = stored_info.storage_url
                total_size += len(media.content_bytes)

                # Cálculo de Hash SHA-256 para o Acervo Acadêmico Digital (RDC-Arq / MEC)
                h = hashlib.sha256()
                h.update(media.content_bytes)
                sha256_hash = f"sha256:{h.hexdigest()}"

        return {
            "success": True,
            "gatekeeper_action": "SAVED_AND_AUTHENTICATED",
            "stored_file_name": stored_file_name,
            "storage_url": storage_url,
            "sha256_hash": sha256_hash,
            "file_size_bytes": total_size,
            "summary": f"Guardião de Custódia: '{stored_file_name}' gravado na pasta A-Z com hash {sha256_hash[:16]}..."
        }
