"""
Motor de Critérios e Regras (Criteria Engine) do Protocolo IMES.
Executa a compilação dinâmica de prompts e a avaliação modular dos critérios.
Zero regras hardcoded: tudo é lido e guiado pelo catálogo de especificações.
"""

import json
import os
import re
import unicodedata
from typing import Dict, Any, List, Optional, Tuple
from core_criteria_models import DocumentSpecification, Criterion, RuleType, MatchingMode


def normalize_text(text: str) -> str:
    """Normaliza texto para comparação (maiúsculas, sem acentos e sem pontuação)."""
    if not text:
        return ""
    text = str(text).replace("_", " ")
    nfkd = unicodedata.normalize('NFKD', text.upper())
    only_ascii = nfkd.encode('ASCII', 'ignore').decode('utf-8')
    return re.sub(r'[^A-Z0-9\s-]', '', only_ascii).strip()


def validate_cpf_digits(cpf_raw: str) -> bool:
    """Valida o cálculo oficial dos dígitos verificadores do CPF brasileiro."""
    if not cpf_raw:
        return False
    digits = [int(c) for c in re.sub(r'\D', '', str(cpf_raw))]
    if len(digits) != 11 or len(set(digits)) == 1:
        return False
    
    # 1º dígito
    sum_1 = sum(digits[i] * (10 - i) for i in range(9))
    d1 = (sum_1 * 10 % 11) % 10
    if digits[9] != d1:
        return False
    
    # 2º dígito
    sum_2 = sum(digits[i] * (11 - i) for i in range(10))
    d2 = (sum_2 * 10 % 11) % 10
    return digits[10] == d2


def format_cpf(cpf_raw: str) -> Optional[str]:
    """Formata um CPF válido no padrão XXX.XXX.XXX-XX."""
    digits = re.sub(r'\D', '', str(cpf_raw or ''))
    if len(digits) == 11:
        return f"{digits[:3]}.{digits[3:6]}.{digits[6:9]}-{digits[9:]}"
    return cpf_raw


def flexible_name_match(name_a: str, name_b: str) -> bool:
    """
    Compara dois nomes com tolerância a abreviações e mudança de nome (solteiro/casado).
    Ex: 'Abel Azeredo de Oliveira' vs 'Abel Oliveira' -> True
    Ex: 'Jessica Lopes Carvalho' vs 'Jessica Lopes Carvalho Rodrigues' -> True
    """
    if not name_a or not name_b:
        return False
    norm_a = normalize_text(name_a)
    norm_b = normalize_text(name_b)

    preps = {'DE', 'DA', 'DO', 'DOS', 'DAS', 'E'}
    words_a = {w for w in norm_a.split() if w not in preps}
    words_b = {w for w in norm_b.split() if w not in preps}

    if not words_a or not words_b:
        return False

    return words_a.issubset(words_b) or words_b.issubset(words_a)


