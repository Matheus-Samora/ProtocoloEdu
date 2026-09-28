---
name: mec-compliance-auditor
description: >-
  Audits academic documents and student dossiers for regulatory compliance with Brazilian Ministry of Education (MEC) ordinances, including Portaria MEC nº 315/2018 and nº 360/2022 (Acervo Acadêmico Digital), the Document Classification Plan and Retention Schedule (TTD), and course-specific admission criteria for 1st Degree, 2nd Degree, Graduate Studies, and High School. Use this skill whenever validating compliance rules, evaluating academic dossiers, structuring digital archives, or auditing institutional regulatory requirements.
---

# MEC Compliance Auditor (Portarias 315/2018 & 360/2022)

Especialista em auditoria regulatória e compliance documental para Instituições de Ensino Superior (IES) e Educação Básica no Brasil, sob a égide do Ministério da Educação (MEC), Conselho Nacional de Educação (CNE) e Conselho Nacional de Arquivos (CONARQ).

---

## 1. Marco Regulatório e Fundamentação Legal

Esta skill normatiza os fluxos de custódia, conversão digital e homologação de documentos escolares com base nos seguintes diplomas legais:

1. **Portaria MEC nº 315/2018**: Dispõe sobre a obrigatoriedade da digitalização e gestão eletrônica do Acervo Acadêmico das Instituições de Educação Superior integrantes do sistema federal de ensino.
2. **Portaria MEC nº 360/2022**: Altera a Portaria MEC nº 315/2018, consolidando diretrizes do Diploma Digital, interoperabilidade com o e-MEC e barramento de serviços do MEC.
3. **Decreto Federal nº 9.235/2017**: Dispõe sobre o exercício das funções de regulação, supervisão e avaliação das instituições de educação superior e dos cursos superiores de graduação e pós-graduação.
4. **Portaria MEC nº 1.224/2013 & Resolução CONARQ nº 43/2015**: Institui o Código de Classificação de Documentos de Arquivo e a Tabela de Temporalidade Documental (TTD) das Atividades-Fim das IFES e do Ensino Superior Privado.
5. **Medida Provisória nº 2.200-2/2001 & Lei nº 14.063/2020**: Regulamentam o uso de assinaturas eletrônicas no Brasil e a Infraestrutura de Chaves Públicas Brasileira (ICP-Brasil).
6. **Decreto nº 8.727/2016 & Resolução CNE/CP nº 01/2018**: Uso do Nome Social de travestis e transexuais nos registros acadêmicos.

---

## 2. Requisitos Técnicos do Acervo Acadêmico Digital (Portaria 315/2018)

Para que um documento digitalizado ou nato-digital possua o mesmo valor probatório e legal do documento original físico (Art. 45 da Lei nº 12.682/2012 e Art. 12 da Portaria 315/2018), os seguintes requisitos técnicos devem ser verificados:

### A. Digitalização e Fidelidade Visual
- **Resolução Óptica Mínima**: 300 DPI (dots per inch) em escala 1:1, sem interpolação destrutiva.
- **Espaço de Cores**: Colorido (RGB/24 bits) para documentos com selos coloridos, brasões, fotos ou marcas d'água; Tons de Cinza (8 bits) aceito para folhas de histórico puramente textuais; Monocromático (1 bit) terminantemente proibido para documentos de identificação ou com carimbos.
- **Formato Arquivístico**: PDF/A (ISO 19005-1 / ISO 19005-2), preferencialmente níveis PDF/A-1a ou PDF/A-2u, garantindo preservação de longo prazo e independência de plataforma.

### B. Assinatura Digital e Integridade Criptográfica
- **Padrão Criptográfico**: Assinatura digital no padrão ICP-Brasil (PAdES - PDF Advanced Electronic Signatures), tipo PAdES-BES ou PAdES-T (com carimbo do tempo).
- **Nível da Assinatura**: Assinatura qualificada institucional (e-CNPJ da IES mantenedora ou e-CPF do Procurador Institucional / Secretário Geral Acadêmico credenciado).
- **Carimbo do Tempo (ACT)**: Fornecido por Autoridade de Carimbo do Tempo credenciada à ICP-Brasil, comprovando a exata hora legal brasileira (Observatório Nacional) da chancela digital.
- **Algoritmo de Hash**: SHA-256 ou superior (SHA-384, SHA-512) para validação de integridade do arquivo.

