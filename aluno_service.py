# -*- coding: utf-8 -*-
# ARQUIVO: aluno_service.py
# DESCRIÇÃO: Versão FINAL ROBUSTA RESTAURADA + SUPORTE COMPLETO A FRENTE/VERSO/PAGINAÇÃO.
# 
# Changelog Atual:
# 1. FIX SANITIZAÇÃO: Substitui caracteres especiais (como underline) por ESPAÇO para evitar
#    que "HISTORICO_GRADUACAO" vire "HISTORICOGRADUACAO" (o que falhava na busca exata).
# 2. SUPER REGEX: Identifica variações como "Pag 1", "Frente", "Verso", "Folha", "Parte"
#    mesmo que tenham separadores diferentes (hífen, ponto, underline).
# 3. INTERFACE AMIGÁVEL: Garante que se encontrar "Pag 1" e "Pag 2", ambos sejam listados
#    na propriedade 'nome_arquivo' para o aluno ver que tudo foi capturado.
# 4. FIX UPLOAD NAME: Garante que uploads com sufixo (ex: PAG 1) usem o nome "bonito"
#    (HISTORICO SUPERIOR PAG 1) em vez da chave técnica (HISTORICO_GRADUACAO PAG 1).

import logging
import json
import os
import unicodedata
import re
import traceback
import time

from drive_handler import DriveHandler

# --- CONFIGURAÇÃO DE TAGS (PALAVRAS-CHAVE) ---
# ATENÇÃO À ORDEM: Itens mais específicos devem vir antes de itens genéricos para evitar
# que "HISTORICO ENSINO MEDIO" seja capturado apenas como "HISTORICO" (Graduação).
STANDARD_FILENAMES = {
    # DIPLOMA E CERTIFICADO DE CONCLUSÃO
    "DIPLOMA_GRADUACAO": [
        "DIPLOMA SUPERIOR", "DIPLOMA", "DIPLOMA DE GRADUACAO", 
        "DIPLOMA FACULDADE", "DIPLOMA DA GRADUACAO", "CERTIFICADO DE CONCLUSAO DE CURSO",
        "CERTIDAO DE CONCLUSAO"
    ],
    
    # DOCUMENTOS PESSOAIS (Prioridade alta para evitar confusão com outros docs)
    "RG": ["RG", "IDENTIDADE", "CARTEIRA DE IDENTIDADE", "R.G", "RG FRENTE", "RG VERSO"],
    "CPF": ["CPF", "CADASTRO DE PESSOA FISICA", "CIC"],
    "CNH": ["CNH", "HABILITACAO", "CARTEIRA DE MOTORISTA", "CARTEIRA NACIONAL DE HABILITACAO"],
    
    # ESCOLARIDADE BÁSICA (Verificado ANTES de Graduação)
    "HISTORICO_ENSINO_MEDIO": [
        "HISTORICO ESCOLAR", "HISTORICO MEDIO", "HISTORICO 2 GRAU", 
        "HISTORICO SEGUNDO GRAU", "HISTORICO ENSINO MEDIO", "HISTORICO DO ENSINO MEDIO"
    ],
    "CERTIFICADO_ENSINO_MEDIO": [
        "CERTIFICADO ESCOLAR", "CERTIFICADO MEDIO", "CERTIFICADO 2 GRAU",
        "DIPLOMA ENSINO MEDIO", "DECLARACAO DE CONCLUSAO MEDIO"
    ],
    # Tag combinada (Legado/Cache)
    "CERTIFICADO_E_HISTORICO_ENSINO_MEDIO": [
        "CERTIFICADO E HISTORICO", "HISTORICO E CERTIFICADO", 
        "DOCS ESCOLARES", "DOCUMENTACAO ESCOLAR"
    ],

    # HISTÓRICO SUPERIOR (Inclui tags com e sem acento/espaço para garantir match)
    "HISTORICO_GRADUACAO": [
        "HISTORICO SUPERIOR", "HISTORICO FACULDADE", "HISTORICO GRADUACAO",
        "HISTORICO ESCOLAR DA GRADUACAO", "HISTORICO ACADEMICO", "GRADE CURRICULAR",
        "HIST SUP", "HISTORICO DA FACULDADE", "HISTORICO"
    ],
    
    # COMPROVANTE DE RESIDÊNCIA
    "COMPROVANTE_RESIDENCIA": [
        "COMPROVANTE DE RESIDENCIA", "RESIDENCIA", "ENDERECO", "COMPROVANTE ENDERECO",
        "CONTA DE LUZ", "CONTA DE AGUA", "CONTA DE TELEFONE"
    ],
    
    # OUTROS DOCUMENTOS
    "QUITACAO_ELEITORAL": ["QUITACAO ELEITORAL", "TITULO DE ELEITOR", "E-TITULO", "SITUACAO ELEITORAL"],
    "DOCUMENTO_MILITAR": ["DOCUMENTO MILITAR", "RESERVISTA", "CERTIFICADO DE RESERVISTA", "CDI", "CAM"],
    "CERTIDAO_NASCIMENTO": ["CERTIDAO DE NASCIMENTO", "NASCIMENTO", "REGISTRO DE NASCIMENTO"],
    "CERTIDAO_CASAMENTO": ["CERTIDAO DE CASAMENTO", "CASAMENTO", "REGISTRO DE CASAMENTO"],
    "CERTIDAO_NASCIMENTO_CASAMENTO": ["CERTIDAO DE NASCIMENTO OU CASAMENTO", "ESTADO CIVIL"],
    
    # ARQUIVO ÚNICO (PDF UNIFICADO)
    "ARQUIVO_UNICO": ["ARQUIVO UNICO", "DOCUMENTOS UNIFICADOS", "TODOS OS DOCS"]
}

