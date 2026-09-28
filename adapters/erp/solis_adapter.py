"""
Adaptador de integração para o ERP SolisGE.
Baseado em chamadas de relatórios genéricos e endpoints de pessoa via JWT (X-Token).
"""

import json
import logging
import re
import requests
from typing import Optional, Dict, Any

from adapters.erp.base import StudentDataProvider, StudentProfile

logger = logging.getLogger("SOLIS_ADAPTER")


class SolisERPAdapter(StudentDataProvider):
    """Conector do ERP SolisGE com busca encadeada segura."""

    def __init__(self, base_url: str, jwt_token: str, reports_map: Optional[Dict[str, str]] = None):
        if not base_url or not jwt_token:
            raise ValueError("URL base e Token JWT do Solis são obrigatórios.")

        self.base_url = base_url.rstrip('/')
        self.headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'X-Token': jwt_token,
            'User-Agent': 'Protocolo-Edu/2.0'
        }
        self.reports_map = reports_map or {
            "search_cpf": "6820251203155305",
            "search_name": "6620251203154311",
            "get_by_id": "7020251204095501"
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        self.session.headers.update({'Connection': 'close'})
        requests.urllib3.disable_warnings(requests.urllib3.exceptions.InsecureRequestWarning)

    def _execute_report(self, report_id: str, params: Dict[str, Any]) -> Optional[list]:
        url = f"{self.base_url}/api/basico/relatorio-generico/gerar/{report_id}"
        try:
            res = self.session.get(url, json={"par": params}, verify=False, timeout=25)
            res.raise_for_status()
            data = res.json()
            return data if isinstance(data, list) else []
        except Exception as e:
            logger.error(f"Erro ao executar relatório Solis '{report_id}': {e}")
            return None

    def search_student(self, identifier: str, search_type: str = "cpf") -> Optional[StudentProfile]:
        """Busca em cadeia de 3 etapas do Solis (CPF -> Nome -> ID -> Valida CPF)."""
        clean_cpf = re.sub(r'\D', '', str(identifier))
        report_cpf = self.reports_map.get("search_cpf", "6820251203155305")
        report_name = self.reports_map.get("search_name", "6620251203154311")
        report_id = self.reports_map.get("get_by_id", "7020251204095501")

        logger.info(f"Buscando aluno no Solis com CPF: {clean_cpf}")
        res_cpf = self._execute_report(report_cpf, {"cpf": clean_cpf})
        if not res_cpf or not res_cpf[0].get("nome"):
            return None

        found_name = res_cpf[0]["nome"]
        res_name = self._execute_report(report_name, {"NOME_ALUNO": found_name.upper()})
        if not res_name:
            return None

        for candidate in res_name:
            cand_id = candidate.get("ID")
            if not cand_id:
                continue

            res_details = self._execute_report(report_id, {"cod": cand_id})
            if res_details and len(res_details) > 0 and res_details[0]:
                item = res_details[0]
                cand_cpf_clean = re.sub(r'\D', '', item.get("cpf", ""))
                if cand_cpf_clean == clean_cpf:
                    return StudentProfile(
                        student_id=str(item.get("codigo", cand_id)),
                        full_name=item.get("nome", found_name),
                        cpf=item.get("cpf"),
                        course_name=item.get("curso"),
                        extra_data=item
                    )
        return None

    def update_student_data(self, student_id: str, fields_to_update: Dict[str, Any]) -> bool:
        """Atualiza pessoa no Solis via /api/basico/pessoa."""
        endpoint = f"{self.base_url}/api/basico/pessoa"
        payload = {"pessoa": {"identificador": str(student_id), **fields_to_update}}
        try:
            res = self.session.post(endpoint, json=payload, verify=False, timeout=25)
            res.raise_for_status()
            data = res.json()
            return bool(data.get("sucesso", False))
        except Exception as e:
            logger.error(f"Erro ao atualizar aluno no Solis: {e}")
            return False
