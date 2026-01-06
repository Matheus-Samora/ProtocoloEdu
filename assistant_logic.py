# -*- coding: utf-8 -*-
# Módulo com a lógica de conversação do Assistente Acadêmico Virtual
# Versão 20.0 - Base de Conhecimento Completa (Contexto Geral IMES Restaurado)

import os
import json
import logging
import re
import google.generativeai as genai

# Módulos da aplicação
import config
from aluno_service import AlunoService

# --- CONFIGURAÇÃO DO LOGGING ---
logging.basicConfig(level=logging.INFO, format='[ASSISTANT_LOGIC] [%(levelname)s] %(message)s')

# =======================================================================
# 1. CONFIGURAÇÃO E INICIALIZAÇÃO
# =======================================================================

MODEL_NAME = 'gemini-2.5-flash'
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

try:
    if hasattr(config, 'GEMINI_API_KEY') and config.GEMINI_API_KEY:
        genai.configure(api_key=config.GEMINI_API_KEY)
    else:
        genai = None
        logging.warning("GEMINI_API_KEY ausente.")
except Exception as e:
    genai = None
    logging.error(f"Erro config IA: {e}")

try:
    aluno_service_instance = AlunoService()
except Exception as e:
    logging.error(f"Falha crítica ao iniciar AlunoService: {e}")
    aluno_service_instance = None