DRIVE_CONFIG_FILE = 'drive_config.json'

logging.basicConfig(level=logging.INFO, format='[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
logger = logging.getLogger('ALUNO_SERVICE')

class AlunoService:
    def __init__(self):
        """Inicializa o serviço, com tratamento de erros rigoroso."""
        logger.info("A iniciar inicialização do AlunoService...")
        self.drive_handler = None
        try:
            logger.info("A tentar inicializar o DriveHandler...")
            self.drive_handler = DriveHandler()
            if not self.drive_handler.is_ready():
                raise ConnectionError("Falha crítica ao inicializar o DriveHandler.")
            logger.info("DriveHandler inicializado com sucesso.")
            logger.info("AlunoService inicializado com sucesso.")

        except (ConnectionError, RuntimeError) as e:
            logger.critical(f"Falha na inicialização do AlunoService: {e}", exc_info=True)
            raise e
        except Exception as e:
            logger.critical(f"Erro inesperado durante a inicialização do AlunoService: {e}", exc_info=True)
            raise RuntimeError(f"Erro inesperado na inicialização do AlunoService: {e}") from e

    # --- FUNÇÕES AUXILIARES ---

    def _sanitize_name(self, text: str) -> str:
        """
        Remove acentos e converte para maiúsculas.
        CRUCIAL: Substitui caracteres especiais (como '_') por ESPAÇO para preservar palavras.
        Ex: 'HISTORICO_GRADUACAO' -> 'HISTORICO GRADUACAO'
        """
        if not text: return ""
        nfkd_form = unicodedata.normalize('NFKD', str(text).upper())
        only_ascii = nfkd_form.encode('ASCII', 'ignore').decode('utf-8')
        
        # Substitui tudo que não é letra, número ou hífen por ESPAÇO
        text_with_spaces = re.sub(r"[^A-Z0-9\-]", ' ', only_ascii)
        
        # Remove espaços duplos resultantes e trim
        return re.sub(r'\s+', ' ', text_with_spaces).strip()

    def _sanitize_for_comparison(self, text: str) -> str:
        """Normaliza para comparação estrita (busca de pastas)."""
        if not text: return ""
        nfkd_form = unicodedata.normalize('NFKD', str(text))
        ascii_bytes = nfkd_form.encode('ascii', 'ignore')
        text_no_accents = ascii_bytes.decode('utf-8')
        return re.sub(r'[^a-z0-9]', '', text_no_accents.lower())

    def _clean_filename_garbage(self, text: str) -> str:
        """
        Remove lixo técnico E indicadores de paginação/partes para identificar a 'base' do documento.
        Isso garante que 'RG Frente' e 'RG Verso' sejam ambos identificados apenas como 'RG'.
        """
        if not text: return ""
        
        # 1. Remove a extensão do arquivo
        text = os.path.splitext(text)[0]
        
        # 2. Remove sufixos de duplicata do Drive/Windows: (1), [1], copy
        text = re.sub(r'\s*[\(\[]\d+[\)\]]', '', text)
        text = re.sub(r'\s+(copia|copy|cópia)', '', text, flags=re.IGNORECASE)
        
        # 3. SUPER REGEX DE LIMPEZA DE PARTES
        # Identifica separadores (espaço, ponto, traço, underline) seguidos de indicadores de parte.
        # Ex: " - PAG 1", "_FRENTE", ".VERSO", " PAGINA 2", " FOLHA 1"
        pattern = r'(?i)[\s\.\-_]+(?:PAGINA|PAG|PÁG|P|PARTE|PT|FRENTE|VERSO|F|V|FOLHA)[\s\.\-_]*\d*$'
        text = re.sub(pattern, '', text)

        # Normaliza (MAIÚSCULAS, SEM ACENTOS, SEM UNDERLINES)
        return self._sanitize_name(text)

    def _get_first_letter_normalized(self, name: str) -> str:
        """Retorna a primeira letra normalizada."""
        if not name: return "A"
        sanitized = self._sanitize_name(name)
        if sanitized: return sanitized[0]
        return "A"

    def _list_all_files_recursively(self, folder_id, drive_id):
        """Lista ficheiros recursivamente com logs detalhados."""
        logger.info(f"Listando ficheiros da pasta ID: {folder_id}...")
        if not self.drive_handler or not self.drive_handler.is_ready():
            logger.error("Drive Handler indisponível em _list_all_files_recursively.")
            return None

        all_items = None
        try:
            logger.debug(f"A chamar drive_handler.list_all_items_in_folder para {folder_id}...")
            all_items = self.drive_handler.list_all_items_in_folder(folder_id, drive_id=drive_id)
        except Exception as e:
             logger.error(f"Exceção inesperada ao chamar list_all_items_in_folder para {folder_id}: {e}", exc_info=True)
             return None

        if all_items is None:
             logger.error(f"Falha ao obter itens da pasta {folder_id} (API retornou erro).")
             return None

        file_names = []
        for item in all_items:
            if not item: continue
            item_name = item.get('name', 'NOME_INVALIDO')
            if item.get('mimeType') != 'application/vnd.google-apps.folder':
                file_names.append(item_name)
            else:
                folder_id_sub = item.get('id')
                logger.debug(f"Item '{item_name}' é subpasta. Processando recursivamente...")
                if folder_id_sub:
                    sub_files = self._list_all_files_recursively(folder_id_sub, drive_id)
                    if sub_files is not None:
                        file_names.extend(sub_files)
                else:
                    logger.warning(f"Subpasta '{item_name}' não tem ID válido.")

        logger.info(f"Listagem concluída. Total de {len(file_names)} ficheiros encontrados.")
        return file_names

    def _find_student_folder_realtime(self, student_name, drive_id):
        """Busca pasta do aluno com fallback para busca sem acentos."""
        logger.info(f"Buscando pasta para: {student_name}")
        if not self.drive_handler or not self.drive_handler.is_ready():
            return None

        candidate_folders = None
        try:
            candidate_folders = self.drive_handler.find_folders_containing_name(student_name, drive_id)
            # Fallback: se não achar, tenta buscar sem acentos
            if not candidate_folders:
                sanitized_name = self._sanitize_name(student_name)
                # Verifica se a sanitização mudou algo relevante antes de tentar de novo
                if sanitized_name.replace(' ', '') != student_name.upper().replace(' ', ''):
                    logger.info(f"Tentando busca alternativa sem acentos: {sanitized_name}")
                    candidate_folders = self.drive_handler.find_folders_containing_name(sanitized_name, drive_id)
        except Exception as e:
            logger.error(f"Erro na busca de pasta: {e}", exc_info=True)
            return None

        if not candidate_folders:
            return None

        sanitized_input_name = self._sanitize_for_comparison(student_name)
        found_folder_id = None
        for folder in candidate_folders:
            folder_name = folder.get('name', '')
            sanitized_folder_name = self._sanitize_for_comparison(folder_name)
            # Comparação exata do nome da pasta (normalizado)
            if sanitized_input_name == sanitized_folder_name:
                found_folder_id = folder.get('id')
                break

        return found_folder_id

    def _get_student_folder_parent(self, base_folder_id, drive_id, student_name):
        """Encontra ou cria a pasta da letra inicial."""
        if not self.drive_handler or not self.drive_handler.is_ready():
            return None
        
        first_letter = self._get_first_letter_normalized(student_name)
        
        try:
            return self.drive_handler.find_or_create_folder(first_letter, base_folder_id, drive_id=drive_id)
        except Exception as e:
            logger.error(f"Erro ao obter pasta pai: {e}", exc_info=True)
            return None

    # --- MÉTODO PRINCIPAL DE VERIFICAÇÃO ---

    def verificar_documentos_existentes(self, student_name, tenant_drive_config, required_docs_keys):
        """
        Verifica documentos usando lógica de TAGS e BUSCA TOTAL (Greedy).
        Identifica FRENTE, VERSO, PAG 1, PAG 2 e os agrupa na interface.
        """
        start_time = time.time()
        logger.info(f"==> verificar_documentos_existentes chamado para: '{student_name}'")
        
        if not self.drive_handler or not self.drive_handler.is_ready():
             msg = "Serviço não inicializado (Drive Handler indisponível)."
             logger.error(msg)
             return {"status": "erro_servico", "mensagem": msg, "documentos": {}}
        
        if not student_name or not isinstance(student_name, str):
            msg = "Nome do aluno inválido."
            logger.error(msg)
            return {"status": "erro_entrada", "mensagem": msg, "documentos": {}}
            
        if not isinstance(required_docs_keys, list):
             logger.warning("Lista de documentos requeridos inválida, usando lista vazia para base.")
             required_docs_keys = []
             
        if not tenant_drive_config or not isinstance(tenant_drive_config, dict):
            msg = "Configuração de Drive do tenant inválida ou não fornecida."
            logger.error(msg)
            return {"status": "erro_config", "mensagem": msg, "documentos": {k: {"encontrado": False, "nome_arquivo": None} for k in required_docs_keys}}

        # --- Determina Drive e Pasta ---
        first_letter = self._get_first_letter_normalized(student_name)
        drive_id_key = 'A-M_drive_id' if 'A' <= first_letter <= 'M' else 'N-Z_drive_id'
        drive_id = tenant_drive_config.get(drive_id_key)
        
        if not drive_id:
            msg = f"Configuração de Drive ('{drive_id_key}') não encontrada no tenant_drive_config."
            logger.error(msg)
            return {"status": "erro_config", "mensagem": msg, "documentos": {k: {"encontrado": False, "nome_arquivo": None} for k in required_docs_keys}}

        student_folder_id = None
        try:
             student_folder_id = self._find_student_folder_realtime(student_name, drive_id)
        except Exception as e:
             logger.error(f"Erro inesperado durante _find_student_folder_realtime: {e}", exc_info=True)
             msg = "Erro interno ao procurar a pasta do aluno."
             return {"status": "erro_busca_pasta", "mensagem": msg, "documentos": {k: {"encontrado": False, "nome_arquivo": None} for k in required_docs_keys}}

        if not student_folder_id:
            msg = f"Pasta do aluno '{student_name}' não encontrada ou erro na busca."
            logger.warning(msg)
            return {"status": "aluno_nao_encontrado", "mensagem": msg, "documentos": {k: {"encontrado": False, "nome_arquivo": None} for k in required_docs_keys}}
        
        # --- Lista Todos os Arquivos ---
        all_files_in_drive = None
        try:
            all_files_in_drive = self._list_all_files_recursively(student_folder_id, drive_id)
        except Exception as e:
            logger.error(f"Erro inesperado durante _list_all_files_recursively: {e}", exc_info=True)
            msg = f"Erro interno ao listar ficheiros na pasta do aluno."
            return {"status": "erro_listagem", "mensagem": msg, "documentos": {k: {"encontrado": False, "nome_arquivo": None} for k in required_docs_keys}}
        
        if all_files_in_drive is None:
             msg = f"Erro ao listar o conteúdo da pasta do aluno (ID: {student_folder_id})."
             logger.error(msg)
             return {"status": "erro_listagem", "mensagem": msg, "documentos": {k: {"encontrado": False, "nome_arquivo": None} for k in required_docs_keys}}
        
        # Inicializa resposta
        found_docs = {key: {"encontrado": False, "nome_arquivo": None} for key in required_docs_keys if isinstance(key, str)}
        if "RG" in found_docs and "CNH" not in found_docs: found_docs["CNH"] = {"encontrado": False, "nome_arquivo": None}

        # --- LÓGICA DE COMPARAÇÃO COM TAGS ---
        logger.info("Iniciando verificação de ficheiros com tags expandidas...")
        
        for filename in all_files_in_drive:
            if not filename: continue
            
            # --- NOVA LÓGICA DE SPLIT (CORREÇÃO PARA SEPARADORES) ---
            doc_name_part = os.path.splitext(filename)[0]
            
            # Tenta separar "NOME ALUNO - TIPO DOC - PAGINA"
            if ' - ' in doc_name_part:
                parts = doc_name_part.split(' - ')
                if len(parts) > 1:
                    # Pega TUDO o que vem depois do primeiro separador (Nome do Aluno)
                    # Isso preserva "HISTORICO_GRADUACAO PAG 1" inteiro para a regex limpar
                    standard_name_from_file = ' '.join(parts[1:]).strip().upper()
                else:
                    standard_name_from_file = parts[-1].strip().upper()
            else:
                standard_name_from_file = doc_name_part.strip().upper()
            
            # Limpeza poderosa (remove _PAG 1, - FRENTE, .VERSO, etc)
            clean_file_name = self._clean_filename_garbage(standard_name_from_file)
            
            logger.debug(f"Arquivo: '{filename}' | Base Extraída: '{standard_name_from_file}' | Limpo: '{clean_file_name}'")

            matched_key = None
            # Verifica contra todas as TAGS configuradas
            for key, tags in STANDARD_FILENAMES.items():
                tag_list = tags if isinstance(tags, list) else [tags]
                
                for tag in tag_list:
                    clean_tag = self._sanitize_name(tag)
                    
                    # Verifica correspondência exata ou parcial da TAG
                    is_match = False
                    if clean_file_name == clean_tag:
                        is_match = True
                    elif clean_tag in clean_file_name:
                         # Evita falsos positivos parciais muito curtos
                         try:
                            pattern = r'\b' + re.escape(clean_tag) + r'\b'
                            if re.search(pattern, clean_file_name):
                                is_match = True
                         except:
                            pass
                    
                    if is_match:
                        matched_key = key
                        break
                if matched_key: break
            
            # Se encontrou correspondência (TAG match)
            if matched_key:
                doc_key = matched_key
                
                # Adiciona ao resultado (Greedy) se não existir
                if doc_key not in found_docs:
                    logger.info(f"Documento EXTRA identificado por TAG: '{doc_key}' ('{filename}')")
                    found_docs[doc_key] = {"encontrado": False, "nome_arquivo": None}

                current = found_docs[doc_key]["nome_arquivo"]
                found_docs[doc_key]["encontrado"] = True
                
                # --- LÓGICA DE CONCATENAÇÃO DE ARQUIVOS (Mostra FRENTE + VERSO na lista) ---
                # Garante que o aluno veja que AMBAS as partes foram identificadas
                if current and current != filename:
                    if filename not in current:
                        found_docs[doc_key]["nome_arquivo"] = f"{current} | {filename}"
                else:
                    found_docs[doc_key]["nome_arquivo"] = filename
                
                # Tratamento especial para chave composta (Nascimento/Casamento)
                composite_key = "CERTIDAO_NASCIMENTO_CASAMENTO"
                if doc_key in ["CERTIDAO_NASCIMENTO", "CERTIDAO_CASAMENTO"]:
                      if composite_key not in found_docs:
                          found_docs[composite_key] = {"encontrado": False, "nome_arquivo": None}
                      
                      found_docs[composite_key]["encontrado"] = True
                      curr_comp = found_docs[composite_key]["nome_arquivo"]
                      
                      if curr_comp is None:
                          found_docs[composite_key]["nome_arquivo"] = filename
                      elif filename not in curr_comp:
                          found_docs[composite_key]["nome_arquivo"] = f"{curr_comp} | {filename}"

        end_time = time.time()
        logger.info(f"Verificação concluída em {end_time - start_time:.2f}s.")
        return {"status": "sucesso", "documentos": found_docs}

    # --- CRIAÇÃO DE PASTA E UPLOAD ---

    def find_or_create_full_student_path(self, student_name, tenant_drive_config):
        """
        Localiza ou cria a estrutura.
        """
        logger.info(f"==> find_or_create_full_student_path chamado para: '{student_name}'")
        start_time = time.time()

        if not self.drive_handler or not self.drive_handler.is_ready():
             msg = "Serviço não inicializado (Drive Handler indisponível)."
             logger.error(msg)
             return None

        if not tenant_drive_config:
            msg = "Configuração de Drive do tenant (tenant_drive_config) não fornecida."
            logger.error(msg)
            return None

        if not student_name or not isinstance(student_name, str):
            msg = "Nome do aluno inválido."
            logger.error(msg)
            return None
        
        first_letter = self._get_first_letter_normalized(student_name)
        
        if 'A' <= first_letter <= 'M':
            drive_id_key = 'A-M_drive_id'
            base_folder_id_key = 'A-M_folder_id'
        else:
            drive_id_key = 'N-Z_drive_id'
            base_folder_id_key = 'N-Z_folder_id'

        drive_id = tenant_drive_config.get(drive_id_key)
        base_folder_id = tenant_drive_config.get(base_folder_id_key)

        if not drive_id:
            logger.error(f"FALHA CRÍTICA: Chave '{drive_id_key}' não encontrada no tenant_drive_config.")
            return None
        if not base_folder_id:
            logger.error(f"FALHA CRÍTICA: Chave '{base_folder_id_key}' não encontrada no tenant_drive_config.")
            return None

        sanitized_name_for_creation = self._sanitize_name(student_name)
        try:
            # Tenta achar a pasta
            logger.info("A tentar encontrar a pasta do aluno via busca flexível...")
            student_folder_id = self._find_student_folder_realtime(student_name, drive_id)

            # Se não achar, cria
            if not student_folder_id:
                logger.info(f"Pasta não encontrada. A criar com nome '{sanitized_name_for_creation}'...")
                
                parent_folder_id = self._get_student_folder_parent(base_folder_id, drive_id, student_name)
                
                if not parent_folder_id:
                    logger.error(f"Não foi possível obter a pasta pai (Letra).")
                    return None
                
                logger.info(f"Pasta pai obtida/criada (ID: {parent_folder_id}). A criar pasta do aluno...")
                
                student_folder_id = self.drive_handler.create_folder(sanitized_name_for_creation, parent_folder_id)
            
            if not student_folder_id:
                 logger.error("ID da pasta do aluno é inválido após busca/criação.")
                 return None
            
            logger.info(f"A garantir subpastas 'OUTROS DOCS' e 'DOC' dentro de {student_folder_id}...")
            
            self.drive_handler.find_or_create_folder("OUTROS DOCS", student_folder_id, drive_id=drive_id)
            doc_folder_id = self.drive_handler.find_or_create_folder("DOC", student_folder_id, drive_id=drive_id)

            if not doc_folder_id:
                logger.error(f"Não foi possível encontrar ou criar a subpasta 'DOC'.")
                return None
                
            end_time = time.time()
            logger.info(f"Caminho completo verificado/criado para '{student_name}' em {end_time - start_time:.2f} segundos. Pasta 'DOC' ID: {doc_folder_id}")
            return doc_folder_id

        except Exception as e:
            logger.error(f"Erro inesperado durante find_or_create_full_student_path: {e}", exc_info=True)
            return None

    def upload_file(self, student_name, doc_key, file_content_bytes, parent_folder_id, mime_type, extension=".pdf"):
        """Realiza upload de arquivo para a pasta especificada."""
        logger.info(f"==> upload_file chamado para: Aluno='{student_name}', Chave='{doc_key}', PastaPai='{parent_folder_id}'")
        start_time = time.time()
        
        if not self.drive_handler or not self.drive_handler.is_ready():
             msg = "Serviço não inicializado (Drive Handler indisponível)."
             logger.error(msg + " Upload cancelado.")
             return None
        
        if not all([student_name, doc_key, file_content_bytes, parent_folder_id, mime_type]):
             msg = f"Parâmetros inválidos fornecidos para upload_file (...)."
             logger.error(msg + " Upload cancelado.")
             return None

        sanitized_student_name = self._sanitize_name(student_name)
        
        # --- LÓGICA DE DETECÇÃO DE SUFIXO (NOVO) ---
        # Detecta se a chave tem sufixo (ex: "HISTORICO_GRADUACAO PAG 1") para usar o nome bonito na base
        base_key = doc_key
        suffix = ""
        
        match = re.search(r'^(.*?)(\s+(?:PAG|PÁG|P|PARTE|PT|FRENTE|VERSO|F|V|FOLHA)[\s\.\-_]*\d*)$', doc_key, re.IGNORECASE)
        if match:
            base_key = match.group(1) # Chave base limpa
            suffix = match.group(2)   # Sufixo (ex: " PAG 1")
            
        # Busca nome bonito para a base
        standard_doc_name = STANDARD_FILENAMES.get(base_key, base_key)
        if isinstance(standard_doc_name, list):
            standard_doc_name = standard_doc_name[0]
            
        # Remove underscores do nome padrão por segurança
        standard_doc_name = standard_doc_name.replace('_', ' ')

        # Monta o nome final (com o sufixo original se houver)
        final_doc_name = f"{standard_doc_name}{suffix}".strip()
        final_doc_name = self._sanitize_name(final_doc_name) # Garante caixa alta e sem caracteres estranhos

        final_filename = f"{sanitized_student_name} - {final_doc_name}{extension}"
        
        logger.info(f"Nome final do ficheiro: '{final_filename}'. A iniciar upload...")
        
        file_id = None
        try:
            file_id = self.drive_handler.upload_file(
                folder_id=parent_folder_id,
                filename=final_filename,
                file_content_bytes=file_content_bytes,
                mime_type=mime_type
            )
        except Exception as e:
            logger.error(f"Erro inesperado durante drive_handler.upload_file: {e}", exc_info=True)
            return None

        end_time = time.time()
        if file_id:
            logger.info(f"Upload concluído com sucesso para '{final_filename}' em {end_time - start_time:.2f} segundos. ID do ficheiro: {file_id}")
        else:
            logger.error(f"Falha no upload para '{final_filename}' após {end_time - start_time:.2f} segundos.")

        return file_id