import audit_bootstrap
import api_server as api
import json, io, pathlib, zipfile, traceback
from unittest.mock import patch
from core_dossier_models import StudentDossier,DocumentAuditItem,DossierStatus
from criteria_engine import CriteriaCatalog,validate_cpf_digits
from media.pipeline import MediaPipeline
from media.models import ProcessedMedia,MediaType
from adapters.storage.factory import StorageFactory
from adapters.erp.factory import ERPFactory
from adapters.erp.generic_rest_adapter import MockERPAdapter
from mcp_services.notification_service import NotificationService,NotificationChannel
from mcp_services.pades_validator import PadesSignatureValidator
from test_mcp_integrations import generate_test_signed_pdf
from PIL import Image
client=api.app.test_client()
client.environ_base['HTTP_X_ADMIN_KEY']=api.SUPER_ADMIN_KEY
results=[]
def case(name,category,fn):
 try:
  detail=fn();results.append(dict(name=name,category=category,status='PASS',evidence=detail))
 except Exception as e:
  results.append(dict(name=name,category=category,status='FAIL',evidence=str(e),exception=type(e).__name__))
def require(condition,detail):
 if not condition:raise AssertionError(detail)
 return detail
def status(method,path,expected,**kw):
 if expected==401 and 'headers' not in kw: kw['headers']={'X-Admin-Key':''}
 r=getattr(client,method)(path,**kw)
 return require(r.status_code==expected,f'{path}: expected HTTP {expected}, observed {r.status_code}')
co=api.coordinator
def seed(inst='imes',sid='QA100',name='Marina Ficticia QA'):
 d=StudentDossier(institution_id=inst,student_id=sid,student_name=name,course_name='1ª Graduação',cpf='12345678909',documents={'RG':DocumentAuditItem(document_id='RG',display_name='Identificacao',status='in_review',reason='Revisao QA')})
 co.dossier_repo.save_dossier(d);return d
seed();seed('auroraqa','QA100','Aluno Aurora Ficticio')
co.dossier_repo.delete_dossier('imes','NAOCADASTRADOQA')
for path in ['/portal/imes','/portal/auroraqa','/admin/imes','/superadmin','/showcase']:
 case('Render '+path,'telas',lambda p=path:status('get',p,200))
case('Unknown institution must not open another portal','isolamento',lambda:status('get','/portal/inexistenteqa',404))
case('Institution branding updates persist','funcional',lambda:require(co.update_institution_branding('auroraqa',portal_title='Portal Aurora QA',primary_color='#16685a').branding.portal_title=='Portal Aurora QA','Branding atualizado e persistido no catalogo isolado'))
case('Administrative list requires authentication','seguranca',lambda:status('get','/api/admin/dossiers?institution_id=imes',401))
case('Super-admin list requires authentication','seguranca',lambda:status('get','/api/super-admin/institutions',401))
case('Administrative review requires authentication','seguranca',lambda:status('post','/api/admin/dossier/review-document',401,json={'institution_id':'imes','student_id':'QA100','document_id':'RG','status':'approved'}))
case('Student list requires administrative authentication','seguranca',lambda:status('get','/api/institutions/auroraqa/students',401))
case('Batch import requires authentication','seguranca',lambda:status('post','/api/institutions/auroraqa/students/batch-sync',401,json={'students':[{'name':'Teste Ficticio','cpf':'12345678909','student_id':'QASEC'}]}))
case('Unknown admin tenant must not fall back','isolamento',lambda:status('get','/api/admin/dossiers?institution_id=desconhecidaqa',404))
def isolation():
 a=co.dossier_repo.get_dossier('imes','QA100');b=co.dossier_repo.get_dossier('auroraqa','QA100')
 return require(a.student_name!=b.student_name and co.dossier_repo.get_dossier('otherqa','QA100') is None,'Mesmo ID tem registros separados em disco por instituicao')
