# -*- coding: utf-8 -*-
# ARQUIVO: core_logic.py (Versão Ajustada para Novo Projeto)
# DESCRIÇÃO: Removemos a dependência do Document AI para classificação.
#            Agora, toda a análise de tipo e extração é feita pelo Gemini.

import logging
import json
import re
import unicodedata
import mimetypes
import os
from concurrent.futures import ThreadPoolExecutor
from collections import defaultdict

# Módulos da aplicação
import config
from gemini_analyzer import DocumentAIAnalyzer
from aluno_service import AlunoService
from comparison_logic import flexible_name_comparison

import subprocess
import sys

logging.basicConfig(level=logging.INFO, format='[CORE_LOGIC] [%(levelname)s] %(message)s')

def _get_nested_value(data_dict, key_path):
    if not key_path: return None
    keys = key_path.split('.')
    value = data_dict
    for key in keys:
        if isinstance(value, dict):
            value = value.get(key)
        else:
            return None
    return value

def _get_mime_type(filename):
    mime_type, _ = mimetypes.guess_type(filename)
    return mime_type or 'application/octet-stream'

def _normalize_text(text):
    if not text: return ""
    text = str(text).replace("_", " ")
    nfkd_form = unicodedata.normalize('NFKD', text.upper())
    only_ascii = nfkd_form.encode('ASCII', 'ignore')
    return re.sub(r'[^A-Z0-9\s-]', '', only_ascii.decode('utf-8')).strip()

def _sanitize_student_name(name):
    if not name: return ""
    nfkd_form = unicodedata.normalize('NFKD', str(name).upper())
    only_ascii = nfkd_form.encode('ASCII', 'ignore')
    return re.sub(r"[^A-Z0-9\s-]", '', only_ascii.decode('utf-8')).strip()

def _find_criteria_robustly(course_type, doc_key):
    normalized_course_type = _normalize_text(course_type)
    for key, spec in config.DOCUMENT_CRITERIA.items():
        if _normalize_text(key) == normalized_course_type:
            for doc_key_from_criteria, doc_spec in spec.items():
                if _normalize_text(doc_key_from_criteria) == _normalize_text(doc_key):
                    logging.info(f"Critérios encontrados para doc '{doc_key}' no curso '{course_type}'.")
                    return doc_spec
    logging.warning(f"Nenhuma correspondência de critérios encontrada para doc_key '{doc_key}' no curso '{course_type}'.")
    return None

def carregar_configuracao_drive(tenant_id):
    try:
        with open(config.DRIVE_CONFIG_FILE, 'r', encoding='utf-8') as f:
            drive_configs = json.load(f)
        tenant_config = drive_configs.get(tenant_id)
        if not tenant_config:
            logging.error(f"Configuração do Drive para o tenant '{tenant_id}' não encontrada.")
            return None
        return tenant_config
    except FileNotFoundError:
        logging.error(f"Ficheiro de configuração do Drive '{config.DRIVE_CONFIG_FILE}' não encontrado.")
        return None
    except Exception as e:
        logging.error(f"Erro inesperado ao carregar configuração do Drive: {e}")
        return None

