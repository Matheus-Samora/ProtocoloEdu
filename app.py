import os
import sys
from env_manager import load_encrypted_env

# 1. Carregar variáveis seguras ANTES de qualquer outra coisa
try:
    # A chave deve vir do ambiente do servidor (Heroku, Docker, AWS, etc.)
    # Em desenvolvimento local, se não tiver a chave, ele tentará ler o .env normal
    master_key = os.environ.get('MASTER_KEY')
    
    # Se estiver em produção e não tiver chave, é melhor falhar cedo
    if not master_key and os.path.exists('.env.enc'):
         print("❌ ERRO CRÍTICO: MASTER_KEY não encontrada em produção.")
         sys.exit(1)

    load_encrypted_env(master_key)
except Exception as e:
    print(f"Erro fatal ao carregar configurações: {e}")
    sys.exit(1)

# 2. O resto da sua aplicação
print("\n--- Aplicação Python Iniciada ---")
print(f"Base de Dados Host: {os.environ.get('DB_HOST', 'Não definido')}")
print(f"API Key: {'********' if os.environ.get('API_KEY') else 'Não definida'}")

# Exemplo simples de servidor ou lógica
def main():
    print("A executar lógica de negócio com variáveis seguras...")
    # conectar_banco(os.environ['DB_PASS'])

if __name__ == "__main__":
    main()