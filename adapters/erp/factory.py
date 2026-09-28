"""
Fábrica de Conectores de ERP Acadêmico (ERP Factory).
Instancia o adaptador correto com base no perfil da instituição de ensino.
"""

import os
from typing import Optional
from adapters.erp.base import StudentDataProvider
from adapters.erp.solis_adapter import SolisERPAdapter
from adapters.erp.totvs_adapter import TotvsEducacionalAdapter
from adapters.erp.sophia_adapter import SophiaERPAdapter
from adapters.erp.generic_rest_adapter import GenericRestERPAdapter, MockERPAdapter
from core_institution_models import InstitutionProfile


class ERPFactory:
    """Instancia o conector correto para cada instituição."""

    @staticmethod
    def get_provider(institution: InstitutionProfile) -> StudentDataProvider:
        erp_cfg = institution.erp
        erp_type = (erp_cfg.erp_type or "mock").lower()

        if erp_type == "solis":
            api_url = os.environ.get("SOLIS_API_URL") or erp_cfg.api_url or ""
            jwt_token_var = erp_cfg.jwt_token_env_var or "SOLIS_JWT_TOKEN"
            jwt_token = os.environ.get(jwt_token_var) or os.environ.get("SOLIS_JWT_TOKEN") or ""

            if not api_url or not jwt_token:
                return MockERPAdapter(demo_student_name=f"ALUNO TESTE SOLIS ({institution.name})")

            return SolisERPAdapter(
                base_url=api_url,
                jwt_token=jwt_token,
                reports_map=erp_cfg.reports_map
            )

        elif erp_type == "totvs":
            api_url = os.environ.get("TOTVS_API_URL") or erp_cfg.api_url or ""
            totvs_user = os.environ.get("TOTVS_USER") or ""
            totvs_pass = os.environ.get("TOTVS_PASSWORD") or ""
            totvs_token = os.environ.get("TOTVS_TOKEN") or ""

            if not api_url:
                return MockERPAdapter(demo_student_name=f"ALUNO TESTE TOTVS ({institution.name})")

            return TotvsEducacionalAdapter(
                base_url=api_url,
                user=totvs_user,
                password=totvs_pass,
                token=totvs_token
            )

        elif erp_type == "sophia":
            api_url = os.environ.get("SOPHIA_API_URL") or erp_cfg.api_url or ""
            token = os.environ.get("SOPHIA_API_TOKEN") or ""

            if not api_url or not token:
                return MockERPAdapter(demo_student_name=f"ALUNO TESTE SOPHIA ({institution.name})")

            return SophiaERPAdapter(
                base_url=api_url,
                api_token=token
            )

        elif erp_type in ("generic", "sponte", "gennera"):
            api_url = erp_cfg.api_url or ""
            if not api_url:
                return MockERPAdapter(demo_student_name=f"ALUNO TESTE {erp_type.upper()} ({institution.name})")
            return GenericRestERPAdapter(base_url=api_url)

        # Padrão seguro
        return MockERPAdapter(demo_student_name=f"ALUNO SIMULADO ({institution.name})")

