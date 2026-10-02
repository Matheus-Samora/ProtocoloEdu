"""
Conector de Inteligência Artificial usando a API oficial do Google Gemini.
Integrado ao Compilador Dinâmico de Prompts e ao Pipeline de Mídia.
Inclui failover resiliente, rotação automática de chaves contra 429/403,
e mascaramento de erros técnicos para preservar a integridade da experiência do estudante.
"""

import os
import json
import time
import random
import logging
from typing import Dict, Any, List, Optional, Tuple

import google.generativeai as genai
from google.api_core.exceptions import ResourceExhausted, GoogleAPICallError

from core_criteria_models import DocumentSpecification
from criteria_engine import PromptCompiler, CriteriaEvaluator
from media.models import ProcessedMedia

logger = logging.getLogger("GEMINI_SERVICE")

# Modelos suportados com failover automático contra exaustão de cota
AVAILABLE_MODELS = ["gemini-3.5-flash-lite", "gemini-2.5-flash", "gemini-2.5-pro"]
DEFAULT_MODEL_NAME = AVAILABLE_MODELS[0]

# Mensagem institucional apresentada ao estudante caso a verificação automática precise de revisão manual
STUDENT_IN_REVIEW_MESSAGE = (
    "Documento recebido com sucesso. O arquivo foi registrado no protocolo institucional "
    "e direcionado para conferência da Secretaria Acadêmica."
)


def get_api_key_candidates() -> List[str]:
    """Obtém a lista de chaves candidatas do Gemini a partir do ambiente e do catálogo."""
    candidates = []
    env_key = os.environ.get("GEMINI_API_KEY")
    if env_key and env_key.startswith("AIza"):
        candidates.append(env_key)

    try:
        from key_manager import get_all_keys
        for k in get_all_keys():
            if k and k.startswith("AIza") and k not in candidates:
                candidates.append(k)
    except Exception as e:
        logger.warning(f"Não foi possível carregar chaves adicionais do key_manager: {e}")

    # Fallback seguro com chave operacional
    if not candidates:
        candidates.append("")

    return candidates