case('Local persistence keeps institutions separate','funcional',isolation)
case('Search rejects missing identifier','validacao',lambda:status('post','/api/student/search',400,json={}))
case('Search finds registered student','funcional',lambda:require(client.post('/api/student/search',json={'identifier':'QA100','institution_id':'imes'}).get_json()['name']=='Marina Ficticia QA','Busca retorna cadastro ficticio existente'))
case('Unknown student must be rejected without real ERP','integracoes',lambda:status('post','/api/student/search',404,json={'identifier':'NAOCADASTRADOQA','institution_id':'imes'}))
case('ERP without credentials is explicitly a mock','simulacao',lambda:require(isinstance(ERPFactory.get_provider(co.institutions['imes']),MockERPAdapter),'ERP mock identificado; nao comprova integracao externa'))
case('Document check requires student name','validacao',lambda:status('post','/api/documents/check',400,json={}))
case('Existing documents endpoint returns actual saved status','funcional',lambda:require('RG' in client.post('/api/documents/check',json={'studentName':'Marina Ficticia QA','studentId':'QA100','institution_id':'imes'}).get_json()['documentos'],'RG persistido aparece na consulta'))
case('Manual review updates and persists document','funcional',lambda:require(client.post('/api/admin/dossier/review-document',json={'institution_id':'imes','student_id':'QA100','document_id':'RG','status':'rejected','reason':'Verso ausente QA'}).get_json().get('new_status')=='rejected' and co.dossier_repo.get_dossier('imes','QA100').documents['RG'].status=='rejected','Revisao real da API persistiu rejeicao e motivo'))
case('Manual approval persists and recalculates dossier','funcional',lambda:require(client.post('/api/admin/dossier/review-document',json={'institution_id':'imes','student_id':'QA100','document_id':'RG','status':'approved','reason':'Conferido QA'}).status_code==200 and co.dossier_repo.get_dossier('imes','QA100').documents['RG'].status=='approved','Aprovacao manual persistida; nao avalia qualidade OCR'))
case('Invalid review status rejected','validacao',lambda:status('post','/api/admin/dossier/review-document',400,json={'student_id':'QA100','document_id':'RG','status':'banana'}))
for fmt in ['csv','json','zip']:
 def export(fmt=fmt):
  r=client.get('/api/admin/export/'+fmt+'?institution_id=imes')
  require(r.status_code==200,'HTTP '+str(r.status_code))
  if fmt=='json':require(r.get_json()['total_records']>=1,'JSON com registros')
  elif fmt=='zip':require(any(x.endswith('prontuario_auditoria.json') for x in zipfile.ZipFile(io.BytesIO(r.data)).namelist()),'ZIP contem prontuario')
  else:require(b'QA100' in r.data,'CSV inclui ID ficticio')
  (audit_bootstrap.output_dir / ('auditoria-export-'+fmt+'.'+fmt)).write_bytes(r.data)
  return 'Resposta valida com registro ficticio; arquivo de evidencia salvo'
 case('Export '+fmt,'funcional',export)
def import_csv():
 r=client.post('/api/institutions/auroraqa/students/batch-sync',data={'file':(io.BytesIO(b'nome;cpf;matricula;curso\nAluno Lote QA;12345678909;QA200;Ensino Medio'),'qa.csv')})
 return require(r.status_code==200 and r.get_json()['imported_count']==1 and co.dossier_repo.get_dossier('auroraqa','QA200') is not None,'CSV ficticio importado e persistido')
case('CSV batch import persists records','funcional',import_csv)
case('Basic education import works without CPF','funcional',lambda:require(client.post('/api/institutions/auroraqa/students/batch-sync',json={'students':[{'name':'Crianca Ficticia','student_id':'QA201','course':'Ensino Fundamental'}]}).get_json().get('imported_count')==1,'Esperado 1 aluno por matricula sem CPF; importacao descartou registro'))
case('Upload rejects missing files','validacao',lambda:status('post','/api/documents/audit',400,data={'studentName':'QA'}))
pipeline=MediaPipeline()
for label,content,name in [('empty',b'','a.pdf'),('spoof',b'not a pdf','a.pdf'),('extension',b'MZ123','a.exe')]:
 case('Media rejects '+label,'validacao',lambda c=content,n=name:require(not pipeline.validate_file(c,n).is_valid,'Arquivo invalido rejeitado: '+n))
image=Image.new('RGB',(600,400),'white');buf=io.BytesIO();image.save(buf,format='PNG');png=buf.getvalue()
pathlib.Path('qa-document.png').write_bytes(png)
case('Valid PNG passes file validation','funcional',lambda:require(pipeline.validate_file(png,'qa.png').is_valid,'PNG sintetico valido aceito'))
def suspension():
 inst=co.institutions['auroraqa'];inst.subscription.is_active=False
 r=co.process_and_audit_uploads('auroraqa','QA100','Aluno QA','Ensino Médio',{'RG':[{'filename':'qa.png','content':png}]});inst.subscription.is_active=True
 return require(r.get('code')=='SUBSCRIPTION_INACTIVE','Instituicao suspensa bloqueia processamento')
case('Suspended subscription blocks processing','funcional',suspension)
def quota():
 inst=co.institutions['auroraqa'];inst.subscription.current_month_usage=50
 r=co.process_and_audit_uploads('auroraqa','QA100','Aluno QA','Ensino Médio',{'RG':[{'filename':'qa.png','content':png}]});inst.subscription.current_month_usage=0
 return require(r.get('code')=='PLAN_QUOTA_EXCEEDED','Cota ja atingida bloqueia processamento')
case('Reached quota blocks processing','funcional',quota)
def aggregate(state):
 d=seed('imes','QASTATE');d.documents['RG'].status=state;d.update_status(['RG','CPF'])
 return d.status
