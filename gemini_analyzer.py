# ARQUIVO: gemini_analyzer.py (Versão BLINDADA contra arquivos vazios, erro 429 e com formatação de CPF)
# DESCRIÇÃO: Inclui verificação de arquivo vazio, Retry para Cota e formatação automática de CPF (XXX.XXX.XXX-XX).

import logging
import base64
import json
import io 
import time 
import random 
import re  # Adicionado para manipulação de Regex no CPF
import vertexai
from vertexai.generative_models import GenerativeModel, Part, GenerationConfig
from google.cloud import documentai
from google.api_core.exceptions import GoogleAPICallError, PermissionDenied, Unauthenticated, ResourceExhausted

document_processor = None
try:
    import document_processor
except ImportError:
    logging.warning("Módulo 'document_processor' não encontrado. A sanitização de imagens será ignorada.")

KEY_MAPPING = {
    "nome completo": "nome_completo", "filiação": "filiacao", "registro geral": "numero_rg",
    "rg": "numero_rg", "órgão expedidor": "orgao_expedidor", "cpf": "numero_cpf",
    "data de conclusão": "data_conclusao", "instituição de ensino": "instituicao_ensino",
    "nome do curso": "nome_curso", "carga horária total": "carga_horaria_total",
    "colação de grau": "data_colacao_grau",
    "número de registro oficial do diploma": "numero_registro_diploma",
    "número de inscrição": "numero_inscricao_eleitor",
    "número de alistamento militar": "numero_alistamento_militar",
    "rne": "numero_rne", "registro nacional de estrangeiro": "numero_rne",
    "crnm": "numero_rne", "classificação": "classificacao_visto"
}

def _generate_dynamic_schema(criteria_list: list) -> str:
    schema_fields = set()
    schema_fields.add('          "nome_aluno_sistema": "string|null"')
    
    for criterion in criteria_list:
        criterion_lower = criterion.lower()
        for keyword, key in KEY_MAPPING.items():
            if keyword in criterion_lower:
                schema_fields.add(f'          "{key}": "string|null"')
    
    if len(schema_fields) <= 1: 
        base_fields = [
            '          "nome_completo": "string|null"',
            '          "numero_cpf": "string|null"',
            '          "numero_rg": "string|null"'
        ]
        schema_fields.update(base_fields)
        
    return ",\n".join(sorted(list(schema_fields)))

