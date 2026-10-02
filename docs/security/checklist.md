# Checklist de segurança e LGPD — protocoloEdu

Data: 02/10/2026. Ambiente: prévia local com dados fictícios; usuário informou ausência de dados reais em produção.

Não constitui certificação de conformidade nem garantia contra invasão. Cada pendência precisa de responsável e evidência antes de ser encerrada.

## Identidade e autorização

| ID | Situação | Controle |
|---|---|---|
| SEC-001 | Implementado e testado automaticamente | Código individual do aluno; CPF sozinho não libera o dossiê |
| SEC-002 | Implementado e testado automaticamente | Sessão vinculada ao aluno e à instituição; bloqueio de troca de identidade |
| SEC-003 | Implementado e testado automaticamente | Permissões da secretaria restritas à própria instituição |
| SEC-004 | Implementado e testado automaticamente | Contas nominativas e MFA obrigatórios no modo produção |
| SEC-005 | Implementado e testado automaticamente | TOTP rejeita reutilização do mesmo código |
| SEC-006 | Implementado e testado automaticamente | Alteração ou remoção da conta invalida sessões existentes |
| SEC-007 | Implementado e testado automaticamente | Senhas administrativas armazenadas como hash scrypt/PBKDF2 |
| SEC-008 | Implementado e testado automaticamente | Logout e rotação invalidam a sessão anterior no servidor |
| SEC-009 | Implementado e testado automaticamente | Expiração de sessão de 20 minutos e cookie opaco |
| SEC-010 | Bloqueador antes de dados reais/produção | Criar contas reais, cadastrar autenticadores e guardar códigos de recuperação por procedimento seguro |
| SEC-011 | Melhoria ou avaliação pendente | Implementar recuperação de acesso e MFA com verificação de identidade e auditoria |
| SEC-012 | Bloqueador antes de dados reais/produção | Revisar permissões e separar usuários de teste e de produção |

## Aplicação e navegador

| ID | Situação | Controle |
|---|---|---|
| SEC-013 | Implementado e testado automaticamente | Origem obrigatória nas alterações autenticadas por cookie; bloqueio cross-site |
| SEC-014 | Implementado e testado automaticamente | CSP com nonce e scripts operacionais locais; bloqueio de scripts de terceiros |
| SEC-015 | Implementado e testado automaticamente | Cookies HttpOnly, SameSite Strict e Secure obrigatório em produção |
| SEC-016 | Implementado e testado automaticamente | Cabeçalhos contra framing, MIME sniffing e referência; cache privado desativado |
| SEC-017 | Implementado e testado automaticamente | Rejeição de requisições grandes |
| SEC-018 | Implementado; validação operacional pendente | Limite de arquivos por envio e validação de tipos de conteúdo |
| SEC-019 | Implementado e testado automaticamente | Contenção de caminhos; isolamento de tenant e rejeição de traversal |
| SEC-020 | Implementado e testado automaticamente | Nome do estudante deriva do cadastro autorizado |
| SEC-021 | Implementado e testado automaticamente | Cabeçalhos encaminhados só aceitos de proxy explicitamente confiável |
| SEC-022 | Implementado; validação operacional pendente | Mensagens de erro não devolvem exceções internas |
| SEC-023 | Implementado; validação operacional pendente | Servidor legado desabilitado em produção |
| SEC-024 | Bloqueador antes de dados reais/produção | Aplicar HTTPS válido e firewall; não expor servidor Flask de desenvolvimento |
| SEC-025 | Melhoria ou avaliação pendente | Limitação de requisições distribuída e proteção contra DoS no gateway |
| SEC-026 | Melhoria ou avaliação pendente | Antivírus, sandbox de PDF/OCR e quarentena de uploads |
| SEC-027 | Melhoria ou avaliação pendente | Validar acessibilidade, dispositivos móveis e todos os estados de erro após alterações |
| SEC-028 | Validado localmente no navegador ou sintaxe | Portal, secretaria e gestão abertos no navegador; login, conferência e rotação visual verificados |
| SEC-029 | Validado localmente no navegador ou sintaxe | Sintaxe dos quatro scripts renderizados validada pelo Node |

## Criptografia e armazenamento

