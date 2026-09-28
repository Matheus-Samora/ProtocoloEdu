import os
import json
import secrets
import hashlib
import hmac
from datetime import datetime, timedelta, timezone
from typing import Optional

# Para usar: pip install bcrypt
import bcrypt

# Importação do seu módulo de criptografia
from env_manager import encrypt_value, decrypt_value


# ---------------------------------------------------------------------------
# BLOCKLIST DE TOKENS (em produção: use Redis ou banco de dados)
# ---------------------------------------------------------------------------
_token_blocklist: set[str] = set()

# ---------------------------------------------------------------------------
# RATE LIMITER SIMPLES (em produção: use Redis com sliding window)
# ---------------------------------------------------------------------------
_failed_attempts: dict[str, list[datetime]] = {}
MAX_ATTEMPTS = 5
LOCKOUT_WINDOW = timedelta(minutes=15)


class SecurityError(Exception):
    """Erro de segurança genérico — não expõe detalhes internos ao cliente."""
    pass


class AuthService:
    def __init__(self, master_key: str):
        if len(master_key) < 32:
            raise ValueError("A master_key deve ter no mínimo 32 caracteres.")
        self.master_key = master_key
        self.token_ttl = timedelta(hours=1)  # Token expira em 1 hora

    # -----------------------------------------------------------------------
    # UTILITÁRIO: Hash de senha com bcrypt
    # -----------------------------------------------------------------------
    @staticmethod
    def hash_password(plain_password: str) -> str:
        """Gera um hash seguro com salt automático."""
        return bcrypt.hashpw(
            plain_password.encode("utf-8"),
            bcrypt.gensalt(rounds=12)  # rounds=12 é o mínimo recomendado
        ).decode("utf-8")

    @staticmethod
    def verify_password(plain_password: str, hashed: str) -> bool:
        """Compara senha com hash de forma segura (timing-safe)."""
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            hashed.encode("utf-8")
        )

    # -----------------------------------------------------------------------
    # RATE LIMITING: Bloqueia IPs/usuários após tentativas excessivas
    # -----------------------------------------------------------------------
    def _check_rate_limit(self, identifier: str) -> None:
        now = datetime.now(timezone.utc)
        attempts = _failed_attempts.get(identifier, [])

        # Remove tentativas fora da janela de tempo
        attempts = [t for t in attempts if now - t < LOCKOUT_WINDOW]
        _failed_attempts[identifier] = attempts

        if len(attempts) >= MAX_ATTEMPTS:
            remaining = LOCKOUT_WINDOW - (now - attempts[0])
            raise SecurityError(
                f"Conta bloqueada temporariamente. Tente novamente em "
                f"{int(remaining.total_seconds() // 60)} minuto(s)."
            )

    def _register_failed_attempt(self, identifier: str) -> None:
        now = datetime.now(timezone.utc)
        _failed_attempts.setdefault(identifier, []).append(now)

    # -----------------------------------------------------------------------
    # LOGIN: Gera token cifrado com expiração e JTI único
    # -----------------------------------------------------------------------
    def login_user(
        self,
        username: str,
        password: str,
        hashed_password_from_db: str,
        user_role: str = "viewer"  # ✅ Role vem do banco, não é hardcoded
    ) -> dict:
        """
        Autentica o usuário e retorna um token cifrado com TTL.
        
        Em produção, `hashed_password_from_db` vem do seu banco de dados.
        """
        try:
            self._check_rate_limit(username)
        except SecurityError as e:
            self._audit_log("LOGIN_BLOCKED", username)
            return {"error": str(e)}

        # ✅ Comparação segura de senha com bcrypt
        if not self.verify_password(password, hashed_password_from_db):
            self._register_failed_attempt(username)
            self._audit_log("LOGIN_FAILED", username)
            # Mensagem genérica — não revela se o usuário existe ou não
            return {"error": "Credenciais inválidas"}

        now = datetime.now(timezone.utc)

        session_data = {
            "jti": secrets.token_hex(16),      # ✅ ID único do token (para revogação)
            "sub": username,                    # Subject
            "role": user_role,                  # ✅ Role do banco de dados
            "iat": now.isoformat(),             # Issued At
            "exp": (now + self.token_ttl).isoformat(),  # ✅ Expiração
        }

        try:
            secure_token = encrypt_value(json.dumps(session_data), self.master_key)
            self._audit_log("LOGIN_SUCCESS", username)
            return {"token": secure_token, "expires_in": int(self.token_ttl.total_seconds())}
        except Exception:
            # ✅ Nunca exponha detalhes de erros internos
            self._audit_log("LOGIN_CRYPTO_ERROR", username)
            return {"error": "Erro interno de segurança"}

    # -----------------------------------------------------------------------
    # VALIDAÇÃO: Decifra e verifica expiração + blocklist
    # -----------------------------------------------------------------------
    def validate_session(self, encrypted_token: str) -> Optional[dict]:
        """
        Valida o token cifrado. Retorna os dados da sessão ou None.
        """
        try:
            plain_json = decrypt_value(encrypted_token, self.master_key)
            session_data = json.loads(plain_json)

            # ✅ Verificar se o token foi revogado
            jti = session_data.get("jti")
            if jti in _token_blocklist:
                self._audit_log("TOKEN_REVOKED", session_data.get("sub", "?"))
                return None

            # ✅ Verificar expiração
            exp = datetime.fromisoformat(session_data["exp"])
            if datetime.now(timezone.utc) > exp:
                self._audit_log("TOKEN_EXPIRED", session_data.get("sub", "?"))
                return None

            return session_data

        except Exception:
            self._audit_log("TOKEN_INVALID", "unknown")
            return None

    # -----------------------------------------------------------------------
    # REVOGAÇÃO: Invalida um token específico (logout)
    # -----------------------------------------------------------------------
    def revoke_token(self, encrypted_token: str) -> bool:
        """
        Adiciona o JTI do token à blocklist (equivale a um logout seguro).
        """
        session = self.validate_session(encrypted_token)
        if session and "jti" in session:
            _token_blocklist.add(session["jti"])
            self._audit_log("TOKEN_REVOKED", session.get("sub", "?"))
            return True
        return False

    # -----------------------------------------------------------------------
    # AUDIT LOG: Registro de eventos de segurança
    # -----------------------------------------------------------------------
    @staticmethod
    def _audit_log(event: str, actor: str) -> None:
        """
        Em produção: grave em arquivo ou sistema de monitoramento (SIEM).
        """
        timestamp = datetime.now(timezone.utc).isoformat()
        print(f"[AUDIT] {timestamp} | {event} | actor={actor}")


# ---------------------------------------------------------------------------
# SIMULAÇÃO DE USO
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    master_key = os.environ.get("MASTER_KEY") or secrets.token_hex(32)
    auth = AuthService(master_key)

    # Simula senha armazenada no banco (já hasheada)
    senha_no_banco = AuthService.hash_password("minha_senha_segura")

    print("=== TESTE DE LOGIN ===")
    resp = auth.login_user(
        username="matheus",
        password="minha_senha_segura",
        hashed_password_from_db=senha_no_banco,
        user_role="editor"
    )

    if "token" in resp:
        token = resp["token"]
        print(f"Token gerado (expira em {resp['expires_in']}s)\n")

        print("=== VALIDANDO SESSÃO ===")
        session = auth.validate_session(token)
        print(f"Sessão válida: {session}\n")

        print("=== LOGOUT (REVOGAÇÃO) ===")
        auth.revoke_token(token)

        print("=== TENTATIVA APÓS LOGOUT ===")
        result = auth.validate_session(token)
        print(f"Resultado esperado (None): {result}")