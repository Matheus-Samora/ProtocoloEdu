import requests
import json
import os
import time
from dotenv import load_dotenv

# --- Configuração ---
FICHEIRO_ENTRADA = "dados_pendentes.json"
FICHEIRO_ERROS = "dados_com_erro.json"

# --- CÓDIGOS DOS RELATÓRIOS ---
# Cole aqui o código do "Relatório 1: Busca de Aluno por Nome".
CODIGO_RELATORIO_BUSCA_POR_NOME = '6620251203154311'

# Cole aqui o código do "Relatório 2: Busca de CPF por ID de Aluno".
CODIGO_RELATORIO_BUSCA_POR_CPF_ID = '6920251204094952'


class SolisAPIClient:
    """ Cliente da API SolisGE para executar relatórios e atualizar dados. """
    def __init__(self, base_url, jwt_token):
        if not base_url or not jwt_token:
            raise ValueError("A URL base e o token JWT não podem ser nulos.")
        
        self.base_url = base_url.rstrip('/')
        self.headers = {'Content-Type': 'application/json', 'Accept': 'application/json', 'X-Token': jwt_token}
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        requests.urllib3.disable_warnings(requests.urllib3.exceptions.InsecureRequestWarning)

    def executar_relatorio(self, report_id, param_name, param_value):
        """ Função genérica para executar um relatório com um único parâmetro. """
        print(f"🔎 A executar relatório '{report_id}' com {param_name} = {param_value}")
        endpoint = f"/api/basico/relatorio-generico/gerar/{report_id}"
        url = f"{self.base_url}{endpoint}"
        payload = {"par": {param_name: param_value}}
        
        try:
            response = self.session.get(url, json=payload, verify=False, timeout=30)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"❌ Erro na API ao executar relatório '{report_id}': {e}")
            return None

    def atualizar_dados_pessoa(self, person_id: str, novos_dados: dict) -> bool:
        """ Envia uma requisição POST para atualizar os dados da pessoa. """
        print(f"🔄 A atualizar dados para o personid: {person_id}...")
        endpoint = "/api/basico/pessoa"
        url = f"{self.base_url}{endpoint}"
        payload = {"pessoa": {"identificador": str(person_id), **novos_dados}}
        
        try:
            response = self.session.post(url, json=payload, verify=False, timeout=30)
            response.raise_for_status()
            if response.json().get('sucesso'):
                print("✅ DADOS ATUALIZADOS COM SUCESSO!")
                return True
            else:
                print(f"❌ Falha na atualização: {response.text}")
                return False
        except Exception as e:
            print(f"❌ Erro na API ao atualizar dados: {e}")
            return False

def registrar_erro(cpf, dados_aluno, motivo):
    """Adiciona um registo de erro ao ficheiro de erros."""
    if os.path.exists(FICHEIRO_ERROS):
        with open(FICHEIRO_ERROS, 'r', encoding='utf-8') as f:
            try:
                erros = json.load(f)
            except json.JSONDecodeError:
                erros = {}
    else:
        erros = {}
    
    erros[cpf] = {
        "motivo": motivo,
        "dados": dados_aluno,
        "timestamp": time.ctime()
    }

    with open(FICHEIRO_ERROS, 'w', encoding='utf-8') as f:
        json.dump(erros, f, indent=4, ensure_ascii=False)
    print(f"🔴 Erro registado para o CPF {cpf} em '{FICHEIRO_ERROS}'.")


