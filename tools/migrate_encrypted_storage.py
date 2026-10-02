"""Copy local data into an encrypted staging tree. Never overwrite source data."""
import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from security.storage import contained,read_record,write_record,read_document,write_document,keyring,atomic_write
p=argparse.ArgumentParser();p.add_argument('--source',required=True);p.add_argument('--destination',required=True);a=p.parse_args()
source=Path(a.source).resolve();destination=Path(a.destination).resolve();active,keys=keyring()
if active not in keys:raise SystemExit('Configure data encryption keys before migration')
if source==destination or destination.is_relative_to(source):raise SystemExit('Use a separate staging directory')
if destination.exists() and any(destination.iterdir()):raise SystemExit('Destination must be empty')
# Run while application is offline. Development mode permits reading legacy plaintext.
for path in (source/'data_dossiers').glob('*/*.json'):
 if path.is_symlink() or path.parent.is_symlink():raise SystemExit('Symlinks cannot be migrated')
 contained(source,path.relative_to(source))
 tenant=path.parent.name;student=path.stem
 write_record(contained(destination,'data_dossiers',tenant,path.name),read_record(path,tenant,student),tenant,student)
for path in (source/'storage').rglob('*'):
 if path.is_symlink():raise SystemExit('Symlinks cannot be migrated')
 if path.is_file():
  target=contained(destination,path.relative_to(source));write_document(destination/'storage',target,read_document(source/'storage',path))
catalog=source/'institutions_catalog.json'
if catalog.is_symlink():raise SystemExit('Symlinks cannot be migrated')
if catalog.is_file():atomic_write(destination/'institutions_catalog.json',catalog.read_bytes())
print('Encrypted staging copy created. Validate backup/restore before switching deployment paths.')
