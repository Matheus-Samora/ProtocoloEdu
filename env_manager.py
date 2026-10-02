import os
import sys
import secrets
from pathlib import Path
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import padding

# Configurações de caminhos
ENV_FILE_PATH = Path.cwd() / '.env'
ENC_FILE_PATH = Path.cwd() / '.env.enc'

# --- LÓGICA CORE (REUTILIZÁVEL) ---

def generate_key():
    """Gera uma chave segura de 32 bytes (hex)."""
    key = secrets.token_hex(32)
    print('\n⚠️  GUARDE ESTA CHAVE NUM LOCAL SEGURO ⚠️')
    print('-' * 60)
    print(f'MASTER_KEY={key}')
    print('-' * 60)
    return key

def encrypt_value(plain_text, master_key_hex):
    """
    Cifra uma string qualquer usando AES-256-CBC.
    Útil para cifrar tokens, chaves de API ou segredos durante o login.
    """
    if not master_key_hex:
        raise ValueError("MASTER_KEY necessária para cifrar.")

    try:
        # Converter texto para bytes se necessário
        if isinstance(plain_text, str):
            data = plain_text.encode('utf-8')
        else:
            data = plain_text

        key = bytes.fromhex(master_key_hex)
        iv = os.urandom(16)

        # Padding (PKCS7)
        padder = padding.PKCS7(128).padder()
        padded_data = padder.update(data) + padder.finalize()

        # Cifrar
        cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
        encryptor = cipher.encryptor()
        encrypted_data = encryptor.update(padded_data) + encryptor.finalize()

        # Retorna formato IV:Conteúdo (tudo em hex)
        return f"{iv.hex()}:{encrypted_data.hex()}"
    except Exception as e:
        raise RuntimeError(f"Erro na encriptação: {e}")

def decrypt_value(encrypted_string, master_key_hex):
    """
    Decifra uma string no formato IV:ConteúdoHex.
    """
    if not master_key_hex:
        raise ValueError("MASTER_KEY necessária para decifrar.")
    
    try:
        parts = encrypted_string.split(':')
        if len(parts) != 2:
            raise ValueError("Formato inválido (Esperado iv_hex:data_hex).")

        iv = bytes.fromhex(parts[0])
        encrypted_data = bytes.fromhex(parts[1])
        key = bytes.fromhex(master_key_hex)

        # Decifrar
        cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
        decryptor = cipher.decryptor()
        decrypted_padded = decryptor.update(encrypted_data) + decryptor.finalize()

        # Remover Padding
        unpadder = padding.PKCS7(128).unpadder()
        decrypted_data = unpadder.update(decrypted_padded) + unpadder.finalize()
        
        return decrypted_data.decode('utf-8')
    except Exception as e:
        raise RuntimeError(f"Erro na desencriptação: {e}")

# --- LÓGICA DE FICHEIRO (.ENV) ---

def encrypt_env(master_key_hex):
    """Lê o .env e usa a lógica core para gerar o .env.enc"""
    if not ENV_FILE_PATH.exists():
        print('❌ Erro: Ficheiro .env não encontrado.')
        sys.exit(1)

    try:
        with open(ENV_FILE_PATH, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Usa a função core reutilizável
        encrypted_output = encrypt_value(content, master_key_hex)
        
        with open(ENC_FILE_PATH, 'w', encoding='utf-8') as f:
            f.write(encrypted_output)
            
        print(f"✅ Sucesso! .env cifrado em: {ENC_FILE_PATH}")
    except Exception as e:
        print(f"❌ Erro ao processar ficheiro: {e}")
        sys.exit(1)

def load_encrypted_env(master_key_hex):
    """Carrega o .env.enc para memória"""
    # Fallback para dev local
    if not master_key_hex and not ENC_FILE_PATH.exists():
        try:
            from dotenv import load_dotenv
            load_dotenv(dotenv_path=os.environ["PROTOCOL_ENV_FILE"]) if os.environ.get("PROTOCOL_ENV_FILE") else None
            return
        except ImportError:
            return

    if not ENC_FILE_PATH.exists():
        return

    try:
        with open(ENC_FILE_PATH, 'r', encoding='utf-8') as f:
            content = f.read().strip()
        
        # Usa a função core reutilizável
        decrypted_content = decrypt_value(content, master_key_hex)
        _parse_and_set_env(decrypted_content)
    except Exception as e:
        print(f"❌ Falha crítica ao carregar ambiente: {e}")
        sys.exit(1)

def _parse_and_set_env(content):
    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        key, value = line.split('=', 1)
        if key.strip() not in os.environ:
            val = value.strip()
            if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
                val = val[1:-1]
            os.environ[key.strip()] = val

# CLI
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Comandos: gen-key, encrypt <KEY>")
        sys.exit(1)
    
    cmd = sys.argv[1]
    if cmd == "gen-key": generate_key()
    elif cmd == "encrypt": 
        k = sys.argv[2] if len(sys.argv) > 2 else os.environ.get('MASTER_KEY')
        encrypt_env(k)