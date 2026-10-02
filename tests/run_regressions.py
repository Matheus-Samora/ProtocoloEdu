"""Run isolated regressions; never use live credentials or student data."""
import os, sys, json, pathlib, tempfile, subprocess
root=pathlib.Path(__file__).resolve().parent.parent
out=pathlib.Path(sys.argv[1]).resolve() if len(sys.argv)>1 else root/'test-results'
out.mkdir(parents=True,exist_ok=True)
with tempfile.TemporaryDirectory(prefix='protocoloedu-qa-') as folder:
 work=pathlib.Path(folder)
 for name in ['criteria.json','document_catalog.json','courses_catalog.json']:
  (work/name).write_bytes((root/name).read_bytes())
 institutions={}
 for ident,name,kind in [('imes','Instituto Ficticio QA','FACULDADE'),('auroraqa','Colegio Ficticio QA','COLEGIO')]:
  institutions[ident]={'id':ident,'name':name,'institution_type':kind,'branding':{'portal_title':'Portal Ficticio QA','primary_color':'#1244a0'},'storage':{'provider':'local','base_path':'storage'},'erp':{'erp_type':'mock'},'enabled_courses':['1ª Graduação'],'subscription':{'admin_access_key':'qa-only-secret','monthly_limit':50}}
 (work/'institutions_catalog.json').write_text(json.dumps({'institutions':institutions}),encoding='utf-8')
 env=dict(os.environ,QA_WORKDIR=str(work),QA_OUTPUT_DIR=str(out),PYTHONIOENCODING='utf-8')
 for script in ['audit_app.py','audit_extra.py','run_existing.py','run_security.py','check_javascript.py']:
  completed=subprocess.run([sys.executable,str(root/'tests'/script)],env=env,capture_output=True,text=True)
  (out/(script+'.log')).write_text(completed.stdout+'\n'+completed.stderr,encoding='utf-8')
  if completed.returncode: print('Runner failed: '+script);sys.exit(1)
 totals={'tests':0,'passed':0,'failed':0,'external_integrations':'disabled; not tested against production'}
 for name in ['auditoria-app-resultados.json','auditoria-app-complementar.json','auditoria-testes-existentes.json','security-results.json']:
  value=json.loads((out/name).read_text(encoding='utf-8')); failed=value.get('failed',0)+value.get('errors',0)
  totals['tests']+=value['tests'];totals['failed']+=failed;totals['passed']+=value.get('passed',value['tests']-failed)
 (out/'summary.json').write_text(json.dumps(totals,ensure_ascii=False,indent=2),encoding='utf-8')
 print(json.dumps(totals,ensure_ascii=False));sys.exit(bool(totals['failed']))
