import requests

pages = {
    "PORTAL DO ALUNO": "https://protocoloedu.netlify.app/",
    "MESA DA SECRETARIA": "https://protocoloedu.netlify.app/admin",
    "SUPER ADMIN SAAS": "https://protocoloedu.netlify.app/superadmin"
}

for name, url in pages.items():
    r = requests.get(url, timeout=10)
    print(f"=== {name} ===")
    print(f"URL: {url} (HTTP {r.status_code})")
    print("Possui seletor compartilhado:", "SELETOR DE" in r.text or "nav-mesa-secretaria" in r.text)
    print("Possui link para /admin:", "href=\"/admin\"" in r.text or "href='/admin'" in r.text)
    print("Possui link para /superadmin:", "href=\"/superadmin\"" in r.text or "href='/superadmin'" in r.text)
    print()
