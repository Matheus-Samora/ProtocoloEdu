from security.storage import sqlite_db
"""Encrypted backups with authenticated manifests and safe restore to an empty directory."""
import base64,hashlib,io,json,os,stat,zipfile,sqlite3
from pathlib import Path
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from security.storage import atomic_write,contained,keyring
MAGIC=b'PEDU-BACKUP1\x00'
LIMIT=512*1024*1024

def backup_key():
    key=base64.b64decode(os.environ.get('BACKUP_ENCRYPTION_KEY',''),validate=True)
    if len(key)!=32:raise ValueError('A separate 32-byte backup key is required')
    _,data_keys=keyring()
    if key in data_keys.values():raise ValueError('Backup and data keys must differ')
    return key

def create_backup(root,output):
    root=Path(root).resolve();items={};total=0
    for name in ['data_dossiers','storage','institutions_catalog.json','security-state/audit.sqlite']:
        path=root/name
        if not path.exists():continue
        paths=path.rglob('*') if path.is_dir() else [path]
        for item in paths:
            if item.is_symlink():raise ValueError('Symlinks excluded from backup')
            if not item.is_file():continue
            if not item.resolve().is_relative_to(root):raise ValueError('Backup source escapes root')
            if item.name=='audit.sqlite':
                with sqlite_db('file:'+str(item)+'?mode=ro',uri=True) as source_db, sqlite_db(':memory:') as snapshot:
                    source_db.backup(snapshot);content=snapshot.serialize()
            else:content=item.read_bytes()
            total+=len(content)
            if total>LIMIT or len(items)>=10000:raise ValueError('Backup limit exceeded')
            items[item.relative_to(root).as_posix()]=content
    if not items:raise ValueError('No data to back up')
    manifest={name:{'size':len(data),'sha256':hashlib.sha256(data).hexdigest()} for name,data in items.items()}
    payload=io.BytesIO()
    with zipfile.ZipFile(payload,'w',zipfile.ZIP_DEFLATED) as z:
        z.writestr('manifest.json',json.dumps(manifest,sort_keys=True))
        for name,content in items.items():z.writestr(name,content)
    nonce=os.urandom(12);header=MAGIC+nonce
    atomic_write(output,header+AESGCM(backup_key()).encrypt(nonce,payload.getvalue(),header))
    return len(items)

def restore_backup(archive,destination):
    content=Path(archive).read_bytes()
    if len(content)>LIMIT or not content.startswith(MAGIC):raise ValueError('Invalid backup')
    nonce=content[len(MAGIC):len(MAGIC)+12];header=content[:len(MAGIC)+12]
    clear=AESGCM(backup_key()).decrypt(nonce,content[len(header):],header)
    dest=Path(destination).resolve()
    if dest.exists() and any(dest.iterdir()):raise ValueError('Restore destination must be empty; live data never overwritten')
    restored={}
    with zipfile.ZipFile(io.BytesIO(clear)) as z:
        infos=z.infolist()
        if len(infos)>10001 or sum(i.file_size for i in infos)>LIMIT:raise ValueError('Archive expansion limit exceeded')
        if len({i.filename for i in infos})!=len(infos):raise ValueError('Duplicate ZIP paths')
        for i in infos:
            if '\\' in i.filename or ':' in i.filename or '..' in Path(i.filename).parts or stat.S_ISLNK(i.external_attr>>16):raise ValueError('Unsafe ZIP path')
            contained(dest,i.filename)
        manifest=json.loads(z.read('manifest.json'))
        if set(manifest)!={i.filename for i in infos if i.filename!='manifest.json'}:raise ValueError('Manifest mismatch')
        for name,expected in manifest.items():
            data=z.read(name)
            if len(data)!=expected['size'] or hashlib.sha256(data).hexdigest()!=expected['sha256']:raise ValueError('Backup integrity mismatch')
            restored[name]=data
    # Nothing is written until authentication, path and manifest checks all succeed.
    dest.mkdir(parents=True,exist_ok=True)
    for name,data in restored.items():atomic_write(contained(dest,name),data)
    return len(restored)
