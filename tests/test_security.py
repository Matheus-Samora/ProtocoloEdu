"""Adversarial regressions against synthetic data only."""
import audit_bootstrap
import base64,hashlib,io,json,os,re,sqlite3,tempfile,time,unittest,zipfile
from pathlib import Path
from unittest.mock import patch
import api_server as api
from core_dossier_models import StudentDossier
from security.storage import sqlite_db,seal,unseal,atomic_write,read_record,write_record,contained,production
from security.backup import create_backup,restore_backup,MAGIC as BACKUP_MAGIC
from security.accounts import authenticate,totp
from security.audit import append_event,verify_events
from security.policy import validate_config
from werkzeug.security import generate_password_hash
from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

KEY=base64.b64encode(b'a'*32).decode();OTHER=base64.b64encode(b'b'*32).decode()
ORIGIN={'Origin':'http://localhost'}

class SecurityTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        self.env=patch.dict(os.environ,{'DATA_ENCRYPTION_KEY':KEY,'DATA_ENCRYPTION_KEY_ID':'v1','DATA_ENCRYPTION_KEYS_JSON':'{}','BACKUP_ENCRYPTION_KEY':OTHER,'PROTOCOL_ENV':'development','SECURITY_STATE_DIR':str(self.root/'state')})
        self.env.start();self.addCleanup(self.env.stop);self.addCleanup(self.temp.cleanup)
        api.rate_limiter.requests.clear()
        self.admin=api.app.test_client();self.admin.environ_base['HTTP_X_ADMIN_KEY']=api.SUPER_ADMIN_KEY
        self.student=api.app.test_client()
        for tenant in ['imes','auroraqa']:
            for sid in ['SEC1','SEC2']:
                api.coordinator.dossier_repo.save_dossier(StudentDossier(institution_id=tenant,student_id=sid,student_name='Pessoa Fictícia '+sid,course_name='1ª Graduação'))
    def access(self,sid='SEC1',tenant='imes'):
        return self.admin.post('/api/admin/student-access',json={'institution_id':tenant,'student_id':sid}).get_json()['access_code']
    def login(self):
        code=self.access();r=self.student.post('/api/student/search',json={'institution_id':'imes','identifier':'SEC1','access_code':code},headers=ORIGIN)
        self.assertEqual(r.status_code,200)
    def check(self,sid='SEC1',tenant='imes',name=None,headers=None):
        return self.student.post('/api/documents/check',json={'institution_id':tenant,'studentId':sid,'studentName':name or 'Pessoa Fictícia '+sid},headers=ORIGIN if headers is None else headers)
    def test_ciphertext_hides_document(self):
        data=seal(b'PRIVATE DOCUMENT','imes:file:A');self.assertNotIn(b'PRIVATE DOCUMENT',data);self.assertEqual(unseal(data,'imes:file:A'),b'PRIVATE DOCUMENT')
    def test_ciphertexts_use_unique_nonce(self):self.assertNotEqual(seal(b'x','imes:x'),seal(b'x','imes:x'))
    def test_wrong_tenant_cannot_decrypt(self):
        with self.assertRaises(InvalidTag):unseal(seal(b'x','imes:x'),'auroraqa:x')
    def test_swapped_file_cannot_decrypt(self):
        with self.assertRaises(InvalidTag):unseal(seal(b'x','imes:file:A'),'imes:file:B')
    def test_tampered_ciphertext_rejected(self):
        data=seal(b'x','imes:x')
        with self.assertRaises(InvalidTag):unseal(data[:-1]+bytes([data[-1]^1]),'imes:x')
    def test_missing_old_key_rejected(self):
        data=seal(b'x','imes:x')
        with patch.dict(os.environ,{'DATA_ENCRYPTION_KEY':OTHER}):
            with self.assertRaises(InvalidTag):unseal(data,'imes:x')
    def test_key_rotation_can_read_old_records(self):
        data=seal(b'x','imes:x')
        with patch.dict(os.environ,{'DATA_ENCRYPTION_KEY_ID':'v2','DATA_ENCRYPTION_KEY':OTHER,'DATA_ENCRYPTION_KEYS_JSON':json.dumps({'v1':KEY})}):self.assertEqual(unseal(data,'imes:x'),b'x')
    def test_production_rejects_plaintext(self):
        with patch.dict(os.environ,{'PROTOCOL_ENV':'production'}):
            with self.assertRaises(ValueError):unseal(b'plain','imes:x')
    def test_atomic_failure_preserves_previous_file(self):
        path=self.root/'record';atomic_write(path,b'old')
        with patch('security.storage.os.replace',side_effect=OSError('test disk failure')):
            with self.assertRaises(OSError):atomic_write(path,b'new')
        self.assertEqual(path.read_bytes(),b'old');self.assertFalse(list(self.root.glob('.pending-*')))
    def test_record_is_encrypted_and_readable(self):
        path=self.root/'r';write_record(path,{'institution_id':'imes','student_id':'SEC1','name':'private'},'imes','SEC1');self.assertNotIn(b'private',path.read_bytes());self.assertEqual(read_record(path,'imes','SEC1')['name'],'private')
    def test_record_identity_mismatch_fails(self):
        path=self.root/'r';write_record(path,{'institution_id':'other','student_id':'SEC1'},'imes','SEC1')
        with self.assertRaises(ValueError):read_record(path,'imes','SEC1')
    def test_directory_traversal_is_rejected(self):
        with self.assertRaises(ValueError):contained(self.root,'../escape')
    def test_invalid_repository_identifier_rejected(self):
        with self.assertRaises(ValueError):api.coordinator.dossier_repo.get_dossier('../other','SEC1')
    def test_storage_dot_folder_rejected(self):
        from adapters.storage.local_storage import sanitize_folder_or_file_name
        with self.assertRaises(ValueError):sanitize_folder_or_file_name('..')
    def test_storage_read_traversal_rejected(self):
        from adapters.storage.local_storage import LocalDiskStorageProvider
        provider=LocalDiskStorageProvider(str(self.root/'storage'),'imes')
        with self.assertRaises(ValueError):provider.get_file_bytes('Pessoa Fictícia','../../credentials.json')
    def test_identifier_alone_does_not_disclose_student(self):self.assertEqual(self.student.post('/api/student/search',json={'institution_id':'imes','identifier':'SEC1'}).status_code,401)
    def test_unknown_and_wrong_codes_are_indistinguishable(self):
        for sid in ['SEC1','UNKNOWN']:
            r=self.student.post('/api/student/search',json={'institution_id':'imes','identifier':sid,'access_code':'wrong'});self.assertEqual(r.status_code,401);self.assertEqual(r.get_json()['error'],'Identificador ou código de acesso inválido.')
    def test_student_authenticated_check_works(self):self.login();self.assertEqual(self.check().status_code,200)
    def test_session_cookie_is_opaque(self):self.login();cookie=self.student.get_cookie('session').value;self.assertRegex(cookie,r'^[A-Za-z0-9_-]{43}$');self.assertNotIn('SEC1',cookie)
    def test_session_database_payload_encrypted(self):
        self.login()
        with api.app.session_interface.connect() as db:row=db.execute('SELECT payload FROM sessions WHERE sid=?',(self.student.get_cookie('session').value,)).fetchone()
        self.assertNotIn(b'SEC1',row[0])
    def test_student_cannot_access_another_student(self):self.login();self.assertEqual(self.check('SEC2').status_code,401)
    def test_student_cannot_access_other_tenant(self):self.login();self.assertEqual(self.check(tenant='auroraqa').status_code,401)
    def test_student_cannot_change_display_identity(self):self.login();self.assertEqual(self.check(name='Another person').status_code,403)
    def test_cookie_mutation_requires_origin(self):self.login();self.assertEqual(self.check(headers={}).status_code,403)
    def test_cookie_mutation_rejects_foreign_origin(self):self.login();self.assertEqual(self.check(headers={'Origin':'https://evil.invalid'}).status_code,403)
    def test_logout_revokes_cookie_on_server(self):
        self.login();old=self.student.get_cookie('session').value
        self.assertEqual(self.student.post('/api/auth/logout',headers=ORIGIN).status_code,200)
        self.student.set_cookie('session',old);self.assertEqual(self.check().status_code,401)
    def test_rotating_student_code_revokes_session(self):self.login();self.access();self.assertEqual(self.check().status_code,401)
    def test_expired_session_is_not_accepted(self):
        self.login()
        with api.app.session_interface.connect() as db:db.execute('UPDATE sessions SET expires=0 WHERE sid=?',(self.student.get_cookie('session').value,))
        self.assertEqual(self.check().status_code,401)
    def test_unauthenticated_cannot_issue_access_code(self):self.assertEqual(self.student.post('/api/admin/student-access',json={'institution_id':'imes','student_id':'SEC1'}).status_code,401)
    def test_production_rejects_legacy_plain_admin_key(self):
        with patch.dict(os.environ,{'PROTOCOL_ENV':'production'}):self.assertFalse(api.valid_key('legacy-key','legacy-key'))
    def test_named_secretary_is_tenant_bound_and_mfa_replay_blocked(self):
        secret=base64.b32encode(b't'*20).decode();registry=self.root/'accounts.json'
        registry.write_text(json.dumps({'secretary':{'role':'secretary','tenant':'imes','password_hash':generate_password_hash('a-safe-fixture-password'),'totp_secret':secret}}))
        with patch.dict(os.environ,{'ADMIN_ACCOUNTS_FILE':str(registry)}):
            otp=totp(secret,int(time.time()//30));c=api.app.test_client()
            r=c.post('/api/auth/login',json={'username':'secretary','institution_id':'imes','key':'a-safe-fixture-password','otp':otp});self.assertEqual(r.status_code,200)
            self.assertEqual(c.get('/api/admin/dossiers?institution_id=imes').status_code,200)
            self.assertEqual(c.get('/api/admin/dossiers?institution_id=auroraqa').status_code,401)
            self.assertEqual(c.get('/api/super-admin/institutions').status_code,401)
            self.assertIsNone(authenticate('secretary','a-safe-fixture-password',otp))
    def test_security_headers_and_private_cache(self):
        r=self.student.get('/api/institutions/imes/profile');self.assertEqual(r.headers['X-Content-Type-Options'],'nosniff');self.assertIn('no-store',r.headers['Cache-Control']);self.assertEqual(r.headers['Referrer-Policy'],'no-referrer')
    def test_csp_blocks_inline_handlers_and_objects(self):
        r=self.student.get('/portal/imes');csp=r.headers['Content-Security-Policy'];self.assertIn("script-src-attr 'none'",csp);self.assertIn("object-src 'none'",csp);self.assertNotIn("'unsafe-inline'",csp.split('script-src ')[1].split(';')[0]);self.assertNotRegex(r.get_data(as_text=True),r'\sonclick=')
    def test_spoofed_forwarding_header_ignored(self):
        with api.app.test_request_context('/',headers={'X-Forwarded-For':'evil'},environ_base={'REMOTE_ADDR':'127.0.0.9'}):self.assertEqual(api.get_client_ip(),'127.0.0.9')
    def test_large_request_rejected(self):
        with patch.dict(api.app.config,{'MAX_CONTENT_LENGTH':64}):self.assertEqual(self.student.post('/api/auth/login',data=b'x'*65,content_type='application/json').status_code,413)
    def test_production_requires_configuration(self):
        with patch.dict(os.environ,{'PROTOCOL_ENV':'production','FLASK_SECRET_KEY':'short'}):
            with self.assertRaises(RuntimeError):validate_config()
    def test_production_https_required_and_hsts_emitted(self):
        with patch.dict(os.environ,{'PROTOCOL_ENV':'production'}):
            self.assertEqual(self.student.get('/api/institutions/imes/profile').status_code,403)
            response=self.student.get('/api/institutions/imes/profile',base_url='https://localhost')
            self.assertEqual(response.status_code,200);self.assertIn('max-age=',response.headers['Strict-Transport-Security'])
    def test_named_account_config_passes_production_gate(self):
        registry=self.root/'master.json';registry.write_text(json.dumps({'master':{'role':'master','password_hash':generate_password_hash('long-fixture-password'),'totp_secret':base64.b32encode(b't'*20).decode()}}))
        with patch.dict(os.environ,{'PROTOCOL_ENV':'production','FLASK_SECRET_KEY':'x'*40,'COOKIE_SECURE':'true','ALLOWED_HOSTS':'localhost','ADMIN_ACCOUNTS_FILE':str(registry),'SUPER_ADMIN_KEY':''}):validate_config()
    def test_untrusted_proxy_cannot_forge_https(self):
        from security.proxy import TrustedProxy
        captured=[]
        app=TrustedProxy(lambda env,start:captured.append(env.copy()) or [])
        app({'REMOTE_ADDR':'198.51.100.1','HTTP_X_FORWARDED_PROTO':'https','wsgi.url_scheme':'http'},lambda *a:None)
        self.assertEqual(captured[0]['wsgi.url_scheme'],'http')
    def test_trusted_proxy_resolves_last_verified_hop(self):
        from security.proxy import TrustedProxy
        captured=[]
        with patch.dict(os.environ,{'TRUSTED_PROXY_IPS':'127.0.0.1'}):app=TrustedProxy(lambda env,start:captured.append(env.copy()) or [])
        app({'REMOTE_ADDR':'127.0.0.1','HTTP_X_FORWARDED_PROTO':'https','HTTP_X_FORWARDED_FOR':'fake, 192.0.2.1','wsgi.url_scheme':'http'},lambda *a:None)
        self.assertEqual(captured[0]['REMOTE_ADDR'],'192.0.2.1');self.assertEqual(captured[0]['wsgi.url_scheme'],'https')
    def backup_fixture(self):
        source=self.root/'source';(source/'data_dossiers/imes').mkdir(parents=True);(source/'data_dossiers/imes/s.json').write_bytes(b'private data');archive=self.root/'backup.enc';create_backup(source,archive);return source,archive
    def test_backup_encrypted_roundtrip(self):
        source,archive=self.backup_fixture();self.assertNotIn(b'private data',archive.read_bytes());dest=self.root/'restored';self.assertEqual(restore_backup(archive,dest),1);self.assertEqual((dest/'data_dossiers/imes/s.json').read_bytes(),b'private data')
    def test_tampered_backup_writes_nothing(self):
        _,archive=self.backup_fixture();data=archive.read_bytes();archive.write_bytes(data[:-1]+bytes([data[-1]^1]));dest=self.root/'restored'
        with self.assertRaises(InvalidTag):restore_backup(archive,dest)
        self.assertFalse(dest.exists())
    def test_wrong_backup_key_rejected(self):
        _,archive=self.backup_fixture()
        with patch.dict(os.environ,{'BACKUP_ENCRYPTION_KEY':base64.b64encode(b'c'*32).decode()}):
            with self.assertRaises(InvalidTag):restore_backup(archive,self.root/'restored')
    def test_restore_never_overwrites_live_data(self):
        _,archive=self.backup_fixture();dest=self.root/'live';dest.mkdir();(dest/'existing').write_bytes(b'keep')
        with self.assertRaises(ValueError):restore_backup(archive,dest)
        self.assertEqual((dest/'existing').read_bytes(),b'keep')
    def test_backup_zip_slip_rejected_before_writing(self):
        buffer=io.BytesIO()
        with zipfile.ZipFile(buffer,'w') as z:z.writestr('../escape',b'x');z.writestr('manifest.json','{}')
        nonce=b'n'*12;header=BACKUP_MAGIC+nonce;archive=self.root/'evil.enc';archive.write_bytes(header+AESGCM(base64.b64decode(OTHER)).encrypt(nonce,buffer.getvalue(),header))
        with self.assertRaises(ValueError):restore_backup(archive,self.root/'dest')
        self.assertFalse((self.root/'dest').exists())
    def test_same_backup_and_data_key_rejected(self):
        source,_=self.backup_fixture()
        with patch.dict(os.environ,{'BACKUP_ENCRYPTION_KEY':KEY}):
            with self.assertRaises(ValueError):create_backup(source,self.root/'invalid.enc')
    def test_security_log_detects_tampering(self):
        append_event('login','401','SEC1');path=self.root/'state/audit.sqlite';self.assertTrue(verify_events(path))
        with sqlite_db(path) as db:db.execute("UPDATE events SET payload='{}'")
        self.assertFalse(verify_events(path))
    def test_security_log_does_not_store_raw_identifier(self):
        append_event('login','401','PRIVATE-IDENTIFIER');self.assertNotIn(b'PRIVATE-IDENTIFIER',(self.root/'state/audit.sqlite').read_bytes())
    def test_export_excludes_access_hash(self):
        self.access();r=self.admin.get('/api/admin/export/json?institution_id=imes');self.assertNotIn(b'portal_access_hash',r.data)