def main():
    """ Função principal que lê os dados pendentes e os processa em cadeia. """
    print("--- 🚀 Atualizador com Pesquisa em Cadeia ---")
    load_dotenv(dotenv_path=os.environ["PROTOCOL_ENV_FILE"]) if os.environ.get("PROTOCOL_ENV_FILE") else None
    
    api_url = os.getenv("SOLIS_API_URL")
    jwt_token = os.getenv("SOLIS_JWT_TOKEN")
    
    if not (api_url and jwt_token and 
            CODIGO_RELATORIO_BUSCA_POR_NOME and
            CODIGO_RELATORIO_BUSCA_POR_CPF_ID):
        print("\n❌ ERRO CRÍTICO: Verifique '.env' e os códigos dos relatórios no topo do script.")
        return
        
    cliente_solis = SolisAPIClient(api_url, jwt_token)

    if not os.path.exists(FICHEIRO_ENTRADA) or os.path.getsize(FICHEIRO_ENTRADA) == 0:
        print(f"[{time.ctime()}] Nenhum dado pendente encontrado em '{FICHEIRO_ENTRADA}'.")
        return

    with open(FICHEIRO_ENTRADA, 'r', encoding='utf-8') as f:
        dados_pendentes = json.load(f)
    
    ids_processados_sucesso = []

    for solicitacao in dados_pendentes:
        dados_extraidos = solicitacao.get("dados_extraidos", {})
        cpf_doc = dados_extraidos.get("numero_cpf")
        nome_doc = dados_extraidos.get("nome_completo")
        id_solicitacao = solicitacao.get("id_solicitacao")

        print(f"\n--- A processar solicitação: {id_solicitacao} para {nome_doc} ---")

        if not (cpf_doc and nome_doc):
            registrar_erro(id_solicitacao or "sem_id", solicitacao, "Dados insuficientes (CPF ou Nome em falta).")
            continue

        # --- 1ª ETAPA DA CADEIA: Buscar por nome ---
        # Assume que o parâmetro do Relatório 1 é 'p_nome_aluno'
        resultados_nome = cliente_solis.executar_relatorio(CODIGO_RELATORIO_BUSCA_POR_NOME, "p_nome_aluno", nome_doc)
        if not resultados_nome:
            registrar_erro(cpf_doc, solicitacao, f"Nenhum aluno encontrado no SolisGE com nome similar a '{nome_doc}'.")
            continue

        aluno_confirmado = None
        for aluno_potencial in resultados_nome:
            person_id = aluno_potencial.get("Código do Aluno")
            if not person_id: continue

            # --- 2ª ETAPA DA CADEIA: Buscar CPF pelo ID encontrado ---
            # Assume que o parâmetro do Relatório 2 é 'personid'
            resultado_cpf = cliente_solis.executar_relatorio(CODIGO_RELATORIO_BUSCA_POR_CPF_ID, "personid", person_id)
            
            if resultado_cpf and resultado_cpf[0].get("CPF"):
                cpf_solis = str(resultado_cpf[0].get("CPF")).replace('.', '').replace('-', '')
                cpf_doc_limpo = str(cpf_doc).replace('.', '').replace('-', '')

                # --- 3ª ETAPA DA CADEIA: Confirmação ---
                if cpf_solis == cpf_doc_limpo:
                    print(f"✅ CONFIRMADO: O CPF do documento ({cpf_doc}) corresponde ao do sistema para o aluno '{aluno_potencial.get('Nome Completo')}' (ID: {person_id}).")
                    aluno_confirmado = aluno_potencial
                    break # Para o loop assim que encontrar a correspondência exata
        
        if not aluno_confirmado:
            registrar_erro(cpf_doc, solicitacao, "Aluno(s) encontrado(s) por nome, mas o CPF do sistema não corresponde ao do documento.")
            continue
        
        # --- ETAPA FINAL: Atualização ---
        person_id_final = aluno_confirmado.get("Código do Aluno")
        # Prepara os dados que serão efetivamente atualizados no SolisGE
        dados_para_atualizar = {
            "name": nome_doc # Use 'name' se soubermos que é o nome correto da coluna
            # Adicione outros campos para atualizar aqui, se necessário
            # Ex: "cpf": cpf_doc,
        }
        
        if cliente_solis.atualizar_dados_pessoa(person_id_final, dados_para_atualizar):
            ids_processados_sucesso.append(id_solicitacao)
        else:
            registrar_erro(cpf_doc, solicitacao, "Falha ao chamar a API de atualização do SolisGE.")

    # Limpa o ficheiro de pendentes
    if ids_processados_sucesso:
        print(f"\n--- A limpar ficheiro de pendentes ---")
        novos_dados_pendentes = [s for s in dados_pendentes if s.get("id_solicitacao") not in ids_processados_sucesso]
        with open(FICHEIRO_ENTRADA, 'w', encoding='utf-8') as f:
            json.dump(novos_dados_pendentes, f, indent=4, ensure_ascii=False)
        print(f"{len(ids_processados_sucesso)} registo(s) processado(s) com sucesso e removido(s) da fila.")

    print("\n--- Processamento Concluído ---")

if __name__ == "__main__":
    main()

