"""
Script para implementar o sistema Multi-Instituição Completo do ProtocoloEdu:
1. Portal do Aluno com Links Únicos e Personalizados (/portal/:inst e ?inst=...)
   - Logomarca dinâmica
   - Cores primária e secundária personalizadas
   - Títulos institucionais dinâmicos
   - Cursos habilitados por instituição (Faculdade vs Colégio)
   - Busca de CPF no banco de dados filtrada estritamente pela instituição
2. Super Admin com Gestão de Alunos em Lote e Links Únicos
   - Coluna de Link Único do Portal do Aluno com botão de Copiar e Abrir
   - Modal de Importação em Lote de Alunos via arquivo CSV / JSON
   - Download de modelo de importação CSV
   - Tabela de alunos cadastrados por instituição
   - Documentação de Integração via API REST / Webhooks para ERP da faculdade
3. Backend api_server.py com endpoints de batch sync de alunos
4. Deploy automático no Netlify e sincronização com Supabase
"""

import os
import re
import json
import zipfile
import urllib.request
import urllib.error

print("[*] Iniciando implementação do Sistema Multi-Instituição e Importação em Lote...")

# ==============================================================================
# 1. ATUALIZAR BACKEND (api_server.py) COM ENDPOINTS DE ALUNOS
# ==============================================================================
with open("api_server.py", "r", encoding="utf-8") as f:
    api_code = f.read()

# Verifica se os endpoints de batch sync já existem
if "/students/batch-sync" not in api_code:
    batch_endpoints = """
@app.route('/api/institutions/<institution_id>/students/batch-sync', methods=['POST'])
@app.route('/api/super-admin/institutions/<institution_id>/students/batch-import', methods=['POST'])
def batch_import_students_endpoint(institution_id: str):
    \"\"\"
    Importação em lote de alunos para a base de dados de uma instituição.
    Aceita arquivo CSV/JSON ou payload JSON direto via API (ERP SolisGE/TOTVS).
    \"\"\"
    clean_tenant = re.sub(r'[^a-zA-Z0-9_-]', '', str(institution_id)).lower().strip()
    data = request.get_json(silent=True)
    students_list = []

    if data and isinstance(data, list):
        students_list = data
    elif data and isinstance(data, dict) and 'students' in data:
        students_list = data['students']
    elif 'file' in request.files:
        uploaded_file = request.files['file']
        content = uploaded_file.read().decode('utf-8', errors='ignore')
        if uploaded_file.filename.endswith('.json'):
            students_list = json.loads(content)
        else:
            import csv
            reader = csv.DictReader(content.splitlines(), delimiter=';' if ';' in content else ',')
            for row in reader:
                students_list.append({
                    "name": row.get('nome') or row.get('name') or row.get('Nome'),
                    "cpf": row.get('cpf') or row.get('CPF'),
                    "course": row.get('curso') or row.get('course') or row.get('Curso') or 'graduacao_1',
                    "student_id": row.get('matricula') or row.get('student_id') or row.get('Matrícula') or row.get('cpf'),
                    "email": row.get('email') or row.get('Email'),
                    "phone": row.get('telefone') or row.get('whatsapp') or row.get('Telefone')
                })

    if not students_list:
        return jsonify({"error": "Nenhum registro de aluno fornecido para importação."}), 400

    imported = []
    from adapters.supabase_client import supabase_manager
    sb_records = []
    for s in students_list:
        name = s.get('name', '').strip()
        cpf_clean = re.sub(r'\\D', '', str(s.get('cpf', '')))
        student_id = s.get('student_id') or cpf_clean
        course = s.get('course', 'graduacao_1')
        if not name or not cpf_clean:
            continue

        coordinator.dossier_repo.get_or_create_dossier(
            institution_id=clean_tenant,
            student_id=student_id,
            student_name=name,
            course_name=course,
            cpf=cpf_clean
        )

        sb_records.append({
            "institution_id": clean_tenant,
            "student_id": student_id,
            "student_name": name,
            "course_name": course,
            "cpf": cpf_clean,
            "status": "PENDENTE",
            "documents_json": {}
        })
        imported.append({"id": student_id, "name": name, "cpf": cpf_clean, "course": course})

    if sb_records and supabase_manager.is_configured:
        try:
            supabase_manager.client.table('student_dossiers').upsert(sb_records).execute()
        except Exception as e:
            logger.warning(f"Erro ao salvar alunos no Supabase: {e}")

    return jsonify({
        "success": True,
        "institution_id": clean_tenant,
        "imported_count": len(imported),
        "students": imported[:50]
    }), 200


@app.route('/api/institutions/<institution_id>/students', methods=['GET'])
def list_institution_students_endpoint(institution_id: str):
    \"\"\"Retorna os alunos cadastrados no banco de dados daquela instituição.\"\"\"
    clean_tenant = re.sub(r'[^a-zA-Z0-9_-]', '', str(institution_id)).lower().strip()
    from adapters.supabase_client import supabase_manager
    students = []
    if supabase_manager.is_configured:
        try:
            res = supabase_manager.client.table('student_dossiers').select('*').eq('institution_id', clean_tenant).execute()
            if res.data:
                students = res.data
        except Exception as e:
            logger.warning(f"Erro ao consultar alunos no Supabase: {e}")

    if not students:
        dossiers = coordinator.dossier_repo.list_dossiers(clean_tenant)
        students = [
            {
                "student_id": d.student_id,
                "student_name": d.student_name,
                "cpf": d.cpf,
                "course_name": d.course_name,
                "status": d.status.value
            }
            for d in dossiers
        ]

    return jsonify({
        "success": True,
        "institution_id": clean_tenant,
        "total": len(students),
        "students": students
    }), 200
"""
    # Inserir antes de @app.route('/ask-assistant'
    api_code = api_code.replace("@app.route('/ask-assistant'", batch_endpoints + "\n\n@app.route('/ask-assistant'")
    with open("api_server.py", "w", encoding="utf-8") as f:
        f.write(api_code)
    print(" -> Endpoints de Alunos e Batch Sync adicionados a 'api_server.py'.")

# ==============================================================================
# 2. ATUALIZAR frontend/_redirects COM SUPORTE A /portal/*
# ==============================================================================
redirects_content = """# Regras de Redirecionamento Oficiais Netlify (ProtocoloEdu)
# Redireciona /admin e /secretaria para a Central Unificada de Registros no Super Admin
/admin        /superadmin.html                302
/secretaria   /superadmin.html                302
/superadmin   /superadmin.html                200
/super-admin  /superadmin.html                200

# Roteamento SPA dos Portais de Alunos Personalizados por Instituição
/portal/*     /index.html                     200
/portal       /index.html                     200
/aluno        /index.html                     200
/*            /index.html                     200
"""

with open("frontend/_redirects", "w", encoding="utf-8") as f:
    f.write(redirects_content)
print(" -> 'frontend/_redirects' configurado para SPA em /portal/*.")

print("[*] Etapa 1 e 2 concluídas com sucesso.")
