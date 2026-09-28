# -*- coding: utf-8 -*-
"""
Script de Segregação Estrita das 3 Áreas do ProtocoloEdu.
Remove completamente a barra de navegação compartilhada entre as áreas.
Garante que cada portal funcione como uma aplicação web 100% isolada e independente:
1. Portal do Aluno (/) - Acesso exclusivo do candidato/aluno
2. Mesa da Secretaria (/admin) - Acesso exclusivo da equipe acadêmica
3. Super Admin SaaS (/superadmin) - Acesso exclusivo do proprietário
"""

import os
import re
import zipfile
import requests

def isolate_portals():
    dist_dir = "frontend"

    # =========================================================================
    # 1. PORTAL DO ALUNO (frontend/index.html)
    # =========================================================================
    with open(os.path.join(dist_dir, "index.html"), "r", encoding="utf-8") as f:
        student_html = f.read()

    # Remove o primeiro header (barra multi-portal com links para Secretaria e Super Admin)
    # O header multi-portal possui a classe bg-[#0B192C] e a tag <nav
    student_html = re.sub(
        r'<!-- BARRA DE NAVEGAÇÃO MULTI-PORTAL PROTOCOLOEDU.*?<!-- MAIN APP CONTAINER -->',
        '<!-- MAIN APP CONTAINER -->',
        student_html,
        flags=re.DOTALL
    )
    # Fallback caso o comentário varie
    student_html = re.sub(
        r'<header class="bg-\[#0B192C\].*?</header>\s*(?=<div id="chat-overlay"|<div id="loading-overlay"|<div id="app-container")',
        '',
        student_html,
        flags=re.DOTALL
    )

    with open(os.path.join(dist_dir, "index.html"), "w", encoding="utf-8") as f:
        f.write(student_html)
    print(" -> 'frontend/index.html' isolado: 100% dedicado ao Aluno (sem links de Secretaria/Admin).")

    # =========================================================================
    # 2. MESA DA SECRETARIA (frontend/admin.html)
    # =========================================================================
    with open(os.path.join(dist_dir, "admin.html"), "r", encoding="utf-8") as f:
        admin_html = f.read()

    # Substitui a barra de navegação multi-portal por um cabeçalho dedicado da Secretaria Acadêmica
    header_secretaria = """  <!-- CABEÇALHO DEDICADO E EXCLUSIVO DA SECRETARIA ACADÊMICA -->
  <header class="bg-[#0B192C] text-white px-6 py-3 flex items-center justify-between border-b border-slate-700 shadow-md flex-shrink-0">
    <div class="flex items-center gap-3">
      <div class="w-9 h-9 rounded-lg bg-blue-600/30 border border-blue-400/40 flex items-center justify-center text-blue-300 font-bold text-base shadow-sm">
        <i class="fa-solid fa-stamp"></i>
      </div>
      <div>
        <div class="flex items-center gap-2">
          <span class="font-extrabold text-sm tracking-tight text-white uppercase">Secretaria Geral Acadêmica</span>
          <span class="text-[10px] font-semibold bg-blue-950 text-blue-300 border border-blue-800 px-2 py-0.5 rounded">Mesa de Auditoria MEC 315</span>
        </div>
        <p class="text-[11px] text-slate-400">Ambiente de Conferência e Homologação de Dossiês • ProtocoloEdu</p>
      </div>
    </div>

    <!-- INFORMAÇÕES DA SESSÃO DO ANALISTA -->
    <div class="flex items-center gap-4 text-xs">
      <div class="hidden sm:flex items-center gap-2 bg-slate-900/90 py-1.5 px-3.5 rounded-lg border border-slate-700 text-slate-300 font-mono text-[11px]">
        <i class="fa-solid fa-user-shield text-blue-400"></i>
        <span>Operador: Monica Silveira (Mat. 4091)</span>
      </div>
      <div class="flex items-center gap-2 bg-emerald-950/60 text-emerald-400 border border-emerald-800/60 py-1 px-3 rounded-full font-semibold text-[11px]">
        <span class="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
        <span>Sessão Segura</span>
      </div>
    </div>
  </header>"""

    admin_html = re.sub(
        r'<header class="bg-\[#0B192C\].*?</header>',
        header_secretaria,
        admin_html,
        count=1,
        flags=re.DOTALL
    )

    with open(os.path.join(dist_dir, "admin.html"), "w", encoding="utf-8") as f:
        f.write(admin_html)
    print(" -> 'frontend/admin.html' isolado: 100% dedicado à Mesa de Análise da Secretaria.")

    # =========================================================================
    # 3. SUPER ADMIN SAAS (frontend/superadmin.html)
    # =========================================================================
    with open(os.path.join(dist_dir, "superadmin.html"), "r", encoding="utf-8") as f:
        super_html = f.read()

    # Remove o header multi-portal inserido anteriormente
    super_html = re.sub(
        r'<!-- BARRA DE NAVEGAÇÃO MULTI-PORTAL PROTOCOLOEDU.*?<!-- CABEÇALHO PRINCIPAL DO SUPER ADMIN -->',
        '<!-- CABEÇALHO PRINCIPAL DO SUPER ADMIN -->',
        super_html,
        flags=re.DOTALL
    )
    # Fallback caso a tag varie
    super_html = re.sub(
        r'<header class="bg-\[#0B192C\].*?</header>\s*(?=<header class="bg-\[#0a2351\])',
        '',
        super_html,
        flags=re.DOTALL
    )

    with open(os.path.join(dist_dir, "superadmin.html"), "w", encoding="utf-8") as f:
        f.write(super_html)
    print(" -> 'frontend/superadmin.html' isolado: 100% dedicado ao Dono do SaaS (sem links para Aluno/Secretaria).")

    # =========================================================================
    # 4. REEMPACOTA E FAZ DEPLOY NO NETLIFY
    # =========================================================================
    zip_name = "protocoloedu-frontend.zip"
    with zipfile.ZipFile(zip_name, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for r_dir, dirs, files in os.walk(dist_dir):
            for fname in files:
                f_path = os.path.join(r_dir, fname)
                zipf.write(f_path, os.path.relpath(f_path, dist_dir))
    print(f" -> Zip '{zip_name}' reconstruído ({os.path.getsize(zip_name)} bytes).")

    token = "nfp_bb69ariUkrzd2SuUky3Z6iVdfxSVYmz48b42"
    site_id = "69dacb8b-0fd1-4550-be1a-78fb68495fb7"
    print("\n[*] Publicando áreas estritamente separadas no Netlify...")
    
    with open(zip_name, "rb") as f:
        zip_bytes = f.read()

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/zip"
    }

    r = requests.post(f"https://api.netlify.com/api/v1/sites/{site_id}/deploys", headers=headers, data=zip_bytes, timeout=30)
    if r.status_code in (200, 201):
        print(f"[SUCESSO] Portais 100% segregados e publicados no ar!")
        print(f"1. Portal do Aluno:    https://protocoloedu.netlify.app/")
        print(f"2. Mesa da Secretaria: https://protocoloedu.netlify.app/admin")
        print(f"3. Super Admin SaaS:   https://protocoloedu.netlify.app/superadmin")
    else:
        print(f"[ERRO] {r.status_code} - {r.text}")

if __name__ == "__main__":
    isolate_portals()
