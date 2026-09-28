# -*- coding: utf-8 -*-
# ARQUIVO: drive_handler.py
# DESCRIÇÃO: Versão BLINDADA contra erros de SSL, Timeout e BrokenPipe.
#            Inclui tratamento exaustivo de exceções de rede.

import logging
import json
import os
import re
import time
import io
import random
import socket
import ssl  # IMPORTANTE: Necessário para capturar erros SSL específicos
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseUpload

# Configura timeout global agressivo para evitar travamentos longos
socket.setdefaulttimeout(300)

CREDENTIALS_FILE = 'credentials.json'

class DriveHandler:
    def __init__(self):
        self.creds = None
        self.service = None
        self._initialize_service()

    def _initialize_service(self):
        """Inicializa ou Reinicializa o serviço do Google Drive."""
        try:
            if os.path.exists(CREDENTIALS_FILE):
                self.creds = service_account.Credentials.from_service_account_file(
                    CREDENTIALS_FILE, scopes=['https://www.googleapis.com/auth/drive']
                )
                self.service = build('drive', 'v3', credentials=self.creds)
                logging.info("Serviço do Google Drive (re)construído com sucesso.")
            else:
                logging.error(f"Arquivo de credenciais não encontrado: {CREDENTIALS_FILE}")
        except Exception as e:
            logging.critical(f"FALHA CRÍTICA ao construir o serviço: {e}", exc_info=True)

    def is_ready(self):
        return self.service is not None

    def _refresh_service(self):
        """Força a recriação do serviço em caso de BrokenPipe/Conexão morta."""
        logging.warning("Detectada instabilidade na conexão. Recriando serviço do Drive...")
        self.service = None
        time.sleep(2) # Espera um pouco antes de reconectar
        self._initialize_service()

    def _escape_query_value(self, value):
        return value.replace("'", "\\'")

    def _execute_paginated_list(self, request_params):
        """Motor de busca paginada com BLINDAGEM contra erros de rede."""
        all_items = []
        page_token = None
        max_retries = 5
        
        # Força pageSize pequeno para evitar sobrecarga no SSL
        if request_params.get('pageSize', 0) > 100:
             request_params['pageSize'] = 100

        while True:
            if page_token:
                request_params['pageToken'] = page_token
            
            success = False
            for attempt in range(max_retries):
                try:
                    if not self.service: self._initialize_service()
                    
                    response = self.service.files().list(**request_params).execute()
                    all_items.extend(response.get('files', []))
                    page_token = response.get('nextPageToken', None)
                    success = True
                    break 
                
                # --- BLOCO DE TRATAMENTO DE ERROS DE REDE ---
                except (socket.error, socket.timeout, ConnectionError, BrokenPipeError, TimeoutError, ssl.SSLError) as net_err:
                     logging.warning(f"Erro de Rede ({type(net_err).__name__}) na tentativa {attempt + 1}: {net_err}")
                     self._refresh_service()
                     time.sleep(2 + attempt) # Backoff progressivo

                except HttpError as error:
                    logging.warning(f"Erro HTTP {error.resp.status}, tentativa {attempt + 1}/{max_retries}.")
                    if attempt + 1 == max_retries: return None
                    time.sleep((2 ** attempt) + random.uniform(0, 1))
                
                except Exception as e:
                    # Captura GENÉRICA para evitar crash por erros desconhecidos (ex: SSL wrapped)
                    logging.error(f"Erro inesperado no Drive (Tentativa {attempt + 1}): {e}")
                    self._refresh_service()
                    time.sleep(2)

            if not success:
                logging.error("Falha ao listar arquivos após todas as tentativas. Retornando parcial ou vazio.")
                break # Sai do loop while se falhar todas as tentativas da página atual
            
            if not page_token:
                break
        return all_items

    def get_folder_details(self, folder_id):
        if not self.is_ready(): return None
        try:
            return self.service.files().get(fileId=folder_id, fields="id, name", supportsAllDrives=True).execute()
        except Exception:
            self._refresh_service()
            try:
                return self.service.files().get(fileId=folder_id, fields="id, name", supportsAllDrives=True).execute()
            except:
                return None

    def find_folder_by_exact_name(self, folder_name, drive_id):
        if not self.is_ready(): return None
        escaped_name = self._escape_query_value(folder_name)
        query = f"name = '{escaped_name}' and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
        request_params = {
            'q': query, 'spaces': 'drive', 'fields': 'files(id, name)', 'corpora': 'drive',
            'driveId': drive_id, 'includeItemsFromAllDrives': True,
            'supportsAllDrives': True, 'pageSize': 10
        }
        folders = self._execute_paginated_list(request_params)
        if folders:
            if len(folders) > 1: logging.warning(f"Múltiplas pastas encontradas com o nome exato '{folder_name}'. A usar a primeira.")
            return folders[0]
        return None

    def find_folders_containing_name(self, name_part, drive_id):
        if not self.is_ready(): return []
        escaped_name = self._escape_query_value(name_part)
        query = f"name contains '{escaped_name}' and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
        request_params = {
            'q': query, 'spaces': 'drive', 'fields': 'files(id, name)',
            'corpora': 'drive', 'driveId': drive_id, 'includeItemsFromAllDrives': True,
            'supportsAllDrives': True, 
            'pageSize': 50,
            'orderBy': 'name'
        }
        return self._execute_paginated_list(request_params) or []

    def list_all_items_in_folder(self, folder_id, drive_id=None):
        if not self.is_ready(): return None
        query = f"'{folder_id}' in parents and trashed = false"
        request_params = {
            'q': query, 'spaces': 'drive', 'fields': 'files(id, name, mimeType)',
            'supportsAllDrives': True, 'includeItemsFromAllDrives': True, 
            'pageSize': 100, 
            'orderBy': 'folder, name'
        }
        if drive_id:
            request_params['driveId'] = drive_id
            request_params['corpora'] = 'drive'
        return self._execute_paginated_list(request_params)

    def list_all_folders_recursively(self, root_folder_id, drive_id=None):
        if not self.is_ready(): return []
        
        all_student_folders = []
        folders_to_scan = [root_folder_id]
        scanned_ids = {root_folder_id}

        while folders_to_scan:
            current_folder_id = folders_to_scan.pop(0)
            items = self.list_all_items_in_folder(current_folder_id, drive_id)

            if items is None:
                continue

            for item in items:
                if item.get('mimeType') == 'application/vnd.google-apps.folder':
                    folder_id = item.get('id')
                    all_student_folders.append(item)
                    
                    if folder_id not in scanned_ids:
                        folders_to_scan.append(folder_id)
                        scanned_ids.add(folder_id)
        
        logging.info(f"Varredura recursiva completa. Total de {len(all_student_folders)} pastas encontradas.")
        all_student_folders.sort(key=lambda f: f.get('name', '').upper())
        return all_student_folders

    def find_or_create_folder(self, folder_name, parent_id=None, drive_id=None):
        query = f"name = '{self._escape_query_value(folder_name)}' and '{parent_id}' in parents and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
        request_params = {'q': query, 'spaces': 'drive', 'fields': 'files(id)', 'supportsAllDrives': True, 'includeItemsFromAllDrives': True}
        if drive_id:
            request_params['driveId'] = drive_id
            request_params['corpora'] = 'drive'
        
        folders = self._execute_paginated_list(request_params)
        if folders:
            return folders[0]['id']
        else:
            return self.create_folder(folder_name, parent_id)

    def create_folder(self, folder_name, parent_id=None):
        if not self.is_ready(): return None
        file_metadata = {'name': folder_name, 'mimeType': 'application/vnd.google-apps.folder'}
        if parent_id: file_metadata['parents'] = [parent_id]
        try:
            return self.service.files().create(body=file_metadata, fields='id', supportsAllDrives=True).execute().get('id')
        except Exception:
            self._refresh_service()
            return None

    def upload_file(self, folder_id, filename, file_content_bytes, mime_type):
        if not self.is_ready(): return None
        file_metadata = {'name': filename, 'parents': [folder_id]}
        media = MediaIoBaseUpload(io.BytesIO(file_content_bytes), mimetype=mime_type, resumable=True)
        try:
            file = self.service.files().create(body=file_metadata, media_body=media, fields='id', supportsAllDrives=True).execute()
            return file.get('id')
        except Exception as e:
            logging.error(f"Erro ao fazer upload: {e}")
            self._refresh_service()
            return None