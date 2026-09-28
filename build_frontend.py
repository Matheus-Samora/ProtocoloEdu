# -*- coding: utf-8 -*-
"""
Script de Construção do Pacote Estático Frontend (JAMstack) para o Netlify.
Desacopla as páginas HTML do Flask/Jinja2 e organiza a pasta 'frontend/' pronta para deploy.
"""

import os
import re
import shutil

def build_frontend():
    root_dir = os.path.dirname(os.path.abspath(__file__))
    dist_dir = os.path.join(root_dir, "frontend")
    os.makedirs(dist_dir, exist_ok=True)
    
    # 1. Copia pasta static
    src_static = os.path.join(root_dir, "static")
    dst_static = os.path.join(dist_dir, "static")
    if os.path.exists(dst_static):
        shutil.rmtree(dst_static)
    shutil.copytree(src_static, dst_static)
    print(" -> Pasta 'static/' copiada com sucesso.")

    # 2. Processa templates/default/portal.html -> frontend/index.html
    portal_src = os.path.join(root_dir, "templates", "default", "portal.html")
    with open(portal_src, "r", encoding="utf-8") as f:
        portal_html = f.read()

    # Substitui Jinja tags por valores canônicos e hidratação dinâmica
    portal_html = portal_html.replace('{{ portal_title or (institution.name ~ " - Portal do Aluno") }}', 'Portal de Envio de Documentos - ProtocoloEdu')
    portal_html = portal_html.replace('{{ institution.branding.logo_url if institution.branding and institution.branding.logo_url else \'/static/images/logo-imes.jpg\' }}', '/static/images/logo-imes.jpg')
    portal_html = portal_html.replace('{{ institution.branding.primary_color if institution.branding and institution.branding.primary_color else "#0a2351" }}', '#0a2351')
    portal_html = portal_html.replace('{{ institution.branding.secondary_color if institution.branding and institution.branding.secondary_color else "#fdb913" }}', '#fdb913')
    portal_html = portal_html.replace('{{ institution.id }}', 'imes')
    portal_html = portal_html.replace('{{ institution.name }}', 'Faculdade IMES')
    portal_html = re.sub(r'\{%\s*if is_suspended\s*%\}.*?\{%\s*endif\s*%\}', '', portal_html, flags=re.DOTALL)

    with open(os.path.join(dist_dir, "index.html"), "w", encoding="utf-8") as f:
        f.write(portal_html)
    print(" -> 'frontend/index.html' gerado com sucesso.")

    # 3. Processa templates/default/admin.html -> frontend/admin.html
    admin_src = os.path.join(root_dir, "templates", "default", "admin.html")
    with open(admin_src, "r", encoding="utf-8") as f:
        admin_html = f.read()

    admin_html = admin_html.replace('{{ portal_title or ("Mesa da Secretaria Acadêmica - " ~ institution.name) }}', 'Mesa da Secretaria Acadêmica - ProtocoloEdu')
    admin_html = admin_html.replace('{{ institution.branding.logo_url if institution.branding and institution.branding.logo_url else \'/static/images/logo-imes.jpg\' }}', '/static/images/logo-imes.jpg')
    admin_html = admin_html.replace('{{ institution.branding.primary_color if institution.branding and institution.branding.primary_color else "#0a2351" }}', '#0a2351')
    admin_html = admin_html.replace('{{ institution.branding.secondary_color if institution.branding and institution.branding.secondary_color else "#fdb913" }}', '#fdb913')
    admin_html = admin_html.replace('{{ institution.id }}', 'imes')
    admin_html = admin_html.replace('{{ institution.name }}', 'Faculdade IMES')
    admin_html = admin_html.replace('{{ subscription.plan_name or "Plano Institucional Pro" }}', 'Plano Profissional MEC')
    admin_html = admin_html.replace('{{ subscription.monthly_limit or 500 }}', '500')
    admin_html = admin_html.replace('{{ subscription.used_this_month or 0 }}', '0')
    admin_html = admin_html.replace('{{ pct if pct <= 100 else 100 }}', '0')
    admin_html = re.sub(r'\{%\s*set pct.*?\s*%\}', '', admin_html)

    with open(os.path.join(dist_dir, "admin.html"), "w", encoding="utf-8") as f:
        f.write(admin_html)
    print(" -> 'frontend/admin.html' gerado com sucesso.")

    # 4. Processa templates/default/super_admin.html -> frontend/superadmin.html
    super_src = os.path.join(root_dir, "templates", "default", "super_admin.html")
    with open(super_src, "r", encoding="utf-8") as f:
        super_html = f.read()

    with open(os.path.join(dist_dir, "superadmin.html"), "w", encoding="utf-8") as f:
        f.write(super_html)
    print(" -> 'frontend/superadmin.html' gerado com sucesso.")

    # 5. Cria arquivo _redirects para o Netlify
    redirects_content = """# Regras de Redirecionamento e Proxy do Netlify (JAMstack)
# Encaminha chamadas de API para o backend na nuvem
/api/*  https://protocoloedu-api.onrender.com/api/:splat  200

# Rotas amigáveis do frontend
/admin        /admin.html       200
/superadmin   /superadmin.html  200
/*            /index.html       200
"""
    with open(os.path.join(dist_dir, "_redirects"), "w", encoding="utf-8") as f:
        f.write(redirects_content)
    print(" -> 'frontend/_redirects' configurado com proxy de API e rotas SPA.")

    # 6. Cria arquivo netlify.toml
    netlify_toml = """[build]
  publish = "."

[[headers]]
  for = "/*"
  [headers.values]
    X-Frame-Options = "DENY"
    X-XSS-Protection = "1; mode=block"
    X-Content-Type-Options = "nosniff"
    Referrer-Policy = "strict-origin-when-cross-origin"

[[headers]]
  for = "/static/*"
  [headers.values]
    Cache-Control = "public, max-age=31536000, immutable"
"""
    with open(os.path.join(dist_dir, "netlify.toml"), "w", encoding="utf-8") as f:
        f.write(netlify_toml)
    print(" -> 'frontend/netlify.toml' criado com headers de segurança.")

    print("\n[OK] PACOTE 'frontend/' CRIADO COM SUCESSO E PRONTO PARA O NETLIFY!")

if __name__ == "__main__":
    build_frontend()
