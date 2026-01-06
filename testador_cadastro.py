# -*- coding: utf-8 -*-
# -----------------------------------------------------------------
# ARQUIVO: testador_cadastro.py
# DESCRIÇÃO: Script AUTÔNOMO para testar a lógica de cadastro/atualização
#            da Solis, simulando os dados da análise.
#            NÃO importa 'processador_lote.py'.
#            Carrega configurações do arquivo .env.
# -----------------------------------------------------------------
import os
import logging
import json
import re
import requests
from datetime import datetime, timezone
from dotenv import load_dotenv
import traceback # Para log mais detalhado em exceções

# --- CONFIGURAÇÃO INICIAL ---
load_dotenv() # Carrega .env
# Nível DEBUG para ver detalhes como o payload enviado para Solis
logging.basicConfig(level=logging.DEBUG, format='[TESTADOR] [%(levelname)s] %(asctime)s - %(message)s')

# ==============================================================================
# --- CÓPIA DAS FUNÇÕES E CLASSES ESSENCIAIS DO processador_lote.py ---
# ==============================================================================

# --- DEFINIÇÃO DE CONSTANTES (Copiadas/Adaptadas) ---
GEMINI_MODEL_NAME = "gemini-2.5-flash" # Modelo Flash normal
MAX_TENTATIVAS = 3 # Embora não usado diretamente no teste, pode ser útil

# --- CONSTANTES ATUALIZADAS PARA BUSCA (NOME E CPF) ---

# 1. Busca por NOME (Método Principal)
CODIGO_RELATORIO_BUSCA_ALUNO_NOME = "6520251203153402"
NOME_PARAMETRO_BUSCA_ALUNO_NOME = "NOME_ALUNO"

# 2. Busca por CPF (Método Fallback)
# !!! ATENÇÃO: VERIFIQUE E PREENCHA ESTES VALORES CORRETAMENTE !!!
#     Pode ser o *mesmo* código de relatório, mas com um parâmetro *diferente*.
CODIGO_RELATORIO_BUSCA_ALUNO_CPF = "6520251203153402" # <<< PREENCHA: Este é o código do relatório que busca por CPF?
NOME_PARAMETRO_BUSCA_ALUNO_CPF = "CPF_ALUNO"      # <<< PREENCHA: Este é o nome do parâmetro esperado (Ex: CPF, CPF_ALUNO)?

# 3. Campo de ID (Comum a ambas as buscas)
CAMPO_ID_BUSCA_ALUNO = "ID"

# 4. Relatório de Detalhes (Após ID ser encontrado)
CODIGO_RELATORIO_DETALHES_ALUNO = "6720251203154641"
NOME_PARAMETRO_BUSCA_ID = "ID_PESSOA"


# --- DEFINIÇÃO DE ERROS CUSTOMIZADOS (Copiadas) ---
class ApiError(Exception):
    """Classe base para erros da API."""
    pass

class PermanentApiError(ApiError):
    """Erro que indica que a requisição não deve ser tentada novamente."""
    pass

class TemporaryApiError(ApiError):
    """Erro que indica que a requisição pode ser tentada novamente."""
    pass

# --- CLASSE SolisAPIClient (Copiada) ---
class SolisAPIClient:
    """
    Cliente de API para interagir com o SolisGE.
    Copiado de processador_lote.py para autonomia.
    """
    def __init__(self, base_url, jwt_token):
        if not base_url or not jwt_token:
            raise ValueError("A URL base e o token JWT não podem ser nulos.")
        self.base_url = base_url.rstrip('/')
        self.headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'X-Token': jwt_token,
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        # Tenta desabilitar warnings de SSL, mas verifica se o módulo existe
        try:
            requests.urllib3.disable_warnings(requests.urllib3.exceptions.InsecureRequestWarning)
        except AttributeError:
            logging.warning("Não foi possível desabilitar warnings de InsecureRequestWarning (pode ser versão antiga do requests/urllib3)")


    def _handle_response(self, response, context_message):
        """Centraliza o tratamento de respostas HTTP."""
        try:
            response.raise_for_status() # Lança HTTPError para status >= 400
            if response.content:
                return response.json()
            else:
                logging.info(f"Resposta de '{context_message}' com status {response.status_code} mas sem conteúdo.")
                return None
        except requests.exceptions.HTTPError as err:
            status_code = err.response.status_code
            error_text = err.response.text
            logging.error(f"--- Erro HTTP em '{context_message}': Status {status_code} ---")
            logging.error(f"Resposta da API: {error_text}")
            if 400 <= status_code < 500:
                raise PermanentApiError(f"Erro permanente ({status_code}) em '{context_message}': {error_text}")
            elif 500 <= status_code < 600:
                raise TemporaryApiError(f"Erro temporário ({status_code}) em '{context_message}': {error_text}")
            else:
                raise ApiError(f"Erro HTTP inesperado ({status_code}) em '{context_message}': {error_text}")
        except json.JSONDecodeError:
            logging.error(f"A resposta de '{context_message}' não é um JSON válido. Conteúdo: {response.text[:500]}...")
            raise PermanentApiError(f"Resposta não-JSON em '{context_message}'")
        except requests.exceptions.RequestException as e:
            logging.error(f"Erro de Conexão em '{context_message}': {e}", exc_info=True)
            raise TemporaryApiError(f"Erro de conexão em '{context_message}': {e}")


    def atualizar_pessoa(self, payload):
        endpoint = "/api/basico/pessoa"
        url = f"{self.base_url}{endpoint}"
        logging.info(f"Enviando POST para {url}")
        logging.debug(f"Payload para atualizar_pessoa: {json.dumps(payload, indent=2)}")
        try:
            response = self.session.post(url, json=payload, verify=False, timeout=30)
            return self._handle_response(response, "atualizar_pessoa")
        except Exception as e:
            logging.error(f"Exceção durante a chamada POST para atualizar_pessoa: {e}")
            logging.error(f"Payload que causou o erro: {json.dumps(payload, indent=2)}")
            raise


    def executar_relatorio_com_parametro(self, codigo_relatorio, nome_param, valor_param):
        endpoint = f"/api/basico/relatorio-generico/gerar/{codigo_relatorio}"
        url = f"{self.base_url}{endpoint}"
        payload = {"par": {nome_param: valor_param}}
        logging.info(f"Executando relatório ID '{codigo_relatorio}' com param: '{nome_param}'='{valor_param}'")
        try:
            response = self.session.get(url, data=json.dumps(payload), verify=False, timeout=30)
            resultado_json = self._handle_response(response, f"relatorio_{codigo_relatorio}")
            if resultado_json is None:
                logging.warning(f"Relatório {codigo_relatorio} retornou null.")
                return None
            if isinstance(resultado_json, list) and not resultado_json:
                logging.warning(f"Relatório {codigo_relatorio} retornou uma lista vazia.")
                return {'dados': []}
            if isinstance(resultado_json, list):
                return {'dados': resultado_json}
            if isinstance(resultado_json, dict):
                return resultado_json
            else:
                logging.error(f"Formato inesperado recebido do relatório {codigo_relatorio}: {type(resultado_json)}")
                raise PermanentApiError(f"Formato inesperado da API para relatório {codigo_relatorio}")
        except Exception as e:
            logging.error(f"Exceção durante a chamada GET para executar_relatorio_com_parametro: {e}")
            logging.error(f"Payload que pode ter causado o erro: {json.dumps(payload, indent=2)}")
            raise

