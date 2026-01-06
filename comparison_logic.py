# -*- coding: utf-8 -*-
# ARQUIVO: comparison_logic.py
# DESCRIÇÃO: Centraliza as funções de comparação de strings.

import unicodedata
import re
from thefuzz import fuzz

def _normalize_text_for_comparison(text: str) -> str:
    """
    Normaliza o texto para comparação, espelhando a lógica de _normalize_text em core_logic.py
    (case-insensitive, sem acentos, sem caracteres especiais).
    """
    if not text:
        return ""
    text = str(text)
    # NFKD decompõe caracteres para separar acentos
    nfkd_form = unicodedata.normalize('NFKD', text.upper())
    # Codifica para ASCII, ignorando caracteres que não podem ser representados (como acentos)
    only_ascii = nfkd_form.encode('ASCII', 'ignore')
    # Remove qualquer coisa que não seja letra, número, espaço ou hífen
    return re.sub(r'[^A-Z0-9\s-]', '', only_ascii.decode('utf-8')).strip()

def flexible_name_comparison(name_from_document: str, student_name: str) -> bool:
    """
    Compara dois nomes aceitando inclusão mútua (bidirecional).
    
    Cenário 1 (Abreviação no doc): 
       Cadastro: "Abel Azeredo de Oliveira" 
       Doc: "Abel Oliveira" 
       -> ACEITA (Partes do aluno estão no doc)
       
    Cenário 2 (Casamento/Nome de solteira - CASO DA JESSICA):
       Cadastro: "Jessica Lopes Carvalho Rodrigues Severo" (Nome Novo)
       Doc: "Jessica Lopes Carvalho Rodrigues" (Nome Antigo)
       -> ACEITA AGORA (Partes do doc estão no cadastro)
    """
    if not name_from_document or not student_name:
        return False

    norm_doc_name = _normalize_text_for_comparison(name_from_document)
    norm_student_name = _normalize_text_for_comparison(student_name)

    prepositions = {'DE', 'DA', 'DO', 'DOS', 'DAS', 'E'}
    
    # Criamos conjuntos (sets) para facilitar a verificação matemática de subconjuntos
    doc_parts = {part for part in norm_doc_name.split() if part not in prepositions}
    student_parts = {part for part in norm_student_name.split() if part not in prepositions}

    if not student_parts or not doc_parts:
        return False

    # Verifica Direção 1: O nome do cadastro cabe no documento?
    # (Útil quando o documento tem o nome completo e o cadastro está abreviado, ou vice-versa na lógica antiga)
    student_in_doc = student_parts.issubset(doc_parts)

    # Verifica Direção 2: O nome do documento cabe no cadastro?
    # (ESSENCIAL PARA O CASO DE CASAMENTO: O doc antigo é um subconjunto do nome novo)
    doc_in_student = doc_parts.issubset(student_parts)

    # Aceita se qualquer uma das direções for verdadeira
    return student_in_doc or doc_in_student

def fuzzy_name_comparison(name_from_document: str, student_name: str, tolerance_ratio: int = 85) -> bool:
    """
    Compara duas strings usando a biblioteca thefuzz para encontrar similaridade percentual.
    Útil para capturar pequenos erros de digitação.
    Ex: "Jhonatan da Silva" vs "Jonathan da Silva" -> True

    NOTA DE CONFIGURAÇÃO:
    - O 'tolerance_ratio' define o quão rigoroso é o teste (0 a 100).
    - 90 (padrão anterior) = Muito rigoroso (quase nenhum erro permitido).
    - 85 = Recomendado (aceita 1 ou 2 letras trocadas em nomes longos).
    """
    if not name_from_document or not student_name:
        return False
        
    norm_doc_name = _normalize_text_for_comparison(name_from_document)
    norm_student_name = _normalize_text_for_comparison(student_name)

    # fuzz.ratio calcula a similaridade de Levenshtein como uma porcentagem (de 0 a 100)
    similarity_ratio = fuzz.ratio(norm_doc_name, norm_student_name)
    
    # Se a similaridade encontrada for maior ou igual à tolerância, retorna True (Aceita)
    return similarity_ratio >= tolerance_ratio