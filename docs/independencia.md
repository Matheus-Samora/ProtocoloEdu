# protocoloEdu — versão independente

Esta instalação foi separada da versão que permanece no Google Cloud. Nenhum comando de alteração, implantação, exclusão ou acesso foi enviado ao servidor anterior.

## Separação aplicada

- Firestore, Drive, Document AI, Vertex AI legado, contas de serviço e comandos do projeto antigo retirados do código distribuído.
- URL fixa do Supabase antigo retirada. Qualquer Supabase exige URL própria e ativação explícita, inclusive no desenvolvimento.
- APIs e coordenador usam um diretório próprio: `private/independent-runtime` por padrão, ou `PROTOCOL_DATA_DIR` absoluto. Catálogo de instituições, dossiês, arquivos, sessões e auditoria não são importados do diretório antigo.
- Somente critérios e catálogos genéricos são copiados na primeira execução. Não há importação de alunos, instituições, `.env`, credenciais ou bancos anteriores.
- O `.env` só é carregado se `PROTOCOL_ENV_FILE` indicar explicitamente um arquivo. Caminhos de contas, chaves e volumes devem pertencer a esta versão.
- Gemini permanece opcional como API de IA; exige `PROTOCOL_GEMINI_API_KEY` nova e `ENABLE_EXTERNAL_PROCESSING=true`. A variável antiga `GEMINI_API_KEY` não é utilizada. O SDK recebe `vertexai=False`, evitando ativação do Google Cloud por variáveis herdadas.
- Integrações externas não são ativadas automaticamente. Compartilhar código e usar GitHub não implica compartilhar banco ou infraestrutura.
- Scripts, telas antigas e bytecode versionados que traziam referências ao ambiente anterior foram retirados. Os arquivos privados locais e o histórico Git foram preservados; não são carregados pela nova instalação por padrão.

## Iniciar instalação própria

1. Criar configuração e chaves exclusivamente desta instalação, usando `.env.example` como lista de parâmetros. Nunca copiar o `.env` ou as credenciais do servidor anterior.
2. Definir `PROTOCOL_DATA_DIR` para um diretório novo e absoluto; se omitido, usar o diretório independente padrão. O catálogo inicial é vazio: cadastrar instituições na gestão desta instalação.
3. Criar a conta administrativa com `tools/create_admin_account.py` e configurar `ADMIN_ACCOUNTS_FILE` com caminho absoluto. Usar também caminhos absolutos para configuração e segredos; a aplicação trabalha dentro do diretório de dados.
4. No PowerShell, definir `$env:PROTOCOL_ENV_FILE = 'CAMINHO_ABSOLUTO_DA_CONFIGURACAO_NOVA'` antes de `python app.py`. Sem arquivo selecionado, são lidas somente variáveis de ambiente explicitamente fornecidas ao processo.
5. Para produção, seguir `docs/security/implantacao.md`, com volumes próprios, HTTPS, cofre e MFA. No Docker, o diretório de dados padrão configurado é `/app/runtime`, que precisa de um volume exclusivo pertencente ao UID 10001.
6. Criar backup usando o diretório de dados independente como `--root`. Não reutilizar backups ou chaves antigas. O histórico de segurança e o checklist continuam aplicáveis; a separação não resolve pendências de implantação/LGPD.

## Verificação

130 testes automatizados aprovados, incluindo 7 testes específicos de independência e os 123 anteriores. Os scripts renderizados das três telas operacionais também passaram na verificação de sintaxe. Provedores externos não foram acessados nesses testes.

Foram verificados: rejeição de provedores Drive/nuvem legados, ausência da URL Supabase anterior, bloqueio de conexão externa sem ativação, não reutilização da chave Gemini anterior, bloqueio da ativação Vertex por configuração herdada e inicialização de diretório novo sem copiar credenciais, configuração ou instituições antigas.

Não foi criado nem modificado nenhum recurso do Google Cloud. A hospedagem final desta versão permanece a definir.
