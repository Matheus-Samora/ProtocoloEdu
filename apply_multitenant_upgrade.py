"""
Script para aplicar a atualização completa Multi-Tenant:
1. frontend/index.html -> Suporte a URLs únicas (/portal/:inst e ?inst=...), branding dinâmico (logo, cores, cursos), busca de alunos por CPF restrita à instituição no Supabase/API.
2. frontend/superadmin.html -> Links personalizáveis únicos com botão Copiar Link, modal completo de Importação em Lote de Alunos (CSV/JSON), tabela de alunos da faculdade e API docs de integração.
3. templates/default/portal.html e templates/default/super_admin.html sincronizados.
4. Deploy no Netlify e teste.
"""

import os
import re
import json
import zipfile
import urllib.request
import urllib.error

print("[*] Iniciando atualização de Multi-Tenant e Importação em Lote...")

# ==============================================================================
# 1. ATUALIZAR frontend/index.html (PORTAL DO ALUNO)
# ==============================================================================
with open("frontend/index.html", "r", encoding="utf-8") as f:
    portal_html = f.read()

# Substituir o bloco do logo na Tela 1 para ter IDs dinâmicos
old_logo_block = """                <!-- Logo da Instituição / IMES -->
                <div class="flex flex-col items-center mb-6 sm:mb-8">
                    <img src="/static/images/logo-imes.jpg" 
                         alt="Logo Faculdade IMES" 
                         class="w-20 h-20 sm:w-24 sm:h-24 mb-3 sm:mb-4 rounded-full object-cover border-4 border-imes-blue/20 dark:border-imes-gold/30 shadow-xl" 
                         onerror="this.onerror=null;this.src='https://placehold.co/96x96/0a2351/fdb913?text=IMES';">
                    <h1 class="text-xl sm:text-2xl font-extrabold text-slate-800 dark:text-white tracking-tight text-center">Portal do Aluno</h1>
                    <p class="text-slate-500 dark:text-slate-400 text-xs sm:text-sm font-medium text-center">Faculdade IMES - Envio e Validação</p>"""

new_logo_block = """                <!-- Logo da Instituição Dinâmica -->
                <div class="flex flex-col items-center mb-6 sm:mb-8">
                    <img id="portal-inst-logo" 
                         src="/static/images/logo-imes.jpg" 
                         alt="Logo da Instituição" 
                         class="w-20 h-20 sm:w-24 sm:h-24 mb-3 sm:mb-4 rounded-full object-cover border-4 border-imes-blue/20 dark:border-imes-gold/30 shadow-xl" 
                         onerror="this.onerror=null;this.src='https://placehold.co/96x96/0a2351/fdb913?text=EDU';">
                    <h1 id="portal-inst-title" class="text-xl sm:text-2xl font-extrabold text-slate-800 dark:text-white tracking-tight text-center">Portal do Aluno</h1>
                    <p id="portal-inst-subtitle" class="text-slate-500 dark:text-slate-400 text-xs sm:text-sm font-medium text-center">Faculdade IMES - Envio e Validação</p>"""

if old_logo_block in portal_html:
    portal_html = portal_html.replace(old_logo_block, new_logo_block)
    print(" -> IDs do cabeçalho da Tela 1 atualizados para branding dinâmico.")

