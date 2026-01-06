# Arquivo: key_manager.py
# Descrição: Módulo central para gerenciar e fornecer as chaves de API do Google AI.

def get_all_keys():
    """
    Retorna uma lista com todas as suas chaves de API do Google AI.
    
    Esta abordagem permite que você adicione ou remova chaves facilmente
    em um único lugar, sem precisar alterar a lógica principal do assistente.
    
    Instrução: Substitua "SUA_CHAVE_API_..." pelas suas chaves reais.
    """
    api_keys = [
        "AIzaSyBbxXALaM60hn-Es-kjKY0yopJ4qaDXF-s",
        "AIzaSyDQQDtxL79WXTdf6rpTSWngjVgE7vRzmFs",
        # Você pode adicionar mais chaves aqui, se tiver.
        # "SUA_CHAVE_API_3_AQUI", 
    ]
    return api_keys