class GeminiDocumentAuditor:
    """Auditor documental inteligente baseado no Google Gemini com failover e mascaramento seguro."""

    def __init__(self, api_key: Optional[str] = None, model_name: str = DEFAULT_MODEL_NAME):
        self.api_keys = [api_key] if api_key else get_api_key_candidates()
        self.current_key_index = 0
        self.models_pool = list(AVAILABLE_MODELS)
        self.current_model_index = 0
        self.model_name = model_name
        self._configure()

    @property
    def current_api_key(self) -> str:
        if 0 <= self.current_key_index < len(self.api_keys):
            return self.api_keys[self.current_key_index]
        return self.api_keys[0] if self.api_keys else ""

    def _configure(self):
        """Inicializa a biblioteca oficial google.generativeai com a chave e modelo ativos."""
        key = self.current_api_key
        try:
            genai.configure(api_key=key)
            self.model = genai.GenerativeModel(self.model_name)
            masked_key = f"{key[:8]}...{key[-4:]}" if len(key) > 12 else "***"
            logger.info(f"Conexão com Gemini configurada (Modelo: '{self.model_name}', Chave: {masked_key}).")
        except Exception as e:
            logger.critical(f"Falha ao configurar a API do Google Gemini: {e}")

    def rotate_key(self) -> bool:
        """Alterna para a próxima chave de API disponível se houver falha de autenticação ou cota."""
        if len(self.api_keys) > 1:
            self.current_key_index = (self.current_key_index + 1) % len(self.api_keys)
            logger.warning(f"Alternando para chave de contingência {self.current_key_index + 1}/{len(self.api_keys)}...")
            self._configure()
            return True
        return False

    def rotate_model(self) -> bool:
        """Alterna para o próximo modelo de IA se houver exaustão de cota no modelo corrente."""
        if len(self.models_pool) > 1:
            self.current_model_index = (self.current_model_index + 1) % len(self.models_pool)
            self.model_name = self.models_pool[self.current_model_index]
            logger.warning(f"Alternando para modelo de contingência: '{self.model_name}'...")
            self._configure()
            return True
        return False

    def generate_text(self, prompt: str, max_retries: int = 3) -> str:
        """Gera texto para o assistente virtual com retries e rotação automática de modelos."""
        for attempt in range(max_retries):
            try:
                res = self.model.generate_content(prompt)
                if res and res.text:
                    return res.text
            except Exception as e:
                logger.warning(f"Falha na geração de texto ({self.model_name}): {e}. Tentando contingência...")
                if self.rotate_model() or self.rotate_key():
                    continue
                time.sleep(1)
        return "Olá! A Secretaria Acadêmica está à disposição para auxiliá-lo na entrega dos documentos de matrícula."

    def audit_document(
        self,
        media_list: List[ProcessedMedia],
        spec: DocumentSpecification,
        student_name: str,
        max_retries: int = 3
    ) -> Dict[str, Any]:
        """
        Executa a auditoria completa de um documento.
        Em caso de qualquer falha técnica de infraestrutura, mascara a resposta para o estudante
        e armazena o diagnóstico técnico em 'admin_diagnostic' para visualização exclusiva da Secretaria/TI.
        """
        if not media_list:
            return {
                "document_id": spec.id,
                "display_name": spec.display_name,
                "status": "in_review",
                "is_approved": False,
                "system_error": True,
                "reason": STUDENT_IN_REVIEW_MESSAGE,
                "admin_diagnostic": "[ENTRADA INVÁLIDA]: Nenhum arquivo legível recebido para conferência.",
                "criteria_results": []
            }

        try:
            # 1. Compila o prompt dinâmico baseado estritamente nos critérios do catálogo
            prompt_text = PromptCompiler.compile_gemini_prompt(spec, student_name)

            # 2. Prepara os blocos de conteúdo (Prompt + Partes de Mídia)
            content_parts = [prompt_text]
            for media in media_list:
                if not media.content_bytes:
                    continue
                content_parts.append({
                    "mime_type": media.mime_type,
                    "data": media.content_bytes
                })

            # 3. Força resposta estruturada em JSON
            generation_config = genai.types.GenerationConfig(
                response_mime_type="application/json",
                temperature=0.1
            )

            # 4. Execução resiliente com retries e rotação de credenciais
            raw_response_text = ""
            last_exception = None

            for attempt in range(max_retries):
                try:
                    response = self.model.generate_content(
                        content_parts,
                        generation_config=generation_config
                    )
                    raw_response_text = response.text
                    last_exception = None
                    break
                except ResourceExhausted as e:
                    last_exception = e
                    wait_time = 2 * (attempt + 1)
                    logger.warning(f"Cota de requisições 429 no modelo '{self.model_name}'. Rotacionando modelo ou chave...")
                    if self.rotate_model() or self.rotate_key():
                        continue
                    time.sleep(wait_time)
                except Exception as e:
                    last_exception = e
                    err_msg = str(e)
                    logger.error(f"Erro na chamada ao Gemini ({type(e).__name__}): {err_msg}")
                    # Se for erro 403 (leaked/invalid key) ou permission denied, rotaciona imediatamente
                    if "403" in err_msg or "leaked" in err_msg.lower() or "permission_denied" in err_msg.lower():
                        if self.rotate_key():
                            continue
                    time.sleep(1.5)

            # Se todas as tentativas falharam
            if last_exception or not raw_response_text:
                logger.warning(f"Falha técnica persistente na auditoria de '{spec.id}'. Mascarando resposta para o aluno.")
                return {
                    "document_id": spec.id,
                    "display_name": spec.display_name,
                    "status": "in_review",
                    "is_approved": False,
                    "system_error": True,
                    "reason": STUDENT_IN_REVIEW_MESSAGE,
                    "admin_diagnostic": f"[FALHA DE INFRAESTRUTURA IA]: {type(last_exception).__name__}: {str(last_exception)}",
                    "criteria_results": []
                }

            # 5. Parsing da resposta JSON da IA
            try:
                ai_data = json.loads(raw_response_text)
            except json.JSONDecodeError as json_err:
                logger.error(f"Resposta da IA não veio em JSON válido: {raw_response_text[:200]}")
                return {
                    "document_id": spec.id,
                    "display_name": spec.display_name,
                    "status": "in_review",
                    "is_approved": False,
                    "system_error": True,
                    "reason": STUDENT_IN_REVIEW_MESSAGE,
                    "admin_diagnostic": f"[FALHA DE PARSER JSON]: Resposta recebida: {raw_response_text[:300]}",
                    "criteria_results": []
                }

            # 6. Avaliação determinística critério por critério
            verdict = CriteriaEvaluator.evaluate(spec, student_name, ai_data)
            verdict["system_error"] = False
            verdict["admin_diagnostic"] = None
            logger.info(
                f"Auditoria concluída para '{spec.display_name}': "
                f"Status = {verdict['status'].upper()} | Motivo = {verdict['reason'][:80]}"
            )
            return verdict

        except Exception as unhandled_err:
            logger.error(f"Exceção não tratada na auditoria de '{spec.id}': {unhandled_err}", exc_info=True)
            return {
                "document_id": spec.id,
                "display_name": spec.display_name,
                "status": "in_review",
                "is_approved": False,
                "system_error": True,
                "reason": STUDENT_IN_REVIEW_MESSAGE,
                "admin_diagnostic": f"[ERRO INESPERADO DO MOTOR]: {type(unhandled_err).__name__}: {str(unhandled_err)}",
                "criteria_results": []
            }
