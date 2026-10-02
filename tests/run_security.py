import audit_bootstrap
import unittest,json
suite=unittest.TestSuite([unittest.defaultTestLoader.loadTestsFromName(name) for name in ['test_security','test_independence']])
result=unittest.TextTestRunner(verbosity=2).run(suite)
summary={'tests':result.testsRun,'passed':result.testsRun-len(result.failures)-len(result.errors)-len(result.skipped),'failed':len(result.failures),'errors':len(result.errors),'skipped':len(result.skipped),'details':[{'test':str(t),'detail':d} for t,d in result.failures+result.errors]}
(audit_bootstrap.output_dir/'security-results.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in summary.items() if k!='details'}))
raise SystemExit(not result.wasSuccessful())