# Injetar o catálogo e o resolvedor de instituições antes de DOMContentLoaded
institution_resolver_js = """
        // =========================================================================
        // MOTOR MULTI-TENANT: RESOLUÇÃO DE INSTITUIÇÃO E BRANDING DINÂMICO
        // =========================================================================
        let CURRENT_INSTITUTION_ID = "imes";
        let CURRENT_INSTITUTION_DATA = {
            id: "imes",
            name: "Faculdade IMES - Instituto Mineiro de Educação Superior",
            institution_type: "FACULDADE",
            branding: {
                portal_title: "Portal de Matrícula e Documentos - Faculdade IMES",
                primary_color: "#0a2351",
                secondary_color: "#fdb913",
                logo_url: "/static/images/logo-imes.jpg"
            },
            allowed_courses: ["graduacao_1", "graduacao_2", "pos_graduacao"]
        };

        const INSTITUTIONS_CATALOG = {
            "imes": {
                id: "imes",
                name: "Faculdade IMES - Instituto Mineiro de Educação Superior",
                institution_type: "FACULDADE",
                branding: {
                    portal_title: "Portal de Matrícula e Documentos - Faculdade IMES",
                    primary_color: "#0a2351",
                    secondary_color: "#fdb913",
                    logo_url: "/static/images/logo-imes.jpg"
                },
                allowed_courses: ["graduacao_1", "graduacao_2", "pos_graduacao"]
            },
            "colegio_modelo": {
                id: "colegio_modelo",
                name: "Colégio Santa Maria Digital",
                institution_type: "COLEGIO",
                branding: {
                    portal_title: "Matrícula Online 2026 - Colégio Santa Maria",
                    primary_color: "#064e3b",
                    secondary_color: "#10b981",
                    logo_url: "https://images.unsplash.com/photo-1546410531-bb4caa6b424d?w=160&h=160&fit=crop&crop=faces"
                },
                allowed_courses: ["ensino_medio"]
            },
            "unimetro": {
                id: "unimetro",
                name: "Universidade Metropolitana Integrada",
                institution_type: "UNIVERSIDADE",
                branding: {
                    portal_title: "Recepção de Prontuários Acadêmicos - UniMetro",
                    primary_color: "#1e3a8a",
                    secondary_color: "#3b82f6",
                    logo_url: "https://images.unsplash.com/photo-1523050854058-8df90110c9f1?w=160&h=160&fit=crop&crop=faces"
                },
                allowed_courses: ["graduacao_1", "graduacao_2", "pos_graduacao"]
            }
        };

        function resolveInstitutionSlug() {
            // 1. Tenta query param: ?inst=colegio_modelo ou ?institution=...
            const params = new URLSearchParams(window.location.search);
            const qInst = params.get('inst') || params.get('institution') || params.get('faculdade');
            if (qInst) return qInst.toLowerCase().trim();

            // 2. Tenta pathname: /portal/colegio_modelo ou /colegio_modelo
            const pathParts = window.location.pathname.split('/').filter(Boolean);
            if (pathParts.length > 0) {
                if (pathParts[0] === 'portal' && pathParts.length > 1) {
                    return pathParts[1].toLowerCase().trim();
                }
                const reserved = ['admin', 'superadmin', 'secretaria', 'index.html', 'static', 'api'];
                if (!reserved.includes(pathParts[0])) {
                    return pathParts[0].toLowerCase().trim();
                }
            }

            // 3. Fallback localStorage ou padrão imes
            return localStorage.getItem('last_active_institution') || 'imes';
        }

        async function loadInstitutionBranding() {
            const slug = resolveInstitutionSlug();
            CURRENT_INSTITUTION_ID = slug;
            localStorage.setItem('last_active_institution', slug);

            let inst = INSTITUTIONS_CATALOG[slug];
            if (supabaseClient) {
                try {
                    const { data, error } = await supabaseClient.from('institutions').select('*').eq('id', slug).single();
                    if (!error && data) {
                        inst = {
                            id: data.id,
                            name: data.name,
                            institution_type: data.institution_type,
                            branding: data.branding || {},
                            allowed_courses: data.enabled_courses || (data.institution_type === 'COLEGIO' ? ['ensino_medio'] : ['graduacao_1', 'graduacao_2', 'pos_graduacao'])
                        };
                    }
                } catch(e) {}
            }

            if (!inst) {
                inst = INSTITUTIONS_CATALOG['imes'];
                CURRENT_INSTITUTION_ID = 'imes';
            }

            CURRENT_INSTITUTION_DATA = inst;
            applyBrandingToDOM(inst);
            initCourseSelect(inst.allowed_courses);
        }

        function applyBrandingToDOM(inst) {
            const b = inst.branding || {};
            const logoEl = document.getElementById('portal-inst-logo');
            const titleEl = document.getElementById('portal-inst-title');
            const subtitleEl = document.getElementById('portal-inst-subtitle');

            if (logoEl && b.logo_url) logoEl.src = b.logo_url;
            if (titleEl) titleEl.textContent = "Portal do Aluno";
            if (subtitleEl) subtitleEl.textContent = `${inst.name} • Envio e Validação`;
            if (b.portal_title) document.title = b.portal_title;

            // Cores dinâmicas
            const primary = b.primary_color || '#0a2351';
            const secondary = b.secondary_color || '#fdb913';

            const searchBtn = document.getElementById('search-cpf-btn');
            if (searchBtn) {
                searchBtn.style.backgroundColor = secondary;
                searchBtn.style.color = primary;
            }

            const sendBtn = document.getElementById('send-files-btn');
            if (sendBtn) {
                sendBtn.style.background = `linear-gradient(135deg, ${primary} 0%, #153a7a 100%)`;
            }
        }
"""

# Substituir const CURRENT_INSTITUTION_ID = "imes";
portal_html = portal_html.replace(
    'const CURRENT_INSTITUTION_ID = "imes";',
    institution_resolver_js
)

