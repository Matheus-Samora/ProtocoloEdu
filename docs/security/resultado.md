# Segurança e LGPD — resultado e limites

02/10/2026 • Branch local `codex/security-lgpd`.

Foram implementadas proteções para impedir consulta de dossiês apenas com CPF, restringir acesso por instituição, exigir contas individuais com MFA em produção, proteger sessões no servidor e cifrar documentos, dossiês e backups locais. Não há garantia de inviolabilidade nem certificação LGPD. A informação de que não existem dados reais em produção permite preparar a implantação antes de receber documentos reais.

## Evidência

- 123 testes automatizados: 123 aprovados, zero falhas. Incluem 49 testes de segurança e 74 regressões anteriores. Integrações externas desativadas; não foram testadas com provedores reais.
- Portal, secretaria e gestão testados no navegador com dados fictícios. O documento cifrado foi aberto e girado na conferência. Um erro de JavaScript na gestão foi encontrado e corrigido.
- Quatro scripts renderizados passaram na verificação de sintaxe do Node.
- Bandit: zero achados no escopo analisado (`security`, API, repositório e armazenamento local). Isso não corresponde a análise completa de todo código legado.
- pip-audit: nenhuma vulnerabilidade conhecida nas 33 dependências diretas instaladas após atualização. A auditoria completa com resolução de dependências transitivas não terminou e foi interrompida; permanece pendência de produção.
- CI, Docker, Supabase, Edge Function remota, HTTPS público, ERP, WhatsApp, Gemini real e recuperação em infraestrutura definitiva não foram executados/validados.

## O que mudou

Sessões usam identificador aleatório e estado no servidor; logout, expiração e mudanças de credencial revogam acesso. Produção recusa configuração sem chave de cifragem, segredo de sessão, hosts explícitos, cookies seguros e contas com MFA. A secretaria emite o código individual do aluno uma vez e guarda apenas seu hash.

AES-256-GCM protege integridade e confidencialidade de conteúdo local com nonce aleatório, chave derivada por instituição e contexto do arquivo. Chaves antigas podem compor keyring de rotação. Escrita atômica evita substituir dados por arquivos parciais. Chaves devem ser guardadas e recuperáveis: código de cifragem não resolve perda da chave.

O backup usa uma chave independente, manifesto de integridade e restauração em destino vazio. Não inclui segredos nem contas; estes exigem recuperação própria. O backup atual é limitado a 512 MB/10.000 arquivos, carrega conteúdo em memória e exige pausa de gravações para consistência global. Caminho customizado de auditoria e provedores remotos exigem cópia adicional.

As telas operacionais usam scripts e fontes locais, CSP com nonce, verificação de origem e cabeçalhos de segurança. CPF não é senha. Conta de aluno e MFA administrativos devem integrar procedimentos institucionais de identificação, recuperação e desligamento.

Credenciais, catálogos e arquivos antes versionados foram removidos do rastreamento atual; arquivos locais foram preservados. Essa mudança não limpa o histórico Git. Validar se algum segredo era real, revogá-lo e planejar saneamento do histórico quando necessário. Não foi realizado force-push ou apagamento permanente de histórico.

As regras Supabase e a retirada da função pública estão preparadas no código; ainda precisam ser aplicadas no ambiente remoto. Serviços externos ficam desativados por padrão em produção até autorização e configuração. O banco remoto e os metadados não recebem automaticamente a cifragem aplicada ao armazenamento local.

## Antes de receber dados reais

Encerrar todos os itens P0 do checklist. Definir hospedagem, HTTPS, ACL, contas reais, cofre de chaves, rotação de credenciais expostas, recuperação de chaves e backups. Executar auditoria transitiva em ambiente limpo, CI e teste de invasão independente. Publicar aviso de privacidade, bases legais, retenção, canal dos titulares e plano de incidentes; avaliar menores e transferências internacionais.

A revisão jurídica depende das finalidades e da operação de cada instituição. Controles técnicos dão suporte a deveres da LGPD; não substituem governança, contratos ou direitos dos titulares. Não presumir consentimento como base única para documentos educacionais.

## Referências oficiais

- [LGPD — texto compilado](https://www.planalto.gov.br/ccivil_03/_ato2015-2018/2018/lei/l13709compilado.htm): princípios, bases legais, direitos e medidas de segurança.
- [ANPD — guia de segurança da informação](https://www.gov.br/anpd/pt-br/centrais-de-conteudo/materiais-educativos-e-publicacoes/guia-orientativo-sobre-seguranca-da-informacao-para-agentes-de-tratamento-de-pequeno-porte): referência para controles e procedimentos.
- [ANPD — crianças e adolescentes](https://www.gov.br/anpd/pt-br/assuntos/noticias/anpd-divulga-enunciado-sobre-o-tratamento-de-dados-pessoais-de-criancas-e-adolescentes): análise do melhor interesse e bases aplicáveis.
- [ANPD — comunicação de incidentes](https://www.gov.br/anpd/pt-br/assuntos/noticias/anpd-aprova-o-regulamento-de-comunicacao-de-incidente-de-seguranca): procedimento deve considerar o regulamento vigente.
- [ANPD — transferências internacionais](https://www.gov.br/anpd/pt-br/acesso-a-informacao/institucional/atos-normativos/regulamentacoes_anpd/resolucao-cd-anpd-no-19-de-23-de-agosto-de-2024): avaliar a contratação dos provedores.
