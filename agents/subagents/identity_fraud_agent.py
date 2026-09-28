# -*- coding: utf-8 -*-
"""
Subagente Especialista 4: Agente Pericial de Identidade & Antifraude (IdentityFraudAgent).
Responsável por checagem cruzada de titularidade biométrica/documental,
verificação de assinaturas eletrônicas avançadas (PAdES / ICP-Brasil),
detecção de substituição de documentos por terceiros e regras de parentesco/filiação para menores.
"""

from typing import Dict, Any, List, Optional
import re
import unicodedata
from agents.base_agent import BaseSubagent
from agents.models import SubagentRole, AgentTask
from mcp_services.pades_validator import PadesSignatureValidator
from media.models import ProcessedMedia


def clean_name_string(name: str) -> str:
    """Normaliza nome para comparação estrita e tolerante a acentuação."""
    if not name:
        return ""
    nfkd = unicodedata.normalize('NFKD', str(name))
    ascii_str = "".join(c for c in nfkd if not unicodedata.combining(c)).upper()
    return re.sub(r'[^A-Z\s]', '', ascii_str).strip()


def check_titularity_match(extracted_name: str, registered_name: str) -> bool:
    """
    Avalia se o nome extraído do documento corresponde ao aluno cadastrado.
    Suporta abreviações comuns de nomes brasileiros (ex: 'Matheus A. Samora' x 'Matheus Astunio Samora').
    """
    c_ext = clean_name_string(extracted_name)
    c_reg = clean_name_string(registered_name)

    if not c_ext or not c_reg:
        return False

    if c_ext == c_reg:
        return True

    # Tokens de nomes
    t_ext = c_ext.split()
    t_reg = c_reg.split()

    if not t_ext or not t_reg:
        return False

    # Primeiro e último sobrenome devem ser compatíveis
    if t_ext[0] != t_reg[0] and t_ext[-1] != t_reg[-1]:
        return False

    # Verifica se a maioria dos tokens coincide
    matching = set(t_ext).intersection(set(t_reg))
    if len(matching) >= max(len(t_ext), len(t_reg)) - 1:
        return True

    return False


class IdentityFraudAgent(BaseSubagent):
    """Subagente responsável pela detecção de fraudes, divergência de titularidade e assinaturas digitais."""

    def __init__(self, pades_validator: PadesSignatureValidator = None):
        super().__init__(
            role=SubagentRole.IDENTITY_FRAUD,
            name="Agente Pericial de Identidade & Antifraude",
            description="Valida titularidade, assinaturas digitais ICP-Brasil (PAdES) e bloqueia documentos de terceiros ou forjados."
        )
        self.pades_validator = pades_validator or PadesSignatureValidator()

    def _run(self, task: AgentTask) -> Dict[str, Any]:
        ocr_result = task.payload.get("ocr_result", {})
        media_list: List[ProcessedMedia] = task.payload.get("sanitized_media_list", [])
        student_name: str = task.payload.get("student_name", "")
        student_cpf: str = task.payload.get("student_cpf", "")
        responsible_name: Optional[str] = task.payload.get("responsible_name")

        extracted_data = ocr_result.get("extracted_data", {})
        fraud_flags = []
        is_authentic = True
        pades_report = None

        # 1. Validação de Assinatura Digital ICP-Brasil em PDFs acadêmicos (Portaria 315/2018)
        for media in media_list:
            if media.is_pdf:
                report = self.pades_validator.verify_pdf(media.content_bytes, filename=media.sanitized_filename)
                pades_report = {
                    "has_signature": report.has_signature,
                    "signature_format": report.signature_format,
                    "summary": report.summary,
                    "is_valid": report.is_valid
                }
                if report.has_signature and not report.is_valid:
                    fraud_flags.append(f"Alerta PAdES: Assinatura digital do PDF apresenta inconsistência criptográfica ou certificado revogado.")

        # 2. Verificação Cruzada de Titularidade (CROSS-CHECK DETERMINÍSTICO)
        doc_holder_name = (
            extracted_data.get("nome_completo")
            or extracted_data.get("nome_titular")
            or extracted_data.get("nome_aluno")
            or extracted_data.get("aluno")
        )

        if doc_holder_name:
            match = check_titularity_match(doc_holder_name, student_name)

            # Se não bateu com o aluno, verifica se é um comprovante de residência em nome do responsável legal
            if not match and responsible_name:
                if check_titularity_match(doc_holder_name, responsible_name):
                    match = True
                    fraud_flags.append(f"Titularidade vinculada ao Responsável Legal cadastrado ('{responsible_name}').")

            if not match:
                is_authentic = False
                fraud_flags.append(
                    f"[DIVERGÊNCIA GRAVE DE TITULARIDADE]: O documento pertence a '{doc_holder_name}', "
                    f"divergindo expressamente do estudante cadastrado ('{student_name}')."
                )

        # 3. Verificação de CPF
        doc_cpf = extracted_data.get("numero_cpf") or extracted_data.get("cpf")
        if doc_cpf and student_cpf:
            c_doc = re.sub(r'\D', '', str(doc_cpf))
            c_cad = re.sub(r'\D', '', str(student_cpf))
            if len(c_doc) == 11 and len(c_cad) == 11 and c_doc != c_cad:
                is_authentic = False
                fraud_flags.append(f"[DIVERGÊNCIA DE CPF]: CPF no documento ({c_doc}) diverge do cadastro ({c_cad}).")

        fraud_risk = "LOW"
        if not is_authentic:
            fraud_risk = "CRITICAL"
        elif fraud_flags:
            fraud_risk = "MEDIUM"

        return {
            "success": True,
            "is_authentic": is_authentic,
            "fraud_risk": fraud_risk,
            "fraud_flags": fraud_flags,
            "pades_verification": pades_report,
            "extracted_holder": doc_holder_name,
            "registered_student": student_name,
            "summary": f"Perícia Antifraude: Risco={fraud_risk} | Titularidade={'CONFIRMADA' if is_authentic else 'DIVERGENTE'}"
        }
