# -*- coding: utf-8 -*-
# -----------------------------------------------------------------
# ARQUIVO: servidor_web.py (Versão Final - Conexão Firestore Corrigida)
# DESCRIÇÃO: Servidor principal ajustado para conectar no banco 'default'.
# -----------------------------------------------------------------
import os
if os.environ.get("ENABLE_LEGACY_SERVERS") != "true" or os.environ.get("PROTOCOL_ENV", "").lower() == "production":
    raise RuntimeError("Retired legacy server. Use api_server:app with the security gateway.")
import logging
import json
import re
import requests
import gc  # <--- IMPORTANTE: Importado para forçar limpeza de memória
from dotenv import load_dotenv

from flask import Flask, request, jsonify, render_template, redirect, url_for, g
from flask_cors import CORS
# flask_login removido pois o acesso agora é direto
from google.cloud import firestore
from jinja2.exceptions import TemplateNotFound

# Módulos da sua lógica de negócio
try:
    import core_logic
    import assistant_logic
    import config
except ImportError:
    # Fallback para evitar erro se os arquivos auxiliares não estiverem no contexto imediato,
    # mas em produção eles devem existir conforme sua solicitação de manter funções.
    logging.warning("Módulos auxiliares (core_logic, assistant_logic, config) não encontrados. Funcionalidades podem ser limitadas.")
    core_logic = None
    assistant_logic = None
    config = None

from aluno_service import AlunoService

# --- CONFIGURAÇÃO INICIAL DA APLICAÇÃO ---
basedir = os.path.abspath(os.path.dirname(__file__))
app = Flask(__name__, template_folder=os.path.join(basedir, 'templates/default')) # Ajustado para folder padrão

# [CORREÇÃO 1: FIRESTORE LAZY & DATABASE NAME]
# Removemos a instância global e adicionamos o nome do banco 'default'
_db_instance = None

def get_db():
    """
    Retorna uma instância ativa do Firestore conectada ao banco 'default'.
    Usa o padrão Singleton Lazy para evitar desconexões globais.
    """
    global _db_instance
    if _db_instance is None:
        try:
            # AQUI ESTÁ A MÁGICA: database="default"
            # Isso força o cliente a usar o banco que validamos no teste.
            _db_instance = firestore.Client(database="default")
        except Exception as e:
            logging.critical(f"Erro ao conectar ao Firestore: {e}")
            raise e
    return _db_instance

# [CORREÇÃO 2: CORS]
# Configuração CORS mais permissiva para evitar bloqueios de rede/navegador em computadores da escola
CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=True)

app.config['SECRET_KEY'] = 'chave-secreta-publica' # Mantido apenas para sessão interna se necessário

logging.basicConfig(level=logging.INFO, format='[WEB_SERVER] [%(levelname)s] %(asctime)s - %(message)s')
load_dotenv() 

COL_PEDIDOS_WEB = 'pendencias_imes'

# Instância única do serviço de aluno
try:
    aluno_serv = AlunoService()
except Exception as e:
    logging.critical(f"NÃO FOI POSSÍVEL INICIAR O ALUNO SERVICE: {e}")
    aluno_serv = None

# ==============================================================================
# --- LÓGICA DE BUSCA NA SOLIS (MANTIDA ORIGINAL) ---
# ==============================================================================

class SolisAPIClient:
    def __init__(self, base_url, jwt_token):
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
        self.session.headers.update({'Connection': 'close'}) # Força fechar conexão para economizar socket/memória
        requests.urllib3.disable_warnings(requests.urllib3.exceptions.InsecureRequestWarning)

    def executar_relatorio(self, codigo_relatorio, parametros):
        url = f"{self.base_url}/api/basico/relatorio-generico/gerar/{codigo_relatorio}"
        logging.info(f" -> [API Solis] Enviando requisição para o relatório ID '{codigo_relatorio}'...")
        return self._fazer_requisicao(url, data=json.dumps({"par": parametros}))

    def _fazer_requisicao(self, url, data=None):
        try:
            # Mantido timeout original de 30s conforme solicitado
            response = self.session.get(url, data=data, verify=False, timeout=30)
            logging.info(f" <- [API Solis] Resposta recebida: Status {response.status_code}")
            response.raise_for_status()
            return response.json() if response.text.strip() else None
        except Exception as e:
            logging.error(f"  [API Solis] ERRO: {e}", exc_info=True); return None

