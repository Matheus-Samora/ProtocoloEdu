"""Offline CLI; keys are read from environment, never command-line arguments."""
import argparse,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from security.backup import create_backup,restore_backup
p=argparse.ArgumentParser();sub=p.add_subparsers(dest='action',required=True)
c=sub.add_parser('create');c.add_argument('--root',required=True);c.add_argument('--output',required=True)
r=sub.add_parser('restore');r.add_argument('--archive',required=True);r.add_argument('--destination',required=True)
a=p.parse_args()
if a.action=='create':print('Encrypted backup files:',create_backup(a.root,a.output))
else:print('Verified restored files:',restore_backup(a.archive,a.destination))