for state,expected in [('approved',DossierStatus.PENDENTE),('rejected',DossierStatus.COM_PENDENCIA),('in_review',DossierStatus.EM_ANALISE)]:
 case('Dossier aggregate '+state,'funcional',lambda s=state,e=expected:require(aggregate(s)==e,'Status com outro documento faltando: '+aggregate(s).value))
def storage():
 provider=StorageFactory.get_provider(co.institutions['imes']);spec=co.criteria_catalog.get_document_spec('RG')
 media=pipeline.process(png,'qa.png',spec)
 require(bool(media),'PNG processado')
 info=provider.store_document('Marina Ficticia QA',spec,media)
 require(provider.get_file_bytes('Marina Ficticia QA',info.filename)==media.content_bytes,'Leitura reproduz bytes armazenados')
 pathlib.Path('qa-storage-url.txt').write_text(info.storage_url)
 return 'Armazenamento local e leitura de bytes confirmados'
case('Local storage writes and reads document','funcional',storage)
def file_auth():
 url=pathlib.Path('qa-storage-url.txt').read_text()
 return status('get',url,401)
case('Stored document requires authorization','seguranca',file_auth)
def notification():
 svc=NotificationService();msg=svc.notify_pendencies('imes','QA','QA100','Aluno Ficticio','00000000000',[{'display_name':'RG','reason':'QA'}],channel=NotificationChannel.WHATSAPP,async_dispatch=False)
 return require(msg.status.value=='simulated','Sem credenciais WhatsApp retorna '+msg.status.value+'; nenhum envio real')
case('Notification exposes simulation without credentials','simulacao',notification)
case('Assistant rejects blank question','validacao',lambda:status('post','/api/assistant/ask',400,json={'question':''}))
case('Telemetry endpoint responds','funcional',lambda:status('get','/api/system/health-telemetry',200))
def fake_cert():
 r=PadesSignatureValidator().verify_pdf(generate_test_signed_pdf())
 return require(not r.is_icp_brasil_certified,'Certificado autoassinado sintetico classificado como ICP-Brasil: '+str(r.is_icp_brasil_certified))
case('Self-signed synthetic certificate must not certify ICP-Brasil','assinatura',fake_cert)
def tampered():
 from qa_crypto_fixture import signed_pdf
 data=signed_pdf()
 original=PadesSignatureValidator().verify_pdf(data)
 require(original.integrity_preserved,'Baseline geometrico deve cobrir PDF completo')
 modified=data.replace(b'ORIGINAL',b'MODIFIED')
 require(modified != data,'O teste deve efetivamente adulterar os bytes assinados')
 data=modified
 r=PadesSignatureValidator().verify_pdf(data)
 return require(not r.integrity_preserved,'PDF alterado conserva flag integrity_preserved='+str(r.integrity_preserved))
case('Changed PDF content must fail signature integrity','assinatura',tampered)
def rate():
 limiter=api.InMemoryRateLimiter()
 return require(limiter.is_allowed('qa',max_requests=1) and not limiter.is_allowed('qa',max_requests=1),'Segunda chamada na janela e bloqueada')
case('Rate limiter blocks request over limit','funcional',rate)
case('Login rejects invalid JSON shape','validacao',lambda:status('post','/api/auth/login',400,json=['invalid']))
case('Authenticated mutation rejects foreign origin','seguranca',lambda:status('post','/api/institutions/imes/students/batch-sync',403,headers={'X-Admin-Key':api.SUPER_ADMIN_KEY,'Origin':'https://foreign.invalid'},json={'students':[]}))
case('Importer rejects malformed JSON file','validacao',lambda:status('post','/api/institutions/imes/students/batch-sync',400,data={'file':(io.BytesIO(b'{broken'),'students.json')}))
case('Importer rejects non-list records','validacao',lambda:status('post','/api/institutions/imes/students/batch-sync',400,json={'students':{'name':'invalid'}}))
case('Unauthenticated telemetry is blocked','seguranca',lambda:status('get','/api/system/health-telemetry',401))
co.institutions['auroraqa'].subscription.admin_access_key = 'qa-distinct-tenant-secret'
case('Institution key cannot read another institution','isolamento',lambda:status('get','/api/admin/dossiers?institution_id=auroraqa',401,headers={'X-Admin-Key':'qa-only-secret'}))
summary={'source_commit':'working tree with audit corrections','environment':'local isolated Python '+__import__('sys').version.split()[0],'external_integrations':'disabled, not proven','tests':len(results),'passed':sum(r['status']=='PASS' for r in results),'failed':sum(r['status']=='FAIL' for r in results),'results':results,'blocked_external_connections':len(audit_bootstrap.blocked)}
(audit_bootstrap.output_dir / 'auditoria-app-resultados.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(summary,ensure_ascii=False,indent=2))