# Atualizar initCourseSelect para filtrar cursos por instituição
old_init_courses = """        function initCourseSelect() {
            courseTypeSelect.innerHTML = '<option value="">Aguardando identificação...</option>';
            Object.entries(criteria).forEach(([key, config]) => {
                const opt = document.createElement('option');
                opt.value = key;
                opt.textContent = config.label;
                opt.className = 'text-slate-800 dark:text-white';
                courseTypeSelect.appendChild(opt);
            });
        }"""

new_init_courses = """        function initCourseSelect(allowedCourses) {
            courseTypeSelect.innerHTML = '<option value="">Aguardando identificação...</option>';
            Object.entries(criteria).forEach(([key, config]) => {
                if (allowedCourses && allowedCourses.length > 0 && !allowedCourses.includes(key)) {
                    return;
                }
                const opt = document.createElement('option');
                opt.value = key;
                opt.textContent = config.label;
                opt.className = 'text-slate-800 dark:text-white';
                courseTypeSelect.appendChild(opt);
            });
        }"""

portal_html = portal_html.replace(old_init_courses, new_init_courses)

# Atualizar DOMContentLoaded para carregar branding dinâmico
portal_html = portal_html.replace(
    """        document.addEventListener('DOMContentLoaded', () => {
            initTheme();
            initCourseSelect();
            initMasks();
            initEvents();
            showScreen1();
        });""",
    """        document.addEventListener('DOMContentLoaded', async () => {
            initTheme();
            await loadInstitutionBranding();
            initMasks();
            initEvents();
            showScreen1();
        });"""
)

# Atualizar handleStudentSearch para buscar no Supabase por institution_id e CPF
old_search_js = """            try {
                const res = await fetch('/api/student/search', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ identifier: raw, institution_id: CURRENT_INSTITUTION_ID })
                });

                if (res.ok) {
                    const student = await res.json();
                    setupIdentifiedStudent(student);
                } else {
                    setupIdentifiedStudent({
                        id: raw,
                        name: 'Estudante (Pré-Matrícula)',
                        cpf: studentCpfInput.value,
                        course: 'graduacao_1'
                    });
                }
            } catch (err) {
                setupIdentifiedStudent({
                    id: raw,
                    name: 'Estudante (Pré-Matrícula)',
                    cpf: studentCpfInput.value,
                    course: 'graduacao_1'
                });
            }"""

new_search_js = """            let studentFound = null;

            // 1. Busca no Supabase filtrando pela instituição ativa
            if (supabaseClient) {
                try {
                    const { data, error } = await supabaseClient
                        .from('student_dossiers')
                        .select('*')
                        .eq('institution_id', CURRENT_INSTITUTION_ID)
                        .eq('cpf', raw)
                        .limit(1);

                    if (!error && data && data.length > 0) {
                        const s = data[0];
                        studentFound = {
                            id: s.student_id || raw,
                            name: s.student_name,
                            cpf: s.cpf || studentCpfInput.value,
                            course: s.course_name || (CURRENT_INSTITUTION_DATA.institution_type === 'COLEGIO' ? 'ensino_medio' : 'graduacao_1')
                        };
                    }
                } catch(e) {}
            }

            // 2. Tenta a API do backend
            if (!studentFound) {
                try {
                    const res = await fetch('/api/student/search', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ identifier: raw, institution_id: CURRENT_INSTITUTION_ID })
                    });
                    if (res.ok) {
                        studentFound = await res.json();
                    }
                } catch(err) {}
            }

            // 3. Resultado da identificação
            if (studentFound) {
                setupIdentifiedStudent(studentFound);
            } else {
                showModal(
                    "CPF Não Localizado no Cadastro",
                    `O CPF informado não consta na lista de matrículas ativas de <strong>${escapeHtml(CURRENT_INSTITUTION_DATA.name)}</strong>.<br><br>Você pode prosseguir selecionando o curso desejado para realizar o pré-envio de documentos, ou revisar o CPF digitado.`
                );
                setupIdentifiedStudent({
                    id: raw,
                    name: 'Candidato (Pré-Matrícula)',
                    cpf: studentCpfInput.value,
                    course: CURRENT_INSTITUTION_DATA.institution_type === 'COLEGIO' ? 'ensino_medio' : 'graduacao_1'
                });
            }"""

portal_html = portal_html.replace(old_search_js, new_search_js)

with open("frontend/index.html", "w", encoding="utf-8") as f:
    f.write(portal_html)
print(" -> 'frontend/index.html' atualizado com suporte Multi-Instituição e busca no banco.")

with open("templates/default/portal.html", "w", encoding="utf-8") as f:
    f.write(portal_html)
print(" -> 'templates/default/portal.html' sincronizado.")

print("[*] Etapa do Portal do Aluno concluída.")