# --- FUNÇÕES DE LÓGICA (Copiadas/Adaptadas) ---

def analisar_dados_com_ia(nome_aluno, texto_documento, gemini_api_key):
    """
    Unifica as chamadas à IA para determinar sexo e estado civil.
    Copiado de processador_lote.py.
    """
    if not gemini_api_key:
        logging.warning("Chave da API Gemini não encontrada. Análise da IA pulada.")
        return {}

    primeiro_nome = nome_aluno.strip().split()[0].capitalize() if nome_aluno else "Aluno"
    prompt = (
        f"Analise os dados a seguir e retorne um objeto JSON. "
        f"1. Para a chave 'sexo', determine o sexo mais provável do nome '{primeiro_nome}'. Use 'M' para masculino ou 'F' para feminino. Se o nome for ambíguo ou desconhecido, retorne null. "
        f"2. Para a chave 'estado_civil', classifique o documento com base no texto '{texto_documento}'. Use um dos seguintes códigos ACEITOS PELA SOLIS: " # Deixe claro para a IA
        f"'S' para Solteiro ou Nascimento, 'C' para Casado, 'U' para União Estável, 'D' para Divorciado, "
        f"'V' para Viúvo, 'P' para Separado judicialmente, 'E' para Solteiro Emancipado. Se não for possível determinar com certeza ou o texto for irrelevante, retorne null. "
        f"Responda APENAS com o objeto JSON válido, nada mais antes ou depois."
    )

    logging.info(f"Consultando IA ({GEMINI_MODEL_NAME}) para análise unificada de '{primeiro_nome}' e documento.")
    api_url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL_NAME}:generateContent?key={gemini_api_key}"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "responseMimeType": "application/json",
            "temperature": 0.2
        }
    }

    try:
        response = requests.post(api_url, json=payload, timeout=45)
        response.raise_for_status()
        resultado = response.json()
        if not resultado or 'candidates' not in resultado or not resultado['candidates']:
            logging.error("Resposta da API Gemini inválida ou sem 'candidates'.")
            return {}
        candidate = resultado['candidates'][0]
        if 'content' not in candidate or 'parts' not in candidate['content'] or not candidate['content']['parts']:
            logging.error("Resposta da API Gemini sem 'content' ou 'parts'.")
            return {}
        json_text = candidate['content']['parts'][0].get('text', '')
        if not json_text:
            logging.error("API Gemini retornou 'text' vazio.")
            return {}
        try:
            dados_ia = json.loads(json_text)
            if not isinstance(dados_ia, dict):
                logging.error(f"IA retornou JSON, mas não é um objeto: {json_text}")
                return {}
            logging.info(f"IA retornou dados: {dados_ia}")
            return dados_ia
        except json.JSONDecodeError as json_err:
            logging.error(f"Falha ao decodificar JSON da resposta da IA: {json_err}")
            logging.error(f"Texto recebido da IA: {json_text}")
            return {}
    except requests.exceptions.RequestException as req_err:
        logging.error(f"Erro de conexão com a API Gemini: {req_err}", exc_info=False)
        return {}
    except Exception as e:
        logging.error(f"Falha inesperada na comunicação com a API Gemini: {e}", exc_info=True)
        return {}

def buscar_endereco_por_cep(cep):
    """Busca endereço usando ViaCEP. Copiado de processador_lote.py."""
    if not cep: return None
    cep_limpo = re.sub(r'[^\d]', '', str(cep))
    if len(cep_limpo) != 8:
        logging.warning(f"CEP inválido fornecido para busca: '{cep}'")
        return None
    logging.info(f"Consultando API de CEP para '{cep_limpo}'...")
    try:
        response = requests.get(f"https://viacep.com.br/ws/{cep_limpo}/json/", timeout=10)
        response.raise_for_status()
        dados_cep = response.json()
        if dados_cep.get('erro'):
            logging.warning(f"API ViaCEP retornou erro para o CEP '{cep_limpo}'.")
            return None
        return dados_cep
    except requests.exceptions.RequestException as e:
        logging.error(f"Falha na comunicação com a API ViaCEP: {e}")
        return None
    except json.JSONDecodeError:
        logging.error(f"Resposta da API ViaCEP não é um JSON válido para o CEP '{cep_limpo}'.")
        return None

def construir_payload_completo(dados_novos, dados_sistema, id_interno_solis):
    """Constrói o payload para a API Solis. Copiado de processador_lote.py."""
    payload_para_envio = dados_sistema.copy() if dados_sistema else {}
    houve_alteracao_real = False
    mapa_de_campos = {
        'filiacao_pai': 'nomedopai', 'filiacao_mae': 'nomedamae', 'numero_cpf': 'cpf',
        'numero_rg': 'rg', 'sexo': 'sexo', 'instituicao_ensino_medio': 'instituicao',
        'data_conclusao_ensino_medio': 'anoensinomedio', 'cep': 'cep', 'cidade': 'cidade',
        'uf': 'uf', 'bairro': 'bairro', 'logradouro': 'logradouro', 'estadocivil': 'estadocivil'
        # 'datadenascimento': 'datanascimento' # Adicionar se necessário
    }
    logging.info("--- Iniciando análise de alterações para o payload ---")
    dados_novos = dados_novos if isinstance(dados_novos, dict) else {}

    for chave_nova, chave_api in mapa_de_campos.items():
        valor_novo = dados_novos.get(chave_nova)
        valor_antigo = payload_para_envio.get(chave_api)
        valor_novo_str = str(valor_novo).strip() if valor_novo is not None else ""
        valor_antigo_str = str(valor_antigo).strip() if valor_antigo is not None else ""
        if valor_novo_str and valor_novo_str.lower() != valor_antigo_str.lower():
            logging.info(f"   - DETECTADA ALTERAÇÃO em '{chave_api}': de '{valor_antigo}' para '{valor_novo}'")
            payload_para_envio[chave_api] = valor_novo
            houve_alteracao_real = True

    if not payload_para_envio.get('email', ''):
        logging.info("   - Email está vazio. Marcando para atualização forçada.")
        houve_alteracao_real = True

    if not houve_alteracao_real:
        logging.info("Nenhuma alteração real detectada.")
        return None

    logging.info("--- Preparando payload final para envio ---")
    if not payload_para_envio.get('email', ''):
        cpf_base = payload_para_envio.get('cpf') or dados_novos.get('numero_cpf')
        if cpf_base:
            cpf_para_email = str(cpf_base).replace('.', '').replace('-', '')
            if len(cpf_para_email) == 11:
                payload_para_envio['email'] = f"atualizar.cadastro.{cpf_para_email}@solis.placeholder"
                logging.info(f"   - Email gerado: {payload_para_envio['email']}")
            else:
                logging.warning(f"   - CPF inválido ('{cpf_base}') para gerar email placeholder.")
        else:
            logging.warning("   - Email vazio e CPF não disponível para gerar email placeholder.")

    payload_para_envio['codigodapessoa'] = id_interno_solis
    payload_para_envio['identificador'] = id_interno_solis
    if 'senha' in payload_para_envio: del payload_para_envio['senha']
    for campo in ['aluno', 'professor', 'funcionario', 'segurado']:
        if campo in payload_para_envio:
            valor = str(payload_para_envio.get(campo, '')).lower().strip()
            is_true = valor in ['s', 'true', 't', '1']
            payload_para_envio[campo] = 's' if is_true else 'n'

    payload_final = { "pessoa": payload_para_envio }
    logging.debug(f"Payload final construído: {json.dumps(payload_final, indent=2)}")
    return payload_final