| ID | Situação | Controle |
|---|---|---|
| SEC-030 | Implementado e testado automaticamente | AES-256-GCM autentica conteúdo e detecta adulteração |
| SEC-031 | Implementado e testado automaticamente | Nonce aleatório evita repetição determinística de ciphertext |
| SEC-032 | Implementado e testado automaticamente | Derivação de chave e contexto vinculam tenant e caminho |
| SEC-033 | Implementado e testado automaticamente | Chaves ausentes e dados em claro são rejeitados em produção |
| SEC-034 | Implementado e testado automaticamente | Leitura com chave incorreta e troca de tenant falham |
| SEC-035 | Implementado e testado automaticamente | Leitura com chave antiga suportada por keyring para rotação |
| SEC-036 | Implementado e testado automaticamente | Persistência atômica conserva o arquivo antigo quando gravação falha |
| SEC-037 | Implementado; validação operacional pendente | Arquivo local e dossiê local cifrados; sessão persistida cifrada quando chave configurada |
| SEC-038 | Implementado; validação operacional pendente | Migração gera cópia separada, sem sobrescrever origem |
| SEC-039 | Bloqueador antes de dados reais/produção | Guardar chaves em cofre externo ao Git e separar contas de serviço |
| SEC-040 | Bloqueador antes de dados reais/produção | Preparar recuperação das chaves: perda da chave pode tornar dados irrecuperáveis |
| SEC-041 | Bloqueador antes de dados reais/produção | Migrar eventuais arquivos antigos para cópia cifrada antes da implantação |
| SEC-042 | Bloqueador antes de dados reais/produção | Aplicar ACL Windows ou permissões do volume; chmod não substitui ACL Windows |
| SEC-043 | Melhoria ou avaliação pendente | Cifrar disco, swap e snapshots; verificar cópias temporárias e logs do sistema |
| SEC-044 | Melhoria ou avaliação pendente | Cifrar banco remoto e reduzir metadados; nomes e IDs ainda aparecem em caminhos locais |
| SEC-045 | Melhoria ou avaliação pendente | Ensaiar rotação com recriptografia completa e encerramento do uso de chaves antigas |
| SEC-046 | Melhoria ou avaliação pendente | Migrar SQLite e escrita de JSON para armazenamento transacional adequado à escala |

## Backup e recuperação

| ID | Situação | Controle |
|---|---|---|
| SEC-047 | Implementado e testado automaticamente | Backup cifrado com chave independente da chave de dados |
| SEC-048 | Implementado e testado automaticamente | Manifesto autentica tamanhos e hashes dos arquivos |
| SEC-049 | Implementado e testado automaticamente | Restauração rejeita chave incorreta, adulteração e Zip Slip |
| SEC-050 | Implementado e testado automaticamente | Restauração exige destino vazio e não sobrescreve dados existentes |
| SEC-051 | Implementado e testado automaticamente | Criação e restauração validadas com arquivos fictícios |
| SEC-052 | Implementado; validação operacional pendente | Backup inclui dados locais, catálogo e audit.sqlite no caminho padrão |
| SEC-053 | Bloqueador antes de dados reais/produção | Programar cópias automáticas externas, imutáveis e com retenção |
| SEC-054 | Bloqueador antes de dados reais/produção | Definir RPO e RTO e realizar ensaio no ambiente definitivo |
| SEC-055 | Bloqueador antes de dados reais/produção | Pausar gravações para consistência do snapshot; backup não fornece snapshot global transacional |
| SEC-056 | Bloqueador antes de dados reais/produção | Incluir destinos remotos e audit.sqlite customizado se SECURITY_STATE_DIR mudar |
| SEC-057 | Bloqueador antes de dados reais/produção | Guardar chaves de recuperação separadas; segredos e contas não entram no backup de dados |
| SEC-058 | Melhoria ou avaliação pendente | Monitorar falhas, espaço, expiração e restauração; limite atual 512 MB e 10.000 arquivos |
| SEC-059 | Melhoria ou avaliação pendente | Ensaiar desastre regional, ransomware e recuperação sem acesso ao provedor principal |

## Integrações, Git e dependências

