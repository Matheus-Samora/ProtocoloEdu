from security.storage import sqlite_db
"""Opaque server-side sessions. Cookie contains no CPF, roles or personal data."""
import json, os, secrets, sqlite3, time, re
from pathlib import Path
from flask.sessions import SessionInterface, SessionMixin
from werkzeug.datastructures import CallbackDict
from security.storage import seal, unseal

class ServerSession(CallbackDict, SessionMixin):
    def __init__(self, initial=None, sid=None):
        super().__init__(initial, lambda obj: setattr(obj,'modified',True))
        self.sid=sid or secrets.token_urlsafe(32);self.modified=False

class SQLiteSessionInterface(SessionInterface):
    def __init__(self,path):
        self.path=Path(path);self.path.parent.mkdir(parents=True,exist_ok=True)
        with self.connect() as db: db.execute('CREATE TABLE IF NOT EXISTS sessions (sid TEXT PRIMARY KEY, expires REAL NOT NULL, payload BLOB NOT NULL)')
        os.chmod(self.path,0o600)
    def connect(self): return sqlite_db(self.path, timeout=15)
    def open_session(self,app,request):
        sid=request.cookies.get(self.get_cookie_name(app),'')
        if not re.fullmatch(r'[A-Za-z0-9_-]{43}',sid):return ServerSession()
        with self.connect() as db:
            db.execute('DELETE FROM sessions WHERE expires < ?', (time.time(),))
            row=db.execute('SELECT expires,payload FROM sessions WHERE sid=?',(sid,)).fetchone()
        if not row or row[0]<time.time():return ServerSession()
        try:return ServerSession(json.loads(unseal(row[1],'sessions:'+sid)),sid)
        except Exception:return ServerSession()
    def save_session(self,app,session,response):
        name=self.get_cookie_name(app)
        if not session:
            with self.connect() as db:db.execute('DELETE FROM sessions WHERE sid=?',(session.sid,))
            response.delete_cookie(name,path='/');return
        if not session.modified:return
        expires=time.time()+app.permanent_session_lifetime.total_seconds()
        payload=seal(json.dumps(dict(session)).encode(),'sessions:'+session.sid)
        with self.connect() as db:db.execute('INSERT OR REPLACE INTO sessions VALUES (?,?,?)',(session.sid,expires,payload))
        response.set_cookie(name,session.sid,max_age=int(app.permanent_session_lifetime.total_seconds()),httponly=True,secure=app.config['SESSION_COOKIE_SECURE'],samesite='Strict',path='/')
    def rotate(self,session):
        with self.connect() as db:db.execute('DELETE FROM sessions WHERE sid=?',(session.sid,))
        session.clear();session.sid=secrets.token_urlsafe(32)