def parse_reason_string(reason_text):
    """Extrai dados de strings de 'reason'. Copiado de processador_lote.py."""
    dados = {}
    padroes = {
        'numero_rg': r"(?:RG|R\.G\.)\s*[:\)]?\s*([\w\d\.\s\-/]+?)(?:,|\s*SSP|\s*EM|\s*$|\])",
        'numero_cpf': r"(?:CPF|C\.P\.F\.)\s*[:\)]?\s*(\d{2,3}\.\d{3}\.\d{3}-?\d{2})",
        'filiacao': r"(?:pais|filia[cç][aã]o)\s*[:\)]?\s*([^,\]]+)",
        'cep': r"(?:CEP|C\.E\.P\.)\s*[:]?\s*(\d{5}-?\d{3})",
        'datadenascimento': r"(?:Nascimento|nasc\.)\s*[:]?\s*(\d{1,2}[/\-.]\d{1,2}[/\-.]\d{2,4}|\d{1,2}\s+de\s+\w+\s+de\s+\d{4})"
    }
    padroes_filiacao = {
        'filiacao_pai': r"(?:Pai|Nome do Pai)\s*[:]?\s*([^,/]+)",
        'filiacao_mae': r"(?:M[ãa]e|Nome d[ao] M[ãa]e)\s*[:]?\s*([^,/]+)"
    }

    if not isinstance(reason_text, str):
        logging.warning("Texto 'reason' inválido para parse.")
        return {}

    for chave, padrao in padroes_filiacao.items():
        match = re.search(padrao, reason_text, re.IGNORECASE)
        if match:
            valor = re.sub(r'[.,;]$', '', match.group(1).strip()).strip()
            if valor and '***' not in valor: dados[chave] = valor

    for chave, padrao in padroes.items():
        if chave not in dados:
            match = re.search(padrao, reason_text, re.IGNORECASE)
            if match:
                valor = re.sub(r'[.,;]$', '', match.group(1).strip()).strip()
                if chave == 'datadenascimento' and ' de ' in valor.lower():
                    try:
                        partes = valor.split(' de ')
                        dia, mes_extenso, ano = partes[0], partes[1].lower(), partes[2]
                        meses = {'janeiro': '01', 'fevereiro': '02', 'março': '03', 'abril': '04', 'maio': '05', 'junho': '06', 'julho': '07', 'agosto': '08', 'setembro': '09', 'outubro': '10', 'novembro': '11', 'dezembro': '12'}
                        mes_num = meses.get(mes_extenso)
                        if mes_num: valor = f"{dia.zfill(2)}/{mes_num}/{ano}"
                        else: logging.warning(f"Mês por extenso não reconhecido: '{mes_extenso}' em '{valor}'")
                    except Exception as e: logging.warning(f"Não foi possível converter a data por extenso '{valor}': {e}")
                elif chave == 'cep': valor = valor.replace('-', '')
                elif chave == 'numero_cpf': valor = valor.replace('.', '').replace('-', '')
                if valor and '***' not in valor: dados[chave] = valor

    if 'filiacao' in dados and 'filiacao_pai' not in dados and 'filiacao_mae' not in dados:
        filiacao_completa = dados['filiacao']
        partes = [p.strip() for p in re.split(r'\s*/\s*|\s*;\s*|\s+e\s+', filiacao_completa) if p.strip()]
        if len(partes) >= 2:
            dados['filiacao_pai'] = partes[0]
            dados['filiacao_mae'] = partes[1]
            logging.debug(f"Filiação dividida: Pai='{partes[0]}', Mãe='{partes[1]}'")
        elif len(partes) == 1:
            logging.warning(f"Campo 'filiacao' contém apenas um nome: '{partes[0]}'. Não foi possível dividir.")
        # Remove a chave filiacao mesmo se não conseguiu dividir, pois tentou
        if 'filiacao' in dados: del dados['filiacao']


    return dados

