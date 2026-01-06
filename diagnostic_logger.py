# -*- coding: utf-8 -*-
# ARQUIVO: diagnostic_logger.py
# DESCRIÇÃO: Script de diagnóstico com BUSCA RECURSIVA (entra nas subpastas DOC, etc).
# EXECUÇÃO: python diagnostic_logger.py

import logging
import json
import os
import unicodedata
import re
import sys
from drive_handler import DriveHandler

# --- CONFIGURAÇÃO MANUAL (PREENCHIDA) ---
ALUNO_ALVO = "ABEL AZEREDO DE OLIVEIRA" 
MANUAL_DRIVE_ID_A_M = "0ALL0qV6e99bpUk9PVA" 
MANUAL_DRIVE_ID_N_Z = "0ALdB4jSukRO3Uk9PVA" 
DRIVE_CONFIG_FILE = 'drive_config.json'

# --- MAPEAMENTO IGUAL AO DO ALUNO_SERVICE ---
STANDARD_FILENAMES = {
    "RG": ["RG", "IDENTIDADE", "CARTEIRA DE IDENTIDADE", "R.G"],
    "CNH": ["CNH", "HABILITACAO", "CARTEIRA DE MOTORISTA", "CARTEIRA NACIONAL DE HABILITACAO"],
}

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger('DIAGNOSTICO')

