# Arquivo: key_manager.py
# Descrição: Módulo central para gerenciar e fornecer as chaves de API do Google AI.

def get_all_keys():
    """
    Retorna uma lista com todas as suas chaves de API do Google AI.
    
    Esta abordagem permite que você adicione ou remova chaves facilmente
    em um único lugar, sem precisar alterar a lógica principal do assistente.
    
    Instrução: Substitua "SUA_CHAVE_API_..." pelas suas chaves reais.
    """
    import os
    env_key = os.environ.get("GEMINI_API_KEY")
    api_keys = []
    if env_key and env_key.startswith("AIza"):
        api_keys.append(env_key)
    return api_keys