def pre_processar_e_consolidar_pendencia(pendencia_data):
    """Consolida dados e busca CEP. Copiado de processador_lote.py."""
    dados_consolidados = {}
    nome_aluno = pendencia_data.get("aluno_nome")
    # A estrutura correta é ter 'dados_analise' que contém os resultados dos documentos
    dados_analise = pendencia_data.get("dados_analise", {})
    texto_documento_certidao = ""

    if not nome_aluno or not isinstance(dados_analise, dict):
        raise ValueError("Dados da pendência inválidos (nome ou 'dados_analise' ausente/incorreto).")

    logging.info(f"--- Pré-processando pendência para: {nome_aluno} ---")
    # Itera sobre os resultados DENTRO de 'dados_analise'
    for tipo_doc, conteudo_doc in dados_analise.items():
        if not isinstance(conteudo_doc, dict):
            logging.warning(f"Conteúdo inválido para o documento '{tipo_doc}'. Pulando.")
            continue
        # Processa apenas documentos aprovados
        if conteudo_doc.get("status") != "approved":
            logging.debug(f"Documento '{tipo_doc}' não está com status 'approved' ({conteudo_doc.get('status')}). Pulando consolidação.")
            continue

        logging.debug(f"Consolidando documento aprovado: {tipo_doc}")
        dados_base = conteudo_doc.get('extracted_data', {})
        reason_text = conteudo_doc.get('reason', '')
        if not isinstance(dados_base, dict): dados_base = {}
        dados_reason = parse_reason_string(reason_text)
        dados_combinados = {**dados_reason, **dados_base}
        logging.debug(f"Dados combinados para {tipo_doc}: {dados_combinados}")

        if tipo_doc == 'CERTIDAO_NASCIMENTO_CASAMENTO':
            texto_documento_certidao = conteudo_doc.get('identified_doc_type') or conteudo_doc.get('classified_doc_type') or ""
            logging.debug(f"Texto da certidão para IA: '{texto_documento_certidao}'")

        if tipo_doc == 'COMPROVANTE_RESIDENCIA' and dados_combinados.get('cep'):
            cep_original = dados_combinados.get('cep')
            endereco = buscar_endereco_por_cep(cep_original)
            if endereco:
                logging.info(f"Endereço encontrado para CEP {cep_original}: {endereco.get('logradouro')}, {endereco.get('localidade')}-{endereco.get('uf')}")
                update_cep = {'cidade': endereco.get('localidade'), 'uf': endereco.get('uf'), 'bairro': endereco.get('bairro'), 'logradouro': endereco.get('logradouro'), 'cep': endereco.get('cep', '').replace('-', ''), 'pais': 'BRASIL'}
                for key, value in update_cep.items():
                    # Só atualiza se o campo ainda não existir nos dados consolidados OU se já existir mas estiver vazio
                    if key not in dados_consolidados or not dados_consolidados[key]:
                        dados_consolidados[key] = value # Aplica ao consolidado
                    # Atualiza também nos combinados para a próxima etapa (sobrescrita)
                    if key not in dados_combinados or not dados_combinados[key]:
                        dados_combinados[key] = value

            else:
                logging.warning(f"Não foi possível obter endereço para o CEP: {cep_original}")
                # Mantém o CEP original se a busca falhar, mas formatado
                cep_formatado = cep_original.replace('-', '') if cep_original else None
                if 'cep' not in dados_consolidados or not dados_consolidados['cep']:
                    dados_consolidados['cep'] = cep_formatado
                if 'cep' not in dados_combinados or not dados_combinados['cep']:
                    dados_combinados['cep'] = cep_formatado


        if tipo_doc == 'HISTORICO_ENSINO_MEDIO':
            if dados_base.get('instituicao_ensino'):
                # Usa o valor extraído diretamente, assume que é o nome correto
                dados_consolidados['instituicao_ensino_medio'] = dados_base['instituicao_ensino']
                dados_combinados['instituicao_ensino_medio'] = dados_base['instituicao_ensino'] # Garante consistência
                logging.debug(f"Instituição EM definida como: {dados_consolidados['instituicao_ensino_medio']}")
            if dados_base.get('data_conclusao'):
                # Tenta extrair ano de varios formatos (dd/mm/yyyy, yyyy, mes de yyyy)
                ano_match = re.search(r'(\d{4})', str(dados_base['data_conclusao']))
                if ano_match:
                    ano_conclusao = ano_match.group(1)
                    dados_consolidados['data_conclusao_ensino_medio'] = ano_conclusao
                    dados_combinados['data_conclusao_ensino_medio'] = ano_conclusao # Garante consistência
                    logging.debug(f"Ano conclusão EM definido como: {ano_conclusao}")
                else:
                    logging.warning(f"Não foi possível extrair ano da data de conclusão: {dados_base['data_conclusao']}")

        # Consolidação Final (sobrescreve com dados do último doc processado)
        for key, value in dados_combinados.items():
            # Verifica se valor é válido (não None, não vazio, não mascarado)
            # Remove a checagem de '***' aqui se a extração já deveria ter filtrado
            if value is not None and str(value).strip() != '':
                # Se a chave já existe e o novo valor é diferente, loga a sobrescrita
                # if key in dados_consolidados and dados_consolidados[key] != value:
                #   logging.debug(f"Sobrescrevendo '{key}': de '{dados_consolidados[key]}' para '{value}' (origem: {tipo_doc})")
                dados_consolidados[key] = value

    # Tratamento de Filiação (após processar todos os docs)
    # Prioriza chaves separadas se existirem
    if 'filiacao_pai' in dados_consolidados or 'filiacao_mae' in dados_consolidados:
        if 'filiacao' in dados_consolidados:
            logging.debug("Removendo chave 'filiacao' pois pai/mãe já definidos separadamente.")
            del dados_consolidados['filiacao']
    # Se não existirem separadas, tenta dividir a chave 'filiacao'
    elif 'filiacao' in dados_consolidados and isinstance(dados_consolidados['filiacao'], str):
        filiacao_completa = dados_consolidados['filiacao']
        # Tenta dividir por / ; ou ' e ' (com espaços)
        partes = [p.strip() for p in re.split(r'\s*/\s*|\s*;\s*|\s+e\s+', filiacao_completa) if p.strip()]
        if len(partes) >= 2:
            # Assume pai primeiro, mãe segundo (pode precisar de ajuste fino)
            # Só define se não existirem ainda
            if 'filiacao_pai' not in dados_consolidados:
                dados_consolidados['filiacao_pai'] = partes[0]
            if 'filiacao_mae' not in dados_consolidados:
                dados_consolidados['filiacao_mae'] = partes[1]
            logging.debug(f"Filiação dividida da chave 'filiacao': Pai='{dados_consolidados.get('filiacao_pai')}', Mãe='{dados_consolidados.get('filiacao_mae')}'")
        elif len(partes) == 1:
            logging.warning(f"Campo 'filiacao' consolidado contém apenas um nome: '{partes[0]}'. Não foi possível dividir.")
        # Remove a chave 'filiacao' original após tentar dividir
        if 'filiacao' in dados_consolidados: del dados_consolidados['filiacao']


    logging.info(f"Dados consolidados para {nome_aluno}: {dados_consolidados}")
    return nome_aluno, texto_documento_certidao, dados_consolidados

