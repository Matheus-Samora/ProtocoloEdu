from security.storage import sqlite_db
"""Named administrative accounts, tenant roles and replay-resistant TOTP."""
import base64,hashlib,hmac,json,os,sqlite3,struct,time
from pathlib import Path
from werkzeug.security import check_password_hash

def accounts():
    filename=os.environ.get('ADMIN_ACCOUNTS_FILE')
    if not filename:return {}
    data=json.loads(Path(filename).read_text(encoding='utf-8'))
    if not isinstance(data,dict):raise ValueError('Invalid account registry')
    return data

def validate_accounts():
    data=accounts()
    if not data or not any(row.get('role')=='master' for row in data.values()):raise RuntimeError('A named master account is required')
    for name,row in data.items():
        if not row.get('password_hash','').startswith(('scrypt:','pbkdf2:')):raise RuntimeError('Administrative passwords must be hashed')
        if row.get('role') not in {'master','secretary'}:raise RuntimeError('Invalid account role')
        if row['role']=='secretary' and not row.get('tenant'):raise RuntimeError('Secretary account requires a tenant')
        if len(base64.b32decode(row.get('totp_secret',''),casefold=True))<20:raise RuntimeError('Every administrative account requires MFA')
    return data

def totp(secret,counter):
    raw=hmac.new(base64.b32decode(secret,casefold=True),struct.pack('>Q',counter),hashlib.sha1).digest()
    offset=raw[-1]&15;value=(struct.unpack('>I',raw[offset:offset+4])[0]&0x7fffffff)%1000000
    return str(value).zfill(6)

def authenticate(username,password,code):
    row=accounts().get(username)
    if not row or not isinstance(password,str) or len(password)>512:return None
    if not check_password_hash(row.get('password_hash',''),password):return None
    if row.get('totp_secret'):
        if not isinstance(code,str) or len(code)!=6:return None
        counter=int(time.time()//30)
        slot=next((i for i in (counter-1,counter,counter+1) if hmac.compare_digest(totp(row['totp_secret'],i),code)),None)
        if slot is None:return None
        path=Path(os.environ.get('SECURITY_STATE_DIR','security-state'))/'mfa.sqlite';path.parent.mkdir(parents=True,exist_ok=True)
        try:
            with sqlite_db(path,timeout=15) as db:
                db.execute('CREATE TABLE IF NOT EXISTS used (username TEXT,counter INTEGER,PRIMARY KEY(username,counter))')
                db.execute('DELETE FROM used WHERE counter < ?', (counter-3,))
                db.execute('INSERT INTO used VALUES (?,?)',(hashlib.sha256(username.encode()).hexdigest(),slot))
        except sqlite3.IntegrityError:return None
    return row

def identity_version(row):return hashlib.sha256(json.dumps(row,sort_keys=True).encode()).hexdigest()
def current_identity(session):
    row=accounts().get(session.get('principal'))
    if not row or session.get('account_version')!=identity_version(row):return None
    return row
