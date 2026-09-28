"""
Adaptador de Integração com o SophiA Gestão Acadêmica / Escolar (Prima Informática).
Permite busca de estudantes e sincronização de entrega documental via SophiA REST API.
"""

import logging
import re
import requests
from typing import Optional, Dict, Any
from adapters.erp.base import StudentDataProvider, StudentProfile

logger = logging.getLogger("SOPHIA_ADAPTER")


class SophiaERPAdapter(StudentDataProvider):
    """
    Conector da API REST do SophiA Gestão Acadêmica / Escolar.
    """

    def __init__(self, base_url: str, api_token: str, unidade_id: Optional[str] = None):
        self.base_url = base_url.rstrip('/')
        self.api_token = api_token
        self.unidade_id = unidade_id
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Token {api_token}",
            "User-Agent": "ProtocoloEdu-Sophia-Connector/2.0"
        })

    def search_student(self, identifier: str, search_type: str = "cpf") -> Optional[StudentProfile]:
        """Busca estudante no SophiA por CPF ou Código de Matrícula."""
        clean_id = re.sub(r'\D', '', str(identifier))
        try:
            endpoint = f"{self.base_url}/api/v1/alunos"
            params = {}
            if len(clean_id) == 11:
                params["cpf"] = clean_id
            else:
                params["codigo"] = clean_id

            if self.unidade_id:
                params["unidade"] = self.unidade_id

            res = self.session.get(endpoint, params=params, timeout=20)
            if res.status_code == 404:
                return None
            res.raise_for_status()
            data = res.json()

            items = data if isinstance(data, list) else data.get("dados", [data]) if isinstance(data, dict) else []
            if not items:
                return None

            item = items[0]
            return StudentProfile(
                student_id=str(item.get("codigo") or item.get("matricula") or clean_id),
                full_name=item.get("nomeCompleto") or item.get("nome") or "ALUNO SOPHIA",
                cpf=item.get("cpf") or clean_id,
                birth_date=item.get("dataNascimento"),
                course_name=item.get("cursoNome") or item.get("turma"),
                status=item.get("situacao", "ativo"),
                extra_data=item
            )
        except Exception as e:
            logger.error(f"Erro na busca no SophiA: {e}")
            return None

    def update_student_data(self, student_id: str, fields_to_update: Dict[str, Any]) -> bool:
        """Atualiza dados cadastrais no SophiA."""
        try:
            endpoint = f"{self.base_url}/api/v1/alunos/{student_id}"
            res = self.session.patch(endpoint, json=fields_to_update, timeout=20)
            res.raise_for_status()
            return True
        except Exception as e:
            logger.error(f"Erro ao atualizar aluno {student_id} no SophiA: {e}")
            return False

    def sync_document_delivery(self, student_id: str, document_name: str, status: str, url: str) -> bool:
        """Registra a entrega e homologação de documento no cadastro do SophiA."""
        try:
            endpoint = f"{self.base_url}/api/v1/alunos/{student_id}/documentos"
            payload = {
                "descricao": document_name,
                "status": "ENTREGUE" if status == "approved" else "PENDENTE",
                "linkArquivo": url
            }
            res = self.session.post(endpoint, json=payload, timeout=20)
            return res.status_code in (200, 201)
        except Exception as e:
            logger.warning(f"Erro ao sincronizar documento no SophiA: {e}")
            return False
