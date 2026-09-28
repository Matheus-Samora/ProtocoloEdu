"""
Orquestrador do Pipeline de Mídia e Documentos (Media Pipeline).
Ponto de entrada unificado para recepção, validação, sanitização e preparação de uploads.
"""

import os
import re
import unicodedata
import logging
from typing import Optional, List, Dict, Any, Tuple

from media.models import ProcessedMedia, MediaType, MediaValidationResult
from media.sanitizer import ImageSanitizer
from media.pdf_handler import PDFHandler
from core_criteria_models import DocumentSpecification

logger = logging.getLogger("MEDIA_PIPELINE")

# Configurações padrão de governança de arquivos
DEFAULT_MAX_FILE_SIZE_BYTES = 35 * 1024 * 1024  # 35 MB
DEFAULT_ALLOWED_EXTENSIONS = [".pdf", ".jpg", ".jpeg", ".png", ".heic", ".heif", ".webp"]


def sanitize_filename(filename: str) -> str:
    """Remove caracteres perigosos e normaliza o nome do arquivo."""
    if not filename:
        return "arquivo_sem_nome"
    # Normaliza unicode
    nfkd = unicodedata.normalize('NFKD', filename)
    clean_name = nfkd.encode('ASCII', 'ignore').decode('utf-8')
    # Substitui caracteres especiais por underscore
    clean_name = re.sub(r'[^a-zA-Z0-9\._-]', '_', clean_name)
    return clean_name.strip('_')


class MediaPipeline:
    """Pipeline profissional de recepção e preparação de arquivos para auditoria."""

    def __init__(
        self,
        max_file_size_bytes: int = DEFAULT_MAX_FILE_SIZE_BYTES,
        allowed_extensions: Optional[List[str]] = None
    ):
        self.max_file_size_bytes = max_file_size_bytes
        self.allowed_extensions = allowed_extensions or DEFAULT_ALLOWED_EXTENSIONS

    def validate_file(
        self,
        file_bytes: bytes,
        filename: str,
        spec: Optional[DocumentSpecification] = None
    ) -> MediaValidationResult:
        """Executa validação prévia de segurança, tamanho e extensão."""
        if not file_bytes or len(file_bytes) == 0:
            return MediaValidationResult(
                is_valid=False,
                error_message="O arquivo enviado está vazio (0 bytes)."
            )

        if len(file_bytes) > self.max_file_size_bytes:
            max_mb = self.max_file_size_bytes / (1024 * 1024)
            return MediaValidationResult(
                is_valid=False,
                error_message=f"O arquivo excede o limite máximo permitido de {max_mb:.0f}MB."
            )

        _, ext = os.path.splitext(filename.lower())
        
        # Extensões aceitas para o documento específico ou padrão geral
        allowed_exts = spec.allowed_extensions if spec else self.allowed_extensions
        if ext not in [e.lower() for e in allowed_exts]:
            return MediaValidationResult(
                is_valid=False,
                error_message=f"Formato de arquivo '{ext}' não permitido. Extensões aceitas: {', '.join(allowed_exts)}."
            )

        # Validação estrita de Magic Bytes / Assinatura Binária (Prevenção de MIME Spoofing)
        if not self._verify_magic_bytes(file_bytes, ext, filename):
            return MediaValidationResult(
                is_valid=False,
                error_message=f"Conteúdo binário do arquivo inválido ou incompatível com a extensão '{ext}'."
            )

        return MediaValidationResult(is_valid=True)

    @staticmethod
    def _verify_magic_bytes(file_bytes: bytes, ext: str, filename: str) -> bool:
        """Verifica a integridade da assinatura binária (magic bytes) do cabeçalho."""
        if len(file_bytes) < 4:
            return False

        if ext == ".pdf":
            return PDFHandler.is_pdf(file_bytes, filename)
        elif ext in (".jpg", ".jpeg"):
            return file_bytes.startswith(b'\xff\xd8\xff')
        elif ext == ".png":
            return file_bytes.startswith(b'\x89PNG\r\n\x1a\n')
        elif ext in (".heic", ".heif"):
            return ImageSanitizer.is_heic(file_bytes[:16], filename)
        elif ext == ".webp":
            return file_bytes.startswith(b'RIFF') and (len(file_bytes) >= 12 and file_bytes[8:12] == b'WEBP')

        return True

    def process(
        self,
        file_bytes: bytes,
        original_filename: str,
        spec: Optional[DocumentSpecification] = None
    ) -> ProcessedMedia:
        """
        Recebe os bytes brutos do arquivo, valida, sanitiza e retorna o objeto ProcessedMedia pronto.
        """
        val_result = self.validate_file(file_bytes, original_filename, spec)
        if not val_result.is_valid:
            raise ValueError(val_result.error_message)

        safe_filename = sanitize_filename(original_filename)
        _, ext = os.path.splitext(original_filename.lower())

        # 1. Fluxo de Tratamento de PDF
        if PDFHandler.is_pdf(file_bytes, original_filename):
            pdf_info = PDFHandler.inspect_pdf(file_bytes)
            if not pdf_info.get("is_valid_pdf", True):
                raise ValueError("O arquivo possui extensão .pdf mas sua estrutura interna está corrompida.")

            if pdf_info.get("is_encrypted", False):
                raise ValueError(
                    "O arquivo PDF enviado está protegido por senha. "
                    "Por favor, remova a senha de proteção do documento antes de fazer o envio."
                )

            return ProcessedMedia(
                original_filename=original_filename,
                sanitized_filename=safe_filename,
                mime_type="application/pdf",
                size_bytes=len(file_bytes),
                extension=".pdf",
                is_pdf=True,
                page_count=pdf_info.get("page_count", 1),
                is_encrypted=False,
                content_bytes=file_bytes,
                metadata={
                    "has_embedded_text": pdf_info.get("has_embedded_text", False),
                    "text_preview": pdf_info.get("extracted_text_preview", "")
                }
            )

        # 2. Fluxo de Tratamento de Imagem (JPG, PNG, HEIC, WEBP)
        clean_bytes, mime_type, img_meta = ImageSanitizer.sanitize_image(file_bytes, original_filename)
        final_ext = ".jpg" if mime_type == "image/jpeg" else ".png"

        # Se o original era HEIC, altera a extensão para .jpg no nome limpo
        base_name, _ = os.path.splitext(safe_filename)
        final_filename = f"{base_name}{final_ext}"

        return ProcessedMedia(
            original_filename=original_filename,
            sanitized_filename=final_filename,
            mime_type=mime_type,
            size_bytes=len(clean_bytes),
            extension=final_ext,
            is_pdf=False,
            page_count=1,
            is_encrypted=False,
            content_bytes=clean_bytes,
            metadata=img_meta
        )
