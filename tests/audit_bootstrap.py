import os, socket, sys, pathlib, logging
os.environ['PYTHON_DOTENV_DISABLED']='1'
for k in list(os.environ):
 if any(s in k for s in ('SUPABASE','GEMINI','WHATSAPP','SMTP','SOLIS','TOTVS','SOPHIA','GOOGLE_APPLICATION_CREDENTIALS','GLOBAL_NOTIFICATION','ADMIN_ACCOUNTS','DATA_ENCRYPTION','BACKUP_ENCRYPTION','SECURITY_STATE','PROTOCOL_ENV')): os.environ.pop(k,None)
os.environ['GEMINI_API_KEY']='AIza_FAKE_AUDIT_ONLY'
os.environ['SUPER_ADMIN_KEY']='qa-fixture-master'
os.environ['FLASK_SECRET_KEY']='qa-isolated-session-only'
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
os.chdir(os.environ['QA_WORKDIR'])
logging.disable(logging.CRITICAL)
original_connect=socket.socket.connect
original_dns=socket.getaddrinfo
blocked=[]
def connect(sock,address):
 if isinstance(address,tuple) and str(address[0]) not in ('127.0.0.1','localhost','::1'):
  blocked.append('external_connection'); raise OSError('External connections disabled in isolated QA')
 return original_connect(sock,address)
def dns(host,*args,**kwargs):
 if str(host) not in ('127.0.0.1','localhost','::1','0.0.0.0'):
  blocked.append('external_dns'); raise OSError('External DNS disabled in isolated QA')
 return original_dns(host,*args,**kwargs)
socket.socket.connect=connect
socket.getaddrinfo=dns
try:
 from google.cloud import firestore
 def no_firestore(*args,**kwargs): raise RuntimeError('Cloud disabled in QA')
 firestore.Client=no_firestore
except ImportError: pass

output_dir = pathlib.Path(os.environ['QA_OUTPUT_DIR'])
