# protocoloEdu

Aplicação Flask independente para recebimento e conferência de documentos educacionais. Esta versão usa recursos próprios e não reutiliza automaticamente o servidor antigo.

## Estrutura

- `api_server.py` e `app.py`: API e entrada local.
- `templates/default/` e `static/`: portal do aluno, secretaria e gestão institucional.
- `services/`, `adapters/`, `media/`, `ai_engine/`, `agents/`, `export/` e `mcp_services/`: módulos usados pelo backend.
- `security/`: autorização, sessões, cifragem, auditoria e recuperação.
- `tools/`: criação de contas, migração e backup.
- `tests/`: regressões com dados fictícios e conexões externas bloqueadas.
- `docs/`: instruções, resultados de auditoria e checklist de segurança.

## Desenvolvimento local

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe tests\run_regressions.py
```

O teste de sintaxe das telas também requer Node.js. `requirements.lock` fixa as dependências diretas; ainda não é um lock transitivo completo com hashes.

Antes de `python app.py`, configure valores próprios conforme `.env.example`. O arquivo de ambiente é carregado apenas quando `PROTOCOL_ENV_FILE` aponta explicitamente para ele. Por padrão, os dados ficam em `private/independent-runtime`; `PROTOCOL_DATA_DIR` permite escolher outro diretório exclusivo. Caminhos de contas e segredos devem ser absolutos. O catálogo inicial é vazio; cadastrar instituições na gestão ou configurar um catálogo próprio no diretório de dados. Não copiar credenciais ou dados da instalação anterior.

O portal exige código individual fornecido pela secretaria. Em produção, contas nominativas e MFA são obrigatórios. Gemini e Supabase exigem ativação e configuração próprias. Não há credenciais padrão nem autenticação pelo CPF sozinho.

## Operação e segurança

Leia [independência](docs/independencia.md), [implantação segura](docs/security/implantacao.md), [checklist](docs/security/checklist.md) e [sanitização](docs/sanitizacao.md). Resultados anteriores são registros datados; a lista de verificação contém pendências reais, não uma certificação.

O Dockerfile inclui somente módulos, recursos e utilitários operacionais. Testes e documentação ficam no repositório, fora da imagem. Nenhuma implantação é realizada automaticamente por estes arquivos; o workflow GitHub executa apenas verificações.

A futura adoção do Cloud Run exige resolver persistência de arquivos, catálogo, sessões e auditoria fora do disco efêmero da instância. Configuração de domínio e implantação estão fora desta limpeza e não foram executadas.

## Limites da validação

Os testes usam dados fictícios e não confirmam funcionamento dos provedores reais, precisão de OCR, conformidade jurídica ou segurança absoluta. Arquivos privados locais são ignorados pelo Git e não entram nos pacotes. Remover código da árvore atual não apaga o histórico do repositório.
