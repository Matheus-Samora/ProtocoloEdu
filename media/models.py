"""
Modelos de dados tipados para o pipeline de mídia e documentos.
Desacoplado de frameworks web (Flask/FastAPI).
"""

from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class MediaType(str, Enum):
    """Classificação do tipo de mídia suportado."""
    PDF = "application/pdf"
    JPEG = "image/jpeg"
    PNG = "image/png"
    HEIC = "image/heic"
    WEBP = "image/webp"
    OCTET_STREAM = "application/octet-stream"


class ProcessedMedia(BaseModel):
    """Representa um arquivo processado e sanitizado, pronto para auditoria e armazenamento."""
    original_filename: str = Field(..., description="Nome original enviado pelo usuário")
    sanitized_filename: str = Field(..., description="Nome padronizado e seguro")
    mime_type: str = Field(..., description="MIME type oficial sanitizado (ex: 'application/pdf', 'image/jpeg')")
    size_bytes: int = Field(..., description="Tamanho final em bytes")
    extension: str = Field(..., description="Extensão final do arquivo (ex: '.pdf', '.jpg')")
    is_pdf: bool = Field(False, description="Flag indicando se é um documento PDF")
    page_count: int = Field(1, description="Número de páginas (1 para imagens, N para PDFs)")
    is_encrypted: bool = Field(False, description="True se o arquivo for um PDF protegido por senha")
    content_bytes: bytes = Field(..., repr=False, description="Conteúdo binário pronto em memória")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Metadados adicionais (dimensões, rotação, etc.)")


class MediaValidationResult(BaseModel):
    """Resultado da validação prévia de arquivo (tamanho, formato e integridade)."""
    is_valid: bool = Field(..., description="Se o arquivo atende às regras da instituição")
    error_message: Optional[str] = Field(None, description="Mensagem de erro amigável se inválido")
    detected_mime: Optional[str] = Field(None, description="MIME detectado")
