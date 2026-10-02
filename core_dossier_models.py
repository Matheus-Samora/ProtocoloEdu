"""
Modelos de dados para o Dossiê Central de Documentos do Estudante.
Representa a 'Secretaria Digital': consolida auditorias, dados extraídos e status de entrega.
Multi-Tenant: Todos os registros são estritamente isolados por 'institution_id'.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field


class DossierStatus(str, Enum):
    """Situação geral da documentação do aluno."""
    COMPLETO = "COMPLETO"        # Todos os documentos obrigatórios foram aprovados
    PENDENTE = "PENDENTE"        # Faltam documentos obrigatórios a serem enviados
    EM_ANALISE = "EM_ANALISE"    # Há documentos recém-enviados em processamento
    COM_PENDENCIA = "COM_PENDENCIA" # Um ou mais documentos foram reprovados e precisam de reenvio


class DocumentAuditItem(BaseModel):
    """Registro de um documento específico avaliado pela IA dentro do dossiê."""
    document_id: str = Field(..., description="ID canônico do documento (ex: 'RG', 'DIPLOMA_GRADUACAO')")
    display_name: str = Field(..., description="Nome amigável exibido")
    status: str = Field("pending", description="'approved', 'rejected', 'in_review', 'pending'")
    reason: Optional[str] = Field(None, description="Motivo pedagógico/institucional exibido ao estudante")
    admin_diagnostic: Optional[str] = Field(None, description="Diagnóstico técnico de infraestrutura visível exclusivamente para a Secretaria/TI")
    system_error: bool = Field(False, description="Flag indicando se a verificação automática sofreu falha de infraestrutura")
    extracted_data: Dict[str, Any] = Field(default_factory=dict, description="Dados extraídos (CPF, RG, Datas, etc.)")
    file_name: Optional[str] = Field(None, description="Nome do arquivo arquivado")
    sha256_hash: Optional[str] = None
    file_size_bytes: Optional[int] = None
    storage_url: Optional[str] = Field(None, description="URL ou chave de acesso ao arquivo")
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class StudentDossier(BaseModel):
    """Dossiê Acadêmico Digital do Aluno por Instituição."""
    institution_id: str = Field(..., description="ID da instituição proprietária do registro")
    student_id: str = Field(..., description="CPF, Matrícula ou ID único do estudante")
    student_name: str = Field(..., description="Nome completo do aluno")
    course_name: str = Field(..., description="Curso, Série ou Nível de Ensino")
    cpf: Optional[str] = Field(None, description="CPF do aluno (se aplicável)")
    status: DossierStatus = Field(DossierStatus.PENDENTE, description="Status consolidado do dossiê")
    documents: Dict[str, DocumentAuditItem] = Field(default_factory=dict, description="Dicionário de documentos por doc_id")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    exported_at: Optional[datetime] = Field(None, description="Última data em que este dossiê foi exportado para o ERP")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Metadados complementares e de integração com ERP")

    @property
    def dossier_id(self) -> str:
        """Identificador canônico do protocolo do dossiê (ex: 'PROT-12345678900')."""
        return f"PROT-{self.student_id}"


    def update_status(self, mandatory_doc_ids: Optional[List[str]] = None):
        """
        Recalcula o status do dossiê com base na conformidade estrita:
        - COM_PENDENCIA: Se qualquer documento (enviado ou obrigatório) estiver rejeitado.
        - EM_ANALISE: Se algum documento estiver sob conferência manual da Secretaria ou com erro de sistema.
        - COMPLETO: APENAS se todos os documentos obrigatórios exigidos estiverem aprovados
          E nenhum documento do dossiê estiver rejeitado ou sob análise.
        - PENDENTE: Se faltam documentos obrigatórios a serem enviados ou aprovados.
        """
        all_docs = list(self.documents.values())

        # 1. Se qualquer documento enviado foi rejeitado, o dossiê tem pendência incontestável
        has_any_rejected = any(doc.status == "rejected" for doc in all_docs)
        if has_any_rejected:
            self.status = DossierStatus.COM_PENDENCIA
            self.updated_at = datetime.now(timezone.utc)
            return

        # 2. Se algum documento está sob revisão manual ou análise
        has_any_in_review = any(
            doc.status in ("in_review", "pending_review") or getattr(doc, "system_error", False)
            for doc in all_docs
        )
        if has_any_in_review:
            self.status = DossierStatus.EM_ANALISE
            self.updated_at = datetime.now(timezone.utc)
            return

        # 3. Se não há documentos enviados ainda
        if not all_docs:
            self.status = DossierStatus.PENDENTE
            self.updated_at = datetime.now(timezone.utc)
            return

        # 4. Verificação com lista de documentos obrigatórios
        if mandatory_doc_ids:
            missing_or_unapproved = []
            for req_id in mandatory_doc_ids:
                doc_item = self.documents.get(req_id)
                if not doc_item or doc_item.status != "approved":
                    missing_or_unapproved.append(req_id)

            if not missing_or_unapproved:
                self.status = DossierStatus.COMPLETO
            else:
                self.status = DossierStatus.PENDENTE
        else:
            # Sem lista de obrigatórios: só é COMPLETO se houver pelo menos um documento aprovado
            has_approved = any(doc.status == "approved" for doc in all_docs)
            if has_approved:
                self.status = DossierStatus.COMPLETO
            else:
                self.status = DossierStatus.PENDENTE

        self.updated_at = datetime.now(timezone.utc)

