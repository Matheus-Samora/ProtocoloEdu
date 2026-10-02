import audit_bootstrap
import unittest, json
suite=unittest.defaultTestLoader.loadTestsFromName('test_mcp_integrations')
result=unittest.TextTestRunner(verbosity=2).run(suite)
summary={'tests':result.testsRun,'failed':len(result.failures),'errors':len(result.errors),'failures':[{'test':str(t),'detail':d} for t,d in result.failures+result.errors],'external_calls_blocked':len(audit_bootstrap.blocked)}
(audit_bootstrap.output_dir / 'auditoria-testes-existentes.json').open('w',encoding='utf-8').write(json.dumps(summary,ensure_ascii=False,indent=2))
print(json.dumps({k:v for k,v in summary.items() if k!='failures'}))
