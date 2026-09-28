---
name: erp-solis-totvs-integrator
description: >-
  Integrates and maps ProtocoloEdu document audit schemas to Brazilian higher education ERPs including SolisGE, TOTVS Educacional (RM), Lyceum (Techne), and Sophia Educacional. Use this skill whenever building or debugging API connectors, mapping database fields, synchronizing student dossiers, updating enrollment approval statuses, or persisting custodial document links.
---

# ERP Solis, TOTVS, Lyceum & Sophia Integrator

Guia de arquitetura, contratos de dados e rotinas de integração bidirecional entre o **ProtocoloEdu** e os principais sistemas de gestão acadêmica (ERPs) utilizados por faculdades, centros universitários e mantenedoras no Brasil.

---

## 1. Arquitetura Geral da Integração

O ProtocoloEdu opera como o motor inteligente de auditoria, higienização cadastral e custódia digital. A comunicação com o ERP acadêmico é regida pelo seguinte fluxo:

```text
┌────────────────┐          ┌────────────────────┐          ┌────────────────────┐
│  Portal Aluno  │          │   ProtocoloEdu     │          │    ERP Acadêmico   │
│  (Upload Doc)  │──(1)────▶│   (Auditoria IA &  │──(3)────▶│   (Solis, TOTVS,   │
└────────────────┘          │   Conformidade 315)│          │   Lyceum, Sophia)  │
                            └─────────┬──────────┘          └────────────────────┘
                                      │ (2)
                                      ▼
                            ┌────────────────────┐
                            │ Repositório Nuvem  │
                            │  (Custódia 300 DPI │
                            │   + Hash SHA-256)  │
                            └────────────────────┘
```

1. **Submissão**: O estudante envia o arquivo pelo portal ou secretaria.
2. **Auditoria e Preservação**: O ProtocoloEdu valida conformidade (MEC 315/2018), extrai os dados estruturados e gera a URL de custódia assinada.
3. **Sincronização no ERP**: O ProtocoloEdu dispara a atualização cadastral, altera o status do documento para `ENTREGUE/HOMOLOGADO` e vincula o link de custódia permanente.

---

## 2. Tabela de Mapeamento Crosswalk de Dados

| Campo Canônico ProtocoloEdu | Tipo | SolisGE (JSON API) | TOTVS Educacional (RM DataServer) | Lyceum (Techne API / Oracle) | Sophia Educacional (Prima WebAPI) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `student_id` | String | `identificador` | `RA` (Registro Acadêmico) | `ALUNO` | `CodigoAluno` |
| `student_name` | String | `nome` | `PPESSOA.NOME` | `NOME_COMPL` | `Nome` |
| `cpf` | String (11) | `cpf` | `PPESSOA.CPF` | `CPF` | `Cpf` |
| `rg_number` | String | `rg` | `PPESSOA.CARTIDENT` | `RG_NUM` | `RgNumero` |
| `rg_issuer` | String | `orgao_emissor` | `PPESSOA.ORGEMISSORIDENT` | `RG_ORGAO` | `RgOrgaoEmissor` |
| `birth_date` | Date (YYYY-MM-DD) | `data_nascimento` | `PPESSOA.DTNASCIMENTO` | `DT_NASC` | `DataNascimento` |
| `mother_name` | String | `nome_mae` | `PPESSOA.NOMEMAE` | `NOME_MAE` | `NomeMae` |
| `father_name` | String | `nome_pai` | `PPESSOA.NOMEPAI` | `NOME_PAI` | `NomePai` |
| `course_code` | String | `cod_curso` | `SMATRICULA.CODCUR` | `CURSO` | `CodigoCurso` |
| `document_code` | String | `codigo_documento` | `SDOCALUNO.CODDOC` | `DOCUMENTO` | `CodigoDocumento` |
| `status_approval` | String | `situacao_entrega` | `SDOCALUNO.SITUACAO` (1=OK, 2=Pend) | `SITUACAO` ('E'=Entregue) | `Status` ('Entregue') |
| `custody_link` | URL | `url_custodia` | `SDOCALUNO.LINKARQUIVO` | `URL_DOCUMENTO` | `ArquivoUrl` |
| `audit_hash` | String (SHA-256)| `hash_sha256` | `SDOCALUNO.OBSERVACAO` | `HASH_ARQUIVO` | `Observacao` |

---

## 3. Conectores e Payloads por Sistema ERP

### A. Solis (SolisGE)
- **Protocolo**: REST API / JSON.
- **Autenticação**: Header HTTP `X-Token: <JWT_TOKEN>`.
- **Rotina de Envio de Pessoa e Documentos**:

```json
// POST /api/academico/documentos/homologacao
{
  "identificador_aluno": "20261019",
  "cpf": "12345678901",
  "documentos": [
    {
      "codigo_documento": "HIST_MEDIO",
      "status": "HOMOLOGADO",
      "data_homologacao": "2026-09-25T12:00:00",
      "url_custodia": "https://storage.protocoloedu.com.br/custodia/20261019/HIST_MEDIO.pdf",
      "hash_sha256": "3a7b9c1d8e2f4a5b6c7d8e9f0a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b",
      "dados_extraidos": {
        "escola_origem": "Colégio Estadual Central",
        "ano_conclusao": "2022",
        "carga_horaria": 3200
      }
    }
  ]
}
```

### B. TOTVS Educacional (Linha RM)
- **Protocolo**: Web Service SOAP ou RM DataServer REST API.
- **Autenticação**: HTTP Basic (`Authorization: Basic <base64>`) ou Token OAuth2.
- **DataServer Responsável**: `EduDocAlunoData` (Tabela `SDOCALUNO`).
- **Exemplo de Payload XML / JSON do DataServer**:

