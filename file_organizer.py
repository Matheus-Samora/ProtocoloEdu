# -*- coding: utf-8 -*-
# ARQUIVO: file_organizer.py (Versão com nomes de arquivo padronizados e finalizados)
# DESCRIÇÃO: Módulo que contém dicionários para mapear e padronizar nomes de arquivos
#            conforme o padrão final solicitado.

import logging

# Configuração do logging
logging.basicConfig(level=logging.INFO, format='[FILE_ORGANIZER] [%(levelname)s] %(message)s')

# Dicionário para mapear chaves internas para nomes padrão de arquivo.
# Estes nomes são usados para criar o padrão 'NOME ALUNO - NOME DOCUMENTO.pdf'
STANDARD_FILENAMES = {
    "DIPLOMA_GRADUACAO": "DIPLOMA SUPERIOR",
    "HISTORICO_GRADUACAO": "HISTORICO SUPERIOR",
    "RG": "RG",
    "CPF": "CPF",
    "CNH": "CNH",
    "COMPROVANTE_RESIDENCIA": "COMPROVANTE DE RESIDENCIA",
    "HISTORICO_ENSINO_MEDIO": "HISTORICO ESCOLAR",
    "CERTIFICADO_ENSINO_MEDIO": "CERTIFICADO ESCOLAR",
    "QUITACAO_ELEITORAL": "QUITACAO ELEITORAL",
    "DOCUMENTO_MILITAR": "DOCUMENTO MILITAR",
    
    # --- ALTERAÇÃO APLICADA AQUI ---
    # Adicionadas chaves específicas para que o core_logic possa nomear o arquivo corretamente.
    "CERTIDAO_NASCIMENTO": "CERTIDAO DE NASCIMENTO",
    "CERTIDAO_CASAMENTO": "CERTIDAO DE CASAMENTO",
    
    # A chave abaixo serve como fallback e para a exibição na interface.
    "CERTIDAO_NASCIMENTO_CASAMENTO": "CERTIDAO DE NASCIMENTO OU CASAMENTO",
    
    "ARQUIVO_UNICO": "ARQUIVO UNICO"
}

logging.info("Módulo File Organizer carregado com os nomes de arquivo padronizados (versão final).")

