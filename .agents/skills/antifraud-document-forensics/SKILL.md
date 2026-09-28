---
name: antifraud-document-forensics
description: >-
  Performs visual and semantic forensic analysis on identification documents (RG, CIN, CNH), academic transcripts, and diplomas to detect fraud, counterfeiting, font tampering, stamp alterations, and forged QR codes. Use this skill whenever inspecting suspect documents, verifying forensic security features, analyzing digital artifacts, or validating document authenticity.
---

# Antifraud Document Forensics

Especialista em perícia grafotécnica, análise forense digital e verificação semântica de documentos civis e acadêmicos. Esta skill capacita o agente e a equipe técnica a identificar contrafações, montagens digitais, adulterações de notas, QR codes maliciosos e fraudes de identidade em processos seletivos e de expedição de diplomas.

---

## 1. Princípios da Perícia Documental Digital

A análise forense moderna combina três pilares investigativos complementares:

```text
               ┌──────────────────────────────────────────────┐
               │         PERÍCIA FORENSE DOCUMENTAL            │
               └──────────────────────┬───────────────────────┘
                                      │
         ┌────────────────────────────┼───────────────────────────┐
         ▼                            ▼                           ▼
┌──────────────────┐       ┌──────────────────────┐      ┌─────────────────┐
│ PERÍCIA GRÁFICA  │       │   PERÍCIA DIGITAL    │      │ PERÍCIA LÓGICA  │
│    E VISUAL      │       │     E PIXELAR        │      │   E SEMÂNTICA   │
├──────────────────┤       ├──────────────────────┤      ├─────────────────┤
│• Guilhochê       │       │• Análise ELA (Error  │      │• Anacronismos   │
│• Microimpressão  │       │  Level Analysis)     ││  temporais     │
│• Marcas d'água   │       │• Metadados EXIF/XMP  │      │• Cruzamento     │
│• Chancelas/Selos │       │• Interpolação DPI    ││  e-MEC / Censo  │
│• Relevo seco     │       │• Kerning e Tipografia│      │• DVs matemáticos│
└──────────────────┘       └──────────────────────┘      └─────────────────┘
```

---

## 2. Checklists de Detecção Forense por Tipologia

### A. Carteiras de Identidade (RG Tradicional vs CIN)
1. **Modelos Estaduais Antigos (SSP)**:
   - **Substrato e Fundo de Segurança**: Deve apresentar papel de segurança com filigranas, impressão em calcografia (relevo sensível ao toque), guilhochês simétricos e brasão estadual ou da República sem pixelização.
   - **Alinhamento Datilográfico/Matricial**: Em RGs antigos emitidos por máquina datilográfica, o alinhamento horizontal deve ser consistente em toda a linha. Caracteres "flutuando" ou com inclinação angular diferente indicam adulteração por colagem digital.
   - **Película Plástica e Carimbo**: Deve existir sobreposição visual do carimbo oficial da SSP sobre a borda da fotografia 3x4 do titular. Se o carimbo passar por baixo da foto, trata-se de substituição fotográfica.
   - **Algoritmo do Dígito Verificador (DV)**: Validar a regra matemática do estado emissor (ex: Módulo 11 para SSP-SP).

2. **Nova Carteira de Identidade Nacional (CIN - Decreto 10.977/2022)**:
   - **Identificador Único**: O número deve ser estritamente o CPF do cidadão (11 dígitos, com validação obrigatória dos dois dígitos verificadores).
   - **Zona de Leitura Mecânica (MRZ)**: Padrão ICAO Doc 9303 (3 linhas de 30 caracteres no verso). Conferir se o código de país `BRA`, nome truncado e checksums da MRZ batem rigorosamente com os dados visuais da frente.
   - **QR Code Criptográfico (VIO - SERPRO)**: O QR code da CIN é criptografado com chave assimétrica (ECDSA) da Secretaria de Governo Digital/Serpro. Um leitor padrão não deve abrir uma página HTTP arbitrária; deve conter o payload binário assinado que o aplicativo oficial "VIO" decodifica.

