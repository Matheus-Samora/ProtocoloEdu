# -*- coding: utf-8 -*-
"""
Gerenciador Central de Conexão com o Supabase (Database & Storage).
Projeto: ProtocoloEdu / IMES
URL Base: https://phipudvmceitxcajggus.supabase.co
"""

import os
import logging
from typing import Optional, Dict, Any, List
import requests
from security.policy import validate_remote_url
from security.storage import production
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("SUPABASE_CLIENT")

# Configurações padrão do projeto Supabase informado
DEFAULT_SUPABASE_URL = "https://phipudvmceitxcajggus.supabase.co"
DEFAULT_STORAGE_BUCKET = "documentos-alunos"


class SupabaseClientManager:
    """
    Gerenciador singleton para a conexão com o Supabase.
    Suporta cliente oficial 'supabase-py' e chamadas REST diretas (PostgREST / Storage).
    """

    def __init__(self):
        self.url = os.getenv("SUPABASE_URL", DEFAULT_SUPABASE_URL).rstrip("/")
        self.key = os.getenv("SUPABASE_KEY") or os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_ANON_KEY") or ""
        self.bucket_name = os.getenv("SUPABASE_STORAGE_BUCKET", DEFAULT_STORAGE_BUCKET)
        self._client = None
        self._init_client()

    def _init_client(self):
        """Inicializa o cliente oficial da biblioteca supabase se a chave estiver configurada."""
        if production() and os.environ.get('ENABLE_EXTERNAL_STORAGE','').lower()!='true':self._client=None;return
        if self.key:validate_remote_url(self.url)
        if not self.key:
            logger.info("Chave do Supabase (SUPABASE_KEY) ainda não configurada no ambiente. Conexão em modo passivo.")
            self._client = None
            return

        try:
            from supabase import create_client, Client
            self._client: Client = create_client(self.url, self.key)
            logger.info(f"Cliente Supabase inicializado com sucesso para: {self.url}")
        except Exception as e:
            logger.error(f"Erro ao inicializar cliente Supabase: {e}")
            self._client = None

    def update_credentials(self, url: Optional[str] = None, key: Optional[str] = None, bucket: Optional[str] = None):
        """Atualiza dinamicamente as credenciais da conexão e reinicializa o cliente."""
        if url:
            self.url = validate_remote_url(url.rstrip("/"))
        if key:
            self.key = key.strip()
        if bucket:
            self.bucket_name = bucket.strip()
        self._init_client()

    @property
    def is_configured(self) -> bool:
        """Retorna True se as credenciais mínimas estiverem presentes."""
        return bool(self.url and self.key and (not production() or os.environ.get('ENABLE_EXTERNAL_STORAGE','').lower()=='true'))

    @property
    def client(self):
        """Retorna o cliente oficial do Supabase se inicializado."""
        return self._client

    def get_auth_headers(self) -> Dict[str, str]:
        """Retorna cabeçalhos HTTP necessários para chamadas REST ao Supabase."""
        return {
            "apikey": self.key,
            "Authorization": f"Bearer {self.key}",
            "Content-Type": "application/json"
        }

    def test_connection(self) -> Dict[str, Any]:
        """
        Executa diagnóstico completo da conexão com o projeto Supabase:
        1. Teste de status da API de Storage (/storage/v1/status)
        2. Teste de autenticação e introspecção no PostgREST (/rest/v1/)
        3. Listagem de buckets existentes
        """
        results = {
            "project_url": self.url,
            "has_api_key": bool(self.key),
            "storage_service": "UNKNOWN",
            "database_api": "UNKNOWN",
            "available_tables": [],
            "buckets": [],
            "status": "DISCONNECTED",
            "message": ""
        }

        # 1. Checa status público da API de Storage
        try:
            resp_storage = requests.get(f"{self.url}/storage/v1/status", timeout=5)
            if resp_storage.status_code == 200:
                results["storage_service"] = "ONLINE"
            else:
                results["storage_service"] = f"HTTP_{resp_storage.status_code}"
        except Exception as e:
            results["storage_service"] = f"OFFLINE ({type(e).__name__})"

        # Se não houver chave configurada, retorna diagnóstico claro
        if not self.key:
            results["database_api"] = "NEEDS_API_KEY"
            results["status"] = "AUTHENTICATION_REQUIRED"
            results["message"] = (
                "O endpoint do Supabase está acessível e online. Para habilitar leitura e gravação no banco "
                "de dados e armazenamento de arquivos, informe a Chave de API (anon ou service_role) do Dashboard Supabase."
            )
            return results

        headers = self.get_auth_headers()

        # 2. Testa PostgREST OpenAPI schema para descobrir tabelas disponíveis
        try:
            resp_rest = requests.get(f"{self.url}/rest/v1/", headers=headers, timeout=5)
            if resp_rest.status_code == 200:
                results["database_api"] = "AUTHENTICATED_AND_ONLINE"
                spec = resp_rest.json()
                definitions = spec.get("definitions", {})
                results["available_tables"] = list(definitions.keys())
            elif resp_rest.status_code == 401:
                results["database_api"] = "INVALID_API_KEY (401 Unauthorized)"
                results["status"] = "UNAUTHORIZED"
                results["message"] = "A chave de API informada foi recusada pelo Supabase. Verifique a chave em Project Settings > API."
                return results
            else:
                results["database_api"] = f"HTTP_{resp_rest.status_code}"
        except Exception as e:
            results["database_api"] = f"ERROR: {str(e)}"

        # 3. Testa listagem de buckets de arquivos
        try:
            resp_buckets = requests.get(f"{self.url}/storage/v1/bucket", headers=headers, timeout=5)
            if resp_buckets.status_code == 200:
                buckets_data = resp_buckets.json()
                results["buckets"] = [b.get("name") for b in buckets_data if isinstance(b, dict)]
            else:
                results["buckets"] = []
        except Exception as e:
            logger.warning(f"Erro ao listar buckets no Supabase: {e}")

        # Avaliação consolidada
        if results["database_api"] == "AUTHENTICATED_AND_ONLINE" and results["storage_service"] == "ONLINE":
            results["status"] = "CONNECTED"
            results["message"] = "Conexão com o Supabase estabelecida com sucesso! Banco e Storage operacionais."
        else:
            results["status"] = "PARTIAL_OR_DEGRADED"
            results["message"] = "Conexão parcial. Verifique se as tabelas e o bucket foram criados."

        return results

    def ensure_bucket_exists(self, bucket_name: Optional[str] = None) -> bool:
        """Garante que o bucket de armazenamento de arquivos dos alunos exista."""
        target_bucket = bucket_name or self.bucket_name
        if not self.is_configured:
            return False

        headers = self.get_auth_headers()
        try:
            # Verifica se já existe
            resp_check = requests.get(f"{self.url}/storage/v1/bucket/{target_bucket}", headers=headers, timeout=5)
            if resp_check.status_code == 200:
                return True

            # Cria se não existir
            payload = {
                "id": target_bucket,
                "name": target_bucket,
                "public": False,
                "file_size_limit": 52428800,  # 50MB
                "allowed_mime_types": [
                    "application/pdf",
                    "image/jpeg",
                    "image/png",
                    "image/heic",
                    "image/webp"
                ]
            }
            resp_create = requests.post(f"{self.url}/storage/v1/bucket", headers=headers, json=payload, timeout=5)
            return resp_create.status_code in (200, 201)
        except Exception as e:
            logger.error(f"Erro ao verificar/criar bucket '{target_bucket}' no Supabase: {e}")
            return False


# Instância global singleton do Gerenciador Supabase
supabase_manager = SupabaseClientManager()