def _analyze_single_document_type(doc_key, files_info_list, dados_externos, course_type, analyzer, student_name):
    """
    Orquestra a análise de um tipo de documento usando SOMENTE O GEMINI.
    """
    try:
        # 1. Obter critérios
        doc_spec = _find_criteria_robustly(course_type, doc_key)
        if not doc_spec:
            return doc_key, {"status": "ignored", "reason": f"Sem critérios definidos para '{doc_key}' no curso '{course_type}'."}

        logging.info(f"--- INICIANDO ANÁLISE DE {len(files_info_list)} FICHEIRO(S) PARA '{doc_spec['display_name']}' ---")
        
        # [MODIFICAÇÃO] REMOVIDA A CLASSIFICAÇÃO VIA DOCUMENT AI
        # O Document AI exigiria IDs específicos do projeto novo.
        # Agora confiamos no prompt do Gemini para validar o tipo.
        
        classified_type = "UNKNOWN"
        identified_doc_type = "UNKNOWN"

        # 2. Análise com Gemini (para todos os documentos)
        criteria_list = doc_spec.get("required_fields", [])
        gemini_criteria_prompts = [item.get('description', item) if isinstance(item, dict) else item for item in criteria_list]
        files_data_for_gemini = [{"content": f['content'], "mime_type": _get_mime_type(f['filename']), "name": f['filename']} for f in files_info_list]
        
        # Pega o tipo esperado do JSON
        expected_type = doc_spec.get("expected_doc_type", doc_key)

        validation_result, error = analyzer.validate_document_with_gemini(
            files_data=files_data_for_gemini, 
            criteria_list=gemini_criteria_prompts,
            nome_aluno_sistema=student_name,
            expected_doc_type=expected_type # Passa o tipo esperado para o Gemini validar
        )
        
        if error:
            return doc_key, {"status": "error", "reason": f"[VALIDAÇÃO GEMINI] {error}"}
        
        # 3. Processar o resultado do Gemini
        is_valid = validation_result.get("isValid", False)
        reasoning = validation_result.get("reasoning", "A IA não forneceu uma justificação.")
        extracted_data = validation_result.get("extracted_data", {})
        identified_doc_type = validation_result.get("document_type")

        # 4. Lógica de Negócio Pós-IA (Comparação de campos)
        if is_valid:
            for rule in criteria_list:
                if isinstance(rule, dict) and rule.get("action") == "extract_and_compare":
                    
                    if doc_key == "COMPROVANTE_RESIDENCIA" and "nome" in rule.get("target_field", ""):
                        logging.info(f"Validação de nome ignorada intencionalmente para '{doc_key}'.")
                        continue

                    doc_value = extracted_data.get(rule.get("source_field"))
                    target_value = _get_nested_value(dados_externos, rule.get("target_field"))
                    comparison_mode = rule.get("comparison_mode", "strict_equals")
                    
                    is_match = False
                    if comparison_mode == "flexible_contain":
                        is_match = flexible_name_comparison(doc_value, target_value)
                    else:
                        is_match = (_normalize_text(doc_value) == _normalize_text(target_value))

                    if not is_match:
                        is_valid = False
                        reasoning = f"Dado no documento ('{doc_value}') não corresponde ao esperado ('{target_value}')."
                        break
                    else:
                        reasoning += f" | Validação de dados confirmada: o nome no sistema ('{target_value}') é compatível com o nome no documento ('{doc_value}')."
        
        # 5. Definir o status final
        status = "approved" if is_valid else "rejected"
        
        return doc_key, {
            "status": status, 
            "reason": reasoning, 
            "extracted_data": extracted_data, 
            "classified_doc_type": identified_doc_type, 
            "identified_doc_type": identified_doc_type
        }

    except Exception as e:
        logging.critical(f"Exceção não tratada em _analyze_single_document_type para {doc_key}: {e}", exc_info=True)
        return doc_key, {"status": "error", "reason": f"Erro inesperado no core: {e}"}

def _chamar_processador_de_lotes(gemini_json_response):
    logging.info("Integração: Preparando para enviar resultado ao processador de lotes...")
    try:
        json_string_para_enviar = json.dumps(gemini_json_response)
    except TypeError as e:
        logging.error(f"ERRO DE INTEGRAÇÃO: JSON inválido: {e}")
        return

    caminho_script_processador = "processador_lotes.py"
    if not os.path.exists(caminho_script_processador):
        logging.error(f"ERRO DE INTEGRAÇÃO: Script '{caminho_script_processador}' não encontrado.")
        return

    comando = [ sys.executable, caminho_script_processador, "add", json_string_para_enviar ]
    logging.info(f"Executando comando de integração...")
    resultado = subprocess.run(comando, capture_output=True, text=True, encoding='utf-8')

    if resultado.returncode == 0:
        logging.info("✅ Sucesso na integração!")
    else:
        logging.error("❌ ERRO na integração!")
        logging.error(resultado.stderr.strip())

