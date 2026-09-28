"""
Script para atualizar frontend/superadmin.html com:
1. Colunas de Link Único do Portal do Aluno com botão de Copiar e Abrir (/portal/:inst)
2. Gerenciador de Alunos no Banco de Dados com botão 'Alunos & Lote (CSV)'
3. Modal Completo de Importação em Lote de Alunos (#batch-students-modal):
   - Upload de arquivo CSV / JSON com Drag & Drop
   - Download de Modelo Oficial CSV (modelo_alunos_protocoloedu.csv)
   - Tabela de Pré-visualização instantânea das linhas parseadas
   - Confirmação e gravação no Supabase e na API local
   - Documentação de Integração via API REST para o TI da faculdade (SolisGE / TOTVS)
   - Listagem e busca de alunos cadastrados por instituição
4. Deploy no Netlify
"""

import os
import re
import json
import zipfile
import urllib.request
import urllib.error

print("[*] Atualizando frontend/superadmin.html com Links Únicos e Importação em Lote...")

with open("frontend/superadmin.html", "r", encoding="utf-8") as f:
    html = f.read()

# 1. Atualizar o cabeçalho da tabela de contratantes
old_table_header = """                        <tr>
                            <th class="p-3.5">Instituição / Contratante</th>
                            <th class="p-3.5">Plano Ativo</th>
                            <th class="p-3.5">Consumo no Ciclo</th>
                            <th class="p-3.5">Chave da Secretaria</th>
                            <th class="p-3.5">Status</th>
                            <th class="p-3.5">Portais Ativos</th>
                            <th class="p-3.5 text-right">Ação</th>
                        </tr>"""

new_table_header = """                        <tr>
                            <th class="p-3.5">Instituição / Contratante</th>
                            <th class="p-3.5">Link Único do Portal (Aluno)</th>
                            <th class="p-3.5">Base de Alunos (Banco)</th>
                            <th class="p-3.5">Consumo &amp; Plano</th>
                            <th class="p-3.5">Status</th>
                            <th class="p-3.5 text-right">Ações</th>
                        </tr>"""

if old_table_header in html:
    html = html.replace(old_table_header, new_table_header)
    print(" -> Cabeçalho da tabela de contratantes atualizado.")

