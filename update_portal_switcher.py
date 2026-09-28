import shutil

with open('frontend/index.html', 'r', encoding='utf-8') as f:
    text = f.read()

target = """                    <!-- Theme Switcher -->
                    <div class="mt-3 sm:mt-4">
                        <label class="switch" title="Alternar Tema">
                            <input checked="true" id="theme-toggle" type="checkbox" />
                            <span class="slider"></span>
                        </label>
                    </div>"""

replacement = """                    <!-- Theme Switcher & Link Institucional -->
                    <div class="mt-3 sm:mt-4 flex items-center justify-center gap-3 flex-wrap">
                        <label class="switch" title="Alternar Tema">
                            <input checked="true" id="theme-toggle" type="checkbox" />
                            <span class="slider"></span>
                        </label>
                        <div class="bg-slate-100 dark:bg-slate-900/80 py-1 px-3 rounded-full border border-slate-200 dark:border-slate-700/60 inline-flex items-center gap-1.5">
                            <i class="ph-bold ph-link text-xs text-blue-500"></i>
                            <select id="quick-inst-switcher" onchange="window.location.href='/portal/' + this.value" class="text-[11px] font-bold bg-transparent text-slate-800 dark:text-white border-none outline-none cursor-pointer font-mono">
                                <option value="imes">Faculdade IMES (/portal/imes)</option>
                                <option value="colegio_modelo">Colégio Santa Maria (/portal/colegio_modelo)</option>
                                <option value="unimetro">Universidade Metropolitana (/portal/unimetro)</option>
                            </select>
                        </div>
                    </div>"""

if target in text:
    text = text.replace(target, replacement)
    print('[*] Seletor institucional adicionado ao cabeçalho do portal.')

old_apply = 'if (b.portal_title) document.title = b.portal_title;'
new_apply = """if (b.portal_title) document.title = b.portal_title;
            const quickSwitcher = document.getElementById('quick-inst-switcher');
            if (quickSwitcher) quickSwitcher.value = inst.id;"""

if old_apply in text:
    text = text.replace(old_apply, new_apply)
    print('[*] Sincronização do switcher no JS atualizada.')

with open('frontend/index.html', 'w', encoding='utf-8') as f:
    f.write(text)

shutil.copy('frontend/index.html', 'templates/default/portal.html')
print('[SUCESSO] Portal do Aluno atualizado e copiado para templates.')
