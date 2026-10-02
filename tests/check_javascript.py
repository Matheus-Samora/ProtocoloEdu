"""Check rendered operational scripts, with isolated synthetic fixtures."""
import audit_bootstrap
import json, re, shutil, subprocess, tempfile
from pathlib import Path
import api_server

node = shutil.which('node')
if not node:
    raise SystemExit('Node.js is required to validate browser script syntax')
results = []
with tempfile.TemporaryDirectory() as folder:
    client = api_server.app.test_client()
    for page in ['/portal/imes', '/admin/imes', '/superadmin']:
        response = client.get(page)
        if response.status_code != 200:
            raise SystemExit('Operational page did not render: ' + page)
        for i, script in enumerate(re.findall(r'<script[^>]*>(.*?)</script>', response.get_data(as_text=True), re.S)):
            if not script.strip():
                continue
            path = Path(folder) / ('script-' + str(len(results)) + '.js')
            path.write_text(script, encoding='utf-8')
            checked = subprocess.run([node, '--check', str(path)], capture_output=True, text=True)
            results.append({'page': page, 'script': i, 'passed': checked.returncode == 0, 'diagnostic': checked.stderr})
(audit_bootstrap.output_dir / 'javascript-syntax.json').write_text(json.dumps(results, indent=2), encoding='utf-8')
print(json.dumps({'scripts': len(results), 'failed': sum(not r['passed'] for r in results)}))
raise SystemExit(any(not r['passed'] for r in results))