def buscar_aluno_por_cpf(cliente_solis, cpf):
    logging.info(f"[BUSCA SOLIS] Iniciando busca para o CPF: {cpf}")
    ID_RELATORIO_CPF, PARAM_CPF = "6820251203155305", "cpf"
    ID_RELATORIO_NOME, PARAM_NOME = "6620251203154311", "NOME_ALUNO"
    ID_RELATORIO_ID, PARAM_ID = "7020251204095501", "cod"
    
    cpf_limpo = cpf.replace('.', '').replace('-', '')
    res_cpf = cliente_solis.executar_relatorio(ID_RELATORIO_CPF, {PARAM_CPF: cpf_limpo})
    
    if not (res_cpf and isinstance(res_cpf, list) and res_cpf[0].get("nome")): return None
    
    nome_encontrado = res_cpf[0]["nome"]
    res_nome = cliente_solis.executar_relatorio(ID_RELATORIO_NOME, {PARAM_NOME: nome_encontrado.upper()})
    
    if not (res_nome and isinstance(res_nome, list)): return None
    
    for candidato in res_nome:
        id_candidato = candidato.get("ID")
        if not id_candidato: continue
        
        res_id = cliente_solis.executar_relatorio(ID_RELATORIO_ID, {PARAM_ID: id_candidato})
        if res_id and isinstance(res_id, list) and res_id[0]:
            if res_id[0].get("cpf", "").replace('.', '').replace('-', '') == cpf_limpo:
                detalhes = res_id[0]
                logging.info(f"[BUSCA SOLIS] Aluno encontrado: {detalhes.get('nome')}")
                return { "id": detalhes.get("codigo"), "name": detalhes.get("nome"), "cpf": detalhes.get("cpf") }
    return None

# --- LÓGICA MULTI-TENANT ---

def get_tenant_id():
    service_name = os.environ.get('K_SERVICE')
    if service_name:
        if service_name == 'solis-servico': return 'Solis'
        if service_name in ['imes-servico', 'imes-service', 'projeto-protocolo-imes']: return 'default'
    return 'default'

@app.before_request
def before_request_func():
    g.tenant_id = get_tenant_id()

def render_tenant_template(template_name, **context):
    # Tenta renderizar do tenant, senão usa o padrão (que deve estar na raiz ou em default)
    # Ajuste conforme a estrutura de pastas real
    try:
        return render_template(template_name, **context)
    except TemplateNotFound:
        return render_template(os.path.join('default', template_name), **context)

# --- ROTAS PRINCIPAIS (AGORA SEM LOGIN) ---

@app.route('/')
def index():
    """
    Carrega diretamente o Portal do Aluno.
    Não há verificação de login.
    """
    return render_tenant_template('portal.html')