class CriteriaCatalog:
    """Gerenciador central dos catálogos de documentos e cursos."""

    def __init__(self, catalog_path: str = "document_catalog.json", courses_path: str = "courses_catalog.json"):
        self.catalog_path = catalog_path
        self.courses_path = courses_path
        self.documents: Dict[str, DocumentSpecification] = {}
        self.courses: Dict[str, Any] = {}
        self.load_catalogs()

    def load_catalogs(self):
        """Carrega e valida o catálogo de documentos e cursos."""
        if os.path.exists(self.catalog_path):
            with open(self.catalog_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for doc_id, doc_data in data.get("documents", {}).items():
                    self.documents[doc_id] = DocumentSpecification(**doc_data)

        if os.path.exists(self.courses_path):
            with open(self.courses_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.courses = data.get("courses", {})

    def get_document_spec(self, doc_id: str) -> Optional[DocumentSpecification]:
        """Obtém a especificação de um documento por ID."""
        return self.documents.get(doc_id)

    def _normalize_course_key(self, course_name: str) -> Optional[str]:
        """
        Normaliza tolerando variações de rótulos entre UI, front-ends e backend.
        Ex: '1ª Graduação (Ensino Superior)' -> '1ª Graduação'
            'graduacao_1' -> '1ª Graduação'
            'pos_graduacao' -> 'Pós-Graduação'
        """
        if not course_name:
            return None
        raw = str(course_name).strip()
        if raw in self.courses:
            return raw

        import unicodedata
        def clean_str(s: str) -> str:
            nfkd = unicodedata.normalize('NFKD', s)
            return "".join(c for c in nfkd if not unicodedata.combining(c)).lower().strip()

        cleaned_input = clean_str(raw)

        # 1. Verifica se coincide com alguma chave ou display_name exato (case-insensitive)
        for canon_key, c_info in self.courses.items():
            if clean_str(canon_key) == cleaned_input:
                return canon_key
            if isinstance(c_info, dict) and clean_str(c_info.get("display_name", "")) == cleaned_input:
                return canon_key

        # 2. Mapeamento canônico ordenado do mais específico para o mais genérico
        alias_map = {
            "2a graduacao": "2ª Graduação",
            "2 graduacao": "2ª Graduação",
            "graduacao_2": "2ª Graduação",
            "segunda graduacao": "2ª Graduação",
            "portadores de diploma": "2ª Graduação",
            "portador de diploma": "2ª Graduação",
            "pos-graduacao": "Pós-Graduação",
            "pos graduacao": "Pós-Graduação",
            "pos_graduacao": "Pós-Graduação",
            "especializacao": "Pós-Graduação",
            "mba": "Pós-Graduação",
            "ensino fundamental": "Ensino Fundamental (1º ao 9º ano)",
            "fundamental": "Ensino Fundamental (1º ao 9º ano)",
            "ensino medio": "Ensino Médio (1ª a 3ª série)",
            "ensino_medio": "Ensino Médio (1ª a 3ª série)",
            "medio": "Ensino Médio (1ª a 3ª série)",
            "cursos rapidos": "Cursos Rápidos",
            "cursos_rapidos": "Cursos Rápidos",
            "rapidos": "Cursos Rápidos",
            "1a graduacao": "1ª Graduação",
            "1 graduacao": "1ª Graduação",
            "graduacao_1": "1ª Graduação",
            "primeira graduacao": "1ª Graduação",
            "ensino superior": "1ª Graduação",
            "graduacao": "1ª Graduação"
        }

        for alias, canon in alias_map.items():
            if alias in cleaned_input:
                if canon in self.courses:
                    return canon

        for canon_key in self.courses:
            cleaned_canon = clean_str(canon_key)
            if cleaned_canon in cleaned_input or cleaned_input in cleaned_canon:
                return canon_key

        return None


    def get_required_docs_for_course(self, course_name: str) -> List[Dict[str, Any]]:
        """Retorna a matriz de grupos de documentos para um curso."""
        canon = self._normalize_course_key(course_name)
        if canon and canon in self.courses:
            return self.courses[canon].get("document_groups", [])
        return []



class PromptCompiler:
    """Compila dinamicamente as instruções da IA com base nos critérios declarados."""

    @staticmethod
    def compile_gemini_prompt(spec: DocumentSpecification, student_name: str) -> str:
        """Gera as diretrizes específicas e o JSON Schema para o Gemini analisar o documento."""
        lines = [
            f"Você é o Auditor Documental Oficial da Faculdade IMES.",
            f"Sua missão é realizar a auditoria técnica e estrita do documento enviado.",
            f"",
            f"--- ESPECIFICAÇÃO DO DOCUMENTO ESPERADO ---",
            f"Nome do Documento: {spec.display_name}",
            f"Tipo Canônico Esperado: {spec.expected_doc_type}",
            f"Nome do Aluno Cadastrado: {student_name}",
            f"",
            f"--- REQUISITOS OBRIGATÓRIOS A SEREM VERIFICADOS ---"
        ]

        extraction_fields = []
        for i, criterion in enumerate(spec.criteria, 1):
            mandatory_label = "[OBRIGATÓRIO]" if criterion.is_mandatory else "[OPCIONAL/INFORMATIVO]"
            lines.append(f"{i}. {mandatory_label} {criterion.name}:")
            lines.append(f"   Descrição: {criterion.description}")
            
            if criterion.rule_type == RuleType.DOC_TYPE:
                acc = criterion.params.get("accepted_types", [])
                forb = criterion.params.get("forbidden_types", [])
                if acc:
                    lines.append(f"   - Tipos aceitos: {', '.join(acc)}")
                if forb:
                    lines.append(f"   - REJEITAR TERMINANTEMENTE se for: {', '.join(forb)}")
            
            elif criterion.rule_type == RuleType.COMPLETENESS:
                if criterion.params.get("requires_both_sides"):
                    lines.append("   - É OBRIGATÓRIO conter Frente e Verso (exceto se for documento digital único com QR Code legível).")

            elif criterion.rule_type == RuleType.HOLDER_MATCH:
                mode = criterion.params.get("matching_mode", "FLEXIBLE")
                if mode == "IGNORE":
                    lines.append("   - NÃO EXIGIR NOME DO ALUNO (Documento pode estar em nome de terceiros/familiares).")
                else:
                    lines.append(f"   - O nome no documento DEVE ser compatível com '{student_name}' (aceite abreviações e mudança de sobrenome por casamento/divórcio).")

            elif criterion.rule_type == RuleType.DIGITAL_SIGNATURE:
                lines.append("   - Conformidade com a Portaria MEC 315/2018 e 360/2022: Verificar a presença e validade de Assinatura Digital ICP-Brasil / Gov.br, carimbo do tempo ou QR Code/código verificador de autenticidade ativo.")

            elif criterion.rule_type == RuleType.STAMP_LEGIBILITY:
                lines.append("   - Carimbo e Fé Pública Escolar: Verificar a nitidez, legibilidade e integridade do carimbo da instituição/diretoria de ensino ou carimbo de 'confere com o original' e visto da inspeção escolar.")

            elif criterion.rule_type == RuleType.CIVIL_ANNOTATION:
                lines.append("   - Averbação Civil: Em caso de divergência ou alteração de nome (casamento, separação, divórcio), verificar a presença de averbação civil no registro que comprove a continuidade da titularidade.")

            elif criterion.rule_type == RuleType.FIELD_EXTRACTION:
                fields = criterion.params.get("fields", [])
                for f in fields:
                    extraction_fields.append(f)

        lines.append("")
        lines.append("--- INSTRUÇÃO DE SAÍDA OBRIGATÓRIA (JSON) ---")
        lines.append("Responda ESTRITAMENTE em formato JSON com a seguinte estrutura:")
        
        schema_dict = {
            "document_identified_type": "string (tipo exato do documento identificado)",
            "is_valid_type": "boolean (se corresponde ao esperado)",
            "has_front_and_back": "boolean (se completo)",
            "is_legible": "boolean (se nítido)",
            "has_digital_signature": "boolean (se possui assinatura digital ICP-Brasil/Gov.br ou validador oficial)",
            "has_legible_school_stamp": "boolean (se o carimbo escolar/inspeção está nítido e autêntico)",
            "has_civil_annotation": "boolean (se averbação civil de alteração de nome está presente/regular)",
            "holder_name_matches": "boolean (se o nome confere ou se titularidade foi dispensada)",
            "all_mandatory_criteria_met": "boolean (true se preencher todos os requisitos obrigatórios)",
            "rejection_reasons": ["string (lista de motivos se rejeitado)"],
            "summary_feedback": "string (justificativa clara)",
            "extracted_data": {f["field_name"]: "string|null" for f in extraction_fields}
        }
        lines.append("```json")
        lines.append(json.dumps(schema_dict, indent=2, ensure_ascii=False))
        lines.append("```")

        return "\n".join(lines)


class CriteriaEvaluator:
    """Motor de avaliação determinística: confere os critérios e emite o parecer final."""

    @staticmethod
    def evaluate(
        spec: DocumentSpecification,
        student_name: str,
        ai_response: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Recebe a resposta da IA e os dados de negócio, avalia critério por critério
        e retorna o veredito final com o status de cada regra.
        """
        results_per_criterion = []
        is_globally_approved = True
        extracted_data = ai_response.get("extracted_data", {})
        reasons = []

        for criterion in spec.criteria:
            passed = True
            detail = ""

            if criterion.rule_type == RuleType.DOC_TYPE:
                passed = ai_response.get("is_valid_type", False)
                identified = ai_response.get("document_identified_type", "DESCONHECIDO")
                detail = f"Identificado: '{identified}'. Válido: {passed}"

            elif criterion.rule_type == RuleType.COMPLETENESS:
                passed = ai_response.get("has_front_and_back", True)
                detail = "Frente e verso / completude confirmada" if passed else "Documento incompleto (ausência de verso ou páginas)"

            elif criterion.rule_type == RuleType.QUALITY_CHECK:
                passed = ai_response.get("is_legible", False)
                detail = "Documento legível" if passed else "Documento com legibilidade comprometida"

            elif criterion.rule_type == RuleType.HOLDER_MATCH:
                mode = criterion.params.get("matching_mode", "FLEXIBLE")
                if mode == "IGNORE":
                    passed = True
                    detail = "Titularidade dispensada por regra de negócio"
                else:
                    passed = ai_response.get("holder_name_matches", False)
                    # Cross-check determinístico em código se o nome do aluno estiver extraído
                    extracted_name = extracted_data.get("nome_completo") or extracted_data.get("nome_aluno")
                    if extracted_name and not passed:
                        if flexible_name_match(extracted_name, student_name):
                            passed = True
                            detail = f"Nome aceito via correspondência flexível ('{extracted_name}' compatível com '{student_name}')"
                    if not passed:
                        detail = f"Nome divergente do cadastro do aluno ('{student_name}')"

            elif criterion.rule_type == RuleType.DIGITAL_SIGNATURE:
                passed = ai_response.get("has_digital_signature", False)
                detail = "Assinatura digital / validação eletrônica em conformidade com a Portaria MEC 315/2018" if passed else "Ausência de assinatura digital válida ou código verificador ilegível"

            elif criterion.rule_type == RuleType.STAMP_LEGIBILITY:
                passed = ai_response.get("has_legible_school_stamp", True)
                detail = "Carimbo escolar e visto de inspeção nítidos e autênticos" if passed else "Carimbo escolar ou visto de inspeção ilegível/ausente"

            elif criterion.rule_type == RuleType.CIVIL_ANNOTATION:
                passed = ai_response.get("has_civil_annotation", True)
                detail = "Averbação civil de alteração de nome devidamente comprovada" if passed else "Ausência de averbação civil para comprovação de mudança de nome"

            elif criterion.rule_type == RuleType.FIELD_EXTRACTION:
                # Regras de normalização e validação especial (ex: CPF)
                if "numero_cpf" in extracted_data and extracted_data["numero_cpf"]:
                    raw_cpf = extracted_data["numero_cpf"]
                    cpf_clean = re.sub(r'\D', '', str(raw_cpf))
                    if len(cpf_clean) == 11:
                        extracted_data["numero_cpf"] = format_cpf(raw_cpf)
                        if criterion.params.get("validate_check_digits"):
                            cpf_ok = validate_cpf_digits(raw_cpf)
                            if not cpf_ok:
                                detail = "CPF com dígitos verificadores inválidos"
                                if criterion.is_mandatory:
                                    passed = False
                    else:
                        detail = f"CPF extraído incompleto: {raw_cpf}"

            if not passed and criterion.is_mandatory:
                is_globally_approved = False
                reasons.append(criterion.failure_message)

            results_per_criterion.append({
                "criterion_id": criterion.id,
                "name": criterion.name,
                "is_mandatory": criterion.is_mandatory,
                "passed": passed,
                "detail": detail
            })

        final_reason = " | ".join(reasons) if reasons else ai_response.get("summary_feedback", "Documento aprovado.")

        return {
            "document_id": spec.id,
            "display_name": spec.display_name,
            "status": "approved" if is_globally_approved else "rejected",
            "is_approved": is_globally_approved,
            "reason": final_reason,
            "extracted_data": extracted_data,
            "criteria_results": results_per_criterion
        }