def processar_pendencia_unica(nome_para_busca, texto_doc_certidao, dados_novos_aluno, cliente_solis, gemini_api_key):
    """Executa a lógica principal (IA, Solis). Copiado de processador_lote.py."""
    logging.info(f"--- Iniciando processamento Solis para: {nome_para_busca} ---")
    dados_ia = analisar_dados_com_ia(nome_para_busca, texto_doc_certidao, gemini_api_key)
    if dados_ia.get('sexo') and not dados_novos_aluno.get('sexo'): # Checa se IA retornou valor não nulo/vazio
        dados_novos_aluno['sexo'] = dados_ia['sexo']
        logging.debug(f"Sexo definido pela IA: {dados_ia['sexo']}")
    if dados_ia.get('estado_civil') and not dados_novos_aluno.get('estadocivil'):
        dados_novos_aluno['estadocivil'] = dados_ia['estado_civil']
        logging.debug(f"Estado Civil ('estadocivil') definido pela IA: {dados_ia['estado_civil']}")

    # --- LÓGICA DE BUSCA ATUALIZADA (NOME -> CPF) ---
    identificador_existente = None

    # --- TENTATIVA 1: Buscar por NOME ---
    logging.info(f"Buscando aluno por NOME: '{nome_para_busca.upper()}' na Solis...")
    try:
        resultado_busca_nome_json = cliente_solis.executar_relatorio_com_parametro(
            CODIGO_RELATORIO_BUSCA_ALUNO_NOME,
            NOME_PARAMETRO_BUSCA_ALUNO_NOME,
            nome_para_busca.upper()
        )
        
        if resultado_busca_nome_json and resultado_busca_nome_json.get('dados'):
            if len(resultado_busca_nome_json['dados']) > 1:
                logging.warning(f"Múltiplos resultados encontrados para o NOME '{nome_para_busca}'. Usando o primeiro ID.")
            
            identificador_existente = resultado_busca_nome_json['dados'][0].get(CAMPO_ID_BUSCA_ALUNO)
            if identificador_existente:
                logging.info(f"Aluno encontrado por NOME. ID Solis: {identificador_existente}")
            else:
                logging.warning(f"Busca por NOME retornou dados, mas sem o campo ID ('{CAMPO_ID_BUSCA_ALUNO}').")
        else:
            logging.warning(f"Busca por NOME para '{nome_para_busca}' não retornou resultados.")
            
    except ApiError as e:
        # Se a API der erro (4xx, 5xx) na busca por NOME, loga mas continua para tentar CPF
        logging.warning(f"Erro na API ao buscar por NOME: {e}. Tentando busca por CPF.")

    # --- TENTATIVA 2: Buscar por CPF (se a busca por NOME falhar) ---
    if not identificador_existente:
        logging.info("Tentativa por NOME falhou. Tentando buscar por CPF...")
        aluno_cpf = dados_novos_aluno.get('numero_cpf')
        
        if not aluno_cpf:
            raise PermanentApiError(f"Busca por NOME falhou e aluno '{nome_para_busca}' não possui CPF nos dados consolidados.")

        # Limpa o CPF para a busca (garante que não tem pontos/traços)
        aluno_cpf_limpo = re.sub(r'[^\d]', '', str(aluno_cpf))
        if len(aluno_cpf_limpo) != 11:
            raise PermanentApiError(f"Busca por NOME falhou e o CPF extraído ('{aluno_cpf}') é inválido.")

        logging.info(f"Buscando aluno por CPF: '{aluno_cpf_limpo}' na Solis...")
        try:
            # Verifica se as constantes de CPF foram preenchidas
            if "AQUI" in CODIGO_RELATORIO_BUSCA_ALUNO_CPF or "AQUI" in NOME_PARAMETRO_BUSCA_ALUNO_CPF:
                logging.error("As constantes 'CODIGO_RELATORIO_BUSCA_ALUNO_CPF' ou 'NOME_PARAMETRO_BUSCA_ALUNO_CPF' não foram preenchidas.")
                raise PermanentApiError("Configuração de busca por CPF incompleta no script.")

            resultado_busca_cpf_json = cliente_solis.executar_relatorio_com_parametro(
                CODIGO_RELATORIO_BUSCA_ALUNO_CPF, 
                NOME_PARAMETRO_BUSCA_ALUNO_CPF, 
                aluno_cpf_limpo
            )
            
            if resultado_busca_cpf_json and resultado_busca_cpf_json.get('dados'):
                if len(resultado_busca_cpf_json['dados']) > 1:
                    logging.warning(f"Múltiplos resultados encontrados para o CPF '{aluno_cpf_limpo}'. Usando o primeiro ID.")
                
                identificador_existente = resultado_busca_cpf_json['dados'][0].get(CAMPO_ID_BUSCA_ALUNO)
                if identificador_existente:
                    logging.info(f"Aluno encontrado por CPF. ID Solis: {identificador_existente}")
                else:
                    # Se a busca por CPF também falhar em achar o ID, é um erro permanente
                    raise PermanentApiError(f"Busca por CPF retornou dados, mas sem o campo ID ('{CAMPO_ID_BUSCA_ALUNO}').")
            else:
                # Se a busca por CPF também falhar, é um erro permanente
                raise PermanentApiError(f"Aluno '{nome_para_busca}' (CPF: {aluno_cpf_limpo}) não encontrado na Solis via NOME ou CPF.")
        
        except ApiError as e:
            # Se a API der erro (4xx, 5xx) na busca por CPF, é um erro final
            logging.error(f"Erro na API ao buscar por CPF: {e}.")
            raise PermanentApiError(f"Falha na API ao buscar por CPF ({aluno_cpf_limpo}): {e}")

    # --- Continuação (se o ID foi encontrado por NOME ou CPF) ---
    if not identificador_existente:
        # Esta linha não deve ser alcançada se a lógica acima estiver correta, mas é uma salvaguarda
        raise PermanentApiError(f"Falha crítica: Nenhuma das buscas (Nome ou CPF) resultou em um ID para '{nome_para_busca}'.")

    logging.info(f"ID final do aluno na Solis: {identificador_existente}")
    # --- FIM DA LÓGICA DE BUSCA ATUALIZADA ---

    logging.info(f"Buscando detalhes do aluno ID {identificador_existente}...")
    dados_atuais_json = cliente_solis.executar_relatorio_com_parametro(
        CODIGO_RELATORIO_DETALHES_ALUNO, NOME_PARAMETRO_BUSCA_ID, identificador_existente
    )
    if not dados_atuais_json or 'dados' not in dados_atuais_json or not dados_atuais_json['dados']:
        raise TemporaryApiError(f"Falha ao buscar detalhes do ID {identificador_existente} ou resposta sem dados.")

    if len(dados_atuais_json['dados']) > 1:
        logging.warning(f"Relatório de detalhes {CODIGO_RELATORIO_DETALHES_ALUNO} retornou múltiplos registros para ID {identificador_existente}. Usando o primeiro.")
    dados_sistema = dados_atuais_json['dados'][0]
    logging.debug(f"Dados atuais do sistema para ID {identificador_existente}: {dados_sistema}")

    payload_api = construir_payload_completo(dados_novos_aluno, dados_sistema, identificador_existente)
    
    # --- INÍCIO DA LÓGICA DE DUAS TENTATIVAS DE ATUALIZAÇÃO ---
    if payload_api:
        # --- TENTATIVA 1: Atualizar usando ID como identificador (padrão) ---
        logging.info(f"Enviando atualização (Tentativa 1/2) para o aluno ID {identificador_existente} usando ID como identificador...")
        try:
            resposta = cliente_solis.atualizar_pessoa(payload_api)
            logging.info(f"✅ SUCESSO (Tentativa 1)! Dados de '{nome_para_busca}' (ID: {identificador_existente}) atualizados.")
            return "Sucesso"
        
        except ApiError as e:
            logging.warning(f"Falha na Tentativa 1 (atualizar por ID): {e}")
            logging.info("--- Iniciando Tentativa 2/2: Atualizar usando CPF como identificador ---")

            # Obter o CPF dos dados novos (deve ter sido consolidado e estar formatado)
            aluno_cpf = dados_novos_aluno.get('numero_cpf')
            
            if not aluno_cpf:
                logging.error("Tentativa 2 falhou: Não foi possível encontrar CPF nos dados consolidados para usar como fallback.")
                raise e # Relança o erro original da Tentativa 1

            # Valida o CPF removendo a formatação, mas usa o original formatado
            cpf_limpo_para_validar = re.sub(r'[^\d]', '', str(aluno_cpf))
            if len(cpf_limpo_para_validar) != 11:
                logging.error(f"Tentativa 2 falhou: CPF extraído ('{aluno_cpf}') parece inválido.")
                raise e # Relança o erro original da Tentativa 1

            # Modifica o payload para a Tentativa 2
            # Usa o CPF formatado (aluno_cpf) como 'identificador' e 'usuario'
            # Mantém o 'codigodapessoa' como o ID original
            payload_api['pessoa']['identificador'] = aluno_cpf
            payload_api['pessoa']['usuario'] = aluno_cpf # Baseado no log de exemplo
            
            logging.debug(f"Payload modificado para Tentativa 2 (CPF formatado): {json.dumps(payload_api, indent=2)}")
            logging.info(f"Enviando atualização (Tentativa 2/2) para o aluno ID {identificador_existente} usando CPF {aluno_cpf} como identificador...")

            # A segunda tentativa. Se falhar, a exceção será capturada pelo bloco 'try' principal da função 'main'
            resposta_cpf = cliente_solis.atualizar_pessoa(payload_api)
            
            logging.info(f"✅ SUCESSO (Tentativa 2)! Dados de '{nome_para_busca}' (ID: {identificador_existente}) atualizados usando CPF.")
            return "Sucesso (via CPF)"
            
    else:
        logging.info(f"✅ Nenhuma atualização necessária para '{nome_para_busca}' (ID: {identificador_existente}).")
        return "Sem alterações"
    # --- FIM DA LÓGICA DE DUAS TENTATIVAS DE ATUALIZAÇÃO ---


