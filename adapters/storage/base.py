"""
Interface abstrata para Provedores de Armazenamento de Documentos.
Suporta Google Drive Institucional, Cloud Storage da Plataforma (SaaS) ou Storage Local.
"""

from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

from media.models import ProcessedMedia
from core_criteria_models import DocumentSpecification


class StoredFileInfo(BaseModel):
    """Informações de um arquivo arquivado com sucesso."""
    file_id: str = Field(..., description="ID ou chave do arquivo no provedor")
    filename: str = Field(..., description="Nome final oficial do arquivo")
    storage_url: Optional[str] = Field(None, description="URL de download ou visualização")
    provider: str = Field(..., description="Tipo do provedor (google_drive, cloud_storage, local)")
    size_bytes: int = Field(..., description="Tamanho do arquivo gravado")


class StorageProvider(ABC):
    """Contrato universal de armazenamento para qualquer instituição."""

    @abstractmethod
    def list_student_documents(self, student_name: str) -> List[str]:
        """
        Retorna a lista de nomes dos arquivos que o estudante já possui arquivados.
        """
        pass

    @abstractmethod
    def store_document(
        self,
        student_name: str,
        spec: DocumentSpecification,
        media: ProcessedMedia,
        suffix: str = ""
    ) -> Optional[StoredFileInfo]:
        """
        Armazena um documento aprovado seguindo a política de nomes da instituição.
        
        Args:
            student_name: Nome do estudante.
            spec: Especificação do documento (RG, Diploma, etc.).
            media: Objeto com bytes limpos e extensão sanitizada.
            suffix: Sufixo adicional (ex: ' FRENTE', ' VERSO', ' PAG 1').
        """
        pass

    def delete_document(self, student_name: str, filename: str) -> bool:
        """
        Remove um arquivo específico das pastas de custódia do aluno caso ele seja invalidado ou rejeitado.
        Garante que documentos em desacordo não permaneçam no repositório oficial.
        """
        return False