```json
// POST /api/framework/v1/dataServer/EduDocAlunoData
{
  "CODCOLIGADA": 1,
  "RA": "20261019",
  "CODDOC": 105,
  "DTENTREGA": "2026-09-25T00:00:00",
  "SITUACAO": 1, 
  "CODMOTIVOPENDENCIA": null,
  "OBSERVACAO": "Homologado via ProtocoloEdu (Portaria MEC 315/2018). Hash: 3a7b9c1d...",
  "LINKARQUIVO": "https://storage.protocoloedu.com.br/custodia/20261019/HIST_MEDIO.pdf"
}
```

### C. Lyceum (Techne)
- **Protocolo**: REST API institucional ou Stored Procedure via Oracle DB.
- **Tabela**: `LY_DOC_ALUNO`.
- **Payload de Homologação**:

```json
// PUT /lyceum-api/v1/alunos/20261019/documentos/HIST_EM
{
  "aluno": "20261019",
  "documento": "HIST_EM",
  "dt_entrega": "2026-09-25",
  "situacao": "E",
  "observacao": "Validado com selo digital ICP-Brasil",
  "url_arquivo": "https://storage.protocoloedu.com.br/custodia/20261019/HIST_MEDIO.pdf",
  "hash_conarq": "3a7b9c1d8e2f..."
}
```

### D. Sophia Educacional (Prima)
- **Protocolo**: WebAPI REST.
- **Autenticação**: `Authorization: Bearer <TOKEN>` e Header `X-Tenant-Id: <TENANT>`.
- **Payload de Homologação**:

```json
// POST /api/v1/alunos/20261019/documentos-entregues
{
  "CodigoDocumento": "DOC_DIPLOMA_GRAD",
  "DataEntrega": "2026-09-25T12:00:00",
  "Status": "Entregue",
  "ArquivoUrl": "https://storage.protocoloedu.com.br/custodia/20261019/DIPLOMA.pdf",
  "Observacao": "Homologado - Colação de Grau confirmada em 18/01/2023"
}
```

---

## 4. Gestão de Idempotência e Resiliência de Rede

Para garantir integridade de dados e evitar duplicação em requisições de rede:

1. **Chave de Idempotência (`X-Idempotency-Key`)**:
   - Cada chamada de integração deve enviar um cabeçalho único:
     `X-Idempotency-Key: SHA256({institution_id}_{student_id}_{document_id}_{audit_timestamp})`
   - O conector rejeita processamento duplo se a chave já foi executada com sucesso nos últimos 30 dias.
2. **Tratamento de Códigos de Retorno**:
   - `200 OK / 201 Created`: Sincronização concluída com sucesso. Atualizar `exported_at` no dossiê do discente.
   - `401 Unauthorized`: Token expirado. Disparar rotina de reautenticação imediata (refresh token ou novo login) e retentar uma vez.
   - `422 Unprocessable Entity`: Erro de validação no ERP (ex: CPF já cadastrado em outra pessoa, código de curso inexistente). Registrar diagnóstico técnico em `admin_diagnostic` e alertar a TI/Secretaria.
   - `500/503 Service Unavailable`: Falha no servidor do ERP. Aplicar fila de retry com **Exponential Backoff e Jitter**:
     - Tentativa 1: após 30 segundos;
     - Tentativa 2: após 2 minutos;
     - Tentativa 3: após 10 minutos;
     - Tentativa 4: após 1 hora.
     - Se persistir após 4 tentativas, mover transação para fila de Dead-Letter Queue (DLQ) para conferência humana.

---

## 5. Exemplo de Código do Adaptador Integrador (Python)

```python
import hashlib
import requests
from typing import Dict, Any, Optional

class ERPIntegrator:
    def __init__(self, erp_type: str, base_url: str, auth_token: str):
        self.erp_type = erp_type.lower()
        self.base_url = base_url.rstrip('/')
        self.token = auth_token

    def sync_document_approval(
        self,
        student_id: str,
        doc_id: str,
        custody_url: str,
        hash_sha256: str,
        extracted_data: Dict[str, Any]
    ) -> bool:
        """Sincroniza a homologação documental no ERP correspondente."""
        idempotency_key = hashlib.sha256(
            f"{student_id}_{doc_id}_{hash_sha256}".encode()
        ).hexdigest()

        headers = {
            "Content-Type": "application/json",
            "X-Idempotency-Key": idempotency_key
        }

        if self.erp_type == "solis":
            headers["X-Token"] = self.token
            url = f"{self.base_url}/api/academico/documentos/homologacao"
            payload = {
                "identificador_aluno": student_id,
                "documento": doc_id,
                "status": "HOMOLOGADO",
                "url_custodia": custody_url,
                "hash_sha256": hash_sha256,
                "dados": extracted_data
            }
        elif self.erp_type == "totvs":
            headers["Authorization"] = f"Bearer {self.token}"
            url = f"{self.base_url}/api/framework/v1/dataServer/EduDocAlunoData"
            payload = {
                "RA": student_id,
                "CODDOC": doc_id,
                "SITUACAO": 1,
                "LINKARQUIVO": custody_url,
                "OBSERVACAO": f"ProtocoloEdu SHA256: {hash_sha256}"
            }
        else:
            raise ValueError(f"ERP '{self.erp_type}' não suportado.")

        try:
            resp = requests.post(url, json=payload, headers=headers, timeout=20)
            resp.raise_for_status()
            return True
        except requests.RequestException as e:
            print(f"[ERPIntegrator] Erro ao sincronizar documento com {self.erp_type}: {e}")
            return False
```