# ==============================================================================
# --- DADOS DE EXEMPLO (SIMULAÇÃO DAS PENDÊNCIAS) ---
# ==============================================================================

# --- TESTE 1: BARBARA BATISTA RODRIGUES (Baseado no Log 1) ---
# Nota: Este log NÃO contém Certidão de Nascimento/Casamento.
# A IA tentará adivinhar o sexo, mas o estado civil provavelmente será nulo.
# O CEP não está no 'extracted_data' do comprovante, apenas no 'reason'.
# A extração do 'reason' (parse_reason_string) pode falhar em pegar o CEP se o regex não bater.
pendencia_barbara = {
    "aluno_nome": "BARBARA BATISTA RODRIGUES", # Nome para busca
    "dados_analise": { # Este é o "results" do Log 1
        "COMPROVANTE_RESIDENCIA": {
            "classified_doc_type": None,
            "drive_file_ids": ["1wPZKi0iN_XZRus4pgySKXiyWqdxn4Q3x"],
            "drive_upload_status": "success",
            "extracted_data": {
                "nome_aluno_sistema": "BARBARA BATISTA RODRIGUES",
                "nome_completo": "CLAUDIO RAMIRES SENSON E CASTRO",
                "numero_cpf": "077.401.156-49",
                "numero_rg": None
                # CEP não está no extracted_data deste log, apenas no 'reason'
            },
            "identified_doc_type": "Comprovante de Residência",
            "reason": "Documento aprovado. Verificação dos critérios: [confirmar se o documento é um comprovante de residência válido: Sim, é uma Fatura Detalhada da INETVIP], [extrair o endereço do destinatário: R Conde Marques Neto, N° 1455, CASA, Cond da Lagoa, Lagoa Santa - MG], [extrair o CEP: 33240-354], [o comprovante de residência deve ser válido e totalmente legível: Sim, totalmente legível].",
            "status": "approved"
        },
        "CPF": {
            "classified_doc_type": None,
            "drive_file_ids": ["1gW6lIBu1smUC9h8ZvegPU6CSsy_FFqDR"],
            "drive_upload_status": "success",
            "extracted_data": {
                "nome_aluno_sistema": "BARBARA BATISTA RODRIGUES",
                "nome_completo": "BARBARA BATISTA RODRIGUES",
                "numero_cpf": "073.074.886-39"
            },
            "identified_doc_type": "CPF",
            "reason": "Documento aprovado. Verificação dos critérios: [Documento é comprovante de CPF: SIM], [Nome Completo: BARBARA BATISTA RODRIGUES], [Número do CPF: 073.074.886-39], [Documento legível: SIM]. | Validação de dados confirmada: o nome no sistema ('BARBARA BATISTA RODRIGUES') é compatível com o nome no documento ('BARBARA BATISTA RODRIGUES') usando o modo 'flexible_contain'.",
            "status": "approved"
        },
        "DIPLOMA_GRADUACAO": {
            "classified_doc_type": None,
            "drive_file_ids": ["1bB5KQKGAp588LwrCUpVb5mBo-XlLJYKh"],
            "drive_upload_status": "success",
            "extracted_data": {
                "data_colacao_grau": "04/03/2015",
                "nome_aluno_sistema": "BARBARA BATISTA RODRIGUES",
                "nome_completo": "Bárbara Batista Rodrigues",
                "numero_registro_diploma": "001234 LvrDSRD-3 Fls 155"
            },
            "identified_doc_type": "Diploma de Graduação",
            "reason": "Documento aprovado. Verificação dos critérios: [Confirmar se o documento é um Diploma de Graduação: Documento é um Diploma de Graduação em Direito], [Extrair o nome completo do diplomado e comparar: Bárbara Batista Rodrigues (correspondente a BARBARA BATISTA RODRIGUES)], [Verificar a data de colação de grau: 04/03/2015], [Localizar o número de registro oficial do diploma: 001234 LvrDSRD-3 Fls 155], [O documento deve ser totalmente legível: Documento legível]. | Validação de dados confirmada: o nome no sistema ('BARBARA BATISTA RODRIGUES') é compatível com o nome no documento ('Bárbara Batista Rodrigues') usando o modo 'flexible_contain'.",
            "status": "approved"
        },
        "HISTORICO_GRADUACAO": {
            "classified_doc_type": None,
            "drive_file_ids": ["1MPYDcoofz4Nz2OZfW3BqiLrux69CR6T-"],
            "drive_upload_status": "success",
            "extracted_data": {
                "carga_horaria_total": "4.524 horas/aula",
                "data_colacao_grau": "04/03/2015",
                "data_conclusao": "04/03/2015",
                "nome_aluno_sistema": "BARBARA BATISTA RODRIGUES",
                "nome_completo": "BÁRBARA BATISTA RODRIGUES",
                "nome_curso": "DIREITO",
                "numero_rg": "MG-13.284.271"
            },
            "identified_doc_type": "Historico Escolar",
            "reason": "Documento aprovado. Verificação dos critérios: Confirmar se o documento é um Histórico Escolar de nível superior.: Histórico Escolar de nível superior, Extrair o nome completo do aluno e o nome do curso.: BÁRBARA BATISTA RODRIGUES, DIREITO, Verificar a Carga Horária Total do curso no documento.: 4.524 horas/aula, Localizar a data de conclusão do curso ou colação de grau.: 04/03/2015, O documento deve ser totalmente legível.: Sim | Validação de dados confirmada: o nome no sistema ('BARBARA BATISTA RODRIGUES') é compatível com o nome no documento ('BÁRBARA BATISTA RODRIGUES') usando o modo 'flexible_contain'.",
            "status": "approved"
        },
        "RG": {
            "classified_doc_type": None,
            "drive_file_ids": ["1034Z7-JWTedzqoGmstOWLg_qaADCn0lM"],
            "drive_upload_status": "success",
            "extracted_data": {
                "filiacao": "MARCIO RODRIGUES DE JESUS / CLAUDIA BATISTA RODRIGUES",
                "nome_aluno_sistema": "BARBARA BATISTA RODRIGUES",
                "nome_completo": "BARBARA BATISTA RODRIGUES",
                "numero_cpf": None,
                "numero_rg": "MG-13.384.271",
                "orgao_expedidor": "Instituto de Identificação/MG"
            },
            "identified_doc_type": "RG",
            "reason": "Documento aprovado. Verificação dos critérios: Confirmar se o documento é um RG válido e não outro tipo: RG, Verificar a presença de uma foto do titular: Foto presente, Extrair o nome completo e comparar com o nome do aluno: BARBARA BATISTA RODRIGUES (correspondente), Extrair a Filiação (nomes dos pais): MARCIO RODRIGUES DE JESUS / CLAUDIA BATISTA RODRIGUES, Extrair a Data de Nascimento: 20/09/1984, Extrair o Número do Registro Geral (RG): MG-13.384.271, Extrair o número do CPF, se presente no RG: Não encontrado, Extrair o Órgão Expedidor/UF: Instituto de Identificação/MG, Extrair a Naturalidade: BELO HORIZONTE-MG, Verificar a presença de uma assinatura do titular: Assinatura presente, O documento deve ser totalmente legível: Totalmente legível. | Validação de dados confirmada: o nome no sistema ('BARBARA BATISTA RODRIGUES') é compatível com o nome no documento ('BARBARA BATISTA RODRIGUES') usando o modo 'flexible_contain'.",
            "status": "approved"
        }
    }
}

