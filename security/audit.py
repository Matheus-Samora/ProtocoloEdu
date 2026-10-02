from security.storage import sqlite_db
"""Tamper-evident security events without raw identifiers or request payloads."""
import hashlib,hmac,json,os,sqlite3,time
from pathlib import Path

def audit_key():return hashlib.sha256((os.environ.get('FLASK_SECRET_KEY') or 'local-development-audit').encode()).digest()
def pseudonym(value):return hmac.new(audit_key(),str(value).encode(),hashlib.sha256).hexdigest()
def append_event(action,outcome,actor='anonymous'):
    path=Path(os.environ.get('SECURITY_STATE_DIR','security-state'))/'audit.sqlite'
    path.parent.mkdir(parents=True,exist_ok=True)
    with sqlite_db(path,timeout=15) as db:
        db.execute('CREATE TABLE IF NOT EXISTS events (id INTEGER PRIMARY KEY,payload TEXT NOT NULL,previous TEXT NOT NULL,digest TEXT NOT NULL)')
        db.execute('BEGIN IMMEDIATE')
        row=db.execute('SELECT digest FROM events ORDER BY id DESC LIMIT 1').fetchone()
        previous=row[0] if row else '0'*64
        payload=json.dumps({'time':int(time.time()),'action':action,'outcome':outcome,'actor':pseudonym(actor)},sort_keys=True)
        digest=hmac.new(audit_key(),(previous+payload).encode(),hashlib.sha256).hexdigest()
        db.execute('INSERT INTO events(payload,previous,digest) VALUES (?,?,?)',(payload,previous,digest))
    os.chmod(path,0o600)
def verify_events(path):
    previous='0'*64
    with sqlite_db(path) as db:
        for payload,prior,digest in db.execute('SELECT payload,previous,digest FROM events ORDER BY id'):
            expected=hmac.new(audit_key(),(previous+payload).encode(),hashlib.sha256).hexdigest()
            if prior!=previous or not hmac.compare_digest(expected,digest):return False
            previous=digest
    return True
