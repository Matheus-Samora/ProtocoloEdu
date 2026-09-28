# -*- coding: utf-8 -*-
"""
Atualizador e Sincronizador das 3 Áreas Oficiais do ProtocoloEdu no Netlify.
Garante que cada uma das 3 áreas possua sua página dedicada, link direto na barra
superior e navegação cruzada transparente.
"""

import os
import zipfile
import requests

def update_portals():
    dist_dir = "frontend"
    
    # =========================================================================
    # 1. ATUALIZA FRONTEND/INDEX.HTML (PORTAL DO ALUNO)
    # =========================================================================
    with open(os.path.join(dist_dir, "index.html"), "r", encoding="utf-8") as f:
        student_html = f.read()

    # Barra de Navegação Unificada no Topo
    nav_student = """  <!-- ========================================================================= -->
  <!-- BARRA DE NAVEGAÇÃO MULTI-PORTAL PROTOCOLOEDU (3 ÁREAS REAIS)                 -->
  <!-- ========================================================================= -->
  <header class="bg-[#0B192C] text-white px-4 md:px-8 py-2.5 flex flex-col md:flex-row items-center justify-between gap-3 border-b border-slate-700 shadow-md sticky top-0 z-50">
    <div class="flex items-center gap-3">
      <a href="/" class="w-9 h-9 rounded-lg bg-blue-600/30 border border-blue-400/40 flex items-center justify-center text-blue-300 font-bold text-base hover:bg-blue-600/50 transition">
        <i class="fa-solid fa-building-columns"></i>
      </a>
      <div>
        <div class="flex items-center gap-2">
          <span class="font-extrabold text-sm tracking-tight text-white uppercase">ProtocoloEdu</span>
          <span class="text-[10px] font-semibold bg-blue-950 text-blue-300 border border-blue-800 px-2 py-0.5 rounded">Portaria MEC 315/2018</span>
        </div>
        <p class="text-[11px] text-slate-400">Sistema Integrado de Protocolo, Acervo Digital & Secretaria Acadêmica</p>
      </div>
    </div>

    <!-- SELETOR DE ÁREAS (3 CAMADAS) -->
    <nav class="flex items-center bg-slate-900/95 p-1 rounded-xl border border-slate-700 text-xs font-semibold shadow-inner">
      <a href="/" class="px-3.5 py-1.5 rounded-lg transition flex items-center gap-2 bg-blue-600 text-white font-bold shadow-sm">
        <i class="fa-solid fa-user-graduate"></i>
        <span>1. Portal do Aluno</span>
      </a>
      <a href="/admin" class="px-3.5 py-1.5 rounded-lg transition flex items-center gap-2 text-slate-300 hover:text-white hover:bg-slate-800/80">
        <i class="fa-solid fa-stamp"></i>
        <span>2. Mesa da Secretaria</span>
      </a>
      <a href="/superadmin" class="px-3.5 py-1.5 rounded-lg transition flex items-center gap-2 text-slate-300 hover:text-white hover:bg-slate-800/80">
        <i class="fa-solid fa-crown text-amber-400"></i>
        <span>3. Super Admin SaaS</span>
      </a>
    </nav>
  </header>"""

    import re
    student_html = re.sub(r'<header class="bg-\[#0B192C\].*?</header>', nav_student, student_html, flags=re.DOTALL)
    
    with open(os.path.join(dist_dir, "index.html"), "w", encoding="utf-8") as f:
        f.write(student_html)
    print(" -> 'frontend/index.html' (Portal do Aluno) atualizado com barra de navegação.")

    # =========================================================================
    # 2. ATUALIZA FRONTEND/ADMIN.HTML (MESA DA SECRETARIA)
    # =========================================================================
    with open(os.path.join(dist_dir, "admin.html"), "r", encoding="utf-8") as f:
        admin_html = f.read()

    nav_admin = """  <!-- ========================================================================= -->
  <!-- BARRA DE NAVEGAÇÃO MULTI-PORTAL PROTOCOLOEDU (3 ÁREAS REAIS)                 -->
  <!-- ========================================================================= -->
  <header class="bg-[#0B192C] text-white px-4 md:px-8 py-2.5 flex flex-col md:flex-row items-center justify-between gap-3 border-b border-slate-700 shadow-md sticky top-0 z-50">
    <div class="flex items-center gap-3">
      <a href="/" class="w-9 h-9 rounded-lg bg-blue-600/30 border border-blue-400/40 flex items-center justify-center text-blue-300 font-bold text-base hover:bg-blue-600/50 transition">
        <i class="fa-solid fa-building-columns"></i>
      </a>
      <div>
        <div class="flex items-center gap-2">
          <span class="font-extrabold text-sm tracking-tight text-white uppercase">ProtocoloEdu</span>
          <span class="text-[10px] font-semibold bg-blue-950 text-blue-300 border border-blue-800 px-2 py-0.5 rounded">Portaria MEC 315/2018</span>
        </div>
        <p class="text-[11px] text-slate-400">Sistema Integrado de Protocolo, Acervo Digital & Secretaria Acadêmica</p>
      </div>
    </div>

    <!-- SELETOR DE ÁREAS (3 CAMADAS) -->
    <nav class="flex items-center bg-slate-900/95 p-1 rounded-xl border border-slate-700 text-xs font-semibold shadow-inner">
      <a href="/" class="px-3.5 py-1.5 rounded-lg transition flex items-center gap-2 text-slate-300 hover:text-white hover:bg-slate-800/80">
        <i class="fa-solid fa-user-graduate"></i>
        <span>1. Portal do Aluno</span>
      </a>
      <a href="/admin" class="px-3.5 py-1.5 rounded-lg transition flex items-center gap-2 bg-blue-600 text-white font-bold shadow-sm">
        <i class="fa-solid fa-stamp"></i>
        <span>2. Mesa da Secretaria</span>
      </a>
      <a href="/superadmin" class="px-3.5 py-1.5 rounded-lg transition flex items-center gap-2 text-slate-300 hover:text-white hover:bg-slate-800/80">
        <i class="fa-solid fa-crown text-amber-400"></i>
        <span>3. Super Admin SaaS</span>
      </a>
    </nav>
  </header>"""

    admin_html = re.sub(r'<header class="bg-\[#0B192C\].*?</header>', nav_admin, admin_html, flags=re.DOTALL)
    
    # Garante que em admin.html a vista view-admin fique SEMPRE visível e view-student fique oculta
    admin_html = admin_html.replace('id="view-student" class="flex-1 flex flex-col p-4 md:p-6 max-w-6xl w-full mx-auto space-y-5"', 'id="view-student" class="flex-1 flex flex-col p-4 md:p-6 max-w-6xl w-full mx-auto space-y-5 hidden"')
    admin_html = admin_html.replace('id="view-admin" class="flex-1 flex flex-col h-[calc(100vh-53px)] overflow-hidden hidden"', 'id="view-admin" class="flex-1 flex flex-col h-[calc(100vh-53px)] overflow-hidden"')

    with open(os.path.join(dist_dir, "admin.html"), "w", encoding="utf-8") as f:
        f.write(admin_html)
    print(" -> 'frontend/admin.html' (Mesa da Secretaria) atualizado com Split-Screen direto.")

    # =========================================================================
    # 3. ATUALIZA FRONTEND/SUPERADMIN.HTML (SUPER ADMIN SAAS)
    # =========================================================================
    with open(os.path.join(dist_dir, "superadmin.html"), "r", encoding="utf-8") as f:
        super_html = f.read()

    # Adiciona FontAwesome se não houver
    if "font-awesome" not in super_html:
        super_html = super_html.replace("</head>", '  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">\n</head>')

    nav_super = """  <!-- BARRA DE NAVEGAÇÃO MULTI-PORTAL PROTOCOLOEDU (3 ÁREAS REAIS) -->
  <header class="bg-[#0B192C] text-white px-4 md:px-8 py-2.5 flex flex-col md:flex-row items-center justify-between gap-3 border-b border-slate-700 shadow-md sticky top-0 z-50">
    <div class="flex items-center gap-3">
      <a href="/" class="w-9 h-9 rounded-lg bg-blue-600/30 border border-blue-400/40 flex items-center justify-center text-blue-300 font-bold text-base hover:bg-blue-600/50 transition">
        <i class="fa-solid fa-building-columns"></i>
      </a>
      <div>
        <div class="flex items-center gap-2">
          <span class="font-extrabold text-sm tracking-tight text-white uppercase">ProtocoloEdu</span>
          <span class="text-[10px] font-semibold bg-amber-500/20 text-amber-300 border border-amber-500/40 px-2 py-0.5 rounded font-mono">Master SaaS</span>
        </div>
        <p class="text-[11px] text-slate-400">Painel Geral do Dono • Franquias, Limites & White-Label</p>
      </div>
    </div>

    <!-- SELETOR DE ÁREAS (3 CAMADAS) -->
    <nav class="flex items-center bg-slate-900/95 p-1 rounded-xl border border-slate-700 text-xs font-semibold shadow-inner">
      <a href="/" class="px-3.5 py-1.5 rounded-lg transition flex items-center gap-2 text-slate-300 hover:text-white hover:bg-slate-800/80">
        <i class="fa-solid fa-user-graduate"></i>
        <span>1. Portal do Aluno</span>
      </a>
      <a href="/admin" class="px-3.5 py-1.5 rounded-lg transition flex items-center gap-2 text-slate-300 hover:text-white hover:bg-slate-800/80">
        <i class="fa-solid fa-stamp"></i>
        <span>2. Mesa da Secretaria</span>
      </a>
      <a href="/superadmin" class="px-3.5 py-1.5 rounded-lg transition flex items-center gap-2 bg-amber-600 text-white font-bold shadow-sm">
        <i class="fa-solid fa-crown text-amber-200"></i>
        <span>3. Super Admin SaaS</span>
      </a>
    </nav>
  </header>
"""
    # Insere o header unificado logo após o <body>
    if "<body" in super_html:
        body_end = super_html.find(">", super_html.find("<body")) + 1
        super_html = super_html[:body_end] + "\n" + nav_super + super_html[body_end:]

    with open(os.path.join(dist_dir, "superadmin.html"), "w", encoding="utf-8") as f:
        f.write(super_html)
    print(" -> 'frontend/superadmin.html' (Super Admin SaaS) atualizado com barra de navegação.")

    # =========================================================================
    # 4. ATUALIZA FRONTEND/_REDIRECTS (ROTAS AMIGÁVEIS DO NETLIFY)
    # =========================================================================
    redirects_content = """# Regras de Redirecionamento Oficiais Netlify (ProtocoloEdu)
/portal       /index.html       200
/aluno        /index.html       200
/admin        /admin.html       200
/secretaria   /admin.html       200
/superadmin   /superadmin.html  200
/super-admin  /superadmin.html  200
/*            /index.html       200
"""
    with open(os.path.join(dist_dir, "_redirects"), "w", encoding="utf-8") as f:
        f.write(redirects_content)
    print(" -> 'frontend/_redirects' atualizado com suporte a todas as URLs amigáveis.")

    # =========================================================================
    # 5. REEMPACOTA PROTOCOLOEDU-FRONTEND.ZIP
    # =========================================================================
    zip_name = "protocoloedu-frontend.zip"
    with zipfile.ZipFile(zip_name, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root_dir_p, dirs, files in os.walk(dist_dir):
            for file_name in files:
                full_path = os.path.join(root_dir_p, file_name)
                rel_path = os.path.relpath(full_path, dist_dir)
                zipf.write(full_path, rel_path)
    print(f" -> Zip '{zip_name}' reconstruído ({os.path.getsize(zip_name)} bytes).")

    # =========================================================================
    # 6. FAZ DEPLOY IMEDIATO NO NETLIFY
    # =========================================================================
    token = "nfp_bb69ariUkrzd2SuUky3Z6iVdfxSVYmz48b42"
    site_id = "69dacb8b-0fd1-4550-be1a-78fb68495fb7"
    print("\n[*] Publicando atualização nas 3 áreas no Netlify...")
    
    with open(zip_name, "rb") as f:
        zip_bytes = f.read()

    deploy_headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/zip"
    }

    deploy_resp = requests.post(
        f"https://api.netlify.com/api/v1/sites/{site_id}/deploys",
        headers=deploy_headers,
        data=zip_bytes,
        timeout=30
    )

    if deploy_resp.status_code in (200, 201):
        deploy_data = deploy_resp.json()
        ssl_url = deploy_data.get("ssl_url") or deploy_data.get("url")
        print("\n" + "=" * 60)
        print(f"[SUCESSO] Todas as 3 áreas estão sincronizadas e ativas!")
        print(f"1. Portal do Aluno:      {ssl_url}/")
        print(f"2. Mesa da Secretaria:   {ssl_url}/admin")
        print(f"3. Super Admin SaaS:     {ssl_url}/superadmin")
        print("=" * 60)
        return True
    else:
        print(f"[ERRO] Falha no deploy: {deploy_resp.status_code} - {deploy_resp.text}")
        return False

if __name__ == "__main__":
    update_portals()
