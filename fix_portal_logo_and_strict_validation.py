"""
Script para aplicar as 3 correções pontuais e decisivas solicitadas pelo usuário:
1. Retirar completamente a logomarca da Faculdade IMES (remover o logo estático e adotar brasão acadêmico moderno / logo da instituição ativa).
2. Remover qualquer seletor ou dropdown de instituição do Portal do Aluno: o link gerado encaminha o aluno diretamente para a instituição correta, sem opção de troca.
3. Se o CPF não estiver cadastrado no banco de dados da instituição, bloquear o avanço e retornar estritamente a mensagem: "Aluno não encontrado na base de dados."
"""

import os
import re
import json
import zipfile
import urllib.request
import urllib.error

print("[*] Iniciando correção do Portal do Aluno (Remoção da logo IMES, bloqueio de seletor e validação estrita)...")

INDEX_PATH = "frontend/index.html"
PORTAL_TEMPLATE_PATH = "templates/default/portal.html"

with open(INDEX_PATH, "r", encoding="utf-8") as f:
    html = f.read()

# ==============================================================================
# 1. REMOVER A LOGOMARCA ESTÁTICA DO IMES E O SELETOR DE INSTITUIÇÃO
# ==============================================================================
# Substituir o favicon para ícone acadêmico
html = html.replace(
    '<link rel="icon" type="image/jpeg" href="/static/images/logo-imes.jpg">',
    '<link rel="icon" type="image/svg+xml" href="data:image/svg+xml,<svg xmlns=\'http://www.w3.org/2000/svg\' viewBox=\'0 0 100 100\'><text y=\'.9em\' font-size=\'90\'>🎓</text></svg>">'
)

# Substituir o bloco do cabeçalho da Tela 1:
# Remove a tag <img> com logo-imes.jpg e o switcher #quick-inst-switcher
old_header_pattern = re.compile(
    r'<div class="flex flex-col items-center mb-6 sm:mb-8">.*?<label for="student-cpf"',
    re.DOTALL
)

new_header_code = """<div class="flex flex-col items-center mb-6 sm:mb-8">
                    <!-- Brasão / Logotipo Institucional Dinâmico (Sem logo IMES estático) -->
                    <div id="portal-inst-logo-container" class="w-20 h-20 sm:w-24 sm:h-24 mb-3 sm:mb-4 rounded-full flex items-center justify-center border-4 border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 shadow-xl overflow-hidden relative">
                        <img id="portal-inst-logo" 
                             src="" 
                             alt="Logomarca Institucional" 
                             class="w-full h-full object-contain p-2 hidden">
                        <div id="portal-inst-logo-fallback" class="w-full h-full flex flex-col items-center justify-center text-slate-700 dark:text-slate-200 bg-gradient-to-br from-slate-100 to-slate-200 dark:from-slate-800 dark:to-slate-900">
                            <i class="ph-bold ph-graduation-cap text-3xl sm:text-4xl text-blue-600 dark:text-amber-400"></i>
                        </div>
                    </div>

                    <h1 id="portal-inst-title" class="text-xl sm:text-2xl font-extrabold text-slate-800 dark:text-white tracking-tight text-center">Portal do Aluno</h1>
                    <p id="portal-inst-subtitle" class="text-slate-500 dark:text-slate-400 text-xs sm:text-sm font-medium text-center">Secretaria Acadêmica Digital • Envio e Validação</p>

                    <!-- Theme Switcher Apenas (SEM NENHUM SELETOR DE INSTITUIÇÃO) -->
                    <div class="mt-3 sm:mt-4 flex items-center justify-center">
                        <label class="switch" title="Alternar Tema Claro/Escuro">
                            <input checked="true" id="theme-toggle" type="checkbox" />
                            <span class="slider"></span>
                        </label>
                    </div>
                </div>

                <div class="space-y-4 sm:space-y-5">
                    <!-- CPF do Aluno -->
                    <div id="student-search-container" class="space-y-3 sm:space-y-4">
                        <div id="student-cpf-container">
                            <label for="student-cpf" """

html = old_header_pattern.sub(new_header_code, html)
print(" -> Logomarca estática do IMES e seletor dropdown removidos com sucesso.")

# Injetar mensagem inline de erro abaixo do CPF se não existir
if 'id="cpf-error-message"' not in html:
    html = html.replace(
        '</button>\n                            </div>\n                        </div>',
        '</button>\n                            </div>\n                            <p id="cpf-error-message" class="hidden text-xs text-rose-500 font-bold mt-1.5 flex items-center gap-1.5"><i class="ph-bold ph-warning-circle text-sm"></i> <span>Aluno não encontrado na base de dados.</span></p>\n                        </div>'
    )
    print(" -> Mensagem inline 'Aluno não encontrado na base de dados.' adicionada.")

# ==============================================================================
# 2. ATUALIZAR O RODAPÉ (REMOVER FACULDADE IMES ESTÁTICA)
# ==============================================================================
old_footer = re.compile(r'&copy;\s*2026\s*Faculdade\s*IMES\.\s*Todos\s*os\s*direitos\s*reservados\.', re.IGNORECASE)
html = old_footer.sub(r'<span id="portal-footer-copy">&copy; 2026 ProtocoloEdu. Todos os direitos reservados.</span>', html)
print(" -> Rodapé estático da Faculdade IMES atualizado para dinâmico.")

# ==============================================================================
# 3. ATUALIZAR applyBrandingToDOM E INSTITUTIONS_CATALOG (REMOVER /static/images/logo-imes.jpg)
# ==============================================================================
# Remove referências a /static/images/logo-imes.jpg no catálogo embutido
html = html.replace('"/static/images/logo-imes.jpg"', '""')
html = html.replace("'/static/images/logo-imes.jpg'", "''")

