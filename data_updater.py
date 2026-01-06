import requests
import json
import os
import shutil
import time
from dotenv import load_dotenv

# --- Configuração ---
# Cole aqui o código do "Relatório 3: Busca Precisa por CPF".
CODIGO_RELATORIO_BUSCA_POR_CPF = '5320251010130226'

# Pastas para organizar o fluxo de trabalho
PASTA_ENTRADA = "dados_para_atualizar"
PASTA_PROCESSADOS = "dados_processados"
PASTA_ERROS = "dados_com_erro"


class SolisAPIClient:
    """
    Cliente da API para buscar e atualizar dados de alunos no SolisGE.
    """
    def __init__(self, base_url, jwt_token):
        if not base_url or not jwt_token:
            raise ValueError("A URL base e o token JWT não podem ser nulos.")
        
        self.base_url = base_url.rstrip('/')
        self.headers = {'Content-Type': 'application/json', 'Accept': 'application/json', 'X-Token': jwt_token}
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        requests.urllib3.disable_warnings(requests.urllib3.exceptions.InsecureRequestWarning)

    def encontrar_aluno_por_cpf(self, cpf):
        """Usa o relatório genérico para encontrar um aluno pelo CPF."""
        endpoint = f"/basico/relatorio-generico/gerar/{CODIGO_RELATORIO_BUSCA_POR_CPF}"
        url = f"{self.base_url.replace('/api', '')}{endpoint}" # Ajuste para URL base correta
        payload = {"par": {"CPF": cpf}}
        
        try:
            response = self.session.get(url, json=payload, verify=False, timeout=30)
            response.raise_for_status()
            resultado = response.json()
            return resultado[0] if resultado and len(resultado) > 0 else None
        except Exception:
            return None

    def atualizar_dados_pessoa(self, person_id, novos_dados):
        """Atualiza os dados de uma pessoa usando o endpoint /basico/pessoa."""
        print(f"🔄  A atualizar dados para o personid: {person_id}...")
        endpoint = "/basico/pessoa"
        url = f"{self.base_url.replace('/api', '')}{endpoint}"
        payload = {"pessoa": {"identificador": str(person_id), **novos_dados}}
        
        try:
            response = self.session.post(url, json=payload, verify=False, timeout=30)
            response.raise_for_status()
            if response.json().get('sucesso'):
                print("✅ DADOS ATUALIZADOS COM SUCESSO!")
                return True
            return False
        except Exception:
            return False

def processar_ficheiro_para_atualizacao(cliente_solis, nome_ficheiro):
    caminho_completo = os.path.join(PASTA_ENTRADA, nome_ficheiro)
    print(f"\n--- A processar para atualização: {nome_ficheiro} ---")
    
    try:
        with open(caminho_completo, 'r', encoding='utf-8') as f:
            dados = json.load(f)

        cnh_data = dados.get("results", {}).get("CNH", {})
        nome_doc = cnh_data.get("extracted_data", {}).get("nome_completo")
        cpf_doc = cnh_data.get("extracted_data", {}).get("numero_cpf")

        if not nome_doc or not cpf_doc:
            print("❌ ERRO: Nome ou CPF não encontrados no JSON.")
            return PASTA_ERROS

        aluno_solis = cliente_solis.encontrar_aluno_por_cpf(cpf_doc)
        
        if not aluno_solis:
            print(f"❌ ERRO: Aluno com CPF {cpf_doc} não encontrado no sistema.")
            return PASTA_ERROS

        person_id_solis = aluno_solis.get("ID")
        nome_solis = aluno_solis.get("Nome Completo")
        print(f"👤  Aluno encontrado: {nome_solis} (ID: {person_id_solis})")
        
        if nome_doc.upper() != nome_solis.upper():
            print(f"   -> O nome será atualizado de '{nome_solis}' para '{nome_doc}'.")
            dados_para_atualizar = {"nome": nome_doc}
            if cliente_solis.atualizar_dados_pessoa(person_id_solis, dados_para_atualizar):
                return PASTA_PROCESSADOS
            else:
                return PASTA_ERROS
        else:
            print("ℹ️  O nome no sistema já está correto. Nenhuma atualização necessária.")
            return PASTA_PROCESSADOS

    except Exception as e:
        print(f"❌ ERRO INESPERADO: {e}")
        return PASTA_ERROS

def main():
    """Função principal que executa o ciclo de atualização."""
    print("--- 🚀 Atualizador de Dados SolisGE ---")
    load_dotenv()
    
    for pasta in [PASTA_ENTRADA, PASTA_PROCESSADOS, PASTA_ERROS]:
        if not os.path.exists(pasta):
            os.makedirs(pasta)
    
    api_url = os.getenv("SOLIS_API_URL")
    jwt_token = os.getenv("SOLIS_JWT_TOKEN")
    
    if not (api_url and jwt_token and CODIGO_RELATORIO_BUSCA_POR_CPF != 'COLOQUE_O_CODIGO_DO_RELATORIO_DE_CPF_AQUI'):
        print("\n❌ ERRO CRÍTICO: Verifique as variáveis em '.env' e o código do relatório no topo do script.")
        return
        
    cliente_solis = SolisAPIClient(api_url, jwt_token)

    # Este loop pode ser agendado para rodar a cada 24h por um serviço externo (cron job)
    print(f"[{time.ctime()}] A procurar por ficheiros em '{PASTA_ENTRADA}'...")
    ficheiros = [f for f in os.listdir(PASTA_ENTRADA) if f.endswith('.json')]
    
    if not ficheiros:
        print("Nenhum ficheiro para processar.")
    else:
        for nome_ficheiro in ficheiros:
            pasta_destino = processar_ficheiro_para_atualizacao(cliente_solis, nome_ficheiro)
            shutil.move(os.path.join(PASTA_ENTRADA, nome_ficheiro), os.path.join(pasta_destino, nome_ficheiro))
            print(f"➡️  Ficheiro '{nome_ficheiro}' movido para '{pasta_destino}'.")

if __name__ == "__main__":
    main()