### C. Metadados Obrigatórios do Objeto Digital (Art. 13)
Todo registro arquivado deve conter a seguinte estrutura mínima de metadados:
```json
{
  "codigo_classificacao_conarq": "125.1",
  "titulo_documento": "Histórico Escolar do Ensino Médio",
  "identificador_discente": "CPF_OU_MATRICULA",
  "nome_discente": "NOME COMPLETO DO ESTUDANTE",
  "data_digitalizacao": "2026-09-25T12:00:00Z",
  "responsavel_digitalizacao": {
    "nome": "NOME DO AGENTE DA SECRETARIA",
    "cpf": "XXX.XXX.XXX-XX",
    "cargo": "Secretário Geral Acadêmico",
    "assinatura_icp_valida": true
  },
  "hash_sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
  "resolucao_dpi": 300,
  "formato_mimetype": "application/pdf"
}
```

---

## 3. Tabela de Temporalidade Documental (TTD) e Destinação Final

A gestão do prontuário do aluno deve seguir rigorosamente os prazos de guarda e destinação final estabelecidos pela Portaria MEC nº 1.224/2013 e Portaria nº 315/2018:

| Código CONARQ | Tipo de Documento | Fase Corrente (Secretaria) | Fase Intermediária (Arquivo Central) | Destinação Final | Justificativa Regulatória |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **125.1** | **Histórico Escolar (Médio/Superior)** | Enquanto durar o curso | Permanente | **Guarda Permanente** | Documento essencial para comprovação de escolaridade e expedição de diploma. |
| **125.1** | **Certificado de Conclusão / Diploma** | Enquanto durar o curso | Permanente | **Guarda Permanente** | Prova irrefutável de colação de grau e titulação acadêmica. |
| **125.1** | **Livro / Registro de Diplomas** | Ativo | Permanente | **Guarda Permanente** | Registro de fé pública institucional auditado pelo MEC. |
| **125.1** | **Certidão de Registro Civil (Nascimento/Casamento)** | Enquanto durar o curso | Permanente | **Guarda Permanente** | Garante cadeia de titularidade civil e averbações de nome. |
| **125.2** | **Documento de Identidade (RG/CIN/RNE)** | Enquanto durar o curso | Permanente | **Guarda Permanente** | Identificação oficial do titular do grau conferido. |
| **125.3** | **Comprovante de Residência** | Enquanto durar o curso | 5 anos após conclusão/evasão | **Eliminação** | Documento comprobatório transitório; não integra acervo histórico do diploma. |
| **125.4** | **Título de Eleitor / Quitação Eleitoral** | Enquanto durar o curso | 5 anos após conclusão/evasão | **Eliminação** | Comprovação circunstancial no ato da matrícula. |
| **125.5** | **Documento Militar (CDI / Reservista)** | Enquanto durar o curso | 5 anos após conclusão/evasão | **Eliminação** | Obrigação circunstancial (Art. 74 da Lei do Serviço Militar). |
| **124.2** | **Requerimentos de Dispensa de Disciplina** | Durante o semestre letivo | 5 anos após conclusão | **Eliminação** | Decisões pedagógicas consolidadas no histórico definitivo. |

> [!IMPORTANT]
> Documentos de **Guarda Permanente** nunca podem ser destruídos, eliminados ou descartados de forma irreversível. A digitalização em conformidade com a Portaria nº 315/2018 confere fé pública ao acervo eletrônico, mas o descarte do documento físico original só é autorizado após parecer formal da Comissão Permanente de Avaliação de Documentos (CPAD) da IES e cumprimento dos editais de eliminação de acervo.

---

## 4. Matriz de Critérios de Auditoria por Nível de Curso

Ao avaliar o dossiê de um estudante, o auditor deve aplicar a matriz regulatória específica para o nível de ensino contratado:

