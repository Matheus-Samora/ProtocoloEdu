# Versão independente

Esta instalação usa dados e configuração próprios. Consulte [separação e inicialização](docs/independencia.md). O servidor anterior do Google Cloud não é utilizado por esta versão.

# protocoloEdu

Aplicativo Flask para recebimento, conferência e custódia de documentos acadêmicos por instituição. A apresentação comercial é uma demonstração independente.

## Correções da auditoria de 02/10/2026

Autorização dos painéis e arquivos; rejeição de instituição inexistente; importação CSV/JSON por CPF ou matrícula; retenção de arquivos em revisão; confirmação de recebimento somente após persistência; remoção de diagnósticos da resposta pública; consulta respeitando a rejeição registrada; correção do filtro da secretaria; painéis alimentados pela API e indicadores sem sucessos externos presumidos; validação criptográfica de PDF e remoção de credenciais embutidas.

As verificações locais estão em `tests/`. Elas usam dados sintéticos, diretório temporário e bloqueiam conexões externas. Não medem precisão de OCR, conformidade jurídica nem disponibilidade dos provedores reais.

## Executar

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe tests\run_regressions.py
```

Configure o ambiente e `institutions_catalog.json` antes de executar `python api_server.py`. O pacote de distribuição inclui `institutions_catalog.example.json`; copie-o para o nome efetivo e configure seus próprios dados. A pasta de dados de uma implantação existente deve ser preservada.

- `FLASK_SECRET_KEY`: segredo estável e próprio do servidor para assinar as sessões.
- `SUPER_ADMIN_KEY`: credencial própria do gestor. Ausência de configuração bloqueia o acesso; não há senha padrão.
- `subscription.admin_access_key` no perfil de cada instituição: credencial da secretaria, distinta por instituição. Chaves padrão conhecidas são recusadas.
- `GEMINI_API_KEY` e credenciais dos conectores: configure somente no servidor.
- `COOKIE_SECURE=true` em implantação HTTPS. `ALLOWED_ORIGINS` aceita origens explícitas separadas por vírgula quando necessário.
- `require_student_cpf=false` no perfil permite a identificação por matrícula no portal. Importações aceitam `student_id` sem CPF.
- `PROTOCOL_DEMO_MODE=true` permite a busca pelo ERP mock; mantenha desativado na operação.

Login: `/admin/<institution_id>` e `/superadmin`. As credenciais são enviadas ao formulário de login e a sessão usa cookie HttpOnly; não use credenciais em links. APIs administrativas aceitam `X-Admin-Key` para integrações autorizadas.

## Assinaturas e integrações

`pyHanko==0.35.1` verifica criptograficamente o conteúdo assinado. PDF adulterado e certificado autoassinado não recebem confirmação ICP-Brasil. `ICP_BRASIL_TRUST_ROOTS_FILE` aponta para um conjunto PEM de raízes confiáveis selecionado pelo responsável. A validação exige evidência de revogação e não presume confiança quando faltam raízes ou comprovação. Cadeia real, revogação e carimbo de autoridade precisam de homologação específica; nenhum rótulo desta aplicação equivale a certificação jurídica ou do MEC.

WhatsApp, e-mail, ERP, Supabase opcional e Gemini precisam de testes de ponta a ponta no sandbox de implantação. Estados ausentes permanecem não confirmados e simulações são identificadas. Hash/tamanho antigos não registrados não são inventados. Documentos recebidos para revisão são retidos para conferência humana.

## Implantação

Este repositório contém as correções da auditoria. Publicar o código no GitHub não atualiza automaticamente o aplicativo em produção nem o site comercial. O aplicativo operacional precisa de um servidor Python com persistência e HTTPS. Hospedagem estática do HTML, sozinha, não executa a API nem constitui implantação desse backend. Use os templates Flask atualizados para os fluxos operacionais.

Credenciais anteriormente expostas devem ser substituídas pelo proprietário nos provedores. Removê-las da árvore atual não apaga o histórico Git. Nenhuma conta externa ou credencial de produção foi alterada nesta correção.

Ainda precisam de verificação específica: câmera/dispositivos, upload pela interface, acessibilidade completa, carga/concorrência e limites por lote, recuperação de dados, autenticação individual do estudante e integrações reais. Os testes locais comprovam os casos exercitados, não a totalidade desses cenários.
