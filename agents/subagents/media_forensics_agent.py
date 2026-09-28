# -*- coding: utf-8 -*-
"""
Subagente Especialista 1: Agente Pericial de Mídia & Anti-Tampering (MediaForensicsAgent).
Responsável pela validação de formato real (magic bytes), rotação automática EXIF,
conversão de contêineres Apple HEIC/HEIF, detecção de desfoque/baixa resolução e compressão otimizada.
"""

from typing import Dict, Any, List
from agents.base_agent import BaseSubagent
from agents.models import SubagentRole, AgentTask
from media.pipeline import MediaPipeline
from media.models import ProcessedMedia
from core_criteria_models import DocumentSpecification


class MediaForensicsAgent(BaseSubagent):
    """Subagente responsável pelo saneamento visual e perícia prévia de arquivos enviados."""

    def __init__(self, media_pipeline: MediaPipeline = None):
        super().__init__(
            role=SubagentRole.MEDIA_FORENSICS,
            name="Agente Pericial de Mídia & Anti-Tampering",
            description="Executa perícia visual, rotação EXIF, conversão HEIC, checagem de resolução e otimização para IA."
        )
        self.pipeline = media_pipeline or MediaPipeline()

    def _run(self, task: AgentTask) -> Dict[str, Any]:
        raw_files = task.payload.get("raw_files", [])
        spec = task.payload.get("spec")
        doc_key = task.payload.get("doc_key", "DOC")

        if not raw_files:
            raise ValueError(f"Nenhum arquivo fornecido para o subagente {self.name}.")

        sanitized_media_list: List[ProcessedMedia] = []
        forensic_flags = []
        total_original_bytes = 0
        total_sanitized_bytes = 0

        for file_info in raw_files:
            file_bytes = file_info.get("content")
            raw_filename = file_info.get("filename", "upload.jpg")
            total_original_bytes += len(file_bytes) if file_bytes else 0

            # Executa o pipeline de mídia de alto desempenho
            processed = self.pipeline.process(
                file_bytes=file_bytes,
                original_filename=raw_filename,
                spec=spec
            )
            sanitized_media_list.append(processed)
            total_sanitized_bytes += processed.size_bytes

            # Análise pericial de metadados
            if processed.is_pdf and processed.is_encrypted:
                forensic_flags.append(f"Arquivo '{raw_filename}' é um PDF com proteção por senha.")

            if processed.metadata.get("is_heic_converted"):
                forensic_flags.append(f"Contêiner Apple HEIC convertido com sucesso para JPEG de alta nitidez.")

            if processed.metadata.get("exif_rotated"):
                forensic_flags.append(f"Orientação de câmera corrigida automaticamente via metadados EXIF.")

            # Checagem de resolução mínima para OCR
            dims = processed.metadata.get("dimensions")
            if dims and (dims[0] < 400 or dims[1] < 400):
                forensic_flags.append(f"Atenção: Dimensões reduzidas ({dims[0]}x{dims[1]}px) podem afetar a legibilidade.")

        compression_ratio = round((1.0 - (total_sanitized_bytes / max(total_original_bytes, 1))) * 100, 1)

        return {
            "success": True,
            "doc_key": doc_key,
            "processed_count": len(sanitized_media_list),
            "sanitized_media_list": sanitized_media_list,
            "forensic_flags": forensic_flags,
            "original_bytes": total_original_bytes,
            "sanitized_bytes": total_sanitized_bytes,
            "compression_ratio_pct": compression_ratio,
            "summary": f"{len(sanitized_media_list)} mídia(s) periciada(s) e otimizada(s) ({compression_ratio}% de compressão)."
        }