# Atualizar a função applyBrandingToDOM
old_apply_branding_func = re.compile(r'function applyBrandingToDOM\(inst\)\s*\{.*?\}\s*function initCourseSelect', re.DOTALL)

new_apply_branding_func = """function applyBrandingToDOM(inst) {
            const b = inst.branding || {};
            const logoImg = document.getElementById('portal-inst-logo');
            const logoFallback = document.getElementById('portal-inst-logo-fallback');
            const titleEl = document.getElementById('portal-inst-title');
            const subtitleEl = document.getElementById('portal-inst-subtitle');
            const footerCopy = document.getElementById('portal-footer-copy');

            // 1. Logo: se tiver logo real (que não seja a antiga do IMES), exibe; senão mostra o brasão acadêmico elegante
            if (b.logo_url && b.logo_url.trim() !== '' && !b.logo_url.includes('logo-imes.jpg')) {
                if (logoImg) {
                    logoImg.src = b.logo_url;
                    logoImg.classList.remove('hidden');
                }
                if (logoFallback) logoFallback.classList.add('hidden');
            } else {
                if (logoImg) logoImg.classList.add('hidden');
                if (logoFallback) logoFallback.classList.remove('hidden');
            }

            // 2. Títulos Institucionais
            if (titleEl) titleEl.textContent = "Portal do Aluno";
            if (subtitleEl) subtitleEl.textContent = `${inst.name} • Envio e Validação`;
            if (b.portal_title) {
                document.title = b.portal_title;
            } else {
                document.title = `${inst.name} - Portal do Aluno`;
            }

            if (footerCopy) {
                footerCopy.innerHTML = `&copy; ${new Date().getFullYear()} ${escapeHtml(inst.name)}. Todos os direitos reservados.`;
            }

            // 3. Cores Institucionais
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

        function initCourseSelect"""

html = old_apply_branding_func.sub(new_apply_branding_func, html)
print(" -> Função applyBrandingToDOM reformulada sem logo IMES.")

# ==============================================================================
# 4. VALIDAÇÃO ESTRITA: SE NÃO ENCONTRAR NO BANCO, RETORNAR "Aluno nao encontrado na base de dados."
# ==============================================================================
old_search_logic = re.compile(r'// 3\. Resultado da identificação.*?\} finally \{', re.DOTALL)

new_search_logic = """// 3. Resultado da identificação estrita no banco de dados da instituição
            const errorMsgEl = document.getElementById('cpf-error-message');

            if (studentFound) {
                if (errorMsgEl) errorMsgEl.classList.add('hidden');
                setupIdentifiedStudent(studentFound);
            } else {
                // ALUNO NÃO ENCONTRADO NO BANCO DE DADOS: BLOQUEIA E RETORNA MENSAGEM
                if (errorMsgEl) {
                    errorMsgEl.classList.remove('hidden');
                }
                showModal(
                    "Aluno não encontrado na base de dados.",
                    `O CPF informado (<strong>${escapeHtml(studentCpfInput.value)}</strong>) não possui cadastro ativo no banco de dados de <strong>${escapeHtml(CURRENT_INSTITUTION_DATA.name)}</strong>.<br><br><span class="text-xs text-slate-500 dark:text-slate-400">Verifique o CPF digitado ou solicite à secretaria acadêmica a inclusão da sua matrícula.</span>`
                );
                // Bloqueia qualquer avanço
                resetStudentSearch();
                studentCpfInput.focus();
            }
        } finally {"""

html = old_search_logic.sub(new_search_logic, html)
print(" -> Validação estrita 'Aluno não encontrado na base de dados.' implementada.")

# Salvar frontend/index.html e templates/default/portal.html
with open(INDEX_PATH, "w", encoding="utf-8") as f:
    f.write(html)

with open(PORTAL_TEMPLATE_PATH, "w", encoding="utf-8") as f:
    f.write(html)

print("[*] 'frontend/index.html' e 'templates/default/portal.html' gravados com sucesso!")

# ==============================================================================
# 5. RECONSTRUIR ZIP E DEPLOY NO NETLIFY
# ==============================================================================
zip_path = "protocoloedu-frontend.zip"
print(f"[*] Reconstruindo {zip_path}...")
with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
    for root, dirs, files in os.walk("frontend"):
        for file in files:
            full_path = os.path.join(root, file)
            arcname = os.path.relpath(full_path, "frontend")
            zf.write(full_path, arcname)

print(f" -> Zip criado ({os.path.getsize(zip_path)} bytes).")

TOKEN = "nfp_bb69ariUkrzd2SuUky3Z6iVdfxSVYmz48b42"
SITE_ID = "69dacb8b-0fd1-4550-be1a-78fb68495fb7"
deploy_url = f"https://api.netlify.com/api/v1/sites/{SITE_ID}/deploys"

print("[*] Publicando no Netlify...")
with open(zip_path, "rb") as f:
    zip_bytes = f.read()

req = urllib.request.Request(
    deploy_url,
    data=zip_bytes,
    headers={
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/zip"
    },
    method="POST"
)

try:
    with urllib.request.urlopen(req) as resp:
        res = json.loads(resp.read().decode("utf-8"))
        print("[SUCESSO Netlify] Deploy publicado com sucesso!")
        print(f" -> Deploy ID: {res.get('id')}")
        print(f" -> State: {res.get('state')}")
        print(f" -> URL: https://protocoloedu.netlify.app/")
except urllib.error.HTTPError as e:
    err_body = e.read().decode('utf-8', errors='ignore')
    print(f"[ERRO Netlify] {e.code}: {err_body}")
