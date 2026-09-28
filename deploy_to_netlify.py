# -*- coding: utf-8 -*-
"""
Script de Deploy Automatizado para o Netlify via API Oficial.
Cria o site com o nome desejado ('ProtocoloEdu') e faz upload do pacote zip estático.
"""

import sys
import os
import requests

NETLIFY_API_URL = "https://api.netlify.com/api/v1"

def deploy(token: str, site_name: str = "protocoloedu", zip_path: str = "protocoloedu-frontend.zip"):
    if not os.path.exists(zip_path):
        print(f"[ERRO] Arquivo zip '{zip_path}' não encontrado. Gere o pacote primeiro.")
        return False

    headers = {
        "Authorization": f"Bearer {token.strip()}"
    }

    print(f"[*] Verificando ou criando site '{site_name}' no Netlify...")
    
    # 1. Tenta listar sites existentes para ver se já existe um site com esse nome na conta
    r = requests.get(f"{NETLIFY_API_URL}/sites", headers=headers)
    if r.status_code != 200:
        print(f"[ERRO] Falha ao autenticar no Netlify ({r.status_code}): {r.text}")
        return False

    sites = r.json()
    target_site = None
    for s in sites:
        if s.get("name", "").lower() == site_name.lower():
            target_site = s
            break

    site_id = None
    if target_site:
        site_id = target_site["id"]
        print(f"[+] Site '{site_name}' já existe na sua conta (ID: {site_id}). Atualizando deploy...")
    else:
        # Cria novo site
        create_resp = requests.post(
            f"{NETLIFY_API_URL}/sites",
            headers={**headers, "Content-Type": "application/json"},
            json={"name": site_name}
        )
        if create_resp.status_code in (200, 201):
            created_data = create_resp.json()
            site_id = created_data["id"]
            print(f"[+] Site '{site_name}' criado com sucesso (ID: {site_id})!")
        else:
            print(f"[-] Aviso ao criar site com nome '{site_name}' ({create_resp.status_code}): {create_resp.text}")
            print("[*] Criando site com nome automático e vinculando deploy...")
            create_resp = requests.post(f"{NETLIFY_API_URL}/sites", headers=headers)
            if create_resp.status_code in (200, 201):
                created_data = create_resp.json()
                site_id = created_data["id"]
            else:
                print(f"[ERRO] Falha ao criar site: {create_resp.text}")
                return False

    # 2. Faz upload do arquivo ZIP
    print(f"[*] Fazendo upload do pacote '{zip_path}' ({os.path.getsize(zip_path)} bytes)...")
    with open(zip_path, "rb") as f:
        zip_bytes = f.read()

    deploy_headers = {
        "Authorization": f"Bearer {token.strip()}",
        "Content-Type": "application/zip"
    }

    deploy_resp = requests.post(
        f"{NETLIFY_API_URL}/sites/{site_id}/deploys",
        headers=deploy_headers,
        data=zip_bytes
    )

    if deploy_resp.status_code in (200, 201):
        deploy_data = deploy_resp.json()
        ssl_url = deploy_data.get("ssl_url") or deploy_data.get("url")
        print("\n" + "=" * 60)
        print(f"[SUCESSO] Site publicado no ar com sucesso!")
        print(f"URL Oficial: {ssl_url}")
        print("=" * 60)
        return ssl_url
    else:
        print(f"[ERRO] Falha no deploy: {deploy_resp.status_code} - {deploy_resp.text}")
        return False

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python deploy_to_netlify.py <SEU_NETLIFY_TOKEN>")
        sys.exit(1)
    deploy(sys.argv[1])
