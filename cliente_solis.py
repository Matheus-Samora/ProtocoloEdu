import requests
import json

class SolisAPIClient:
    """
    Um cliente de API para interagir com os endpoints do SolisGE
    que requerem autenticação via X-Token (JWT).
    """
    def __init__(self, base_url, jwt_token):
        """
        Inicializa o cliente com a URL base e o token de autenticação JWT.
        """
        if not base_url or not jwt_token:
            raise ValueError("A URL base e o token JWT não podem ser nulos.")
            
        self.base_url = base_url.rstrip('/')
        self.headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'X-Token': jwt_token,
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        # Desativa avisos de SSL não verificado globalmente para a sessão
        requests.urllib3.disable_warnings(requests.urllib3.exceptions.InsecureRequestWarning)

    def cadastrar_pessoa(self, payload):
        """
        Envia os dados de uma pessoa (aluno) para o endpoint de cadastro.
        Retorna a resposta JSON em caso de sucesso, ou None em caso de falha.
        """
        endpoint = "/api/basico/pessoa"
        url = f"{self.base_url}{endpoint}"
        
        try:
            response = self.session.post(
                url, 
                json=payload, 
                verify=False, # Essencial para ambientes de teste
                timeout=20
            )
            response.raise_for_status() # Lança um erro para status HTTP 4xx/5xx
            return response.json()

        except requests.exceptions.HTTPError as err:
            print(f"--- ❌ Erro HTTP ao enviar dados ---")
            print(f"Status: {err.response.status_code} {err.response.reason}")
            if err.response.status_code == 401:
                print("!! Causa Provável: O seu SOLIS_JWT_TOKEN está inválido ou expirou. !!")
            else:
                try:
                    print(f"Resposta da API: {err.response.text}")
                except Exception:
                    print("Não foi possível ler a resposta da API.")
            return None
        except requests.exceptions.RequestException as e:
            print(f"--- ❌ Erro de Conexão com a API ---")
            print(f"Ocorreu um erro ao tentar conectar-se à API: {e}")
            return None
        except json.JSONDecodeError:
            print(f"--- ❌ Erro de Resposta da API ---")
            print("A API não respondeu com um JSON válido.")
            return None

    def atualizar_pessoa(self, payload):
        """
        Envia os dados de uma pessoa (aluno) para o endpoint de alteração,
        utilizando o método POST, conforme especificado pela API.
        Retorna a resposta JSON em caso de sucesso, ou None em caso de falha.
        """
        # O endpoint é o mesmo para cadastro e alteração,
        # a API diferencia pela presença do 'identificador' no payload.
        endpoint = "/api/basico/pessoa"
        url = f"{self.base_url}{endpoint}"
        
        try:
            # Utiliza o método POST para a atualização, conforme API
            response = self.session.post(
                url, 
                json=payload, 
                verify=False, 
                timeout=20
            )
            response.raise_for_status() 
            return response.json()

        except requests.exceptions.HTTPError as err:
            print(f"--- ❌ Erro HTTP ao ALTERAR dados ---")
            print(f"Status: {err.response.status_code} {err.response.reason}")
            if err.response.status_code == 401:
                print("!! Causa Provável: O seu SOLIS_JWT_TOKEN está inválido ou expirou. !!")
            else:
                try:
                    print(f"Resposta da API: {err.response.text}")
                except Exception:
                    print("Não foi possível ler a resposta da API.")
            return None
        except requests.exceptions.RequestException as e:
            print(f"--- ❌ Erro de Conexão com a API ao ALTERAR ---")
            print(f"Ocorreu um erro ao tentar conectar-se à API: {e}")
            return None
        except json.JSONDecodeError:
            print(f"--- ❌ Erro de Resposta da API ao ALTERAR ---")
            print("A API não respondeu com um JSON válido.")
            return None

    def executar_relatorio_com_parametro(self, codigo_relatorio, nome_param, valor_param):
        """
        Executa um relatório genérico passando um ID, o nome de um parâmetro e o seu valor.
        """
        endpoint = f"/api/basico/relatorio-generico/gerar/{codigo_relatorio}"
        url = f"{self.base_url}{endpoint}"
        
        payload = {
            "par": {
                nome_param: valor_param
            }
        }
        
        print(f"\n🔎 Executando relatório ID '{codigo_relatorio}' com payload: {json.dumps(payload)}")

        try:
            # Nota: Relatórios genéricos no Solis podem usar GET com corpo, o que não é padrão.
            # A biblioteca 'requests' lida com isso.
            response = self.session.get(url, data=json.dumps(payload), verify=False, timeout=30)
            response.raise_for_status()
            
            print(f"Status da Resposta: {response.status_code} {response.reason}")
            
            try:
                resultado_json = response.json()
                print("✅ Sucesso! Resposta JSON recebida.")
                return resultado_json
            except json.JSONDecodeError:
                print("❌ A resposta do servidor não é um JSON válido.")
                print("Resposta Bruta:", response.text)
                return None

        except requests.exceptions.HTTPError as err:
            print(f"--- ❌ Erro HTTP ao executar relatório ---")
            print(f"Status: {err.response.status_code} {err.response.reason}")
            print(f"Resposta: {err.response.text}")
            return None
        except requests.exceptions.RequestException as e:
            print(f"--- ❌ Erro de Conexão ---")
            print(f"Ocorreu um erro: {e}")
            return None