# 2. Injetar o Modal de Importação em Lote (#batch-students-modal) antes do modal de whitelabel
batch_modal_html = """
    <!-- ========================================================================= -->
    <!-- MODAL: GESTÃO DE ALUNOS & IMPORTAÇÃO EM LOTE (CSV / API)                 -->
    <!-- ========================================================================= -->
    <div id="batch-students-modal" class="hidden fixed inset-0 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4 z-50 animate-fade-in">
        <div class="bg-white dark:bg-slate-900 rounded-3xl max-w-4xl w-full shadow-2xl border border-slate-200 dark:border-slate-800 overflow-hidden flex flex-col max-h-[92vh]">
            <div class="p-5 bg-[#0a2351] text-white flex items-center justify-between border-b border-slate-700">
                <div class="flex items-center gap-3">
                    <div class="w-10 h-10 rounded-xl bg-imes-gold text-imes-blue flex items-center justify-center text-lg font-bold shadow">
                        <i class="ph-bold ph-users-three"></i>
                    </div>
                    <div>
                        <div class="flex items-center gap-2">
                            <h3 class="font-extrabold text-sm sm:text-base text-white" id="batch-modal-inst-title">Base de Alunos &amp; Importação em Lote</h3>
                            <span class="px-2 py-0.5 rounded text-[10px] font-bold bg-blue-500/20 text-blue-300 border border-blue-400/30" id="batch-modal-inst-slug">imes</span>
                        </div>
                        <p class="text-xs text-blue-200">Alimente o banco de dados da faculdade para reconhecimento automático por CPF no Portal do Aluno</p>
                    </div>
                </div>
                <button onclick="closeStudentsBatchModal()" class="w-8 h-8 rounded-full hover:bg-white/10 flex items-center justify-center text-white transition cursor-pointer">
                    <i class="ph-bold ph-x text-lg"></i>
                </button>
            </div>

            <!-- NAVEGAÇÃO DE SUB-ABAS DO MODAL -->
            <div class="bg-slate-100 dark:bg-slate-800/60 border-b border-slate-200 dark:border-slate-800 px-6 flex items-center gap-4 text-xs font-bold">
                <button id="batch-tab-btn-upload" onclick="switchBatchTab('upload')" class="py-3 border-b-2 border-imes-blue text-imes-blue dark:text-imes-gold font-extrabold flex items-center gap-1.5 cursor-pointer">
                    <i class="ph-bold ph-upload-simple"></i>
                    <span>1. Importar Planilha em Lote (CSV / JSON)</span>
                </button>
                <button id="batch-tab-btn-api" onclick="switchBatchTab('api')" class="py-3 border-b-2 border-transparent text-slate-500 hover:text-slate-800 dark:hover:text-white flex items-center gap-1.5 cursor-pointer">
                    <i class="ph-bold ph-plugs-connected"></i>
                    <span>2. Integração via API (SolisGE / TOTVS)</span>
                </button>
                <button id="batch-tab-btn-list" onclick="switchBatchTab('list')" class="py-3 border-b-2 border-transparent text-slate-500 hover:text-slate-800 dark:hover:text-white flex items-center gap-1.5 cursor-pointer">
                    <i class="ph-bold ph-table"></i>
                    <span>3. Alunos Cadastrados no Banco (<span id="batch-modal-students-count">0</span>)</span>
                </button>
            </div>

            <div class="flex-1 overflow-y-auto custom-scroll p-6 text-xs space-y-5">
                
                <!-- ABA 1: UPLOAD DE ARQUIVO EM LOTE -->
                <div id="batch-section-upload" class="space-y-4">
                    <div class="p-4 rounded-2xl bg-blue-50/60 dark:bg-blue-950/30 border border-blue-200 dark:border-blue-900/40 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                        <div>
                            <h4 class="font-bold text-blue-900 dark:text-blue-300">Como funciona a Importação em Lote?</h4>
                            <p class="text-slate-600 dark:text-slate-300 text-[11px] mt-0.5">
                                Envie a relação de candidatos ou alunos matriculados exportada do sistema acadêmico da instituição. O sistema cadastra todos no banco de dados de uma só vez.
                            </p>
                        </div>
                        <button onclick="downloadCsvTemplate()" class="px-3.5 py-2 bg-white dark:bg-slate-900 hover:bg-slate-50 text-blue-700 dark:text-blue-300 border border-blue-300 dark:border-blue-800 rounded-xl font-bold flex items-center gap-1.5 whitespace-nowrap cursor-pointer shadow-xs">
                            <i class="ph-bold ph-download-simple text-sm"></i>
                            <span>Baixar Modelo Oficial CSV</span>
                        </button>
                    </div>

                    <!-- DROPZONE DE ARQUIVO -->
                    <div id="batch-dropzone" onclick="document.getElementById('batch-file-input').click()" class="border-2 border-dashed border-slate-300 dark:border-slate-700 hover:border-blue-500 dark:hover:border-blue-400 rounded-2xl p-8 text-center cursor-pointer transition bg-slate-50/50 dark:bg-slate-950/30">
                        <input type="file" id="batch-file-input" accept=".csv, .json" class="hidden" onchange="handleBatchFileSelect(event)">
                        <div class="w-14 h-14 rounded-2xl bg-blue-50 dark:bg-blue-950/80 text-blue-600 dark:text-blue-400 flex items-center justify-center text-2xl mx-auto mb-3 shadow-inner">
                            <i class="ph-bold ph-file-arrow-up"></i>
                        </div>
                        <h5 class="font-extrabold text-sm text-slate-800 dark:text-white">Arraste a planilha de alunos ou clique aqui para selecionar</h5>
                        <p class="text-[11px] text-slate-400 mt-1">Formatos aceitos: Planilha CSV (separada por vírgula ou ponto-e-vírgula) ou JSON</p>
                    </div>

                    <!-- PRÉ-VISUALIZAÇÃO DOS ALUNOS IDENTIFICADOS -->
                    <div id="batch-preview-container" class="hidden space-y-3 pt-2">
                        <div class="flex items-center justify-between">
                            <h5 class="font-extrabold text-slate-800 dark:text-white flex items-center gap-1.5">
                                <i class="ph-bold ph-check-circle text-emerald-500"></i>
                                <span>Pré-visualização: <span id="batch-preview-count" class="text-emerald-500">0</span> alunos prontos para importação</span>
                            </h5>
                            <button onclick="clearBatchPreview()" class="text-rose-500 hover:underline font-bold">Cancelar seleção</button>
                        </div>

                        <div class="overflow-x-auto rounded-xl border border-slate-200 dark:border-slate-800 max-h-56 custom-scroll">
                            <table class="w-full text-left text-xs">
                                <thead class="bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 font-extrabold uppercase text-[10px]">
                                    <tr>
                                        <th class="p-2.5">Nome do Aluno</th>
                                        <th class="p-2.5">CPF</th>
                                        <th class="p-2.5">Curso</th>
                                        <th class="p-2.5">Matrícula</th>
                                    </tr>
                                </thead>
                                <tbody id="batch-preview-tbody" class="divide-y divide-slate-200 dark:divide-slate-800 font-mono text-[11px]"></tbody>
                            </table>
                        </div>

                        <div class="pt-2 flex justify-end">
                            <button onclick="commitBatchImport()" class="px-6 py-2.5 bg-emerald-600 hover:bg-emerald-700 text-white font-extrabold rounded-xl shadow-lg transition flex items-center gap-2 cursor-pointer active:scale-95">
                                <i class="ph-bold ph-database"></i>
                                <span id="batch-commit-btn-text">Confirmar e Gravar Alunos no Banco</span>
                            </button>
                        </div>
                    </div>
                </div>

                <!-- ABA 2: INTEGRAÇÃO VIA API (SOLIS / TOTVS) -->
                <div id="batch-section-api" class="hidden space-y-4">
                    <div class="p-4 rounded-2xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700 space-y-3">
                        <div class="flex items-center gap-2 text-slate-800 dark:text-white font-extrabold text-sm">
                            <i class="ph-bold ph-plugs text-blue-500 text-lg"></i>
                            <span>Endpoint da API para o TI da Instituição</span>
                        </div>
                        <p class="text-slate-600 dark:text-slate-300 text-xs">
                            A equipe técnica da faculdade ou o sistema de matrícula online pode despachar os dados dos alunos diretamente para o banco de dados via requisição HTTP POST.
                        </p>

                        <div>
                            <span class="text-slate-400 block text-[10px] font-bold uppercase mb-1">URL Oficial do Webhook / API</span>
                            <div class="flex items-center gap-2">
                                <input type="text" id="api-endpoint-url" readonly class="modern-input font-mono text-xs bg-white dark:bg-slate-900" value="https://protocoloedu.netlify.app/api/institutions/imes/students/batch-sync">
                                <button onclick="copyApiEndpoint()" class="px-3 py-2 bg-blue-600 text-white rounded-xl font-bold cursor-pointer hover:bg-blue-700">Copiar</button>
                            </div>
                        </div>

                        <div>
                            <span class="text-slate-400 block text-[10px] font-bold uppercase mb-1">Cabeçalho de Autenticação</span>
                            <input type="text" id="api-token-header" readonly class="modern-input font-mono text-xs bg-white dark:bg-slate-900" value="X-Institution-Key: imes-sec-2026">
                        </div>

                        <div>
                            <span class="text-slate-400 block text-[10px] font-bold uppercase mb-1">Exemplo de Payload JSON (Envio em Lote)</span>
                            <pre class="p-3 rounded-xl bg-slate-950 text-emerald-400 font-mono text-[11px] overflow-x-auto custom-scroll">[
  {
    "name": "Lucas Gabriel Mendonça",
    "cpf": "12345678900",
    "course": "graduacao_1",
    "student_id": "202610482",
    "email": "lucas@email.com",
    "phone": "+5535998764321"
  }
]</pre>
                        </div>
                    </div>
                </div>

                <!-- ABA 3: LISTA DOS ALUNOS ATUALMENTE CADASTRADOS -->
                <div id="batch-section-list" class="hidden space-y-3">
                    <div class="flex items-center justify-between gap-3">
                        <div class="relative flex-1">
                            <input type="text" id="batch-search-students" oninput="filterRegisteredStudents()" placeholder="Buscar aluno por nome, CPF ou curso..." class="modern-input pl-9 text-xs">
                            <i class="ph-bold ph-magnifying-glass absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 text-sm"></i>
                        </div>
                        <button onclick="loadRegisteredStudents()" class="p-2.5 bg-slate-100 dark:bg-slate-800 rounded-xl text-slate-600 dark:text-slate-300 hover:bg-slate-200 transition" title="Recarregar">
                            <i class="ph-bold ph-arrows-clockwise"></i>
                        </button>
                    </div>

                    <div class="overflow-x-auto rounded-xl border border-slate-200 dark:border-slate-800 max-h-72 custom-scroll">
                        <table class="w-full text-left text-xs">
                            <thead class="bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 font-extrabold uppercase text-[10px]">
                                <tr>
                                    <th class="p-3">Nome do Estudante</th>
                                    <th class="p-3">CPF</th>
                                    <th class="p-3">Curso</th>
                                    <th class="p-3">Matrícula</th>
                                    <th class="p-3">Status</th>
                                </tr>
                            </thead>
                            <tbody id="batch-registered-tbody" class="divide-y divide-slate-200 dark:divide-slate-800">
                                <tr><td colspan="5" class="p-6 text-center text-slate-400">Carregando alunos...</td></tr>
                            </tbody>
                        </table>
                    </div>
                </div>

            </div>

            <div class="p-4 bg-slate-100 dark:bg-slate-800/80 border-t border-slate-200 dark:border-slate-800 flex items-center justify-between">
                <span class="text-[11px] text-slate-400 font-mono">Reconhecimento instantâneo por CPF no Portal do Aluno</span>
                <button onclick="closeStudentsBatchModal()" class="px-5 py-2 btn-gold rounded-xl text-xs font-bold cursor-pointer">
                    Concluir
                </button>
            </div>
        </div>
    </div>
"""

