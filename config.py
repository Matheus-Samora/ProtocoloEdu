# -*- coding: utf-8 -*-
# ARQUIVO: config.py
# DESCRIÇÃO: Centraliza todas as configurações.
# CORREÇÃO APLICADA: Atualizado o Project ID padrão para o novo ambiente.

import json
import logging
import os

# Configuração do logging
logging.basicConfig(level=logging.INFO, format='[%(asctime)s] [%(levelname)s] [%(module)s] %(message)s')

# --- CAMINHOS PARA OS ARQUIVOS DE CONFIGURAÇÃO ---
DRIVE_CREDENTIALS_FILE = "credentials.json"
DRIVE_CONFIG_FILE = "drive_config.json"
CRITERIA_FILE = "criteria.json"

# --- CONFIGURAÇÕES DO PROJETO GOOGLE CLOUD ---
# AQUI ESTAVA O ERRO: O fallback estava apontando para o projeto antigo.
# Alterado para "protocolo-imes-imm" para garantir que funcione no novo ambiente.
PROJECT_ID = os.environ.get("GCP_PROJECT_ID") or os.environ.get("PROJECT_ID") or "protocolo-imes-imm"

# Localização padrão
LOCATION = os.environ.get("GCP_LOCATION") or os.environ.get("LOCATION") or "us-central1"

# --- CONFIGURAÇÃO DA API DO GEMINI ---
# A chave da API deve ser configurada aqui.
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY") or "AIzaSyDQANcdEKJtmIu51T9WUHN7QQ46oXjmT-w"

# --- LOG DE DEPURACAO ---
logging.info(f"Configuração carregada: PROJECT_ID='{PROJECT_ID}', LOCATION='{LOCATION}'")


# --- FUNÇÃO DE CARREGAMENTO DE CONFIGURAÇÃO ---
def load_json_config(filepath):
    """
    Função auxiliar para carregar um arquivo JSON de forma segura.
    """
    try:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        json_path = os.path.join(base_dir, filepath)
        with open(json_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            logging.critical(f"ARQUIVO DE CONFIGURAÇÃO NÃO ENCONTRADO: '{filepath}'.")
            return {}
    except json.JSONDecodeError:
        logging.critical(f"ERRO DE SINTAXE no arquivo JSON: '{filepath}'.")
        return {}

# --- CARREGAMENTO DOS CRITÉRIOS DE ANÁLISE ---
DOCUMENT_CRITERIA = load_json_config(CRITERIA_FILE)