def _load_full_drive_config():
    try:
        caminho_config = os.path.join(BASE_DIR, config.DRIVE_CONFIG_FILE)
        if not os.path.exists(caminho_config):
            caminho_config = config.DRIVE_CONFIG_FILE

        if os.path.exists(caminho_config):
            with open(caminho_config, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get('default', data)
    except Exception as e:
        logging.error(f"Erro config Drive: {e}")
    return None

# =======================================================================
# 2. SMART CHUNKING (LÓGICA DE HUMANIZAÇÃO)
# =======================================================================

def smart_chunk_text(text):
    """
    Quebra o texto em blocos semânticos (pequenos parágrafos) para simular envio de mensagens.
    Usa pontuação para evitar cortes bruscos no meio de frases.
    """
    if not text: return ""

    # 1. Limpeza inicial
    text = text.replace('*', '') # Remove asteriscos excessivos se houver
    
    # 2. Regex para dividir por sentenças (ponto, exclamação, interrogação seguido de espaço ou quebra)
    sentences = re.split(r'(?<=[.!?])\s+', text)
    
    chunks = []
    current_chunk = ""
    
    # 3. Reconstrói blocos de tamanho ideal
    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence: continue
        
        # Se o chunk atual + a nova sentença for muito grande, fecha o chunk anterior
        if len(current_chunk) + len(sentence) > 180: 
            if current_chunk:
                chunks.append(current_chunk)
                current_chunk = sentence
            else:
                chunks.append(sentence)
                current_chunk = ""
        else:
            if current_chunk:
                current_chunk += "\n" + sentence
            else:
                current_chunk = sentence
    
    if current_chunk:
        chunks.append(current_chunk)
    
    # 4. Junta tudo com o separador ÚNICO para o Frontend animar
    return "<SPLIT>".join(chunks)

# =======================================================================
# 3. BASE DE CONHECIMENTO COMPLETA (RESTAURADA)
# =======================================================================

INFO_RAPIDA_CONTATO = """📍 **Endereço:**
Rua Peçanha, 662 - 10º andar - Centro.
<SPLIT>
📞 **Telefones:**
(33) 3212-3418
(33) 988894455 (WhatsApp)
<SPLIT>
📧 **E-mail:**
imesgvr@imes.org.br"""

CONTEXTO_GERAL_IMES = """
VOCÊ É O ASSISTENTE VIRTUAL DA FACULDADE IMES.
Use APENAS as informações abaixo para responder às perguntas.

--- SOBRE A INSTITUIÇÃO ---
O IMES – Instituto Mineiro de Educação Superior é uma Organização do Terceiro Setor, Associação Civil de fins não-econômicos.
A instituição possui nota máxima (5) no credenciamento EAD pelo MEC.
Oferece cursos 100% online com diploma EAD com a mesma validade do presencial.
Foco: Educação como veículo transformador para reverter desigualdades sociais.

--- PRINCÍPIOS ---
Missão: Promover o ensino, a pesquisa aplicada e a extensão como atividades viabilizadoras da aprendizagem para o mundo do trabalho.
Visão: Ser reconhecida pela excelência acadêmica, ética, competência, empreendedorismo e impacto socioambiental.
Valores: Respeito aos direitos humanos, Democracia republicana, Sustentabilidade ambiental, Gestão colegiada, Liberdade política e ideológica, A paz, a ética e a cidadania.

--- POR QUE ESCOLHER O IMES? ---
1. Vinculado ao MEC-Sistema Federal de Ensino Superior.
2. Conceito Institucional EAD Nota 5 (Máxima).
3. Mobilidade acadêmica internacional.
4. Atuação em todo território nacional.

--- LOCALIZAÇÃO E CONTATOS ---
Endereço: Rua Peçanha, 662 - 10º andar - Centro, Governador Valadares - MG. CEP: 35010-161.
Contatos: (33) 3212-3418 (Fixo) | (33) 988894455 (WhatsApp).
Horário: Segunda a Sexta (9h às 18h), Sábado (8h às 12h).

--- FORMAS DE INGRESSO ---
1. Vestibular Agendado: Online pelo site faculdadeimes.org.br.
2. Nota do ENEM: Edições anteriores.
3. Transferência Externa.
4. Obtenção de Novo Título (2ª Graduação).

--- CURSOS DE GRADUAÇÃO (EAD) ---
1. Administração (Bacharelado - 4 anos)
2. Análise e Desenvolvimento de Sistemas (Tecnólogo - 2,5 anos)
3. Ciências Contábeis (Bacharelado - 4 anos)
4. Pedagogia (Licenciatura - 4 anos)
5. Processos Gerenciais (Tecnólogo - 2 anos)
6. Gestão de Recursos Humanos (Tecnólogo - 2 anos)

--- PÓS-GRADUAÇÃO (LATO SENSU - EAD) ---
Mais de 200 cursos com conclusão a partir de 4 a 6 meses.
EXEMPLOS DE ÁREAS E CURSOS:
- SAÚDE: Enfermagem do Trabalho, Saúde Pública, Farmacologia, Análises Clínicas, Neurociência, Nutrição Esportiva, Gerontologia, Autismo (ABA), Saúde Mental.
- EDUCAÇÃO: Psicopedagogia, Neuropsicopedagogia, Educação Especial/Inclusiva, Libras, Docência (Superior, Técnico, Médio), Alfabetização, Gestão Escolar, Educação 4.0.
- DIREITO: Administrativo, Civil, Constitucional, Penal, Trabalhista, Tributário, Previdenciário, Digital, Compliance, Direitos Humanos, Direito de Família.
- GESTÃO/MBA: Marketing (Digital/Esportivo), Finanças, Recursos Humanos, Projetos, Logística, Gestão Pública, Empreendedorismo, Varejo, Gestão de Cidades Inteligentes.
- TECNOLOGIA (TI): Big Data, Ciência de Dados, IA Aplicada, Cloud Computing & DevOps, Segurança da Informação/Cibernética, Engenharia de Software, Governança em TIC.
- OUTROS: Teologia, Psicologia (TCC), Serviço Social, Arquitetura Urbanística, Design de Interiores, Meio Ambiente (ESG), Engenharia de Produção.

--- SERVIÇOS AO ALUNO ---
- Secretaria Acadêmica: imesgvr@imes.org.br (Matrículas, históricos).
- Financeiro (PROUNE): proune@imes.edu.br (Mensalidades, bolsas).
- Biblioteca: Acervo físico e digital ("Minha Biblioteca").
- Portal do Aluno: academico.faculdadeimes.org.br.
- Envio de Documentos: Sistema PROTOCOLO IMES.

INSTRUÇÃO PARA RESPOSTA:
Seja objetivo. Se o aluno perguntar de um curso específico, verifique se está na lista acima.
"""

# =======================================================================
# 4. LÓGICA DE DADOS (ALUNO SERVICE)
# =======================================================================

def verificar_documentos_aluno_drive(student_name, course_type=None):
    if not aluno_service_instance:
        return {'status': 'erro', 'mensagem': "Serviço indisponível."}

    tenant_config = _load_full_drive_config()
    if not tenant_config:
        return {'status': 'erro', 'mensagem': "Erro de Configuração."}

    tipo_curso_chave = course_type if course_type in config.DOCUMENT_CRITERIA else "1ª Graduação"
    criteria_list = config.DOCUMENT_CRITERIA.get(tipo_curso_chave, {})
    required_docs_keys = list(criteria_list.keys())

    try:
        resultado = aluno_service_instance.verificar_documentos_existentes(
            student_name=student_name,
            tenant_drive_config=tenant_config,
            required_docs_keys=required_docs_keys
        )
        
        if resultado['status'] == 'sucesso':
            docs_info = resultado.get('documentos', {})
            enviados = []
            faltantes = []
            
            for key, info in docs_info.items():
                nome_amigavel = criteria_list.get(key, {}).get('display_name', key)
                if info.get('encontrado'):
                    enviados.append(nome_amigavel)
                else:
                    faltantes.append(nome_amigavel)
            
            return {'status': 'sucesso', 'enviados': sorted(enviados), 'faltantes': sorted(faltantes)}
        
        elif resultado['status'] == 'aluno_nao_encontrado':
            return {'status': 'aluno_nao_encontrado'}
        else:
            return {'status': 'erro', 'mensagem': resultado.get('mensagem')}

    except Exception as e:
        logging.error(f"Erro verificação: {e}")
        return {'status': 'erro', 'mensagem': "Erro técnico."}

# =======================================================================
# 5. FORMATADORES DE RESPOSTA
# =======================================================================

def formatar_relatorio_documentos(nome, dados):
    """Gera relatório usando o separador <SPLIT> para animação."""
    faltantes = dados.get('faltantes', [])
    enviados = dados.get('enviados', [])
    
    blocos = []
    blocos.append(f"📂 Relatório para: **{nome.upper()}**")
    
    if not faltantes:
        blocos.append("🎉 **Parabéns! Tudo certo.**\nTodos os documentos obrigatórios constam na sua pasta.")
    else:
        # Bloco de pendências
        lista = "\n".join([f"❌ {d}" for d in faltantes])
        blocos.append(f"⚠️ **Atenção aos Pendentes:**\n{lista}")
        blocos.append("Por favor, envie estes documentos o quanto antes para regularizar sua situação.")
    
    if enviados:
        blocos.append(f"✅ **Recebidos:** {len(enviados)} documentos validados.")
    
    return "<SPLIT>".join(blocos)

def get_assistant_response(question, chat_history, user_name=None, student_name=None, course_type=None):
    
    # --- MENU INICIAL ---
    if not chat_history:
        nome = user_name if user_name else "Visitante"
        return f"🎓 Olá, **{nome}**!<SPLIT>Sou o Assistente Virtual do IMES.<SPLIT>Selecione uma opção:\n1️⃣ Analisar pendências\n2️⃣ Contatos<SPLIT>Ou digite sua dúvida."

    user_input = question.strip()
    
    # --- RECUPERAÇÃO DE CONTEXTO ---
    last_msg_text = ""
    for msg in reversed(chat_history):
        if msg.get('role') == 'model':
            parts = msg.get('parts', [])
            if isinstance(parts, str): last_msg_text = parts
            elif isinstance(parts, list): last_msg_text = " ".join([p.get('text', '') for p in parts])
            break

    # --- 1. PENDÊNCIAS ---
    if "1" in user_input and ("opção" in last_msg_text or "ajudar" in last_msg_text):
        target_name = student_name if student_name else None
        if target_name:
            res = verificar_documentos_aluno_drive(target_name, course_type)
            if res['status'] == 'sucesso':
                return formatar_relatorio_documentos(target_name, res)
            elif res['status'] == 'aluno_nao_encontrado':
                return f"🚫 Não encontrei a pasta de **{target_name}**.<SPLIT>Verifique se o nome está correto no cadastro."
            else:
                return f"Erro técnico: {res.get('mensagem')}"
        return "📝 Certo!<SPLIT>Por favor, digite seu **Nome Completo** para eu buscar."

    # --- 2. CONTATOS ---
    if "2" in user_input and ("opção" in last_msg_text or "ajudar" in last_msg_text):
        return INFO_RAPIDA_CONTATO

    # --- 3. BUSCA MANUAL ---
    if "Nome Completo" in last_msg_text:
        nome_busca = user_input.strip().upper()
        res = verificar_documentos_aluno_drive(nome_busca, course_type)
        if res['status'] == 'sucesso':
            return formatar_relatorio_documentos(nome_busca, res)
        elif res['status'] == 'aluno_nao_encontrado':
            return f"🚫 Não localizei **{nome_busca}**.<SPLIT>Tente digitar novamente ou contate a secretaria."
        return "Erro técnico."

    # --- 4. IA GENERATIVA ---
    if not genai:
        return "⚠️ Serviço de IA indisponível."

    contexto = ""
    if student_name: contexto += f"Aluno: {student_name}. "
    if course_type: contexto += f"Curso: {course_type}."

    prompt = (
        f"{CONTEXTO_GERAL_IMES}\n"
        f"Contexto da conversa: {contexto}\n"
        f"Pergunta do aluno: {user_input}\n\n"
    )

    try:
        model = genai.GenerativeModel(MODEL_NAME)
        response = model.generate_content(prompt)
        texto_bruto = response.text
        
        # APLICA O CHUNKING INTELIGENTE
        return smart_chunk_text(texto_bruto)
        
    except Exception as e:
        logging.error(f"Erro IA: {e}")
        return "Desculpe, tive um problema técnico.<SPLIT>Pode perguntar novamente?"