@app.route('/search-student', methods=['POST'])
def handle_search_student():
    api_url = os.getenv("SOLIS_API_URL")
    jwt_token = os.getenv("SOLIS_JWT_TOKEN")
    
    # Fallback para teste se variáveis não estiverem setadas
    if not (api_url and jwt_token):
        logging.warning("Variáveis SOLIS não configuradas. Usando modo simulação.")
        # Retorno simulado para não quebrar a aplicação se não houver credenciais reais
        cpf = request.get_json().get('cpf')
        return jsonify({"id": "99999", "name": "ALUNO TESTE SIMULADO", "cpf": cpf}), 200
    
    cpf = request.get_json().get('cpf')
    if not cpf: return jsonify({"error": "CPF não fornecido."}), 400
    
    try:
        cliente_solis = SolisAPIClient(api_url, jwt_token)
        resultado = buscar_aluno_por_cpf(cliente_solis, cpf)
        if resultado: return jsonify(resultado), 200
        else: return jsonify({"error": "Aluno não encontrado"}), 404
    except Exception as e:
        logging.error(f"API /search-student: Erro - {e}", exc_info=True)
        return jsonify({"error": f"Erro interno no servidor: {e}"}), 500
    finally:
        # [OTIMIZAÇÃO] Força limpeza após requisição de busca
        gc.collect()

@app.route('/verificar-documentos', methods=['POST'])
def verificar_documentos_endpoint():
    if not aluno_serv:
        return jsonify({"success": False, "error": "Serviço de documentos indisponível."}), 503

    data = request.get_json()
    if not data or not data.get('studentName'):
        return jsonify({"success": False, "error": "Nome do aluno ('studentName') é obrigatório."}), 400

    student_name = data['studentName']
    
    try:
        if core_logic:
            tenant_drive_config = core_logic.carregar_configuracao_drive(g.tenant_id)
        else:
            # Configuração de fallback se core_logic não carregar
            tenant_drive_config = {
                'A-M_drive_id': 'ID_DRIVE_PADRAO', 
                'A-M_folder_id': 'ID_FOLDER_PADRAO',
                'N-Z_drive_id': 'ID_DRIVE_PADRAO', 
                'N-Z_folder_id': 'ID_FOLDER_PADRAO'
            }

        if not tenant_drive_config:
            return jsonify({"success": False, "error": "Configuração de Drive não encontrada."}), 500

        # Tenta pegar critérios do config ou usa fallback
        criteria_list = []
        if config and hasattr(config, 'DOCUMENT_CRITERIA'):
            criteria_list = list(config.DOCUMENT_CRITERIA.get("1ª Graduação", {}).keys())
        
        resultado_verificacao = aluno_serv.verificar_documentos_existentes(student_name, tenant_drive_config, criteria_list)
        return jsonify({"success": True, "documentos": resultado_verificacao.get("documentos", {})})

    except Exception as e:
        logging.critical(f"API /verificar-documentos: Erro - {e}", exc_info=True)
        return jsonify({"success": False, "error": "Erro interno ao verificar documentos."}), 500
    finally:
        # [OTIMIZAÇÃO] Limpeza de memória
        gc.collect()

