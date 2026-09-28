"""
Adaptador Genérico REST / Webhook para ERPs Educacionais (SophiA, Sponte, Gennera, TOTVS, etc.).
Permite parametrizar endpoints, headers e chaves de resposta diretamente no JSON de configuração.
"""

import logging
import requests
from typing import Optional, Dict, Any

from adapters.erp.base import StudentDataProvider, StudentProfile

logger = logging.getLogger("GENERIC_ERP_ADAPTER")


class GenericRestERPAdapter(StudentDataProvider):
    """
    Adaptador HTTP REST configurável para qualquer ERP escolar ou universitário.
    """

    def __init__(
        self,
        base_url: str,
        auth_header_name: str = "Authorization",
        auth_header_value: str = "",
        search_endpoint_template: str = "/api/v1/students?search={identifier}",
        update_endpoint_template: str = "/api/v1/students/{student_id}",
        field_mapping: Optional[Dict[str, str]] = None
    ):
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        if auth_header_value:
            self.session.headers.update({auth_header_name: auth_header_value})
        self.session.headers.update({
            "Content-Type": "application/json",
            "Accept": "application/json"
        })
        self.search_endpoint = search_endpoint_template
        self.update_endpoint = update_endpoint_template
        self.mapping = field_mapping or {
            "id": "id",
            "name": "name",
            "cpf": "cpf",
            "course": "course"
        }

    def search_student(self, identifier: str, search_type: str = "cpf") -> Optional[StudentProfile]:
        url = f"{self.base_url}{self.search_endpoint.format(identifier=identifier)}"
        try:
            res = self.session.get(url, timeout=20)
            res.raise_for_status()
            data = res.json()

            # Trata se a resposta for lista ou objeto único
            item = data[0] if isinstance(data, list) and len(data) > 0 else data if isinstance(data, dict) else None
            if not item:
                return None

            return StudentProfile(
                student_id=str(item.get(self.mapping.get("id", "id"))),
                full_name=item.get(self.mapping.get("name", "name")),
                cpf=item.get(self.mapping.get("cpf", "cpf")),
                course_name=item.get(self.mapping.get("course", "course")),
                extra_data=item
            )
        except Exception as e:
            logger.error(f"Erro na busca no ERP Genérico: {e}")
            return None

    def update_student_data(self, student_id: str, fields_to_update: Dict[str, Any]) -> bool:
        url = f"{self.base_url}{self.update_endpoint.format(student_id=student_id)}"
        try:
            res = self.session.patch(url, json=fields_to_update, timeout=20)
            if res.status_code == 404:
                # Tenta PUT se PATCH não for aceito
                res = self.session.put(url, json=fields_to_update, timeout=20)
            res.raise_for_status()
            return True
        except Exception as e:
            logger.error(f"Erro ao atualizar dados no ERP Genérico: {e}")
            return False


class MockERPAdapter(StudentDataProvider):
    """Adaptador de simulação para desenvolvimento local, testes e novas escolas."""

    def __init__(self, demo_student_name: str = "ALUNO TESTE HOMOLOGACAO"):
        self.demo_name = demo_student_name

    def search_student(self, identifier: str, search_type: str = "cpf") -> Optional[StudentProfile]:
        return StudentProfile(
            student_id="99999",
            full_name=self.demo_name,
            cpf=identifier,
            course_name="Curso Demonstração",
            status="ativo",
            extra_data={"mock": True}
        )

    def update_student_data(self, student_id: str, fields_to_update: Dict[str, Any]) -> bool:
        logger.info(f"[MOCK ERP] Dados recebidos para atualização do aluno {student_id}: {fields_to_update}")
        return True
