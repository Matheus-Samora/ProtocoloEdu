"""Create a named admin account registry offline; password is never echoed."""
import argparse,base64,getpass,json,secrets,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from werkzeug.security import generate_password_hash
from security.storage import atomic_write
p=argparse.ArgumentParser();p.add_argument('--file',required=True);p.add_argument('--username',required=True);p.add_argument('--role',choices=['master','secretary'],required=True);p.add_argument('--tenant');a=p.parse_args()
path=Path(a.file)
if a.role=='secretary' and not a.tenant:raise SystemExit('Tenant required')
password=getpass.getpass('Nova senha individual (mínimo 16 caracteres): ')
if len(password)<16:raise SystemExit('Use at least 16 characters')
if password!=getpass.getpass('Confirme a senha: '):raise SystemExit('Passwords differ')
data=json.loads(path.read_text(encoding='utf-8')) if path.exists() else {}
if a.username in data:raise SystemExit('Account exists; use an explicit administrative rotation procedure')
secret=base64.b32encode(secrets.token_bytes(20)).decode()
data[a.username]={'role':a.role,'tenant':a.tenant,'password_hash':generate_password_hash(password),'totp_secret':secret}
atomic_write(path,json.dumps(data).encode())
print('Account registry saved. Enroll this private TOTP secret in your authenticator:',secret)
