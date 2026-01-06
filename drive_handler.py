# -*- coding: utf-8 -*-
# ARQUIVO: drive_handler.py
# DESCRIÇÃO: Versão final consolidada que une todas as funcionalidades e correções,
#           incluindo a solução para o filtro de data da API.

import logging
import json
import os
import re
import time
import io
import random
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseUpload

CREDENTIALS_FILE = 'credentials.json'

class DriveHandler:
    def __init__(self):
        self.service = None
        try:
            if os.path.exists(CREDENTIALS_FILE):
                creds = service_account.Credentials.from_service_account_file(
                    CREDENTIALS_FILE, scopes=['https://www.googleapis.com/auth/drive']
                )
                self.service = build('drive', 'v3', credentials=creds)
                logging.info("Serviço do Google Drive construído com sucesso.")
        except Exception as e:
            logging.critical(f"FALHA CRÍTICA ao construir o serviço: {e}", exc_info=True)

    def is_ready(self):
        return self.service is not None

    def _escape_query_value(self, value):
        """Escapa apóstrofos em valores de query para evitar erros de sintaxe."""
        return value.replace("'", "\\'")

    def _execute_paginated_list(self, request_params):
        """Motor de busca paginada, com tratamento de erros e novas tentativas."""
        all_items = []
        page_token = None
        max_retries = 5
        while True:
            if page_token:
                request_params['pageToken'] = page_token
            
            for attempt in range(max_retries):
                try:
                    response = self.service.files().list(**request_params).execute()
                    all_items.extend(response.get('files', []))
                    page_token = response.get('nextPageToken', None)
                    break 
                except HttpError as error:
                    logging.warning(f"Erro HTTP {error.resp.status}, tentativa {attempt + 1}/{max_retries}.")
                    if attempt + 1 == max_retries: return None
                    time.sleep((2 ** attempt) + random.uniform(0, 1))
            
            if not page_token:
                break
        return all_items

    def get_folder_details(self, folder_id):
        """Obtém os detalhes (como o nome) de uma pasta específica pelo seu ID."""
        if not self.is_ready(): return None
        try:
            return self.service.files().get(fileId=folder_id, fields="id, name", supportsAllDrives=True).execute()
        except HttpError as error:
            logging.error(f"Erro ao obter detalhes da pasta ID '{folder_id}': {error}")
            return None

    def find_folder_by_exact_name(self, folder_name, drive_id):
        """Busca uma pasta pelo seu nome exato em todo o Drive especificado."""
        if not self.is_ready(): return None
        escaped_name = self._escape_query_value(folder_name)
        query = f"name = '{escaped_name}' and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
        request_params = {
            'q': query, 'spaces': 'drive', 'fields': 'files(id, name)', 'corpora': 'drive',
            'driveId': drive_id, 'includeItemsFromAllDrives': True,
            'supportsAllDrives': True, 'pageSize': 10
        }
        try:
            folders = self._execute_paginated_list(request_params)
            if folders:
                if len(folders) > 1: logging.warning(f"Múltiplas pastas encontradas com o nome exato '{folder_name}'. A usar a primeira.")
                return folders[0]
            return None
        except HttpError as error:
            logging.error(f"Erro HTTP na busca por nome exato: {error}")
            return None

    def find_folders_containing_name(self, name_part, drive_id):
        """Busca por TODAS as pastas em um Drive cujo nome CONTENHA o texto fornecido."""
        if not self.is_ready(): return []
        escaped_name = self._escape_query_value(name_part)
        query = f"name contains '{escaped_name}' and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
        request_params = {
            'q': query, 'spaces': 'drive', 'fields': 'files(id, name)',
            'corpora': 'drive', 'driveId': drive_id, 'includeItemsFromAllDrives': True,
            'supportsAllDrives': True, 'pageSize': 1000,
            'orderBy': 'name'  # Força a ordenação e evita filtros de data
        }
        return self._execute_paginated_list(request_params) or []

    def list_all_items_in_folder(self, folder_id, drive_id=None):
        """Lista todos os itens (ficheiros e pastas) dentro de uma pasta específica."""
        if not self.is_ready(): return None
        query = f"'{folder_id}' in parents and trashed = false"
        request_params = {
            'q': query, 'spaces': 'drive', 'fields': 'files(id, name, mimeType)',
            'supportsAllDrives': True, 'includeItemsFromAllDrives': True, 'pageSize': 1000,
            'orderBy': 'folder, name' # Força a ordenação e evita filtros de data
        }
        if drive_id:
            request_params['driveId'] = drive_id
            request_params['corpora'] = 'drive'
        return self._execute_paginated_list(request_params)

    def list_all_folders_recursively(self, root_folder_id, drive_id=None):
        """Varre recursivamente e retorna TODAS as subpastas, imune a filtros de data."""
        if not self.is_ready(): return []
        
        all_student_folders = []
        folders_to_scan = [root_folder_id]
        scanned_ids = {root_folder_id}

        while folders_to_scan:
            current_folder_id = folders_to_scan.pop(0)
            logging.info(f"A varrer conteúdo da pasta ID: {current_folder_id}")
            
            items = self.list_all_items_in_folder(current_folder_id, drive_id)

            if items is None:
                logging.error(f"Não foi possível listar o conteúdo da pasta {current_folder_id}. A continuar...")
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
        """Encontra uma pasta; se não encontrar, cria."""
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
        """Cria uma nova pasta."""
        if not self.is_ready(): return None
        file_metadata = {'name': folder_name, 'mimeType': 'application/vnd.google-apps.folder'}
        if parent_id: file_metadata['parents'] = [parent_id]
        try:
            return self.service.files().create(body=file_metadata, fields='id', supportsAllDrives=True).execute().get('id')
        except HttpError as error:
            logging.error(f"Erro ao criar a pasta '{folder_name}': {error}")
            return None

    def upload_file(self, folder_id, filename, file_content_bytes, mime_type):
        """Faz o upload de um ficheiro para uma pasta específica."""
        if not self.is_ready(): return None
        file_metadata = {'name': filename, 'parents': [folder_id]}
        media = MediaIoBaseUpload(io.BytesIO(file_content_bytes), mimetype=mime_type, resumable=True)
        try:
            file = self.service.files().create(body=file_metadata, media_body=media, fields='id', supportsAllDrives=True).execute()
            return file.get('id')
        except HttpError as error:
            logging.error(f"Erro ao fazer upload do ficheiro '{filename}': {error}")
            return None