class DocumentAIAnalyzer:
    def __init__(self, project_id: str, location: str):
        if not project_id or not location:
            raise ValueError("Project ID e Location são obrigatórios.")
        self.project_id = project_id
        self.location = location
        logging.info(f"Analisador a ser inicializado com project_id='{self.project_id}' e location='{self.location}'.")

        self.doc_ai_client = None
        self.initialization_error = None
        try:
            self.doc_ai_client = documentai.DocumentProcessorServiceClient(
                client_options={"api_endpoint": f"{location}-documentai.googleapis.com"}
            )
            
            vertexai_location = "us-central1"
            vertexai.init(project=self.project_id, location=vertexai_location)

            logging.info(f"DocumentAI inicializado na região '{location}'. VertexAI inicializado na região '{vertexai_location}'.")
        except Exception as e:
            self.initialization_error = f"Falha ao inicializar os clientes do Google Cloud: {e}"
            logging.critical(f"[ERRO DE INICIALIZAÇÃO] {self.initialization_error}")

    def classify_document_type(self, processor_id: str, processor_version_id: str, file_content_bytes: bytes, mime_type: str):
        if self.initialization_error:
            return None, self.initialization_error
        
        try:
            clean_content_bytes = file_content_bytes
            clean_mime_type = mime_type

            if document_processor:
                try:
                    stream_in = io.BytesIO(file_content_bytes)
                    clean_stream, clean_mime_type = document_processor.prepare_file_for_api(stream_in)
                    clean_content_bytes = clean_stream.read()
                    logging.info(f"Arquivo sanitizado: {mime_type} -> {clean_mime_type}")
                except Exception as dp_error:
                    logging.warning(f"Falha na sanitização, usando arquivo original: {dp_error}")
            
            name = self.doc_ai_client.processor_version_path(
                self.project_id, self.location, processor_id, processor_version_id
            ) if processor_version_id else self.doc_ai_client.processor_path(
                self.project_id, self.location, processor_id
            )
            
            raw_document = documentai.RawDocument(content=clean_content_bytes, mime_type=clean_mime_type)
            request = documentai.ProcessRequest(name=name, raw_document=raw_document, skip_human_review=True)
            
            for attempt in range(3):
                try:
                    result = self.doc_ai_client.process_document(request=request)
                    break
                except ResourceExhausted:
                    time.sleep(2 * (attempt + 1))
            else:
                 return None, "Erro de Cota no Document AI após retries."

            document = result.document

            if not document.entities:
                return None, "Não foi possível classificar o tipo do documento (nenhuma entidade encontrada)."

            best_entity = max(document.entities, key=lambda e: e.confidence)

            if best_entity.confidence > 0.50:
                document_type = best_entity.type_
                logging.info(f"[ETAPA 1 SUCESSO] Classificado como: '{document_type}' com {best_entity.confidence:.2%} de confiança.")
                
                standardized_type = document_type.replace("-", " ").replace("_", " ").upper()
                return standardized_type, None
            else:
                return None, f"Baixa confiança na classificação: '{best_entity.type_}' ({best_entity.confidence:.2%})."

        except (GoogleAPICallError, PermissionDenied, Unauthenticated) as api_err:
             logging.error(f"[ETAPA 1 ERRO API] {api_err}", exc_info=True)
             return None, f"Erro de conexão com API Google: {api_err}"
        except Exception as e:
            logging.error(f"[ETAPA 1 ERRO GERAL] {e}", exc_info=True)
            return None, f"Erro interno na classificação: {e}"

    def _infer_doc_type_from_criteria(self, criteria_list: list) -> str:
        text_criteria = " ".join(criteria_list).lower()
        if "rne" in text_criteria or "estrangeiro" in text_criteria or "migrat" in text_criteria or "crnm" in text_criteria:
            return "RNE - REGISTRO NACIONAL DE ESTRANGEIRO"
        if "diploma" in text_criteria:
            return "DIPLOMA DE GRADUACAO"
        if "histórico" in text_criteria or "historico" in text_criteria:
            return "HISTORICO DE GRADUACAO"
        if "conclusão" in text_criteria or "conclusao" in text_criteria or "curso" in text_criteria:
            return "DOCUMENTO ACADEMICO"
        if "cnh" in text_criteria or "habilitação" in text_criteria or "motorista" in text_criteria:
            return "CNH"
        if "rg" in text_criteria or "registro geral" in text_criteria or "expedidor" in text_criteria or "identidade" in text_criteria:
            return "RG"
        if "residência" in text_criteria or "residencia" in text_criteria or "endereço" in text_criteria or "luz" in text_criteria:
            return "COMPROVANTE DE RESIDENCIA"
        if ("casamento" in text_criteria and "nascimento" in text_criteria) or "civil" in text_criteria:
            return "CERTIDAO DE NASCIMENTO OU CASAMENTO"
        if "casamento" in text_criteria:
            return "CERTIDAO DE CASAMENTO"
        if "nascimento" in text_criteria:
            return "CERTIDAO DE NASCIMENTO"
        return "DOCUMENTO"

    def validate_document_with_gemini(self, files_data: list, criteria_list: list, nome_aluno_sistema: str = "", expected_doc_type: str = None):
        if self.initialization_error:
            return None, self.initialization_error
        
        try:
            if not expected_doc_type:
                expected_doc_type = self._infer_doc_type_from_criteria(criteria_list)
                logging.info(f"Inferido tipo: '{expected_doc_type}'")

            model = GenerativeModel("gemini-2.5-flash") 
            dynamic_schema = _generate_dynamic_schema(criteria_list)
            
            prompt = (
                "Você é um analista de documentos sênior e robótico (rigoroso). Sua tarefa é analisar o(s) ficheiro(s) e responder APENAS com um objeto JSON no formato especificado.\n\n"
                
                f"**CONTEXTO DA ANÁLISE:**\n"
                f"O sistema está aguardando estritamente um documento do tipo: **{expected_doc_type.upper()}**.\n"
                f"Nome do Aluno para validação: {nome_aluno_sistema}\n\n"

                "**REGRAS DE VALIDAÇÃO (SEGUIR NESTA ORDEM EXATA):**\n"
                f"1. **VALIDAÇÃO DE TIPO (CRÍTICO - REGRA DE OURO):** Identifique o tipo do documento enviado. Se o documento enviado NÃO FOR um **{expected_doc_type}**, você DEVE retornar `isValid: false` imediatamente.\n"
                "   - Exemplo A: Se o esperado é 'RG' e o aluno enviou uma 'CNH', o documento é **INVÁLIDO**.\n"
                "   - Exceção 1: Se o esperado for 'CNH', obviamente aceite CNH.\n"
                "   - **REGRA CRÍTICA PARA RNE (Estrangeiros):** Se o esperado for 'RNE - REGISTRO NACIONAL DE ESTRANGEIRO', você deve aceitar **APENAS**:\n"
                "     - RNE (Registro Nacional de Estrangeiro) antigo (CIE).\n"
                "     - CRNM (Carteira de Registro Nacional Migratório) nova.\n"
                "     - Protocolo de solicitação de refúgio (se legível e oficial).\n"
                "     - **ATENÇÃO:** Se o esperado for RNE, você **NÃO PODE** aceitar RG Brasileiro (Civil) nem CNH. Deve retornar `isValid: false` com o motivo 'Tipo incorreto: Exigido RNE/CRNM para estrangeiros'.\n"
                "   - **REGRA CRÍTICA PARA ACADÊMICOS (DIPLOMA vs HISTÓRICO):**\n"
                "     - Se o esperado for **'DIPLOMA DE GRADUACAO'**: Aceite APENAS Diplomas ou Certificados de Conclusão oficiais. **REJEITE IMEDIATAMENTE** se for um 'Histórico Escolar' (lista de notas) ou 'Declaração de Matrícula'. Motivo: 'Tipo incorreto: Enviado Histórico/Declaração, exigido Diploma'.\n"
                "     - Se o esperado for **'HISTORICO DE GRADUACAO'**: Aceite APENAS o Histórico Escolar (documento com grade curricular, notas e disciplinas). **REJEITE IMEDIATAMENTE** se for apenas um 'Diploma' (certificado de uma página) sem a grade de notas. Motivo: 'Tipo incorreto: Enviado Diploma, exigido Histórico'.\n"
                "   - Exceção 3: Se o esperado for genérico 'DOCUMENTO' ou 'DOCUMENTO ACADEMICO', aceite ambos.\n"
                "2. **VERIFIQUE COMPLETUDE:**\n"
                "   - Para RG/RNE: Frente e Verso são obrigatórios. Se faltar um lado, é inválido.\n"
                "   - Para CNH: Frente e Verso (ou CNH digital aberta) são aceitos.\n"
                "3. **EXTRAIA DADOS:** Se o tipo estiver correto, extraia as informações solicitadas nos critérios abaixo para o objeto `extracted_data`.\n"
                "   - **REGRA DE EXCLUSIVIDADE:** As informações de **RG, CPF, RNE e Órgão Expedidor** DEVEM ser extraídas APENAS se o documento for do tipo de identidade correto. Se o documento for de outro tipo (ex: Certidão, Diploma), retorne `null` para estes campos, mesmo que eles apareçam no texto.\n"
                "4. **VALIDAÇÃO DE TITULARIDADE (AJUSTADA PARA CASOS DE MUDANÇA DE NOME):**\n"
                "   - **SE FOR COMPROVANTE DE RESIDÊNCIA:** IGNORE O NOME DO TITULAR. O documento PODE estar em nome de terceiros.\n"
                "   - **SE FOR OUTRO DOCUMENTO (RG, CNH, RNE, DIPLOMA):** O nome no documento DEVE corresponder ao nome do aluno.\n"
                "     **IMPORTANTE:** ACEITE divergências causadas por casamento ou abreviações.\n\n"
                
                f"**Critérios para Extração:**\n- {', '.join(criteria_list)}\n\n"
                
                "**REGRAS PARA O CAMPO `reasoning`:**\n"
                "1. **SE O DOCUMENTO FOR VÁLIDO (`isValid: true`):** Use o formato: 'Documento aprovado. Verificação dos critérios: [critério 1: DADO ENCONTRADO]...'.\n"
                "2. **SE O DOCUMENTO FOR INVÁLIDO (`isValid: false`):** Explique claramente o motivo (ex: 'Documento rejeitado. O tipo enviado foi Histórico Escolar, mas o solicitado era estritamente Diploma de Graduação.').\n\n"
                
                "**Formato JSON de Saída OBRIGATÓRIO:**\n"
                "```json\n"
                "{\n"
                '  "document_type": "string (tipo identificado)",\n'
                '  "isValid": boolean,\n'
                '  "reasoning": "string",\n'
                '  "extracted_data": {\n'
                f"{dynamic_schema}\n"
                '  }\n'
                "}\n"
                "```"
            )

            content_parts = [prompt]
            
            for file_data in files_data:
                # --- CORREÇÃO DE ERRO 400 (DOCUMENT HAS NO PAGES) ---
                # Se o arquivo estiver vazio (falha de download), ignora para não travar a IA
                if not file_data.get('content'):
                    logging.warning(f"Arquivo '{file_data.get('name')}' ignorado pois está vazio (0 bytes).")
                    continue

                file_bytes = file_data['content']
                file_mime = "application/pdf" if file_data.get("name", "").lower().endswith(".pdf") else "image/png"
                
                if document_processor:
                    try:
                        stream_in = io.BytesIO(file_bytes)
                        clean_stream, clean_mime = document_processor.prepare_file_for_api(stream_in)
                        file_bytes = clean_stream.read()
                        file_mime = clean_mime
                    except Exception as e:
                        logging.warning(f"Erro ao sanitizar arquivo para o Gemini, enviando original: {e}")

                content_parts.append(Part.from_data(
                    mime_type=file_mime,
                    data=file_bytes
                ))

            # Se todos os arquivos foram ignorados (vazios), retorna erro controlado
            if len(content_parts) == 1: # Só tem o prompt
                return None, "Todos os arquivos enviados estavam vazios ou corrompidos."

            generation_config = GenerationConfig(response_mime_type="application/json")

            max_gemini_retries = 3
            for attempt in range(max_gemini_retries):
                try:
                    response = model.generate_content(content_parts, generation_config=generation_config)
                    validation_result = json.loads(response.text)

                    # --- INICIO BLOCO DE FORMATACAO DE CPF ---
                    # Formata o CPF para o padrao 000.000.000-00 se ele tiver sido extraido
                    if 'extracted_data' in validation_result:
                        extracted = validation_result['extracted_data']
                        raw_cpf = extracted.get('numero_cpf')
                        
                        if raw_cpf:
                            # Remove tudo que não for dígito
                            cpf_limpo = re.sub(r'\D', '', str(raw_cpf))
                            
                            # Verifica se tem 11 dígitos para formatar corretamente
                            if len(cpf_limpo) == 11:
                                cpf_formatado = f"{cpf_limpo[:3]}.{cpf_limpo[3:6]}.{cpf_limpo[6:9]}-{cpf_limpo[9:]}"
                                validation_result['extracted_data']['numero_cpf'] = cpf_formatado
                                logging.info(f"CPF formatado com sucesso: {cpf_formatado}")
                            else:
                                # Se não tiver 11 dígitos, mantém o original (pode ser erro de OCR ou CPF incompleto)
                                logging.warning(f"CPF extraído não possui 11 dígitos ({raw_cpf}), mantendo original.")
                    # --- FIM BLOCO DE FORMATACAO DE CPF ---

                    if 'extracted_data' in validation_result and nome_aluno_sistema:
                        validation_result['extracted_data']['nome_aluno_sistema'] = nome_aluno_sistema

                    return validation_result, None
                
                except ResourceExhausted:
                    wait_time = 5 * (attempt + 1) + random.uniform(0, 2)
                    logging.warning(f"Cota Gemini Excedida (429). Aguardando {wait_time:.1f}s... (Tentativa {attempt+1}/{max_gemini_retries})")
                    time.sleep(wait_time)
                except Exception as inner_e:
                     if "503" in str(inner_e):
                         time.sleep(2)
                         continue
                     raise inner_e
            
            return None, "Falha na validação Gemini: Cota excedida após múltiplas tentativas."
            
        except Exception as e:
            logging.error(f"[ERRO DE VALIDAÇÃO GEMINI] Erro inesperado: {e}", exc_info=True)
            error_details = getattr(e, 'response', e)
            return None, f"Erro na validação com Gemini: {error_details}"