import os.path
import httplib2
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google_auth_httplib2 import AuthorizedHttp

# --- CONFIGURAÇÕES ---
SERVICE_ACCOUNT_FILE = 'credentials.json'
SCOPES = ['https://www.googleapis.com/auth/drive.readonly'] # Apenas permissão de leitura
DRIVE_ID = "0ALL0qV6e99bpUk9PVA" 

def get_drive_service():
    """Autentica e constrói o objeto de serviço do Drive."""
    try:
        creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
        http_client = httplib2.Http(timeout=60)
        authed_http = AuthorizedHttp(creds, http=http_client)
        print("Serviço do Google Drive autenticado com sucesso em modo de leitura.\n")
        return build('drive', 'v3', http=authed_http)
    except Exception as e:
        print(f"Ocorreu um erro na autenticação: {e}")
        return None

def find_trashed_folders(service, drive_id):
    """Busca e retorna TODAS as pastas que estão na lixeira de um Drive Compartilhado."""
    all_folders = []
    page_token = None
    print("Iniciando busca na lixeira do Drive Compartilhado...")
    while True:
        try:
            request_params = {
                # A mudança crucial: 'trashed=true' para buscar na lixeira
                'q': "mimeType='application/vnd.google-apps.folder' and trashed=true",
                'fields': 'nextPageToken, files(id, name)',
                'corpora': 'drive',
                'driveId': drive_id,
                'includeItemsFromAllDrives': True,
                'supportsAllDrives': True,
                'pageSize': 100
            }
            if page_token:
                request_params['pageToken'] = page_token

            results = service.files().list(**request_params).execute()
            all_folders.extend(results.get('files', []))
            
            page_token = results.get('nextPageToken', None)
            if page_token is None:
                break
        except HttpError as error:
            print(f"Ocorreu um erro durante a busca na lixeira: {error}")
            return []
    return all_folders

def main():
    """Função principal que localiza pastas na lixeira do Drive."""
    service = get_drive_service()
    if not service:
        return
    
    trashed_folders = find_trashed_folders(service, DRIVE_ID)
    
    print("\n--- RELATÓRIO DA LIXEIRA ---")

    if trashed_folders:
        print("\n[!!!] PASTAS ENCONTRADAS NA LIXEIRA (PODEM SER RESTAURADAS):")
        trashed_folders.sort(key=lambda x: x['name'])
        for folder in trashed_folders:
            print(f"- {folder['name']} (ID: {folder['id']})")
    else:
        print("\nNenhuma pasta foi encontrada na lixeira do Drive Compartilhado.")
    
    print("\n--- FIM DO RELATÓRIO ---")
    print("\nSe as pastas estiverem aqui, podemos criar um script para restaurá-las.")


if __name__ == '__main__':
    main()