# --- TESTE 2: ABEL AZEREDO DE OLIVEIRA (Baseado no Log 2) ---
# Nota: Este log contém documentos rejeitados (CPF, RG) que serão ignorados pelo script.
# Contém Certidão de Casamento, que será usada pela IA para definir o estado civil.
pendencia_abel = {
    "aluno_nome": "ABEL AZEREDO DE OLIVEIRA", # Nome para busca
    "dados_analise": { # Este é o "results" do Log 2
        "CERTIDAO_NASCIMENTO_CASAMENTO": {
            "classified_doc_type": "CERTIDAO NASCIMENTO CASAMENTO",
            "drive_file_ids": ["1IwIa-xhYP6BWmyhma2_Jpoq9Epm_LGsV"],
            "drive_upload_status": "success",
            "extracted_data": {
                "filiacao": "JOSÉ FORTUNATO DE OLIVEIRA FILHO e WANDA IRLEY AZEREDO DE OLIVEIRA",
                "nome_aluno_sistema": "ABEL AZEREDO DE OLIVEIRA",
                "nome_completo": "ABEL AZEREDO DE OLIVEIRA"
            },
            "identified_doc_type": "Certidão de Casamento",
            "reason": "Documento aprovado. Verificação dos critérios: [Tipo de documento: Certidão de Casamento], [Nome completo do aluno: ABEL AZEREDO DE OLIVEIRA (corresponde ao nome no sistema)], [Filiação do aluno: JOSÉ FORTUNATO DE OLIVEIRA FILHO e WANDA IRLEY AZEREDO DE OLIVEIRA], [Data de Nascimento do aluno: 06 de outubro de 1986], [Data do Casamento: 19 de dezembro de 2019], [Averbação de divórcio/separação: Não consta], [Informações do cartório: Presentes], [Legibilidade: Totalmente legível]. | Validação de dados confirmada: o nome no sistema ('ABEL AZEREDO DE OLIVEIRA') é compatível com o nome no documento ('ABEL AZEREDO DE OLIVEIRA') usando o modo 'flexible_contain'.",
            "status": "approved"
        },
        "CNH": {
            "classified_doc_type": None,
            "drive_file_ids": ["1ai1ccw91qZInD6Y72dCO2D5_f1AZVVDH"],
            "drive_upload_status": "success",
            "extracted_data": {
                "nome_aluno_sistema": "ABEL AZEREDO DE OLIVEIRA",
                "nome_completo": "ABEL AZEREDO DE OLIVEIRA",
                "numero_cpf": "119.490.627-32"
            },
            "identified_doc_type": "CNH Digital",
            "reason": "Documento aprovado. Verificação dos critérios: CNH válida: Sim, Nome completo: ABEL AZEREDO DE OLIVEIRA, CNH válida e em conformidade: Válida até 29/06/2033, Foto do titular: Presente, Número do CPF: 119.490.627-32, Data de validade do documento: 29/06/2033, Legibilidade do documento: Totalmente legível. | Validação de dados confirmada: o nome no sistema ('ABEL AZEREDO DE OLIVEIRA') é compatível com o nome no documento ('ABEL AZEREDO DE OLIVEIRA') usando o modo 'flexible_contain'.",
            "status": "approved"
        },
        "COMPROVANTE_RESIDENCIA": {
            "classified_doc_type": None,
            "drive_file_ids": ["1jxvsHjLeLaYBXjf6frfDzJMw9U8cUmKr"],
            "drive_upload_status": "success",
            "extracted_data": {
                "nome_aluno_sistema": "ABEL AZEREDO DE OLIVEIRA",
                "nome_completo": "Williane Alves da Silva",
                "numero_cpf": "119.490.627-32",
                "numero_rg": None
            },
            "identified_doc_type": "Comprovante de Residência",
            "reason": "Documento aprovado. Verificação dos critérios: comprovante de residência válido: Sim, endereço do destinatário: RUA DO SOL / NAZARE, N\\D Santo Agostinho/PE, CEP: 54590-000, comprovante de residência legível: Sim.",
            "status": "approved"
        },
        "CPF": {
            "classified_doc_type": None,
            "extracted_data": {
                "nome_aluno_sistema": "ABEL AZEREDO DE OLIVEIRA",
                "nome_completo": "BARBARA BATISTA RODRIGUES",
                "numero_cpf": "119.490.627-32"
            },
            "identified_doc_type": "CPF",
            "reason": "O nome no documento (BARBARA BATISTA RODRIGUES) não corresponde ao nome do aluno no sistema (ABEL AZEREDO DE OLIVEIRA).",
            "status": "rejected"
        },
        "DIPLOMA_GRADUACAO": {
            "reason": "Sem critérios definidos para 'DIPLOMA_GRADUACAO' no curso '1ª Graduação'. Verifique o ficheiro criteria.json.",
            "status": "ignored"
        },
        "DOCUMENTO_MILITAR": {
            "classified_doc_type": None,
            "drive_file_ids": ["1fxXwzk2HSNNAMOsjr3BSOONR2-UMS0Y_"],
            "drive_upload_status": "success",
            "extracted_data": {
                "filiacao": "José Fortunato de Oliveira Filho e Wanda Irley Azeredo de Oliveira",
                "nome_aluno_sistema": "ABEL AZEREDO DE OLIVEIRA",
                "nome_completo": "Abel Azeredo de Oliveira",
                "numero_alistamento_militar": "101575"
            },
            "identified_doc_type": "Certificado de Reservista",
            "reason": "Documento aprovado. Verificação dos critérios: documento é um Certificado de Reservista, nome completo: ABEL AZEREDO DE OLIVEIRA (corresponde ao do aluno), filiação: José Fortunato de Oliveira Filho e Wanda Irley Azeredo de Oliveira, número de alistamento militar: 101575, legibilidade: Legível | Validação de dados confirmada: o nome no sistema ('ABEL AZEREDO DE OLIVEIRA') é compatível com o nome no documento ('Abel Azeredo de Oliveira') usando o modo 'flexible_contain'.",
            "status": "approved"
        },
        "HISTORICO_ENSINO_MEDIO": {
            "classified_doc_type": None,
            "drive_file_ids": ["17xM3sD4OmXJsYYwsSY6q4jbBXXwEgIOp"],
            "drive_upload_status": "success",
            "extracted_data": {
                "carga_horaria_total": "1200",
                "data_conclusao": "14.03.2025",
                "instituicao_ensino": "INSTITUTO DE FORMAÇÃO PROFISSIONAL E EMPREGO",
                "nome_aluno_sistema": "ABEL AZEREDO DE OLIVEIRA",
                "nome_completo": "ABEL AZEREDO DE OLIVEIRA",
                "numero_rg": "218016228-RJ"
            },
            "identified_doc_type": "Histórico Escolar",
            "reason": "Documento aprovado. Verificação dos critérios: [documento é um Histórico Escolar: Histórico Escolar], [nome da instituição de ensino: INSTITUTO DE FORMAÇÃO PROFISSIONAL E EMPREGO], [nome completo do aluno: ABEL AZEREDO DE OLIVEIRA], [nome do aluno no sistema: ABEL AZEREDO DE OLIVEIRA], [data de conclusão do curso: 14.03.2025], [Carga Horária Total cursada: 1200], [documento totalmente legível: Sim]. | Validação de dados confirmada: o nome no sistema ('ABEL AZEREDO DE OLIVEIRA') é compatível com o nome no documento ('ABEL AZEREDO DE OLIVEIRA') usando o modo 'flexible_contain'.",
            "status": "approved"
        },
        "RG": {
            "classified_doc_type": None,
            "extracted_data": {
                "filiacao": "FAUSTO LUCIO DIMAS / MARIA DO CARMO FERREIRA DIMAS",
                "nome_aluno_sistema": "ABEL AZEREDO DE OLIVEIRA",
                "nome_completo": "PABLO LUCIO DIMAS",
                "numero_cpf": "074.111.926-94",
                "numero_rg": "MG-11.955.485",
                "orgao_expedidor": "Instituto de Identificação/MG"
            },
            "identified_doc_type": "RG",
            "reason": "O nome no documento (PABLO LUCIO DIMAS) não corresponde ao nome do aluno no sistema (ABEL AZEREDO DE OLIVEIRA).",
            "status": "rejected"
        }
    }
}