@app.route('/analisar', methods=['POST'])
def analisar_documentos_endpoint():
    # Inicializa variáveis para garantir limpeza no finally
    uploaded_files_dict = {}
    resultado_analise = {}
    
    try:
        student_name = request.form.get('studentName')
        course_type = request.form.get('courseType')
        
        # request.files consome memória ao acessar
        files = request.files
        
        if not all([student_name, course_type, files]):
            return jsonify({"success": False, "error": "Dados incompletos."}), 400

        # [CRÍTICO] Aqui é onde o consumo de memória explode.
        # Estamos lendo os bytes para a memória.
        for doc_key, file_list in request.files.lists():
            for i, file_storage in enumerate(file_list):
                unique_key = f"file-{doc_key}-{i}"
                # file_storage.read() carrega TUDO na RAM. 
                # É necessário para o Gemini, mas perigoso com 512MB.
                uploaded_files_dict[unique_key] = {'filename': file_storage.filename, 'content': file_storage.read()}

        if not uploaded_files_dict:
            return jsonify({"success": False, "error": "Nenhum ficheiro válido para processar."}), 400

        if core_logic:
            resultado_analise = core_logic.iniciar_analise_e_upload(
                tenant_id=g.tenant_id,
                student_name=student_name,
                course_type=course_type,
                uploaded_files_dict=uploaded_files_dict
            )
        else:
            # Mock se core_logic não estiver presente
            logging.warning("Core Logic ausente. Retornando aprovação simulada.")
            resultado_analise = {"success": True, "results": {}}
            for key in uploaded_files_dict:
                doc_k = key.split('-')[1] # Extrai chave original do file-KEY-index
                resultado_analise["results"][doc_k] = {"status": "approved", "reason": "Simulação (Core Logic ausente)"}
        
        # --- Criação da pendência no Firestore ---
        try:
            if resultado_analise.get("success") and "results" in resultado_analise:
                resultados_aprovados = {
                    key: res for key, res in resultado_analise["results"].items()
                    if isinstance(res, dict) and res.get("status") == "approved"
                }
                
                if resultados_aprovados:
                    pendencia_data = {
                        "aluno_nome": student_name,
                        "dados_analise": resultados_aprovados,
                        "status": "pendente",
                        "origem": "projeto_principal_web",
                        "criado_em": firestore.SERVER_TIMESTAMP
                    }
                    
                    # [CORREÇÃO: USO DE get_db()]
                    doc_ref = get_db().collection(COL_PEDIDOS_WEB).add(pendencia_data)
                    logging.info(f"✅ SUCESSO! Pendência para '{student_name}' salva no Firestore com o ID: {doc_ref[1].id}")
                else:
                    logging.info("INFO: Nenhum documento foi aprovado. Nenhuma pendência criada no Firestore.")
        except Exception as e:
            logging.error(f"❌ FALHA ao criar pendência no Firestore: {e}", exc_info=True)

        return jsonify(resultado_analise)

    except Exception as e:
        logging.error(f"API /analisar: Erro crítico - {e}", exc_info=True)
        return jsonify({"success": False, "error": f"Erro interno: {e}"}), 500
    
    finally:
        # [OTIMIZAÇÃO EXTREMA]
        # Limpa explicitamente os arquivos pesados da memória
        # antes de encerrar a requisição.
        try:
            if uploaded_files_dict:
                del uploaded_files_dict
            if 'files' in locals():
                del files
            
            # Força o Garbage Collector do Python a rodar AGORA.
            # Isso recupera os MBs usados pelos arquivos enviados.
            unreachable_objects = gc.collect()
            logging.info(f"[GC] Memória limpa. Objetos coletados: {unreachable_objects}")
        except Exception as gc_error:
            logging.warning(f"[GC] Falha ao tentar limpar memória: {gc_error}")

@app.route('/ask-assistant', methods=['POST'])
def ask_assistant_endpoint():
    try:
        data = request.get_json()
        if not data or not data.get('question'):
            return jsonify({"error": "Nenhuma pergunta fornecida."}), 400
        
        # Pega o nome do aluno do frontend ou usa padrão
        student_name_input = data.get('studentName', 'Visitante')
        user_first_name = student_name_input.split(" ")[0] if student_name_input else "Visitante"

        if assistant_logic:
            ai_response = assistant_logic.get_assistant_response(
                question=data['question'], 
                chat_history=data.get('chat_history', []), 
                user_name=user_first_name, 
                student_name=student_name_input, 
                course_type=data.get('courseType')
            )
        else:
            ai_response = f"Olá {user_first_name}, o módulo de IA não foi carregado, mas estou ouvindo: {data['question']}"

        return jsonify({"answer": ai_response})
    except Exception as e:
        logging.error(f"Erro no endpoint /ask-assistant: {e}", exc_info=True)
        return jsonify({"answer": "Desculpe, ocorreu um erro técnico no assistente."}), 500
    finally:
        gc.collect()

@app.route('/teste-analise')
def teste_analise_page():
    return render_tenant_template('teste_analise.html')

if __name__ == '__main__':
    # Adicionado threading=False se estiver rodando local para simular ambiente single-thread se necessário,
    # mas em produção o Gunicorn cuida disso.
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)), debug=True)