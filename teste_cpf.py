import os
import json
import requests
from dotenv import load_dotenv
from pathlib import Path
import sys

# --- CÓDIGO DO CLIENTE DA API SOLIS ---

class SolisAPIClient:
    """
    Cliente de API para interagir com os endpoints do SolisGE.
    """
    def __init__(self, base_url, jwt_token):
        if not base_url or not jwt_token:
            raise ValueError("A URL base e o token JWT não podem ser nulos.")
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        self.headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'X-Token': jwt_token
        }
        self.session.headers.update(self.headers)
        requests.urllib3.disable_warnings(requests.urllib3.exceptions.InsecureRequestWarning)

    def executar_relatorio(self, codigo_relatorio, parametros):
        endpoint = f"/api/basico/relatorio-generico/gerar/{codigo_relatorio}"
        url = f"{self.base_url}{endpoint}"
        payload = {"par": parametros}
        print(f"  -> Enviando requisição para o relatório ID '{codigo_relatorio}'...")
        return self._fazer_requisicao(url, data=json.dumps(payload))

    def _fazer_requisicao(self, url, data=None, params=None):
        try:
            if data:
                response = self.session.get(url, data=data, verify=False, timeout=30)
            else:
                response = self.session.get(url, params=params, verify=False, timeout=30)
            print(f"  <- Resposta recebida: Status {response.status_code}")
            response.raise_for_status()
            if not response.text.strip():
                print("  ⚠️ Aviso: A API retornou uma resposta vazia.")
                return None
            return response.json()
        except json.JSONDecodeError:
            print(f"  ❌ ERRO: A resposta não é um JSON válido. Resposta: {response.text}")
            return None
        except requests.exceptions.HTTPError as http_err:
            print(f"  ❌ ERRO HTTP: {http_err}")
            return None
        except requests.exceptions.RequestException as e:
            print(f"  ❌ ERRO de Conexão: {e}")
            return None

# --- LÓGICA DE BUSCA COM LOGS DETALHADOS ---

def buscar_aluno_por_cpf(cliente_solis, cpf):
    print("\n=============================================")
    print(f"Iniciando busca completa para o CPF: {cpf}")
    
    # IDs dos Relatórios
    ID_RELATORIO_NOME = "6620251203154311"
    PARAM_NOME = "NOME_ALUNO"
    ID_RELATORIO_ID = "7020251204095501"
    PARAM_ID = "cod"
    ID_RELATORIO_CPF = "6820251203155305"
    PARAM_CPF = "cpf"
    
    cpf_limpo = cpf.replace('.', '').replace('-', '')
    aluno_encontrado = None

    print("\n--- Etapa 1: Buscando Nome com o CPF ---")
    resultado_cpf = cliente_solis.executar_relatorio(ID_RELATORIO_CPF, {PARAM_CPF: cpf_limpo})
    
    if not (resultado_cpf and isinstance(resultado_cpf, list) and len(resultado_cpf) > 0):
        print("--- ❌ FALHA na Etapa 1: Nenhum aluno encontrado com este CPF.")
        return None

    nome_encontrado_cpf = resultado_cpf[0].get("nome")
    if not nome_encontrado_cpf:
        print("--- ❌ FALHA na Etapa 1: Relatório de CPF não retornou um nome.")
        return None
    print(f"--- ✅ SUCESSO na Etapa 1: Nome encontrado -> '{nome_encontrado_cpf}'")

    print("\n--- Etapa 2: Buscando IDs com o Nome encontrado ---")
    resultado_nome = cliente_solis.executar_relatorio(ID_RELATORIO_NOME, {PARAM_NOME: nome_encontrado_cpf.upper()})

    if not (resultado_nome and isinstance(resultado_nome, list)):
        print(f"--- ❌ FALHA na Etapa 2: Não foi possível encontrar IDs para o nome '{nome_encontrado_cpf}'.")
        return None
    print(f"--- ✅ SUCESSO na Etapa 2: {len(resultado_nome)} ID(s) candidato(s) encontrado(s).")

    print("\n--- Etapa 3: Validando cada ID para confirmar o CPF ---")
    for i, aluno_candidato in enumerate(resultado_nome):
        id_final = aluno_candidato.get("ID")
        print(f"  - Verificando candidato {i+1}/{len(resultado_nome)} com ID: {id_final}")
        if not id_final:
            print("    - Candidato sem ID, pulando.")
            continue

        res_final = cliente_solis.executar_relatorio(ID_RELATORIO_ID, {PARAM_ID: id_final})
        if res_final and isinstance(res_final, list) and res_final[0]:
            detalhes = res_final[0]
            cpf_final = detalhes.get("cpf", "").replace('.', '').replace('-', '')
            print(f"    - ID {id_final} corresponde ao CPF: {cpf_final}")
            if cpf_final == cpf_limpo:
                print(f"--- ✅ SUCESSO na Etapa 3: CPF confirmado para o ID {id_final}!")
                aluno_encontrado = {
                    "id": detalhes.get("codigo"),
                    "name": detalhes.get("nome"),
                    "cpf": detalhes.get("cpf")
                }
                break 
    
    if not aluno_encontrado:
        print("--- ❌ FALHA na Etapa 3: Nenhum dos IDs candidatos correspondeu ao CPF original.")
    
    print("=============================================\n")
    return aluno_encontrado

# --- FUNÇÃO PRINCIPAL DE EXECUÇÃO ---

def main():
    """
    Orquestra a execução do script de teste a partir da linha de comando.
    """
    load_dotenv()
    api_url = os.getenv("SOLIS_API_URL")
    jwt_token = os.getenv("SOLIS_JWT_TOKEN")

    if not all([api_url, jwt_token]):
        print("❌ ERRO: Verifique seu arquivo '.env'. As variáveis SOLIS_API_URL e SOLIS_JWT_TOKEN são obrigatórias.")
        sys.exit(1) # Encerra o script se as chaves não estiverem configuradas

    try:
        cliente_solis = SolisAPIClient(api_url, jwt_token)
    except ValueError as e:
        print(f"❌ ERRO ao inicializar API: {e}")
        sys.exit(1)

    while True:
        try:
            cpf_input = input("Digite o CPF do aluno para buscar (ou 'sair' para finalizar): ")
            if cpf_input.lower() == 'sair':
                break
            
            resultado = buscar_aluno_por_cpf(cliente_solis, cpf_input)
            
            print("\n--- RESULTADO FINAL DA BUSCA ---")
            if resultado:
                print(json.dumps(resultado, indent=2, ensure_ascii=False))
            else:
                print("Nenhum aluno encontrado com os critérios fornecidos.")
            print("--------------------------------\n")

        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"\nOcorreu um erro inesperado: {e}\n")
    
    print("\nScript finalizado.")


if __name__ == "__main__":
    main()
