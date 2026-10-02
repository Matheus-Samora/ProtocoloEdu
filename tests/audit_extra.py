import audit_bootstrap
import api_server as api
import pathlib,json,io
from unittest.mock import patch
from agents.models import SubagentRole
from core_dossier_models import StudentDossier,DocumentAuditItem,DossierStatus
from core_criteria_models import DocumentSpecification
from criteria_engine import CriteriaEvaluator
co=api.coordinator;c=api.app.test_client()
c.environ_base['HTTP_X_ADMIN_KEY']=api.SUPER_ADMIN_KEY;out=[]
c.environ_base['HTTP_X_ADMIN_KEY']=api.SUPER_ADMIN_KEY
def case(name,fn):
 try:
  evidence=fn();out.append({'name':name,'status':'PASS','evidence':evidence})
 except Exception as e:out.append({'name':name,'status':'FAIL','evidence':str(e)})
def req(ok,msg):
 if not ok:raise AssertionError(msg)
 return msg
def batch():
 r=c.post('/api/institutions/auroraqa/students/batch-sync',data={'file':(io.BytesIO(b'nome;cpf;matricula\nAluno QA;12345678909;QAEXTRA'),'qa.csv')})
 return req(r.status_code==200,f'CSV HTTP {r.status_code}; DossierRepository possui get_or_create_dossier={hasattr(co.dossier_repo,"get_or_create_dossier")}')
case('CSV persistence method exists and endpoint succeeds',batch)
def honest_records():
 r=c.get('/api/super-admin/inbound-outbound-records').get_json()['records']
 d=next(x for x in r if x['student_id']=='QA100' and x['institution_id']=='imes')
 return req(d['notif_status']!='ENTREGUE' and d['erp_status']!='SINCRONIZADO',f'Sem enviar mensagem ou sincronizar: notif_status={d["notif_status"]}, erp_status={d["erp_status"]}, ai_time={d["ai_time"]}')
case('Record feed must not invent successful external deliveries',honest_records)
case('Health must not claim live Gemini without probing',lambda:req(c.get('/api/super-admin/system/health').get_json()['gemini']['status']!='ONLINE','Gemini declarado ONLINE com credencial ficticia e rede externa desativada'))
def fallback():
 with patch.object(co,'process_and_audit_uploads',side_effect=RuntimeError('QA_INFRA_FAILURE')):
  r=c.post('/api/documents/audit',data={'studentName':'Falha Ficticia QA','studentId':'QAFALLBACK','institution_id':'imes','RG':(io.BytesIO(pathlib.Path('qa-document.png').read_bytes()),'qa.png')}).get_json()
 return req(not r.get('success') or co.dossier_repo.get_dossier('imes','QAFALLBACK') is not None,'Resposta success=True e documento recebido sem persistencia do dossie apos excecao; erro induzido no teste')
case('Unhandled failure must not confirm unpersisted receipt',fallback)
case('Student audit response must not expose admin diagnostic',lambda:req('admin_diagnostic' not in c.post('/api/documents/audit',data={'studentName':'Falha Ficticia QA','studentId':'QADIAG','institution_id':'imes','DESCONHECIDO':(io.BytesIO(b'qa'),'qa.png')}).get_json().get('results',{}).get('DESCONHECIDO',{}),'Caso documento desconhecido: resposta publica verificada'))
png=pathlib.Path('qa-document.png').read_bytes()
ocr=co.orchestrator.registry.get(SubagentRole.COGNITIVE_OCR)
def review_flow():
 verdict={'status':'in_review','is_approved':False,'system_error':True,'reason':'Recebido para revisao QA','admin_diagnostic':'QA_INFRA_DIAGNOSTIC','extracted_data':{}}
 with patch.object(ocr.auditor,'audit_document',return_value=verdict):
  response=c.post('/api/documents/audit',data={'institution_id':'imes','studentId':'QAREVIEW','studentName':'Documento Revisao QA','courseType':'1ª Graduação','RG':(io.BytesIO(png),'qa.png')}).get_json()
 d=co.dossier_repo.get_dossier('imes','QAREVIEW');item=d.documents['RG']
 pathlib.Path('qa-review-response.json').write_text(json.dumps(response,default=str),encoding='utf-8')
 return req(item.status=='in_review' and d.status==DossierStatus.EM_ANALISE,'OCR substituido por falha controlada: fluxo real registra EM_ANALISE')
case('Controlled OCR failure persists review state',review_flow)
def custody_review():
 d=co.dossier_repo.get_dossier('imes','QAREVIEW');item=d.documents['RG']
 return req(bool(item.file_name and item.storage_url),'Estado in_review persistido, mas file_name=None e storage_url=None: secretaria nao tem arquivo para conferir')
case('Human review must retain the received document',custody_review)
def admin_diag():
 r=json.loads(pathlib.Path('qa-review-response.json').read_text(encoding='utf-8'))
 return req(not r['results']['RG'].get('admin_diagnostic'),'Resposta ao aluno inclui admin_diagnostic de infraestrutura; OCR controlado')
case('Public review response hides infrastructure diagnostics',admin_diag)
def archived_rejection():
 spec=co.criteria_catalog.get_document_spec('RG');provider=__import__('adapters.storage.factory',fromlist=['StorageFactory']).StorageFactory.get_provider(co.institutions['imes'])
 media=co.media_pipeline.process(png,'qa.png',spec);info=provider.store_document('Documento Arquivado QA',spec,media)
 d=StudentDossier(institution_id='imes',student_id='QAARCHIVE',student_name='Documento Arquivado QA',course_name='1ª Graduação',documents={'RG':DocumentAuditItem(document_id='RG',display_name='RG',status='rejected',file_name=info.filename)})
 co.dossier_repo.save_dossier(d)
 status=co.check_existing_documents('imes','QAARCHIVE','1ª Graduação')['documentos']['RG']['status']
 return req(status=='rejected','Arquivo presente sobrescreve rejeicao no retorno para aluno: '+status)
case('Archived file must not override rejected audit status',archived_rejection)
def known_courses():
 groups=co.criteria_catalog.get_required_docs_for_course('1ª Graduação')
 return req(bool(groups),'Catalogo de graduacao retorna grupos de documentos obrigatorios')
case('Course criteria catalog resolves real course requirements',known_courses)
summary={'tests':len(out),'passed':sum(x['status']=='PASS' for x in out),'failed':sum(x['status']=='FAIL' for x in out),'results':out,'controlled_ai_boundary':True,'real_ai_accuracy_tested':False}
(audit_bootstrap.output_dir / 'auditoria-app-complementar.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(summary,ensure_ascii=False,indent=2))
