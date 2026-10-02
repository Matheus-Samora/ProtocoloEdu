# Sanitização do protocoloEdu

02/10/2026. Escopo: somente limpeza do repositório e dos pacotes. Nenhuma implantação no Cloud Run, alteração de DNS, recurso de nuvem ou conta de produção foi realizada.

## Resultado

71 arquivos obsoletos removidos, 9 dependências diretas sem uso retiradas e testes existentes centralizados em `tests/`. O backend ativo e seus módulos de autorização, criptografia, integrações opcionais, processamento, conferência e exportação foram preservados.

Removidos frontends duplicados, simulador showcase, templates de instituições antigas, scripts de alteração automática e geração de telas, utilitários legados sem importação pelo backend, dumps/logs versionados, materiais comerciais antigos, mockups sem uso e configurações de Netlify, Cloudflare, Nginx/Compose e outras entradas antigas. A retirada do showcase é verificada por resposta 404; não foi substituído por funcionalidade simulada.

As telas operacionais são exclusivamente `templates/default/portal.html`, `admin.html` e `super_admin.html`. Recursos locais de CSS e ícones foram mantidos. A imagem da secretaria usa o logo genérico existente em lugar de uma referência antiga a arquivo ausente.

`requirements.txt` passa a apontar para `requirements.lock`, evitando listas divergentes. Nove dependências usadas apenas pelos arquivos retirados foram removidas da lista direta; `psutil` foi declarado para preservar as métricas usadas pelo backend. Isso não é auditoria completa de vulnerabilidades transitivas nem lock com hashes.

O Dockerfile copia explicitamente apenas código, recursos e ferramentas operacionais. Testes, documentação e artefatos de desenvolvimento ficam fora da imagem. O diretório de dados exclusivo permanece; arquivos privados locais, credenciais, catálogo efetivo, documentos e backups não foram apagados e são ignorados pelo Git.

## Verificação

- 130 testes automatizados aprovados, zero falhas, com dados fictícios e provedores externos bloqueados.
- Verificação de sintaxe dos scripts renderizados aprovada.
- Cópia isolada do conteúdo previsto para a imagem iniciou sem acesso à rede: portal, secretaria e gestão responderam 200; showcase retirado respondeu 404.
- Bandit sem achados no escopo de segurança/API/repositório/armazenamento local.
- `git diff --check` aprovado.
- Docker não foi construído nem executado: o executável Docker não está disponível neste ambiente. A verificação da cópia não equivale a um build Docker.

## Publicação e limites

As exclusões são publicadas na branch `codex/security-lgpd`, junto das correções anteriores. A branch principal e o servidor existente não são alterados por esta limpeza. Arquivos removidos continuam recuperáveis no histórico Git; não houve saneamento destrutivo do histórico.

A implantação futura e o domínio próprio permanecem fora deste escopo, conforme pedido. A operação no Cloud Run ainda exige resolver persistência de catálogo, arquivos, sessões e auditoria fora do disco efêmero. Isso não foi implementado ou anunciado como pronto nesta sanitização.

## Inventário dos arquivos retirados

- `.agents/mcp_config.json`
- `.agents/skills/academic-design-system/SKILL.md`
- `.agents/skills/antifraud-document-forensics/SKILL.md`
- `.agents/skills/erp-solis-totvs-integrator/SKILL.md`
- `.agents/skills/generative-analytics-reports/SKILL.md`
- `.agents/skills/mec-compliance-auditor/SKILL.md`
- `Procfile`
- `_redirects`
- `admin.html`
- `admin_web.html`
- `apply_multitenant_upgrade.py`
- `auth_service.py`
- `build_frontend.py`
- `cache_manager.py`
- `chained_updater.py`
- `cliente_solis.py`
- `comparison_logic.py`
- `contexto_geral_imes.txt`
- `data_updater.py`
- `deploy_to_netlify.py`
- `docker-compose.yml`
- `docs_comerciais_e_licitacao/01_PROPOSTA_TECNICA_COMERCIAL.md`
- `docs_comerciais_e_licitacao/02_DECLARACAO_CONFORMIDADE_MEC.md`
- `docs_comerciais_e_licitacao/03_TERMO_TRATAMENTO_DADOS_LGPD_DPA.md`
- `docs_comerciais_e_licitacao/04_MEMORIAL_DESCRITIVO_E_SEGURANCA.md`
- `docs_comerciais_e_licitacao/05_MINUTA_TERMO_PILOTO_POC.md`
- `docs_comerciais_e_licitacao/06_MODELO_ATESTADO_CAPACIDADE_TECNICA.md`
- `docs_comerciais_e_licitacao/CHECKLIST_DO_EMPREENDEDOR.md`
- `env_manager.py`
- `file_organizer.py`
- `fix_portal_logo_and_strict_validation.py`
- `frontend/_redirects`
- `frontend/admin.html`
- `frontend/index.html`
- `frontend/netlify.toml`
- `frontend/static/css/theme.css`
- `frontend/static/images/logo_protocoloedu.jpg`
- `frontend/static/images/mockup_admin_protocoloedu.jpg`
- `frontend/static/images/mockup_mesa_analise.jpg`
- `frontend/static/images/mockup_portal_aluno_mec.jpg`
- `frontend/static/images/mockup_protocoloedu.jpg`
- `frontend/superadmin.html`
- `implement_multitenant_system.py`
- `key_manager.py`
- `log.txt`
- `mcp_config.json`
- `netlify.toml`
- `nginx/conf.d/default.conf`
- `pendencias.json`
- `requirements-legacy.txt`
- `resposta_analise.json`
- `seed_sample_dossiers.py`
- `servidor_web.py`
- `static/css/theme.css`
- `static/images/mockup_admin_protocoloedu.jpg`
- `static/images/mockup_mesa_analise.jpg`
- `static/images/mockup_portal_aluno_mec.jpg`
- `static/images/mockup_protocoloedu.jpg`
- `strictly_separate_portals.py`
- `templates/Solis/login.html`
- `templates/Solis/portal.html`
- `templates/default/showcase.html`
- `templates/default/teste_analise.html`
- `templates/empresa_b/login.html`
- `templates/empresa_b/portal.html`
- `test_portal_isolation.py`
- `unify_superadmin_records.py`
- `update_all_portals.py`
- `update_portal_switcher.py`
- `update_superadmin_multitenant_batch.py`
- `wrangler.jsonc`

Teste movido: `test_mcp_integrations.py` → `tests/test_mcp_integrations.py`.

Dependências diretas retiradas: `Flask-Login`, `bcrypt`, `beautifulsoup4`, `fastapi`, `protobuf`, `python-docx`, `thefuzz`, `uvicorn`, `watchdog`.
