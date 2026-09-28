# -*- coding: utf-8 -*-
"""
Subagente Especialista 3: Agente Auditor de Conformidade Regulatória MEC (MecComplianceAgent).
Responsável pela auditoria estrita de acordo com as normas do Ministério da Educação:
Portaria MEC nº 315/2018 e nº 360/2022 (Acervo Acadêmico Digital), Portaria nº 554/2019 (Diploma Digital),
Tabela de Temporalidade Documental (TTD) e requisitos de admissão por tipo de curso.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from agents.base_agent import BaseSubagent
from agents.models import SubagentRole, AgentTask
from core_criteria_models import DocumentSpecification


class MecComplianceAgent(BaseSubagent):
    """Subagente responsável pelo compliance regulatório perante o MEC e legislações educacionais."""

    def __init__(self):
        super().__init__(
            role=SubagentRole.MEC_COMPLIANCE,
            name="Agente Auditor de Conformidade Regulatória MEC",
            description="Audita regras das Portarias MEC 315/2018, 360/2022, TTD e critérios legais de ingresso acadêmico."
        )

    def _run(self, task: AgentTask) -> Dict[str, Any]:
        ocr_result = task.payload.get("ocr_result", {})
        spec: DocumentSpecification = task.payload.get("spec")
        course_name: str = task.payload.get("course_name", "1ª Graduação")
        student_name: str = task.payload.get("student_name", "")
        extracted_data = ocr_result.get("extracted_data", {})

        regulatory_reasons = []
        is_compliant = True
        ttd_classification = "TRANSITORIO"
        retention_years = 5

        doc_id_upper = str(getattr(spec, "id", "")).upper()
        course_clean = str(course_name).upper()

        # 1. Regras do Acervo Acadêmico Digital (Portaria MEC 315/2018 - Art. 12 / 360/2022)
        if any(term in doc_id_upper for term in ["HISTORICO", "DIPLOMA", "CERTIFICADO", "CONCLUSAO"]):
            ttd_classification = "PERMANENTE"
            retention_years = 100  # Guarda permanente da vida escolar

        # 2. Critérios específicos de curso: 2ª Graduação e Pós-Graduação exigem Diploma Superior Oficial
        if any(c in course_clean for c in ["2ª GRADUAÇÃO", "2 GRADUACAO", "POS-GRADUACAO", "PÓS-GRADUAÇÃO", "ESPECIALIZACAO"]):
            if "DIPLOMA" in doc_id_upper:
                # Se foi enviado apenas histórico ou declaração simples
                curso_concluido = extracted_data.get("nome_curso") or extracted_data.get("curso")
                has_degree = bool(extracted_data.get("data_colacao_grau") or extracted_data.get("numero_registro_diploma"))
                if not has_degree and not ocr_result.get("is_approved"):
                    regulatory_reasons.append(
                        "Portaria MEC nº 315/2018 & Parecer CNE/CES: Para ingresso em 2ª Graduação ou Pós-Graduação, "
                        "é indispensável a comprovação inequívoca de conclusão prévia de curso superior reconhecido (Diploma ou Certidão com Colação de Grau)."
                    )
                    is_compliant = False

        # 3. Verificação de Quitação Militar (Lei nº 4.375/1964)
        if "MILITAR" in doc_id_upper:
            ttd_classification = "TRANSITORIO"
            retention_years = 10
            # Se a data de nascimento indicar sexo masculino entre 18 e 45 anos
            ano_nasc = self._extract_year(extracted_data.get("data_nascimento"))
            if ano_nasc:
                idade = datetime.now(timezone.utc).year - ano_nasc
                if idade > 45:
                    regulatory_reasons.append("Estudante com mais de 45 anos: Dispensa de quitação militar conforme Lei nº 4.375/1964.")

        # 4. Verificação de Quitação Eleitoral (Lei nº 4.737/1965)
        if "ELEITORAL" in doc_id_upper:
            ttd_classification = "TRANSITORIO"
            retention_years = 5

        # Se a análise de OCR já rejeitou por ausência de verso ou carimbo
        if not ocr_result.get("is_approved"):
            is_compliant = False
            if ocr_result.get("reason"):
                regulatory_reasons.append(ocr_result.get("reason"))

        return {
            "success": True,
            "is_compliant": is_compliant,
            "regulatory_reasons": regulatory_reasons,
            "ttd_classification": ttd_classification,
            "retention_years": retention_years,
            "portaria_reference": "Portaria MEC nº 315/2018 e Portaria MEC nº 360/2022",
            "summary": f"Auditoria MEC: {'CONFORME' if is_compliant else 'PENDÊNCIA REGULATÓRIA'} | Guarda: {ttd_classification}"
        }

    def _extract_year(self, date_str: Optional[str]) -> Optional[int]:
        if not date_str:
            return None
        import re
        match = re.search(r'\b(19\d{2}|20\d{2})\b', str(date_str))
        return int(match.group(1)) if match else None
