# ARQUIVO: config_manager.py
# Módulo responsável por carregar todas as configurações do projeto.
import json
import os
import logging
import string # Importado para ajudar a verificar o alfabeto

# --- Caminhos de Configuração ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Caminho para os critérios de validação dos documentos
CRITERIA_CONFIG_PATH = os.path.join(BASE_DIR, 'config', 'criteria.json')

# Caminho para as credenciais do Cliente OAuth 2.0
CREDENTIALS_PATH = os.path.join(BASE_DIR, 'credentials.json')

# Caminho para o ficheiro que guarda os IDs dos Drives Compartilhados por tenant
DRIVE_CONFIG_PATH = os.path.join(BASE_DIR, 'config', 'drive_config.json')


def load_criteria():
    """Carrega os critérios de validação do arquivo JSON."""
    try:
        with open(CRITERIA_CONFIG_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        logging.error(f"Erro: Arquivo de critérios não encontrado em {CRITERIA_CONFIG_PATH}")
        return {}
    except json.JSONDecodeError:
        logging.error(f"Erro: O arquivo de critérios {CRITERIA_CONFIG_PATH} não é um JSON válido.")
        return {}

# --- FUNÇÕES PARA O GOOGLE DRIVE ---

def get_credentials_file():
    """Retorna o caminho para o arquivo de credenciais OAuth 2.0, se ele existir."""
    if not os.path.exists(CREDENTIALS_PATH):
        logging.error(f"ERRO CRÍTICO: O arquivo 'credentials.json' não foi encontrado na pasta raiz do projeto.")
        return None
    return CREDENTIALS_PATH

def load_drive_ids():
    """
    Função para carregar os IDs dos Drives Compartilhados do arquivo de configuração.
    Nome alterado de '_load_drive_ids' para 'load_drive_ids' para compatibilidade.
    """
    try:
        with open(DRIVE_CONFIG_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        logging.error(f"ERRO: Arquivo 'drive_config.json' não encontrado na pasta 'config'. Crie este arquivo.")
        return {}
    except json.JSONDecodeError:
        logging.error(f"ERRO: O arquivo 'drive_config.json' não é um JSON válido.")
        return {}

# --- FUNÇÃO MODIFICADA ---
def get_drive_id_for_tenant(tenant_id, student_name=None):
    """
    Carrega todos os IDs de drive e retorna o específico para o tenant.
    Se a configuração do tenant for dividida por letras (ex: A-M, N-Z),
    usa o nome do aluno para decidir qual ID de pasta usar.
    """
    drive_configs = load_drive_ids() # Chamada interna atualizada para usar a função pública
    tenant_config = drive_configs.get(tenant_id)
    
    if not tenant_config:
        logging.error(f"Configuração do Drive não foi encontrada para o tenant '{tenant_id}' no arquivo 'config/drive_config.json'.")
        return None
    
    # Se a configuração for um dicionário (dividida por letras)
    if isinstance(tenant_config, dict):
        if not student_name:
            logging.error(f"O tenant '{tenant_id}' tem configuração de Drive dividida, mas o nome do aluno não foi fornecido.")
            return None
        
        first_letter = student_name.strip().upper()[0]
        if first_letter not in string.ascii_uppercase:
            logging.warning(f"Primeira letra do nome '{student_name}' não é uma letra válida. Usando a primeira configuração encontrada.")
            return next(iter(tenant_config.values()))

        # Itera sobre as faixas de letras (ex: "A-M")
        for letter_range, drive_id in tenant_config.items():
            try:
                start_char, end_char = letter_range.split('-')
                if start_char.upper() <= first_letter <= end_char.upper():
                    logging.info(f"Aluno '{student_name}' pertence à faixa '{letter_range}'. Usando Drive ID: {drive_id}")
                    return drive_id
            except ValueError:
                logging.error(f"A faixa de letras '{letter_range}' no config do drive está mal formatada. Deveria ser 'LETRA-LETRA'.")
                continue # Pula para a próxima faixa
        
        logging.error(f"Nenhuma faixa de letras correspondente encontrada para '{student_name}' no tenant '{tenant_id}'.")
        return None

    # Se for uma string simples (um único ID para o tenant)
    elif isinstance(tenant_config, str):
        logging.info(f"Usando ID do Drive '{tenant_config}' para o tenant '{tenant_id}'.")
        return tenant_config

    else:
        logging.error(f"Formato de configuração de Drive inválido para o tenant '{tenant_id}'.")
        return None

