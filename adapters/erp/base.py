"""
Interface base abstrata para conectores de ERP Acadêmico.
Permite plugar qualquer sistema escolar ou universitário sem alterar o core da aplicação.
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field


class StudentProfile(BaseModel):
    """Modelo canônico de aluno unificado entre todos os ERPs."""
    student_id: str = Field(..., description="ID ou código de matrícula no ERP")
    full_name: str = Field(..., description="Nome completo oficial cadastrado")
    cpf: Optional[str] = Field(None, description="Número de CPF (se aplicável)")
    birth_date: Optional[str] = Field(None, description="Data de nascimento")
    course_name: Optional[str] = Field(None, description="Curso, série ou turma matriculada")
    status: str = Field("ativo", description="Situação da matrícula (ativo, trancado, pré-matriculado)")
    extra_data: Dict[str, Any] = Field(default_factory=dict, description="Campos adicionais específicos do ERP")


class StudentDataProvider(ABC):
    """Contrato abstrato que qualquer integração de ERP deve implementar."""

    @abstractmethod
    def search_student(self, identifier: str, search_type: str = "cpf") -> Optional[StudentProfile]:
        """
        Localiza um estudante por CPF, matrícula ou nome.
        
        Args:
            identifier: Valor a buscar (ex: '12345678900' ou 'MATR-2026-01').
            search_type: Tipo do identificador ('cpf', 'matricula', 'nome').
        """
        pass

    @abstractmethod
    def update_student_data(self, student_id: str, fields_to_update: Dict[str, Any]) -> bool:
        """
        Atualiza dados cadastrais extraídos da auditoria (RG, endereço, etc.) no ERP.
        """
        pass
