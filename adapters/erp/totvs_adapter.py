"""
Adaptador de Integração com o TOTVS Educacional (Linha RM / RM Web Services & REST).
Permite consulta cadastral e sincronização bidirecional de documentos acadêmicos e deferimento de matrícula.
"""

import logging
import re
import requests
from typing import Optional, Dict, Any, List
from adapters.erp.base import StudentDataProvider, StudentProfile

logger = logging.getLogger("TOTVS_ADAPTER")


class TotvsEducacionalAdapter(StudentDataProvider):
    """
    Conector do TOTVS Educacional (RM Portal / RM DataServer REST API).
    Suporta busca por RA/CPF e atualização de status de documentos no módulo acadêmico.
    """

    def __init__(
        self,
        base_url: str,
        user: str = "",
        password: str = "",
        cod_coligada: int = 1,
        token: Optional[str] = None
    ):
        self.base_url = base_url.rstrip('/')
        self.cod_coligada = cod_coligada
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "ProtocoloEdu-TOTVS-Connector/2.0"
        })
        if token:
            self.session.headers.update({"Authorization": f"Bearer {token}"})
        elif user and password:
            self.session.auth = (user, password)

    def search_student(self, identifier: str, search_type: str = "cpf") -> Optional[StudentProfile]:
        """
        Consulta estudante no TOTVS Educacional via DataServer EduAlunoData ou REST API.
        """
        clean_id = re.sub(r'\D', '', str(identifier))
        try:
            # Endpoint padrão do RM REST API para consulta de alunos
            endpoint = f"{self.base_url}/api/v1/RM/EduAlunoData/alunos"
            params = {"codColigada": self.cod_coligada}
            if len(clean_id) == 11:
                params["cpf"] = clean_id
            else:
                params["ra"] = clean_id

            res = self.session.get(endpoint, params=params, timeout=20)
            if res.status_code == 404:
                return None
            res.raise_for_status()
            data = res.json()

            items = data if isinstance(data, list) else data.get("items", [data]) if isinstance(data, dict) else []
            if not items:
                return None

            item = items[0]
            return StudentProfile(
                student_id=str(item.get("ra") or item.get("codAluno") or clean_id),
                full_name=item.get("nome") or item.get("nomeSocial") or "ALUNO TOTVS",
                cpf=item.get("cpf") or clean_id,
                birth_date=item.get("dataNascimento"),
                course_name=item.get("nomeCurso") or item.get("curso"),
                status=item.get("statusMatricula", "ativo"),
                extra_data=item
            )
        except Exception as e:
            logger.error(f"Erro na busca no TOTVS Educacional: {e}")
            return None

    def update_student_data(self, student_id: str, fields_to_update: Dict[str, Any]) -> bool:
        """
        Atualiza dados complementares do aluno no RM Educacional.
        """
        try:
            endpoint = f"{self.base_url}/api/v1/RM/EduAlunoData/alunos/{student_id}"
            payload = {
                "codColigada": self.cod_coligada,
                "campos": fields_to_update
            }
            res = self.session.patch(endpoint, json=payload, timeout=20)
            if res.status_code == 404:
                res = self.session.put(endpoint, json=payload, timeout=20)
            res.raise_for_status()
            return True
        except Exception as e:
            logger.error(f"Erro ao atualizar aluno {student_id} no TOTVS: {e}")
            return False

    def sync_matricula_status(self, student_id: str, is_approved: bool, protocol_number: str) -> Dict[str, Any]:
        """
        Registra no TOTVS Educacional o deferimento de matrícula e entrega do dossiê.
        """
        endpoint = f"{self.base_url}/api/v1/RM/EduMatriculaData/status"
        payload = {
            "codColigada": self.cod_coligada,
            "ra": student_id,
            "statusDocumentacao": "DEFERIDO" if is_approved else "PENDENTE",
            "protocoloProtocoloEdu": protocol_number
        }
        try:
            res = self.session.post(endpoint, json=payload, timeout=20)
            res.raise_for_status()
            return {"success": True, "totvs_response": res.json() if res.content else {}}
        except Exception as e:
            logger.warning(f"Erro ao atualizar status de matrícula no TOTVS: {e}")
            return {"success": False, "error": str(e)}