### A. 1ª Graduação (Bacharelado, Licenciatura e Tecnológico)
*Requisitos inafastáveis para homologação de matrícula e posterior colação de grau (Art. 44, II da LDB nº 9.394/1996):*
1. **Documento de Identificação Oficial**:
   - RG (Secretarias de Segurança Pública Estaduais) ou CIN (Carteira de Identidade Nacional - Decreto 10.977/2022).
   - RNE / CRNM para estrangeiros (com visto válido ou permanente).
   - *Nota*: CNH pode ser aceita para identificação inicial de matrícula, mas para emissão e registro de diploma digital, o MEC exige dados de naturalidade e órgão emissor que frequentemente não constam em modelos antigos de CNH.
2. **Cadastro de Pessoa Física (CPF)**:
   - Situação cadastral ativa/regular na Receita Federal do Brasil.
3. **Certificado de Conclusão do Ensino Médio**:
   - Certificado expedido por instituição credenciada pela respectiva Secretaria de Educação Estadual.
   - Presença obrigatória de Visto da Inspeção Escolar, carimbo com registro de publicação em Diário Oficial do Estado (ex: GDAE em SP, SEEDUC no RJ) ou código de validação eletrônica autenticável.
4. **Histórico Escolar do Ensino Médio**:
   - Matriz curricular completa das 3 séries do Ensino Médio (ou equivalente EJA/ENCCEJA).
   - Carga horária total cursada (mínimo de 2.400 horas pela Lei 9.394/1996, ou 3.000 horas pelo Novo Ensino Médio Lei 13.415/2017).
   - Carimbos com identificação legível do Diretor e Secretário Escolar com respectivos números de autorização/registro.
5. **Certidão de Registro Civil (Nascimento ou Casamento)**:
   - Obrigatória averbação civil caso haja divergência no sobrenome entre o Histórico do Ensino Médio e o Documento de Identidade atual.
6. **Quitação com o Serviço Militar**:
   - Obrigatório para brasileiros do sexo masculino entre 18 e 45 anos (Certificado de Alistamento Militar - CAM, Certificado de Reservista, Certificado de Dispensa de Incorporação - CDI).
7. **Quitação Eleitoral**:
   - Certidão emitida pelo Tribunal Superior Eleitoral (TSE) ou comprovante dos 2 turnos da última eleição.

### B. 2ª Graduação / Formação Pedagógica (R2) / Complementação
*Requisitos específicos para aproveitamento de estudos e titulação de novo grau:*
1. **Diploma de Graduação Anterior**:
   - Diploma devidamente registrado nos termos do Art. 48 da LDB 9.394/1996 e Portaria MEC 1.095/2018 (ou Portaria 360/2022 para Diploma Digital).
   - Verificação obrigatória do código e-MEC da instituição expedidora e registradora.
   - Data de Colação de Grau explicitada no diploma ou em certidão de colação anexa.
2. **Histórico Escolar da Graduação Anterior**:
   - Relação de disciplinas com notas/conceitos, cargas horárias e situação final.
   - Indicação expressa do processo seletivo de ingresso (Vestibular, ENEM, Transferência).
   - Carga horária total acumulada do curso anterior.
3. **Documentos Civis**:
   - RG/CIN, CPF, Certidão de Casamento/Nascimento atualizada.

### C. Pós-Graduação (Lato Sensu - Especialização / MBA)
*Resolução CNE/CES nº 1/2018:*
1. **Diploma de Graduação (Frente e Verso ou RVDD com XML)**:
   - O aluno **deve ter colado grau obrigatoriamente antes do primeiro dia de aula** do curso de pós-graduação. Alunos que não concluíram a graduação não podem obter certificado de pós-graduação (apenas declaração de extensão).
2. **Histórico Escolar da Graduação**:
   - Comprovação da área de formação para conferência de pré-requisitos pedagógicos quando exigido pelo PPC da pós-graduação.
3. **Documentos Pessoais**:
   - RG/CIN, CPF, Certidão com averbação civil em caso de alteração patronímica.

### D. Ensino Médio / Educação Profissional Técnica
*Diretrizes Curriculares Nacionais para a Educação Básica:*
1. **Histórico Escolar do Ensino Fundamental**:
   - Comprovação de conclusão dos 9 anos do Ensino Fundamental.
