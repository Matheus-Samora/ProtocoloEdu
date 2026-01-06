# cache_manager.py
# Módulo para gerenciar um cache persistente dos resultados da análise de arquivos.
import json
import os
import hashlib

# Define o caminho para o arquivo de cache
CACHE_FILE_PATH = os.path.join(os.path.dirname(__file__), 'config', 'analysis_cache.json')

def _load_cache():
    """Carrega o cache do arquivo JSON. Retorna um dicionário vazio se não existir."""
    if not os.path.exists(CACHE_FILE_PATH):
        return {}
    try:
        with open(CACHE_FILE_PATH, 'r', encoding='utf-8') as f:
            # Garante que o ficheiro de cache vazio seja tratado corretamente
            content = f.read()
            if not content:
                return {}
            return json.loads(content)
    except (json.JSONDecodeError, FileNotFoundError):
        return {}

def _save_cache(cache_data):
    """Salva o dicionário de cache de volta no arquivo JSON."""
    try:
        with open(CACHE_FILE_PATH, 'w', encoding='utf-8') as f:
            json.dump(cache_data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"ERRO: Não foi possível salvar o cache em {CACHE_FILE_PATH}: {e}")

def generate_file_hash(file_path):
    """
    Gera um hash SHA256 único para um arquivo com base em seu conteúdo.
    """
    sha256_hash = hashlib.sha256()
    try:
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    except IOError as e:
        print(f"ERRO: Não foi possível ler o arquivo {file_path} para gerar o hash: {e}")
        return None

def get_from_cache(file_hash):
    """
    Busca um resultado no cache usando o hash do arquivo.
    """
    if not file_hash:
        return None
    cache = _load_cache()
    return cache.get(file_hash)

def add_to_cache(file_hash, identified_type):
    """
    Adiciona um novo resultado de análise ao cache.
    """
    if not file_hash or not identified_type:
        return
    cache = _load_cache()
    cache[file_hash] = identified_type
    _save_cache(cache)
    print(f"INFO: Resultado para o hash '{file_hash[:8]}...' salvo no cache como '{identified_type}'.")