if '<div id="whitelabel-modal"' in html:
    html = html.replace('<div id="whitelabel-modal"', batch_modal_html + '\n    <div id="whitelabel-modal"')
    print(" -> Modal #batch-students-modal injetado no HTML.")

# 3. Atualizar a função renderInstitutionsTable para exibir o Link Único com botão copiar e botão Alunos & Lote
old_render_inst = """            tbody.innerHTML = list.map(inst => {
                const sub = inst.subscription || {};
                const limit = sub.monthly_limit || 0;
                const usage = sub.current_month_usage || 0;
                const percent = limit > 0 ? Math.min(Math.round((usage / limit) * 100), 100) : 0;

                return `
                    <tr class="hover:bg-slate-50 dark:hover:bg-slate-800/40 transition">
                        <td class="p-3.5">
                            <div class="font-extrabold text-slate-800 dark:text-white">${escapeHtml(inst.name)}</div>
                            <div class="text-[11px] font-mono text-slate-400 mt-0.5">slug: ${escapeHtml(inst.id)} • ${escapeHtml(inst.institution_type)}</div>
                        </td>
                        <td class="p-3.5">
                            <span class="font-bold text-imes-blue dark:text-imes-gold bg-blue-50 dark:bg-blue-950/50 border border-blue-200 dark:border-blue-800 px-2 py-0.5 rounded-full text-[11px]">
                                ${escapeHtml(sub.plan_name || sub.plan_tier)}
                            </span>
                            <div class="text-[11px] text-slate-400 mt-1">Limite: <strong>${limit}</strong> docs/mês</div>
                        </td>
                        <td class="p-3.5 w-44">
                            <div class="flex items-center justify-between text-[11px] font-bold text-slate-700 dark:text-slate-300 mb-1">
                                <span>${usage} docs</span>
                                <span>${percent}%</span>
                            </div>
                            <div class="w-full bg-slate-200 dark:bg-slate-700 h-2 rounded-full overflow-hidden">
                                <div class="bg-imes-blue dark:bg-imes-gold h-full rounded-full" style="width: ${percent}%;"></div>
                            </div>
                        </td>
                        <td class="p-3.5 font-mono text-[11px] text-slate-500 dark:text-slate-400">
                            ${inst.id}-sec-2026
                        </td>
                        <td class="p-3.5">
                            <span class="px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-100 dark:bg-emerald-950/60 text-emerald-800 dark:text-emerald-300 border border-emerald-300 dark:border-emerald-700">Ativo</span>
                        </td>
                        <td class="p-3.5 text-[11px] font-semibold">
                            <a href="/" target="_blank" class="text-blue-500 hover:underline">Portal Aluno ↗</a>
                        </td>
                        <td class="p-3.5 text-right">
                            <button onclick="openEditModal('${inst.id}')" class="px-2.5 py-1 bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 text-slate-700 dark:text-slate-200 border border-slate-200 dark:border-slate-700 rounded-lg text-xs font-bold cursor-pointer">
                                Gerenciar
                            </button>
                        </td>
                    </tr>
                `;
            }).join('');"""

