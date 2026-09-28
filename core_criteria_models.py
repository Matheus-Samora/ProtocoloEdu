"""
Módulo de Definição de Tipos e Modelos de Critérios para o Protocolo IMES.
Baseado em Clean Architecture e Princípio da Responsabilidade Única (SRP).
Permite configurar e parametrizar qualquer documento sem alterar código.
"""

from enum import Enum
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class RuleType(str, Enum):
    """Tipos de regras executáveis pelo motor de validação."""
    DOC_TYPE = "DOC_TYPE"                  # Valida tipo documental estrito (ex: RG vs CNH vs Diploma)
    COMPLETENESS = "COMPLETENESS"          # Valida completude (ex: frente e verso, página única, todas as páginas)
    QUALITY_CHECK = "QUALITY_CHECK"        # Valida legibilidade, foco, ausência de cortes ou reflexos
    HOLDER_MATCH = "HOLDER_MATCH"          # Valida se o titular é o aluno (solteiro, casado, abreviado)
    ELEMENT_PRESENCE = "ELEMENT_PRESENCE"  # Valida presença visual (foto, assinatura, carimbo, selo MEC)
    FIELD_EXTRACTION = "FIELD_EXTRACTION"  # Extrai dados estruturados (RG, CPF, Órgão, Datas, Filiação)
    VALIDITY_CHECK = "VALIDITY_CHECK"      # Valida data de validade / vigência do documento
    ACADEMIC_INTEGRITY = "ACADEMIC_INTEGRITY" # Valida carga horária, colação de grau, instituição credenciada
    DIGITAL_SIGNATURE = "DIGITAL_SIGNATURE" # Valida assinatura digital ICP-Brasil/Gov.br e metadados PAdES (Portaria MEC 315/2018)
    STAMP_LEGIBILITY = "STAMP_LEGIBILITY"   # Valida nitidez e autenticidade de carimbos escolares, visto de inspeção e confere com original
    CIVIL_ANNOTATION = "CIVIL_ANNOTATION"   # Valida averbações civis (casamento, separação, divórcio) para conciliação patronímica


class MatchingMode(str, Enum):
    """Modo de tolerância para comparação de nomes de titulares."""
    STRICT = "STRICT"                      # Exige correspondência exata
    FLEXIBLE = "FLEXIBLE"                  # Aceita abreviações e mudança de nome (casamento/divórcio)
    FUZZY = "FUZZY"                        # Distância de Levenshtein (similaridade percentual)
    IGNORE = "IGNORE"                      # Não valida titularidade (ex: comprovante de residência)


class Portaria315ComplianceMetadata(BaseModel):
    """Metadados de auditoria e conformidade regulatória segundo a Portaria MEC 315/2018."""
    conarq_classification: str = Field("125.1", description="Código CONARQ do Acervo Acadêmico")
    retention_schedule: str = Field("PERMANENTE", description="Tabela de Temporalidade Documental (TTD)")
    requires_digital_signature_check: bool = Field(False, description="Exige validação criptográfica ICP-Brasil/Gov.br")
    requires_school_stamp_legibility: bool = Field(False, description="Exige nitidez de carimbo escolar/inspeção")
    requires_civil_annotation_check: bool = Field(False, description="Exige averbação civil se houver divergência de nome")


class Criterion(BaseModel):
    """Representa um critério atômico que o documento deve satisfazer."""
    id: str = Field(..., description="Identificador único da regra (ex: 'rg_frente_verso')")
    name: str = Field(..., description="Nome amigável da regra")
    rule_type: RuleType = Field(..., description="Tipo de mecanismo de checagem")
    is_mandatory: bool = Field(True, description="Se True, a reprovação neste critério rejeita o documento")
    description: str = Field(..., description="Descrição detalhada do que deve ser verificado")
    params: Dict[str, Any] = Field(default_factory=dict, description="Parâmetros específicos da regra")
    failure_message: str = Field(..., description="Mensagem de retorno ao aluno se o critério falhar")


class DocumentSpecification(BaseModel):
    """Especificação completa de um documento: identidade, regras e critérios."""
    id: str = Field(..., description="ID técnico único (ex: 'RG', 'DIPLOMA_GRADUACAO')")
    display_name: str = Field(..., description="Nome público exibido no portal do aluno")
    expected_doc_type: str = Field(..., description="Identificador canônico de classificação pela IA")
    aliases: List[str] = Field(default_factory=list, description="Variações de nomes aceitas no Drive ou na busca")
    target_filename_pattern: str = Field(..., description="Padrão de nome para arquivamento no Drive")
    target_drive_folder: str = Field("DOC", description="Subpasta de destino no Drive (ex: 'DOC', 'OUTROS DOCS')")
    allowed_extensions: List[str] = Field(default_factory=lambda: [".pdf", ".jpg", ".jpeg", ".png", ".heic"])
    criteria: List[Criterion] = Field(default_factory=list, description="Lista ordenada de critérios de validação")
    compliance_315: Optional[Portaria315ComplianceMetadata] = Field(None, description="Parâmetros regulatórios da Portaria MEC 315/2018")

    def get_mandatory_criteria(self) -> List[Criterion]:
        """Retorna apenas os critérios eliminatórios."""
        return [c for c in self.criteria if c.is_mandatory]

    def get_extraction_fields(self) -> List[str]:
        """Retorna a lista de campos que devem ser extraídos pelo modelo de IA."""
        fields = []
        for c in self.criteria:
            if c.rule_type == RuleType.FIELD_EXTRACTION:
                f_name = c.params.get("field_name")
                if f_name:
                    fields.append(f_name)
        return fields
