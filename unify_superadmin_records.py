"""
Script de Unificação do Portal de Logs de Envio com o Super Admin SaaS.
Integra todo o controle de registro de entrada e saída (Inbound/Outbound),
dossiês dos alunos, auditoria dos subagentes e despacho ERP SolisGE/WhatsApp
diretamente no Super Admin.
"""

import os
import json
import zipfile
import urllib.request
import urllib.error

print("[*] Iniciando unificação do Portal de Logs de Envio com o Super Admin...")

SUPERADMIN_HTML_PATH = "frontend/superadmin.html"
SUPERADMIN_TEMPLATE_PATH = "templates/default/super_admin.html"
REDIRECTS_PATH = "frontend/_redirects"
ADMIN_HTML_PATH = "frontend/admin.html"

# 1. Atualizar frontend/_redirects
redirects_content = """# Regras de Redirecionamento Oficiais Netlify (ProtocoloEdu)
# Redireciona /admin e /secretaria para a Central Unificada de Registros no Super Admin
/portal       /index.html                     200
/aluno        /index.html                     200
/admin        /superadmin.html                302
/secretaria   /superadmin.html                302
/superadmin   /superadmin.html                200
/super-admin  /superadmin.html                200
/*            /index.html                     200
"""

with open(REDIRECTS_PATH, "w", encoding="utf-8") as f:
    f.write(redirects_content)
print(" -> 'frontend/_redirects' atualizado para apontar /admin para o Super Admin.")

# 2. Atualizar frontend/admin.html com fallback de redirecionamento imediato
admin_redirect_html = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8">
  <meta http-equiv="refresh" content="0; url=/superadmin#records">
  <title>Redirecionando para Central Unificada de Registros • Super Admin</title>
  <script>
    window.location.replace("/superadmin#records");
  </script>
  <style>
    body { font-family: sans-serif; background: #0B132B; color: #E2E8F0; display: flex; align-items: center; justify-content: center; height: 100vh; margin: 0; text-align: center; }
    .box { background: #1B263B; padding: 2rem; border-radius: 1rem; border: 1px solid #334155; max-width: 480px; }
    a { color: #FDB913; font-weight: bold; }
  </style>
</head>
<body>
  <div class="box">
    <h2>Central de Registros Unificada</h2>
    <p>O portal de logs e registros de entrada e saída foi unificado diretamente no <strong>Super Admin</strong>.</p>
    <p>Redirecionando automaticamente...</p>
    <p><a href="/superadmin#records">Clique aqui se não for redirecionado em instantes</a></p>
  </div>
</body>
</html>
"""

with open(ADMIN_HTML_PATH, "w", encoding="utf-8") as f:
    f.write(admin_redirect_html)
print(" -> 'frontend/admin.html' configurado com redirecionamento instantâneo para o Super Admin.")

# 3. Ler o conteúdo atual do superadmin para aproveitar os estilos, modais e scripts
with open(SUPERADMIN_HTML_PATH, "r", encoding="utf-8") as f:
    orig_superadmin = f.read()

print(f" -> 'frontend/superadmin.html' original lido ({len(orig_superadmin)} bytes).")

print("[*] Escrevendo a nova versão unificada do Super Admin...")