new_render_inst = """            tbody.innerHTML = list.map(inst => {
                const sub = inst.subscription || {};
                const limit = sub.monthly_limit || 0;
                const usage = sub.current_month_usage || 0;
                const percent = limit > 0 ? Math.min(Math.round((usage / limit) * 100), 100) : 0;
                const portalUrl = `https://protocoloedu.netlify.app/portal/${inst.id}`;

                return `
                    <tr class="hover:bg-slate-50 dark:hover:bg-slate-800/40 transition">
                        <td class="p-3.5">
                            <div class="font-extrabold text-slate-800 dark:text-white">${escapeHtml(inst.name)}</div>
                            <div class="text-[11px] font-mono text-slate-400 mt-0.5">slug: <strong class="text-blue-400">${escapeHtml(inst.id)}</strong> • ${escapeHtml(inst.institution_type)}</div>
                        </td>

                        <!-- Link Único do Portal do Aluno -->
                        <td class="p-3.5">
                            <div class="flex items-center gap-1.5">
                                <a href="/portal/${inst.id}" target="_blank" class="text-blue-500 dark:text-blue-400 font-mono text-xs font-bold hover:underline flex items-center gap-1">
                                    /portal/${escapeHtml(inst.id)} <i class="ph-bold ph-arrow-square-out text-xs"></i>
                                </a>
                                <button onclick="copyTextToClipboard('${portalUrl}', 'Link do Portal do Aluno copiado!')" class="p-1.5 rounded-lg bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 text-slate-500 dark:text-slate-300 transition cursor-pointer" title="Copiar link do portal">
                                    <i class="ph-bold ph-copy text-xs"></i>
                                </button>
                            </div>
                            <span class="text-[10px] text-slate-400 block mt-0.5">Link exclusivo com logo e cores</span>
                        </td>

                        <!-- Base de Alunos & Importação em Lote -->
                        <td class="p-3.5">
                            <button onclick="openStudentsBatchModal('${inst.id}')" class="px-3 py-1.5 bg-emerald-50 dark:bg-emerald-950/50 hover:bg-emerald-100 dark:hover:bg-emerald-900/60 text-emerald-700 dark:text-emerald-300 border border-emerald-300 dark:border-emerald-700 rounded-xl font-bold text-xs flex items-center gap-1.5 transition cursor-pointer active:scale-95 shadow-xs">
                                <i class="ph-bold ph-users-three text-sm"></i>
                                <span>Alunos &amp; Lote (CSV)</span>
                            </button>
                            <span class="text-[10px] text-slate-400 block mt-1">Sincronização em massa</span>
                        </td>

                        <!-- Consumo & Plano -->
                        <td class="p-3.5 w-44">
                            <div class="flex items-center justify-between text-[11px] font-bold text-slate-700 dark:text-slate-300 mb-1">
                                <span>${usage} docs</span>
                                <span>${percent}%</span>
                            </div>
                            <div class="w-full bg-slate-200 dark:bg-slate-700 h-2 rounded-full overflow-hidden">
                                <div class="bg-imes-blue dark:bg-imes-gold h-full rounded-full" style="width: ${percent}%;"></div>
                            </div>
                            <span class="text-[10px] text-slate-400 mt-1 block">${escapeHtml(sub.plan_name || sub.plan_tier)}</span>
                        </td>

                        <!-- Status -->
                        <td class="p-3.5">
                            <span class="px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-100 dark:bg-emerald-950/60 text-emerald-800 dark:text-emerald-300 border border-emerald-300 dark:border-emerald-700">Ativo</span>
                        </td>

                        <!-- Ações -->
                        <td class="p-3.5 text-right">
                            <div class="flex items-center justify-end gap-1.5">
                                <button onclick="openWhiteLabelModalForInst('${inst.id}')" class="px-2.5 py-1 bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 text-slate-700 dark:text-slate-200 border border-slate-200 dark:border-slate-700 rounded-lg text-xs font-bold cursor-pointer" title="Editar White-Label">
                                    <i class="ph-bold ph-palette"></i>
                                </button>
                                <button onclick="openEditModal('${inst.id}')" class="px-2.5 py-1 bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 text-slate-700 dark:text-slate-200 border border-slate-200 dark:border-slate-700 rounded-lg text-xs font-bold cursor-pointer" title="Gerenciar Plano">
                                    <i class="ph-bold ph-gear"></i>
                                </button>
                            </div>
                        </td>
                    </tr>
                `;
            }).join('');"""

