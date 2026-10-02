# -*- coding: utf-8 -*-
"""
Ponto de Entrada Principal da Aplicação ProtocoloEdu (SaaS Multi-Institucional).
Inicializa o servidor Web, APIs de Compliance MEC e Portais Integrados.
"""

import os
import sys
import logging

# Carrega a aplicação oficial e logger do api_server
from api_server import app, logger

def main():
    port = int(os.environ.get("PORT", 8080))
    host = os.environ.get("HOST", "127.0.0.1")
    
    print("=" * 70)
    print("🎓 PROTOCOLOEDU - PLATAFORMA DIGITAL DE GESTÃO E PROTOCOLO MEC")
    print(f"🚀 Servidor Web iniciado com sucesso em http://{host}:{port}")
    print(f"👉 Portal do Aluno:       http://localhost:{port}/portal/imes")
    print(f"👉 Central Super Admin:   http://localhost:{port}/superadmin")
    print("=" * 70)
    
    logger.info(f"ProtocoloEdu online na porta {port}.")
    app.run(host=host, port=port, debug=False)

if __name__ == "__main__":
    main()