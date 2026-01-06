# ARQUIVO: gemini_analyzer.py (Versão com Lógica RNE Estrita + Diploma/Histórico Separados)
# DESCRIÇÃO: Módulo responsável pela análise de documentos usando Google Document AI (Classificação)
#            e Google Gemini (Extração e Validação).
#            Inclui suporte seguro para sanitização de imagens via document_processor.

import logging
import base64
import json
import io  # Necessário para manipulação de streams
import vertexai
from vertexai.generative_models import GenerativeModel, Part, GenerationConfig
from google.cloud import documentai
from google.api_core.exceptions import GoogleAPICallError, PermissionDenied, Unauthenticated

# Tenta importar o processador de documentos para limpeza de imagens
document_processor = None
try:
    import document_processor
except ImportError:
    logging.warning("Módulo 'document_processor' não encontrado. A sanitização de imagens será ignorada.")

# Mapeamento de chaves para padronização do JSON de saída
# ATUALIZADO: Incluído suporte para RNE
KEY_MAPPING = {
    "nome completo": "nome_completo", "filiação": "filiacao", "registro geral": "numero_rg",
    "rg": "numero_rg", "órgão expedidor": "orgao_expedidor", "cpf": "numero_cpf",
    "data de conclusão": "data_conclusao", "instituição de ensino": "instituicao_ensino",
    "nome do curso": "nome_curso", "carga horária total": "carga_horaria_total",
    "colação de grau": "data_colacao_grau",
    "número de registro oficial do diploma": "numero_registro_diploma",
    "número de inscrição": "numero_inscricao_eleitor",
    "número de alistamento militar": "numero_alistamento_militar",
    # Mapeamentos específicos para RNE
    "rne": "numero_rne", "registro nacional de estrangeiro": "numero_rne",
    "crnm": "numero_rne", "classificação": "classificacao_visto"
}

def _generate_dynamic_schema(criteria_list: list) -> str:
    """Gera o schema JSON dinamicamente com base nos critérios solicitados."""
    schema_fields = set()
    # Adiciona o novo campo fixo ao schema para comparação posterior
    schema_fields.add('          "nome_aluno_sistema": "string|null"')
    
    for criterion in criteria_list:
        criterion_lower = criterion.lower()
        for keyword, key in KEY_MAPPING.items():
            if keyword in criterion_lower:
                schema_fields.add(f'          "{key}": "string|null"')
    
    # Se não encontrar critérios específicos, adiciona campos base
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
        """
        Classifica o tipo do documento usando o Document AI.
        Inclui sanitização prévia (HEIC->JPG) SE o módulo estiver disponível.
        """
        if self.initialization_error:
            return None, self.initialization_error
        
        try:
            # 1. Prepara o conteúdo (limpeza opcional)
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
            result = self.doc_ai_client.process_document(request=request)
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
        """
        Tenta adivinhar o tipo de documento baseado nas palavras-chave dos critérios.
        Prioridade ajustada para evitar falsos positivos e separar Diploma de Histórico.
        """
        text_criteria = " ".join(criteria_list).lower()
        
        # 1. RNE / Documentos de Estrangeiro (PRIORIDADE MÁXIMA)
        if "rne" in text_criteria or "estrangeiro" in text_criteria or "migrat" in text_criteria or "crnm" in text_criteria:
            return "RNE - REGISTRO NACIONAL DE ESTRANGEIRO"

        # 2. Documentos Acadêmicos (SEPARADOS)
        if "diploma" in text_criteria:
            return "DIPLOMA DE GRADUACAO"
        
        if "histórico" in text_criteria or "historico" in text_criteria:
            return "HISTORICO DE GRADUACAO"
            
        # Fallback genérico para acadêmicos se não especificar Diploma ou Histórico
        if "conclusão" in text_criteria or "conclusao" in text_criteria or "curso" in text_criteria:
            return "DOCUMENTO ACADEMICO"
            
        # 3. CNH
        if "cnh" in text_criteria or "habilitação" in text_criteria or "motorista" in text_criteria:
            return "CNH"

        # 4. Documentos de Identidade Simples (RG)
        if "rg" in text_criteria or "registro geral" in text_criteria or "expedidor" in text_criteria or "identidade" in text_criteria:
            return "RG"

        # 5. Residência
        if "residência" in text_criteria or "residencia" in text_criteria or "endereço" in text_criteria or "luz" in text_criteria:
            return "COMPROVANTE DE RESIDENCIA"

        # 6. Certidões
        if ("casamento" in text_criteria and "nascimento" in text_criteria) or "civil" in text_criteria:
            return "CERTIDAO DE NASCIMENTO OU CASAMENTO"

        if "casamento" in text_criteria:
            return "CERTIDAO DE CASAMENTO"
            
        if "nascimento" in text_criteria:
            return "CERTIDAO DE NASCIMENTO"
            
        return "DOCUMENTO"

    def validate_document_with_gemini(self, files_data: list, criteria_list: list, nome_aluno_sistema: str = "", expected_doc_type: str = None):
        """
        Valida o documento usando o Gemini.
        """
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
                # Lógica Segura de Sanitização
                file_bytes = file_data['content']
                file_mime = "application/pdf" if file_data.get("name", "").lower().endswith(".pdf") else "image/png" # Fallback simples
                
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

            generation_config = GenerationConfig(response_mime_type="application/json")

            response = model.generate_content(content_parts, generation_config=generation_config)
            validation_result = json.loads(response.text)

            if 'extracted_data' in validation_result and nome_aluno_sistema:
                validation_result['extracted_data']['nome_aluno_sistema'] = nome_aluno_sistema

            return validation_result, None
            
        except Exception as e:
            logging.error(f"[ERRO DE VALIDAÇÃO GEMINI] Erro inesperado: {e}", exc_info=True)
            error_details = getattr(e, 'response', e)
            return None, f"Erro na validação com Gemini: {error_details}"