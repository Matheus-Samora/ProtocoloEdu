"""Deployment gates: refuse unsafe production configuration."""
import os
from urllib.parse import urlsplit
from security.storage import production, keyring

def validate_config():
    keyring() # Also validate accidentally malformed keys in development.
    if not production():return
    if len(os.environ.get('FLASK_SECRET_KEY',''))<32:raise RuntimeError('Stable FLASK_SECRET_KEY with 32+ characters required')
    if os.environ.get('COOKIE_SECURE','').lower()!='true':raise RuntimeError('Production cookies require HTTPS')
    from security.accounts import validate_accounts
    validate_accounts()
    master=os.environ.get('SUPER_ADMIN_KEY','')
    if master and not master.startswith(('scrypt:','pbkdf2:')):raise RuntimeError('SUPER_ADMIN_KEY must be a password hash in production')
    if os.environ.get('PROTOCOL_DEMO_MODE','').lower()=='true':raise RuntimeError('Demo mode forbidden in production')
    if not os.environ.get('ALLOWED_HOSTS'):raise RuntimeError('Explicit ALLOWED_HOSTS required')
    backup_key=os.environ.get('BACKUP_ENCRYPTION_KEY')
    if backup_key and backup_key==os.environ.get('DATA_ENCRYPTION_KEY'):raise RuntimeError('Use separate data and backup encryption keys')

def external_processing_allowed():return os.environ.get('ENABLE_EXTERNAL_PROCESSING','').lower()=='true'

def validate_remote_url(value):
    parsed=urlsplit(value or '')
    if parsed.scheme!='https' or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError('Remote endpoint must use HTTPS without embedded credentials')
    if production():
        hosts={x.strip().lower() for x in os.environ.get('OUTBOUND_ALLOWED_HOSTS','').split(',') if x.strip()}
        if parsed.hostname.lower() not in hosts:raise ValueError('Remote endpoint not in deployment allowlist')
    return value