class DiagnosticTool:
    def __init__(self):
        print("\n--- INICIANDO FERRAMENTA DE DIAGNÓSTICO (RECURSIVA) ---")
        try:
            self.drive_handler = DriveHandler()
            if not self.drive_handler.is_ready():
                print("ERRO: DriveHandler não conectou.")
                sys.exit(1)
            print(">> Conexão com Google Drive: OK")
        except Exception as e:
            print(f"ERRO CRÍTICO ao iniciar: {e}")
            sys.exit(1)

    def _sanitize_name(self, text: str) -> str:
        if not text: return ""
        nfkd_form = unicodedata.normalize('NFKD', str(text).upper())
        only_ascii = nfkd_form.encode('ASCII', 'ignore')
        return re.sub(r"[^A-Z0-9\s'-]", '', only_ascii.decode('utf-8')).strip()

    def _clean_filename_garbage(self, text: str) -> str:
        if not text: return ""
        text = os.path.splitext(text)[0]
        text = re.sub(r'\s*[\(\[]\d+[\)\]]', '', text)
        text = re.sub(r'\s+(copia|copy|cópia)', '', text, flags=re.IGNORECASE)
        text = re.sub(r'\s+(FRENTE|VERSO|PARTE\s+\d+|PAG\s+\d+|PÁG\s+\d+)$', '', text, flags=re.IGNORECASE)
        return self._sanitize_name(text)

    def list_files_recursive(self, folder_id, drive_id, path_prefix=""):
        """Lista arquivos entrando em subpastas, igual ao sistema principal."""
        try:
            items = self.drive_handler.list_all_items_in_folder(folder_id, drive_id=drive_id)
        except Exception as e:
            print(f"   [Erro ao ler pasta {folder_id}]: {e}")
            return []

        if not items:
            return []

        all_files_found = []
        
        for item in items:
            if not item: continue
            name = item.get('name', '???')
            mime = item.get('mimeType', '')
            item_id = item.get('id')

            if mime == 'application/vnd.google-apps.folder':
                # Se for pasta, entra nela (Recursão)
                print(f"   [Subpasta Encontrada]: {path_prefix}/{name} - Entrando...")
                sub_files = self.list_files_recursive(item_id, drive_id, path_prefix + "/" + name)
                all_files_found.extend(sub_files)
            else:
                # Se for arquivo, adiciona à lista
                item['_debug_path'] = f"{path_prefix}/{name}"
                all_files_found.append(item)
        
        return all_files_found

    def run_diagnostic(self, student_name):
        print(f"\n>> 1. Configurando busca para aluno: '{student_name}'")
        first_letter = student_name.strip().upper()[0]
        is_a_m = 'A' <= first_letter <= 'M'
        drive_id_key = 'A-M_drive_id' if is_a_m else 'N-Z_drive_id'
        
        drive_id = None
        try:
            if os.path.exists(DRIVE_CONFIG_FILE):
                with open(DRIVE_CONFIG_FILE, 'r') as f:
                    config = json.load(f)
                    if 'default' in config: drive_id = config['default'].get(drive_id_key)
                    else: drive_id = config.get(drive_id_key)
        except: pass

        if not drive_id: drive_id = MANUAL_DRIVE_ID_A_M if is_a_m else MANUAL_DRIVE_ID_N_Z
        
        if not drive_id:
            drive_id = input(f"   > ID do Drive ({'A-M' if is_a_m else 'N-Z'}) não encontrado. Cole aqui: ").strip()

        print(f"   - Usando Drive ID: {drive_id}")

        # 2. Localizar Pasta
        print(f"\n>> 2. Buscando pasta do aluno...")
        folders = self.drive_handler.find_folders_containing_name(student_name, drive_id)
        if not folders:
            sanitized = self._sanitize_name(student_name)
            folders = self.drive_handler.find_folders_containing_name(sanitized, drive_id)

        if not folders:
            print("   - FALHA: Nenhuma pasta encontrada.")
            return
        
        target_folder = folders[0]
        print(f"   - Pasta ALVO: '{target_folder['name']}' (ID: {target_folder['id']})")

        # 3. Listar Arquivos (AGORA RECURSIVO)
        print(f"\n>> 3. Listando TODOS os arquivos (Recursivo)...")
        all_files = self.list_files_recursive(target_folder['id'], drive_id, target_folder['name'])
        
        if not all_files:
            print("   - A pasta está vazia (sem arquivos, apenas pastas vazias?).")
            return

        print(f"   - Total de arquivos encontrados: {len(all_files)}")

        # 4. SIMULAÇÃO DE MATCH
        print(f"\n{'='*60}")
        print(f"ANÁLISE DETALHADA DE CADA ARQUIVO")
        print(f"{'='*60}")

        for file in all_files:
            raw_name = file.get('name', '???')
            full_path = file.get('_debug_path', raw_name)
            print(f"\nARQUIVO: [{full_path}]")
            
            doc_name_part = os.path.splitext(raw_name)[0]
            if ' - ' in doc_name_part:
                standard_name_from_file = doc_name_part.split(' - ')[-1].strip().upper()
                print(f"   -> Nome Extraído (após ' - '): '{standard_name_from_file}'")
            else:
                standard_name_from_file = doc_name_part.strip().upper()
                print(f"   -> Nome Extraído (tudo): '{standard_name_from_file}'")

            cleaned_name = self._clean_filename_garbage(standard_name_from_file)
            print(f"   -> Nome LIMPO para busca: '{cleaned_name}'")

            found_something = False
            for doc_type, synonyms in STANDARD_FILENAMES.items():
                print(f"   --- Testando [{doc_type}] ---")
                for term in synonyms:
                    term_clean = self._sanitize_name(term)
                    
                    if cleaned_name == term_clean:
                        print(f"       [SUCESSO] Match EXATO: '{term}'")
                        print(f"       >>> RESULTADO: É UM {doc_type} <<<")
                        found_something = True
                        break
                    
                    try:
                        pattern = r'\b' + re.escape(term_clean) + r'\b'
                        if re.search(pattern, cleaned_name):
                            print(f"       [SUCESSO] Match REGEX: '{term}'")
                            print(f"       >>> RESULTADO: É UM {doc_type} <<<")
                            found_something = True
                            break
                    except: pass
                if found_something: break

            if not found_something:
                print("   >>> RESULTADO: NÃO IDENTIFICADO como RG ou CNH.")

if __name__ == "__main__":
    tool = DiagnosticTool()
    tool.run_diagnostic(ALUNO_ALVO)