# Lista de amostras para processar
testes_a_executar = {
    "teste_log_barbara": pendencia_barbara,
    "teste_log_abel": pendencia_abel,
}

# ==============================================================================
# --- EXECUÇÃO PRINCIPAL DO TESTE ---
# ==============================================================================

if __name__ == "__main__":
    logging.info("--- INICIANDO SCRIPT DE TESTE AUTÔNOMO (usando .env) ---")

    # Carrega configurações da API Solis e Gemini do .env
    api_url = os.getenv("SOLIS_API_URL")
    jwt_token = os.getenv("SOLIS_JWT_TOKEN")
    gemini_api_key = os.getenv("GEMINI_API_KEY")

    if not api_url or not jwt_token:
        logging.error("ERRO CRÍTICO: Variáveis SOLIS_API_URL ou SOLIS_JWT_TOKEN não encontradas no .env")
        exit(1)
    if not gemini_api_key:
        logging.warning("AVISO: Variável GEMINI_API_KEY não encontrada no .env. Análise de IA será pulada.")

    # Inicializa o cliente Solis
    try:
        cliente_solis_teste = SolisAPIClient(api_url, jwt_token)
        logging.info("Cliente Solis API inicializado com sucesso.")
    except Exception as e:
        logging.error(f"Erro ao inicializar SolisAPIClient: {e}", exc_info=True)
        exit(1)

    # Processa cada amostra de teste
    resultados_gerais = {}
    for nome_teste, pendencia_data in testes_a_executar.items():
        logging.info(f"\n{'='*20} EXECUTANDO: {nome_teste} {'='*20}")
        resultado_teste = "FALHA (Erro inesperado no script)"
        try:
            logging.info("--- Etapa 1: Pré-processamento ---")
            # Validação básica da estrutura antes de processar
            if not isinstance(pendencia_data, dict) or "aluno_nome" not in pendencia_data or "dados_analise" not in pendencia_data:
                raise ValueError("Estrutura da 'pendencia_para_teste' está inválida. Verifique 'aluno_nome' e 'dados_analise'.")

            nome_aluno_proc, texto_doc_certidao_proc, dados_consolidados_proc = pre_processar_e_consolidar_pendencia(pendencia_data)
            logging.info(f"Pré-processamento OK para: {nome_aluno_proc}")
            logging.debug(f"Dados Consolidados: {json.dumps(dados_consolidados_proc, indent=2)}")

            logging.info("--- Etapa 2: Processamento Principal ---")
            resultado_proc = processar_pendencia_unica(
                nome_aluno_proc, texto_doc_certidao_proc, dados_consolidados_proc,
                cliente_solis_teste, gemini_api_key
            )
            logging.info(f"Processamento OK para {nome_aluno_proc}. Resultado: {resultado_proc}")
            resultado_teste = resultado_proc

        except PermanentApiError as e: logging.error(f"ERRO PERMANENTE: {e}"); resultado_teste = f"Erro Permanente: {e}"
        except TemporaryApiError as e: logging.warning(f"ERRO TEMPORÁRIO: {e}"); resultado_teste = f"Erro Temporário: {e}"
        except ApiError as e: logging.error(f"ERRO DE API: {e}"); resultado_teste = f"Erro API: {e}"
        except ValueError as e: logging.error(f"ERRO DE VALIDAÇÃO: {e}"); resultado_teste = f"Erro Validação: {e}"
        except Exception as e: logging.critical(f"ERRO INESPERADO: {e}", exc_info=True); resultado_teste = f"Erro Inesperado: {e}"

        resultados_gerais[nome_teste] = resultado_teste

    # --- Resumo Final ---
    logging.info(f"\n{'='*20} RESUMO DOS TESTES {'='*20}")
    for nome_teste, resultado in resultados_gerais.items():
        logging.info(f"- {nome_teste}: {resultado}")
    logging.info("--- FIM DO SCRIPT DE TESTE ---")