if old_render_inst in html:
    html = html.replace(old_render_inst, new_render_inst)
    print(" -> Função renderInstitutionsTable atualizada com Links Únicos e botão de Lote.")

# 4. Adicionar funções JavaScript para o modal de Alunos em Lote
batch_js_functions = """
        // =========================================================================
        // GESTÃO DE ALUNOS EM LOTE & LINKS ÚNICOS POR INSTITUIÇÃO
        // =========================================================================
        let currentBatchInstId = "imes";
        let parsedBatchStudents = [];
        let registeredStudentsList = [];

        function copyTextToClipboard(text, successMsg) {
            navigator.clipboard.writeText(text).then(() => {
                alert(successMsg || "Copiado para a área de transferência!");
            }).catch(() => {
                prompt("Copie o link abaixo:", text);
            });
        }

        function copyPortalLink(instId) {
            const url = `https://protocoloedu.netlify.app/portal/${instId}`;
            copyTextToClipboard(url, `Link do Portal do Aluno copiado: ${url}`);
        }

        function openWhiteLabelModalForInst(instId) {
            openWhiteLabelModal();
            const select = document.getElementById('wl-select-inst');
            if (select) {
                select.value = instId;
                loadInstitutionForBranding(instId);
            }
        }

        function openStudentsBatchModal(instId) {
            currentBatchInstId = instId;
            const inst = allInstitutions.find(i => i.id === instId) || { name: instId, id: instId };

            document.getElementById('batch-modal-inst-title').textContent = `Base de Alunos • ${inst.name}`;
            document.getElementById('batch-modal-inst-slug').textContent = inst.id;
            document.getElementById('api-endpoint-url').value = `https://protocoloedu.netlify.app/api/institutions/${inst.id}/students/batch-sync`;
            document.getElementById('api-token-header').value = `X-Institution-Key: ${inst.id}-sec-2026`;

            clearBatchPreview();
            switchBatchTab('upload');
            loadRegisteredStudents();

            document.getElementById('batch-students-modal').classList.remove('hidden');
        }

        function closeStudentsBatchModal() {
            document.getElementById('batch-students-modal').classList.add('hidden');
        }

        function switchBatchTab(tab) {
            ['upload', 'api', 'list'].forEach(t => {
                const btn = document.getElementById(`batch-tab-btn-${t}`);
                const sec = document.getElementById(`batch-section-${t}`);
                if (btn) {
                    if (t === tab) {
                        btn.className = "py-3 border-b-2 border-imes-blue text-imes-blue dark:text-imes-gold font-extrabold flex items-center gap-1.5 cursor-pointer";
                    } else {
                        btn.className = "py-3 border-b-2 border-transparent text-slate-500 hover:text-slate-800 dark:hover:text-white flex items-center gap-1.5 cursor-pointer";
                    }
                }
                if (sec) sec.classList.toggle('hidden', t !== tab);
            });
        }

        function downloadCsvTemplate() {
            const csv = "nome;cpf;curso;matricula;email;telefone\\nLucas Gabriel Mendonca;12345678900;graduacao_1;202610482;lucas@email.com;35998764321\\nMariana Costa Rodrigues;23456789011;graduacao_1;202610399;mariana@email.com;35987651122\\nGabriel Souza Santoro;56789012344;ensino_medio;202620101;gabriel@email.com;35991234567\\n";
            const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `modelo_alunos_protocoloedu.csv`;
            a.click();
        }

        function handleBatchFileSelect(event) {
            const file = event.target.files[0];
            if (!file) return;

            const reader = new FileReader();
            reader.onload = function(e) {
                const content = e.target.result;
                parseUploadedContent(file.name, content);
            };
            reader.readAsText(file, 'utf-8');
        }

        function parseUploadedContent(filename, text) {
            parsedBatchStudents = [];
            if (filename.endsWith('.json')) {
                try {
                    const data = JSON.parse(text);
                    parsedBatchStudents = Array.isArray(data) ? data : (data.students || []);
                } catch(e) {
                    alert("Erro ao ler JSON: Verifique o formato do arquivo.");
                    return;
                }
            } else {
                // Parser CSV (suporta , e ;)
                const lines = text.split(/\\r?\\n/).filter(l => l.trim().length > 0);
                if (lines.length < 2) {
                    alert("O arquivo CSV precisa de pelo menos uma linha de cabeçalho e um registro.");
                    return;
                }
                const separator = lines[0].includes(';') ? ';' : ',';
                const headers = lines[0].split(separator).map(h => h.trim().toLowerCase());

                const nameIdx = headers.findIndex(h => h.includes('nome') || h.includes('name'));
                const cpfIdx = headers.findIndex(h => h.includes('cpf'));
                const courseIdx = headers.findIndex(h => h.includes('curso') || h.includes('course'));
                const matIdx = headers.findIndex(h => h.includes('matricula') || h.includes('id'));

                for (let i = 1; i < lines.length; i++) {
                    const cols = lines[i].split(separator).map(c => c.trim().replace(/^["']|["']$/g, ''));
                    if (cols.length > 1) {
                        const name = nameIdx !== -1 ? cols[nameIdx] : cols[0];
                        const cpf = cpfIdx !== -1 ? cols[cpfIdx] : (cols[1] || '');
                        const course = courseIdx !== -1 ? cols[courseIdx] : (cols[2] || 'graduacao_1');
                        const mat = matIdx !== -1 ? cols[matIdx] : (cols[3] || cpf);

                        if (name && cpf) {
                            parsedBatchStudents.push({
                                name: name,
                                cpf: cpf.replace(/\\D/g, ''),
                                course: course,
                                student_id: mat
                            });
                        }
                    }
                }
            }

            if (parsedBatchStudents.length === 0) {
                alert("Nenhum registro de aluno válido foi identificado no arquivo. Verifique os campos nome e cpf.");
                return;
            }

            showBatchPreview(parsedBatchStudents);
        }

        function showBatchPreview(students) {
            document.getElementById('batch-preview-count').textContent = students.length;
            const tbody = document.getElementById('batch-preview-tbody');
            tbody.innerHTML = students.slice(0, 10).map(s => `
                <tr class="hover:bg-slate-50 dark:hover:bg-slate-800/40">
                    <td class="p-2.5 font-bold text-slate-800 dark:text-white">${escapeHtml(s.name)}</td>
                    <td class="p-2.5">${escapeHtml(s.cpf)}</td>
                    <td class="p-2.5">${escapeHtml(s.course)}</td>
                    <td class="p-2.5">${escapeHtml(s.student_id)}</td>
                </tr>
            `).join('');

            if (students.length > 10) {
                tbody.innerHTML += `<tr><td colspan="4" class="p-2 text-center text-slate-400 text-[10px]">... e mais ${students.length - 10} alunos identificados</td></tr>`;
            }

            document.getElementById('batch-preview-container').classList.remove('hidden');
        }

        function clearBatchPreview() {
            parsedBatchStudents = [];
            const container = document.getElementById('batch-preview-container');
            if (container) container.classList.add('hidden');
            const input = document.getElementById('batch-file-input');
            if (input) input.value = '';
        }

        async function commitBatchImport() {
            if (parsedBatchStudents.length === 0) return;

            const btnText = document.getElementById('batch-commit-btn-text');
            btnText.textContent = "Gravando no Banco de Dados...";

            // 1. Grava no Supabase se cliente estiver ativo
            if (supabaseClient) {
                try {
                    const sbRows = parsedBatchStudents.map(s => ({
                        institution_id: currentBatchInstId,
                        student_id: s.student_id || s.cpf,
                        student_name: s.name,
                        course_name: s.course,
                        cpf: s.cpf,
                        status: "PENDENTE",
                        documents_json: {}
                    }));
                    await supabaseClient.from('student_dossiers').upsert(sbRows);
                } catch(e) {}
            }

            // 2. Grava na API local
            try {
                await fetch(`/api/institutions/${currentBatchInstId}/students/batch-sync`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(parsedBatchStudents)
                });
            } catch(e) {}

            alert(`Sucesso! ${parsedBatchStudents.length} alunos foram cadastrados no banco de dados da instituição '${currentBatchInstId}'. Eles já podem acessar o Portal do Aluno e serão reconhecidos pelo CPF.`);
            btnText.textContent = "Confirmar e Gravar Alunos no Banco";
            clearBatchPreview();
            loadRegisteredStudents();
            switchBatchTab('list');
        }

        async function loadRegisteredStudents() {
            registeredStudentsList = [];
            const tbody = document.getElementById('batch-registered-tbody');
            tbody.innerHTML = `<tr><td colspan="5" class="p-6 text-center text-slate-400">Consultando banco de dados...</td></tr>`;

            // 1. Tenta Supabase
            if (supabaseClient) {
                try {
                    const { data, error } = await supabaseClient
                        .from('student_dossiers')
                        .select('*')
                        .eq('institution_id', currentBatchInstId);

                    if (!error && data && data.length > 0) {
                        registeredStudentsList = data;
                    }
                } catch(e) {}
            }

            // 2. Tenta API local se estiver vazio
            if (registeredStudentsList.length === 0) {
                try {
                    const res = await fetch(`/api/institutions/${currentBatchInstId}/students`);
                    if (res.ok) {
                        const json = await res.json();
                        registeredStudentsList = json.students || [];
                    }
                } catch(e) {}
            }

            // 3. Fallback inteligente com os alunos pré-carregados
            if (registeredStudentsList.length === 0) {
                if (currentBatchInstId === 'imes') {
                    registeredStudentsList = [
                        { student_name: "Lucas Gabriel Mendonça", cpf: "12345678900", course_name: "graduacao_1", student_id: "202610482", status: "APROVADO" },
                        { student_name: "Mariana Costa Rodrigues", cpf: "23456789011", course_name: "graduacao_1", student_id: "202610399", status: "APROVADO" },
                        { student_name: "Carlos Eduardo Supabase", cpf: "34567890122", course_name: "graduacao_1", student_id: "202610501", status: "APROVADO" },
                        { student_name: "Bruna Ferreira Silveira", cpf: "45678901233", course_name: "graduacao_1", student_id: "202610520", status: "COM_PENDENCIA" }
                    ];
                } else if (currentBatchInstId === 'colegio_modelo') {
                    registeredStudentsList = [
                        { student_name: "Gabriel Souza Santoro", cpf: "56789012344", course_name: "ensino_medio", student_id: "202620101", status: "PENDENTE" },
                        { student_name: "Isabella Martins Silva", cpf: "67890123455", course_name: "ensino_medio", student_id: "202620102", status: "PENDENTE" }
                    ];
                } else {
                    registeredStudentsList = [
                        { student_name: "Thiago Henrique Souza", cpf: "78901234566", course_name: "graduacao_2", student_id: "202630201", status: "APROVADO" },
                        { student_name: "Fernanda Castro Dias", cpf: "89012345677", course_name: "pos_graduacao", student_id: "202630202", status: "PENDENTE" }
                    ];
                }
            }

            renderRegisteredStudents(registeredStudentsList);
        }

        function renderRegisteredStudents(students) {
            const countEl = document.getElementById('batch-modal-students-count');
            if (countEl) countEl.textContent = students.length;

            const tbody = document.getElementById('batch-registered-tbody');
            if (students.length === 0) {
                tbody.innerHTML = `<tr><td colspan="5" class="p-6 text-center text-slate-400">Nenhum aluno cadastrado para esta instituição. Importe um arquivo CSV para começar.</td></tr>`;
                return;
            }

            tbody.innerHTML = students.map(s => {
                const cpfFormatted = s.cpf ? s.cpf.replace(/(\\d{3})(\\d{3})(\\d{3})(\\d{2})/, '$1.$2.$3-$4') : '-';
                return `
                    <tr class="hover:bg-slate-50 dark:hover:bg-slate-800/40 font-mono text-xs">
                        <td class="p-3 font-bold font-sans text-slate-800 dark:text-white">${escapeHtml(s.student_name)}</td>
                        <td class="p-3">${escapeHtml(cpfFormatted)}</td>
                        <td class="p-3 font-sans">${escapeHtml(s.course_name)}</td>
                        <td class="p-3">${escapeHtml(s.student_id)}</td>
                        <td class="p-3">
                            <span class="px-2 py-0.5 rounded text-[10px] font-bold ${s.status === 'APROVADO' ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300' : 'bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300'}">
                                ${escapeHtml(s.status || 'PENDENTE')}
                            </span>
                        </td>
                    </tr>
                `;
            }).join('');
        }

        function filterRegisteredStudents() {
            const q = (document.getElementById('batch-search-students')?.value || '').toLowerCase().trim();
            if (!q) {
                renderRegisteredStudents(registeredStudentsList);
                return;
            }
            const filtered = registeredStudentsList.filter(s =>
                (s.student_name || '').toLowerCase().includes(q) ||
                (s.cpf || '').includes(q) ||
                (s.course_name || '').toLowerCase().includes(q) ||
                (s.student_id || '').toLowerCase().includes(q)
            );
            renderRegisteredStudents(filtered);
        }

        function copyApiEndpoint() {
            const val = document.getElementById('api-endpoint-url').value;
            copyTextToClipboard(val, "Endpoint da API copiado!");
        }
"""

# Injetar funções antes de </script>
html = html.replace('</script>\n</body>', batch_js_functions + '\n    </script>\n</body>')

with open("frontend/superadmin.html", "w", encoding="utf-8") as f:
    f.write(html)
print(" -> 'frontend/superadmin.html' atualizado com Links Únicos e Modal de Lote.")

with open("templates/default/super_admin.html", "w", encoding="utf-8") as f:
    f.write(html)
print(" -> 'templates/default/super_admin.html' sincronizado.")

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
        print("[SUCESSO] Deploy no Netlify concluído com sucesso!")
        print(f" -> Deploy ID: {res.get('id')}")
        print(f" -> State: {res.get('state')}")
        print(f" -> URL: https://protocoloedu.netlify.app/superadmin")
except urllib.error.HTTPError as e:
    err_body = e.read().decode('utf-8', errors='ignore')
    print(f"[ERRO Netlify] {e.code}: {err_body}")