def iniciar_analise_e_upload(tenant_id, student_name, course_type, uploaded_files_dict):
    dados_externos = {"aluno": {"nome_completo": student_name}}
    student_name_log = student_name or "[NOME INDEFINIDO]"
    logging.info(f"--- INICIANDO PROCESSO COMPLETO PARA '{student_name_log}', CURSO '{course_type}' ---")

    logging.info("A agrupar ficheiros recebidos por tipo de documento...")
    grouped_files = defaultdict(list)
    for key, file_info in uploaded_files_dict.items():
        try:
            doc_type = key.split('-')[1]
            grouped_files[doc_type].append(file_info)
        except IndexError:
            logging.warning(f"Chave inválida ignorada: '{key}'.")
            continue
    
    if not grouped_files:
        return {"success": False, "error": "Nenhum ficheiro válido para análise."}

    # [ATUALIZAÇÃO] Removida inicialização do DocumentAIClient antigo
    try:
        analyzer = DocumentAIAnalyzer(
            project_id=config.PROJECT_ID, 
            location=config.LOCATION,
        )
        servico_aluno = AlunoService()
    except Exception as e:
        logging.critical(f"ERRO CRÍTICO DE CONFIGURAÇÃO: {e}", exc_info=True)
        return {"success": False, "error": f"Erro de configuração: {e}"}

    analysis_results = {}
    logging.info("A iniciar a análise de documentos em paralelo...")
    with ThreadPoolExecutor(max_workers=5) as executor:
        future_to_doc = {}
        for doc_key, files_list in grouped_files.items():
            future = executor.submit(_analyze_single_document_type, doc_key, files_list, dados_externos, course_type, analyzer, student_name)
            future_to_doc[future] = doc_key

        for future in future_to_doc:
            doc_key = future_to_doc[future]
            try:
                _, result = future.result()
                analysis_results[doc_key] = result
                logging.info(f"Análise para '{doc_key}' concluída: {result.get('status')}")
            except Exception as exc:
                analysis_results[doc_key] = {"status": "error", "reason": str(exc)}
                logging.error(f"Exceção em '{doc_key}': {exc}")
    
    logging.info("A iniciar o processo de upload para os documentos aprovados...")
    try:
        tenant_drive_config = carregar_configuracao_drive(tenant_id)
        if not tenant_drive_config:
            raise ValueError(f"Configuração de Drive não encontrada para '{tenant_id}'.")
        
        sanitized_student_name_for_drive = _sanitize_student_name(student_name)
        student_folder_id = servico_aluno.find_or_create_full_student_path(student_name, tenant_drive_config)
        
        if not student_folder_id:
            raise ConnectionError(f"Falha ao obter pasta no Drive para '{sanitized_student_name_for_drive}'.")

        for doc_key, result in analysis_results.items():
            if result.get("status") == "approved":
                files_to_upload = grouped_files.get(doc_key, [])
                uploaded_ids = []
                
                upload_key_base = doc_key
                if doc_key == "CERTIDAO_NASCIMENTO_CASAMENTO":
                    doc_type_norm = _normalize_text(result.get("identified_doc_type", ""))
                    upload_key_base = "CERTIDAO_CASAMENTO" if "CASAMENTO" in doc_type_norm else "CERTIDAO_NASCIMENTO"

                for i, file_info in enumerate(files_to_upload):
                    final_upload_key = upload_key_base
                    if len(files_to_upload) > 1:
                        identity_docs = ["RG", "CNH"]
                        if doc_key in identity_docs:
                            suffix = " FRENTE" if i == 0 else " VERSO" if i == 1 else f" PARTE {i+1}"
                        else:
                            suffix = f" PAG {i+1}"
                        final_upload_key += suffix

                    _, extension = os.path.splitext(file_info['filename'])
                    
                    upload_id = servico_aluno.upload_file(
                        student_name=sanitized_student_name_for_drive,
                        doc_key=final_upload_key,
                        file_content_bytes=file_info['content'],
                        parent_folder_id=student_folder_id,
                        mime_type=_get_mime_type(file_info['filename']),
                        extension=extension or ".pdf"
                    )
                    if upload_id:
                        uploaded_ids.append(upload_id)
                
                if uploaded_ids:
                    result['drive_upload_status'] = 'success'
                    result['drive_file_ids'] = uploaded_ids
                else:
                    result['drive_upload_status'] = 'failed'

    except Exception as e:
        logging.critical(f"ERRO CRÍTICO NA ETAPA DE UPLOAD: {e}", exc_info=True)
        for res in analysis_results.values():
            if res.get("status") == "approved":
                res['drive_upload_status'] = 'failed_due_to_system_error'
    
    final_response = {"success": True, "results": analysis_results}
    _chamar_processador_de_lotes(final_response)

    logging.info(f"--- PROCESSO CONCLUÍDO PARA '{student_name}' ---")
    return final_response