### B. Carteira Nacional de Habilitação (CNH)
1. **Espelho Gráfico e Numismática**:
   - Impressão calcográfica com microletras contendo falha técnica proposital ("SENATRAN" ou "DENATRAN").
   - Fundo numismático duplex com variação tonal contínua e perfeita continuidade das linhas sem descontinuidades causadas por scanner comum.
2. **Numeração de Controle**:
   - Número do espelho de segurança (10 dígitos impressos em tipografia vermelha magnética ou laser).
   - Número do Registro RENACH com 11 dígitos, acompanhado da sigla da UF emissora.
3. **Data de Emissão vs Validade**:
   - A validade da CNH obedece à Lei nº 14.071/2020:
     - 10 anos para condutores com menos de 50 anos;
     - 5 anos para condutores entre 50 e 69 anos;
     - 3 anos para condutores com 70 anos ou mais.
   - Divergências nesta regra indicam CNH montada a partir de modelo pré-existente.

### C. Certificados e Históricos Escolares do Ensino Médio
1. **Tipografia e Adulteração de Fontes (Font Tampering)**:
   - **Incompatibilidade de Fontes**: Utilização de fontes modernas (ex: Calibri, Roboto, Segoe UI) em formulários timbrados que datam dos anos 1980 a 2000 (período em que se utilizavam máquinas datilográficas mecânicas ou impressoras matriciais com fontes monoespaçadas como Courier ou Roman).
   - **Desalinhamento de Kerning e Linha de Base**: Nomes ou notas alteradas frequentemente exibem desalinhamento vertical (baseline shift) de 1 a 3 pixels em relação aos caracteres vizinhos legítimos.
   - **Artefatos de Compressão e Ruído JPEG (ELA)**: Ao inspecionar o arquivo em ferramenta de análise de nível de erro (Error Level Analysis), o campo alterado apresenta nível de ruído e compressão radicalmente divergente da matriz do documento.
2. **Carimbo de "Confere com o Original" e Carimbos da Direção**:
   - **Ausência de Carimbo Obrigatório**: Cópias desprovidas de carimbo de autenticação da secretaria da escola de origem ou visto de conferência com assinatura física/digital devem ser colocadas em exigência.
   - **Fotomontagem de Carimbo (Stamp Cloning)**:
     - O carimbo apresenta contornos perfeitamente nítidos e retilíneos, sem penetração de tinta na fibra celulósica do papel.
     - Ausência de distorção de rotação: em documentos escaneados com leve inclinação (ex: 1,5°), o carimbo adulterado costuma aparecer a 0,0° exatos.
3. **Carimbo e Visto de Inspeção Escolar (Supervisão de Ensino)**:
   - Estados como São Paulo, Rio de Janeiro e Minas Gerais exigem expressamente o visto da Diretoria de Ensino ou publicação no Diário Oficial (número de lauda, página e data da publicação) para concluintes até determinada vigência legal.

### D. Diplomas de Ensino Superior e Históricos de Graduação
1. **Credenciamento e-MEC**:
   - Conferir se a IES emissora e a IES registradora possuíam credenciamento ativo no Ministério da Educação na data da colação de grau informada.
   - Verificar se o curso possuía Portaria de Autorização ou Reconhecimento vigente na época.
2. **Dados Obrigatórios de Registro (Portaria MEC nº 1.095/2018)**:
   - Número do Livro de Registro, Número da Folha e Número de Ordem do Registro.
   - CNPJ da instituição registradora.
   - Identificação completa do processo de registro arquivado no acervo acadêmico.
3. **Diploma Digital (Portaria MEC nº 360/2022)**:
   - Deve possuir URL ou QR Code de validação que aponte estritamente para o domínio oficial da IES registradora (`ies.edu.br` ou subdomínio oficial institucional) ou para o validador nacional do MEC (`validadordiplomadigital.mec.gov.br`).
   - O documento oficial juridicamente válido é o arquivo XML assinado com certificado padrão ICP-Brasil. A representação visual (RVDD em PDF) é mero extrato auxiliar.

---

## 3. Investigação Forense de QR Codes Forjados

Fraudes sofisticadas geram QR codes em diplomas e históricos falsos direcionando para sites clones projetados para ludibriar secretarias acadêmicas:

| Vetor de Ataque | Mecanismo de Fraude | Procedimento de Detecção | Veredito |
| :--- | :--- | :--- | :--- |
| **Domínio Falso / Typosquatting** | O QR Code aponta para `validador-mec-gov.com` ou `ufscar-diplomas.org` em vez do domínio oficial `.gov.br` ou `.edu.br`. | Analisar a URL de destino decodificada antes de navegar; checar WHOIS e certificado SSL (Let's Encrypt recente em site institucional é forte indício de phishing). | **FRAUDE CRÍTICA** (Rejeição imediata) |
| **Redirecionamento Encurtado** | O QR Code aponta para encurtadores (`bit.ly`, `tinyurl`, `cutt.ly`) para ocultar o IP do atacante. | Proibir a validação através de encurtadores de links em documentos oficiais. | **SUSPEITA DE FRAUDE** |
| **Página Estática em Nuvem Gratuita** | URL hospedada em `firebaseapp.com`, `vercel.app`, `github.io` ou `s3.amazonaws.com` exibindo tela estática simulando "Documento Autêntico". | Conferir se a consulta realiza busca transacional em base oficial de dados com banco e-MEC. | **FRAUDE CRÍTICA** |
| **QR Code Decorativo / Desconectado** | O QR code contém apenas o nome do aluno ou uma chave alfanumérica aleatória sem protocolo HTTP ou sem assinatura VIO. | Tentar a leitura com leitor especializado e verificar ausência de serviço de autenticação. | **DOCUMENTO INVÁLIDO** |

---

## 4. Matriz de Detecção de Anacronismos Temporais

Inconsistências cronológicas constituem a prova material mais irrefutável de documento falsificado:

1. **Legislação Anacrônica**:
   - Citação da Lei de Diretrizes e Bases da Educação Nacional (LDB - Lei nº 9.394) em históricos emitidos antes de 20 de dezembro de 1996.
   - Citação do Novo Ensino Médio (Lei nº 13.415/2017) ou da BNCC em históricos anteriores a 2017/2018.
   - Citação de decretos de reconhecimento com datas posteriores à data da colação de grau ou da emissão do diploma.
2. **Carga Horária Incompatível**:
   - Cursos de graduação com carga horária total inferior ao piso curricular nacional estabelecido pelas Diretrizes Curriculares Nacionais (DCNs) de cada área (ex: Direito < 3.700h; Medicina < 7.200h; Pedagogia < 3.200h).
3. **Cronologia Pessoal Impossível**:
   - Conclusão do Ensino Médio ocorrida após o suposto ingresso na Graduação.
   - Conclusão de duas graduações presenciais integrais em cidades distantes sem regime de transferência.

---

## 5. Protocolo de Quarentena e Veredito Forense

Ao concluir a perícia de qualquer documento, o perito/sistema deve classificar a ocorrência em uma das três faixas de risco:

```text
[SCORE FORENSE DE RISCO]

🟢 FAIXA VERDE (Risco 0-15) -> AUTÊNTICO / REGULAR
└── Todos os elementos de segurança presentes, carimbos nítidos, QR codes oficiais validados, tipografia íntegra.
└── Ação: Homologação no Dossiê e avanço para arquivamento no Acervo Digital.

🟡 FAIXA AMARELA (Risco 16-60) -> DILIGÊNCIA / PENDÊNCIA TÉCNICA
└── Documento ilegível, carimbo borrado sem má-fé evidente, foto de baixa resolução, corte de borda sem perda de texto crucial.
└── Ação: Retornar ao aluno solicitando reenvio de arquivo nítido ("Envie foto original bem iluminada, sem cortes").

🔴 FAIXA VERMELHA (Risco 61-100) -> FRAUDE DOCUMENTAL DETECTADA
└── QR code falso, montagem gráfica evidente (ELA positivo), anacronismo legislativo, divergência no e-MEC, substituição de foto.
└── Ação: Bloqueio do processo, emissão de Parecer Pericial Circunstanciado e notificação à Procuradoria Jurídica da IES.
```