| ID | Situação | Controle |
|---|---|---|
| SEC-060 | Implementado; validação operacional pendente | Credenciais, catálogo e arquivos de estudantes retirados do rastreamento atual do Git |
| SEC-061 | Bloqueador antes de dados reais/produção | Verificar histórico Git e revogar qualquer credencial exposta, mesmo sem dados reais em produção |
| SEC-062 | Bloqueador antes de dados reais/produção | Se houver dados pessoais no histórico, coordenar saneamento também de clones e forks |
| SEC-063 | Implementado; validação operacional pendente | SQL preparado para RLS exclusiva de service_role e bucket privado |
| SEC-064 | Bloqueador antes de dados reais/produção | Aplicar e testar SQL no Supabase; identificar políticas adicionais e URLs antigas |
| SEC-065 | Implementado; validação operacional pendente | Edge Function antiga substituída por resposta 410 no código |
| SEC-066 | Bloqueador antes de dados reais/produção | Implantar a retirada da função antiga e confirmar que endpoints públicos desapareceram |
| SEC-067 | Implementado; validação operacional pendente | Processamento e armazenamento externo desabilitados por padrão em produção |
| SEC-068 | Implementado; validação operacional pendente | Endpoint remoto exige HTTPS e hostname permitido em produção |
| SEC-069 | Bloqueador antes de dados reais/produção | Contratos e configuração de Gemini, Supabase, ERP e WhatsApp antes de enviar dados reais |
| SEC-070 | Melhoria ou avaliação pendente | Testar respostas, timeout, falhas, privilégios e exclusão em cada provedor real |
| SEC-071 | Implementado; validação operacional pendente | Bibliotecas pypdf, Pillow e cryptography atualizadas; SDK ativo migrado para google-genai |
| SEC-072 | Implementado e testado automaticamente | Auditoria das 33 dependências diretas instaladas não encontrou vulnerabilidades conhecidas |
| SEC-073 | Bloqueador antes de dados reais/produção | Concluir resolução e auditoria de todas as dependências transitivas em ambiente limpo |
| SEC-074 | Implementado; validação operacional pendente | CI preparada para regressões, Bandit e pip-audit; execução remota ainda pendente |
| SEC-075 | Bloqueador antes de dados reais/produção | Validar imagem Docker e executor CI; builds locais não executados |
| SEC-076 | Melhoria ou avaliação pendente | Fixar dependências transitivas com hashes, gerar SBOM e verificar licenças |
| SEC-077 | Implementado; validação operacional pendente | Docker usa usuário sem root e exclui arquivos privados do contexto |
| SEC-078 | Bloqueador antes de dados reais/produção | Não usar Netlify estático como backend protegido; servir telas operacionais pelo Flask |

## Auditoria e operação

| ID | Situação | Controle |
|---|---|---|
| SEC-079 | Implementado e testado automaticamente | Eventos sem identificador bruto e cadeia HMAC detecta alteração de conteúdo |
| SEC-080 | Implementado; validação operacional pendente | Falha do registro de segurança em produção bloqueia resposta normal |
| SEC-081 | Bloqueador antes de dados reais/produção | Centralizar logs protegidos com retenção e acesso restrito |
| SEC-082 | Melhoria ou avaliação pendente | Ancorar cadeia externamente: HMAC local não detecta sozinho remoção final, rollback ou comprometimento da chave |
| SEC-083 | Bloqueador antes de dados reais/produção | Definir plano de incidentes, responsáveis, contatos e procedimento de comunicação |
| SEC-084 | Melhoria ou avaliação pendente | Alertar tentativas de acesso, exportação em massa e falhas de backup |
| SEC-085 | Melhoria ou avaliação pendente | Teste de invasão independente, revisão ASVS e análise de risco antes de abertura pública |
| SEC-086 | Melhoria ou avaliação pendente | Revisar concorrência, corrupção, esgotamento de recursos e segregação de ambientes |

## LGPD e governança

| ID | Situação | Controle |
|---|---|---|
| SEC-087 | Bloqueador antes de dados reais/produção | Inventariar dados, finalidades, controlador, operadores e fluxo por instituição |
| SEC-088 | Bloqueador antes de dados reais/produção | Definir base legal por finalidade; não presumir que consentimento atende a tudo |
| SEC-089 | Bloqueador antes de dados reais/produção | Publicar aviso de privacidade claro e canal de atendimento do titular |
| SEC-090 | Bloqueador antes de dados reais/produção | Definir retenção, eliminação segura e exceções legais para documentos educacionais |
| SEC-091 | Bloqueador antes de dados reais/produção | Estabelecer procedimentos de acesso, correção, portabilidade e eliminação quando aplicáveis |
| SEC-092 | Bloqueador antes de dados reais/produção | Avaliar melhor interesse e regras de tratamento de crianças e adolescentes |
| SEC-093 | Bloqueador antes de dados reais/produção | Avaliar transferências internacionais e mecanismos contratuais aplicáveis |
| SEC-094 | Bloqueador antes de dados reais/produção | Avaliar necessidade de RIPD e designação de encarregado conforme enquadramento |
| SEC-095 | Bloqueador antes de dados reais/produção | Documentar fornecedores, suboperadores, medidas e proibição de usos incompatíveis |
| SEC-096 | Bloqueador antes de dados reais/produção | Treinar equipe e definir processo de admissão e desligamento de usuários |
| SEC-097 | Melhoria ou avaliação pendente | Verificar minimização e necessidade de OCR/IA; evitar enviar documentos inteiros sem justificativa |
| SEC-098 | Melhoria ou avaliação pendente | Planejar eliminação também em cópias, logs, backups e fornecedores |
| SEC-099 | Melhoria ou avaliação pendente | Implementar workflow e evidências dos pedidos de titulares e prazos |
| SEC-100 | Melhoria ou avaliação pendente | Revisar afirmações comerciais de segurança: não anunciar certificação LGPD ou inviolabilidade |
