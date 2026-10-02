"""Security primitives: authenticated storage, containment and atomic persistence."""
import base64, json, os, re, secrets, tempfile
from pathlib import Path
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives import hashes

MAGIC = b'PEDU-AEAD1\x00'

def production():
    return os.environ.get('PROTOCOL_ENV', 'development').lower() == 'production'

def keyring():
    raw = json.loads(os.environ.get('DATA_ENCRYPTION_KEYS_JSON', '{}'))
    active = os.environ.get('DATA_ENCRYPTION_KEY_ID', 'v1')
    if os.environ.get('DATA_ENCRYPTION_KEY'): raw[active] = os.environ['DATA_ENCRYPTION_KEY']
    keys = {}
    for ident, value in raw.items():
        if not re.fullmatch(r'[A-Za-z0-9_-]{1,32}', ident): raise ValueError('Invalid encryption key ID')
        key = base64.b64decode(value, validate=True)
        if len(key) != 32: raise ValueError('Encryption keys must contain 32 random bytes')
        keys[ident] = key
    if production() and active not in keys: raise RuntimeError('Production requires an active data encryption key')
    return active, keys

def derived_key(master, context):
    tenant = context.split(':', 1)[0]
    return HKDF(algorithm=hashes.SHA256(), length=32, salt=None, info=('protocoloedu:'+tenant).encode()).derive(master)

def seal(content, context):
    active, keys = keyring()
    if active not in keys: return content  # Development only; production keyring raises.
    nonce = secrets.token_bytes(12); ident = active.encode()
    header = MAGIC + bytes([len(ident)]) + ident + nonce
    return header + AESGCM(derived_key(keys[active], context)).encrypt(nonce, content, header + context.encode())

def unseal(content, context):
    if not content.startswith(MAGIC):
        if production(): raise ValueError('Plaintext data must be migrated before production')
        return content
    pos = len(MAGIC); size = content[pos]; pos += 1
    if not 1 <= size <= 32 or len(content) < pos+size+12+16: raise ValueError('Invalid encrypted envelope')
    ident = content[pos:pos+size].decode('ascii'); pos += size
    nonce = content[pos:pos+12]; pos += 12
    _, keys = keyring()
    if ident not in keys: raise ValueError('Encryption key unavailable; refusing fallback')
    return AESGCM(derived_key(keys[ident], context)).decrypt(nonce, content[pos:], content[:pos]+context.encode())

def component(value):
    value = str(value)
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,100}', value): raise ValueError('Invalid identifier')
    return value

def contained(root, *parts):
    root = Path(root).resolve(); target = root.joinpath(*parts).resolve()
    if target == root or not target.is_relative_to(root): raise ValueError('Path outside allowed directory')
    return target

def atomic_write(path, content):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(prefix='.pending-', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(content); stream.flush(); os.fsync(stream.fileno())
        os.chmod(temp, 0o600)
        os.replace(temp, path)
        if os.name != 'nt':
            directory = os.open(path.parent, os.O_RDONLY)
            try: os.fsync(directory)
            finally: os.close(directory)
    finally:
        if os.path.exists(temp): os.unlink(temp)

def record_context(tenant, student):
    return component(tenant)+':dossier:'+component(student)

def file_context(base, path):
    rel = Path(path).resolve().relative_to(Path(base).resolve()).as_posix()
    return rel.split('/',1)[0]+':file:'+rel

def write_record(path, data, tenant, student):
    atomic_write(path, seal(json.dumps(data,ensure_ascii=False).encode('utf-8'), record_context(tenant,student)))

def read_record(path, tenant, student):
    data=json.loads(unseal(Path(path).read_bytes(),record_context(tenant,student)))
    if data.get('institution_id')!=tenant or data.get('student_id')!=student: raise ValueError('Record identity mismatch')
    return data

def write_document(base,path,content): atomic_write(path,seal(content,file_context(base,path)))
def read_document(base,path): return unseal(Path(path).read_bytes(),file_context(base,path))


from contextlib import contextmanager
import sqlite3

@contextmanager
def sqlite_db(path, **options):
    connection=sqlite3.connect(path,**options)
    try:
        with connection:yield connection
    finally:connection.close()