2. **Certidão de Nascimento**:
   - Identificação do discente e filiação completa.
3. **Documento de Identidade e CPF do Aluno e do Responsável Legal**:
   - Obrigatório documento oficial com foto e CPF do pai, mãe ou tutor legal para menores de 18 anos.
4. **Declaração de Transferência Escolar**:
   - Documento provisório expedido pela escola de origem com validade máxima de 30 dias, até a entrega do Histórico Escolar definitivo.
5. **Comprovante de Vacinação**:
   - Exigido conforme legislações sanitárias estaduais e municipais vigentes.

---

## 5. Checklist Operacional de Auditoria Automatizada

Ao processar qualquer documento ou dossiê completo, execute o seguinte procedimento:

```text
[PASS0 1: CLASSIFICAÇÃO E INTEGRIDADE FORMAL]
├── 1.1 O arquivo está em formato PDF ou imagem com resolução equivalente a >= 300 DPI?
├── 1.2 O documento é completo (frente e verso, todas as folhas de anexos/notas)?
└── 1.3 As bordas estão íntegras e os quatro cantos do papel são visíveis?

[PASSO 2: AUTENTICIDADE E RECONHECIMENTO JURÍDICO]
├── 2.1 Emissão Digital: Há assinatura digital ICP-Brasil/Gov.br ou código de validação com QR Code ativo?
├── 2.2 Emissão Física Digitalizada: Há carimbo de "Confere com o Original", data, matrícula e assinatura da secretaria?
└── 2.3 Estabelecimento Emissor: A instituição emissora possui ato regulatório ativo no e-MEC ou Diário Oficial Estadual?

[PASSO 3: CONCILIAÇÃO DE IDENTIDADE E CADEIA DE CUSTÓDIA]
├── 3.1 O nome do titular no documento confere com o cadastro do aluno no ERP acadêmico?
├── 3.2 Em caso de divergência de nome (casamento, divórcio, união estável), há certidão civil com averbação correspondente?
└── 3.3 A data de nascimento, filiação e CPF são consistentes em todos os documentos do dossiê?

[PASSO 4: TEMPORALIDADE E ENCERRAMENTO DO CICLO]
├── 4.1 O documento foi catalogado com o código CONARQ correto no Plano de Classificação?
├── 4.2 O prazo de guarda foi atribuído de acordo com a TTD da IES?
└── 4.3 O status do dossiê foi recalculado no ERP (COMPLETO, PENDENTE, COM_PENDENCIA)?
```

---

## 6. Exemplos de Não-Conformidade e Ações Corretivas

### Exemplo 1: Diploma Digital de 2ª Graduação sem XML ou Validador
- **Cenário**: Candidato envia apenas a impressão escaneada da representação visual (RVDD) de um diploma digital emitido após 2022, sem o XML correspondente e com QR Code borrado.
- **Parecer Regulatório**: `REPROVADO`. O Art. 19 da Portaria MEC nº 360/2022 determina que o documento acadêmico digital é o arquivo XML assinado com certificado digital ICP-Brasil. A representação visual impressa desprovida de validação eletrônica é cópia simples ineficaz.
- **Mensagem Corretiva para o Aluno**: *"Prezado(a) discente, o arquivo enviado é uma cópia impressa do Diploma Digital. Nos termos da Portaria MEC 360/2022, solicitamos o envio do arquivo original em formato XML assinado digitalmente ou do PDF oficial que contém o QR Code e o código de validação legível para conferência no portal do MEC."*

### Exemplo 2: Histórico Escolar do Ensino Médio sem Visto de Inspeção
- **Cenário**: Histórico de escola extinta em 2015 no Estado do Rio de Janeiro sem publicação no Diário Oficial e sem visto da Diretoria Regional de Educação.
- **Parecer Regulatório**: `PENDÊNCIA REGULATÓRIA`. Aluno deve protocolar certidão de escolaridade de escola extinta emitida pela SEEDUC-RJ.
- **Ação**: Marcar documento como `COM_PENDENCIA` e orientar o aluno a obter a Certidão de Regularidade Escolar perante a Secretaria Estadual de Educação.
