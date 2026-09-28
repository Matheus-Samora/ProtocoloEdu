---
name: academic-design-system
description: >-
  Provides institutional design system guidelines, accessibility standards (WCAG 2.1 AA), ergonomic UI patterns for academic registrar back-offices, high-contrast color palettes (MEC Navy, Slate, Academic Blue), and mobile-first student upload experiences. Use this skill whenever designing, reviewing, or styling user interfaces for Brazilian educational institutions and student document portals.
---

# Academic Design System (ProtocoloEdu & MEC UI)

Diretrizes de interface, ergonomia cognitiva e design system para portais acadêmicos, secretarias digitais e sistemas de homologação documental no ensino superior e na educação básica brasileira.

---

## 1. Princípios de Design Institucional

1. **Autoridade e Fé Pública**: A interface deve transmitir sobriedade institucional, segurança e conformidade jurídica, sem abrir mão da modernidade e fluidez.
2. **Ergonomia de Alta Densidade (Back-Office)**: Secretários acadêmicos analisam centenas de dossiês por dia. A interface de conferência deve minimizar cliques, oferecer atalhos de teclado e evitar fadiga visual.
3. **Acolhimento e Clareza (Portal do Aluno)**: A experiência do estudante deve ser simples, orientada e transparente, reduzindo o abandono de matrícula causado pela burocracia de envio de documentos.
4. **Acessibilidade Universal**: Conformidade rigorosa com a Lei Brasileira de Inclusão da Pessoa com Deficiência (Lei nº 13.146/2015) e as diretrizes internacionais WCAG 2.1 nível AA.

---

## 2. Paleta de Cores e Tokens de Alto Contraste

A paleta oficial do ProtocoloEdu equilibra o rigor regulatório do MEC com usabilidade contemporânea:

```text
┌────────────────────────────────────────────────────────────────────────┐
│                        CORES INSTITUCIONAIS                            │
├───────────────────┬───────────────────┬────────────────────────────────┤
│ MEC Navy          │ #0B192C           │ Header, Navbar, Autoridade     │
│ Slate Deep        │ #1E293B           │ Tipografia Principal, Títulos  │
│ Slate Muted       │ #64748B           │ Legendas, Metadados, Labels    │
│ Academic Blue     │ #1D4ED8           │ Ações Primárias, Botões, Links │
│ Blue Hover        │ #1E40AF           │ Estados de Hover e Foco        │
├───────────────────┴───────────────────┴────────────────────────────────┤
│                        CORES SEMÂNTICAS DE STATUS                      │
├───────────────────┬───────────────────┬────────────────────────────────┤
│ Emerald (Aprovado)│ #059669 (Bg: #ECFDF5, Border: #10B981) - Conforme │
│ Amber (Análise)   │ #D97706 (Bg: #FFFBEB, Border: #F59E0B) - Pendência│
│ Crimson (Rejeitado) #DC2626 (Bg: #FEF2F2, Border: #EF4444) - Reprovado │
│ Neutral Surface   │ #F8FAFC (Fundo App), #FFFFFF (Cards), #E2E8F0 (Bordas)│
└────────────────────────────────────────────────────────────────────────┘
```

### Validação de Contraste WCAG 2.1 AA
- `MEC Navy (#0B192C)` sobre Branco `#FFFFFF`: **16.8:1** (Supera amplamente o mínimo exigido de 4.5:1).
- `Slate Deep (#1E293B)` sobre Branco `#FFFFFF`: **12.6:1** (Excelente legibilidade para textos longos).
- `Academic Blue (#1D4ED8)` sobre Branco `#FFFFFF`: **4.65:1** (Conforme com nível AA para links e botões).
- Texto em botões primários (`#FFFFFF` sobre `Academic Blue #1D4ED8`): **4.65:1**.
- Badges semânticos sempre combinam texto escuro e borda de alto contraste sobre fundo suavizado para máxima legibilidade.

---

## 3. Tipografia e Hierarquia Visual

- **Família Tipográfica Primária**: `Inter`, `Roboto` ou system-ui (`system-ui, -apple-system, sans-serif`).
- **Escala Modular**:
  - `Display / H1`: 24px (1.5rem), peso 700, line-height 1.25 (ex: "Auditoria do Dossiê do Estudante").
  - `Section / H2`: 18px (1.125rem), peso 600, line-height 1.35 (ex: "Documentos de Conclusão do Ensino Médio").
  - `Card Header / H3`: 15px (0.9375rem), peso 600, line-height 1.4.
  - `Body / Texto Padrão`: 14px (0.875rem), peso 400, line-height 1.5.
  - `Caption / Metadado`: 12px (0.75rem), peso 500, line-height 1.4 (ex: "Código CONARQ: 125.1").

---

## 4. Ergonomia para a Secretaria Acadêmica (Visualizador Split-Screen)

Para otimizar o fluxo de trabalho de auditores e secretários acadêmicos, a tela de conferência de documentos deve seguir o padrão de tela dividida:

```text
┌─────────────────────────────────────────────────────────────────────────────────┐
│ [LOGO] ProtocoloEdu - Secretaria Acadêmica | Aluno: Matheus Samora (Matrícula: 2026101) │
├────────────────────────────────────────┬────────────────────────────────────────┤
│          VISUALIZADOR FORENSE          │         PAINEL DE AUDITORIA MEC        │
│          (55% da largura de tela)      │         (45% da largura de tela)       │
├────────────────────────────────────────┼────────────────────────────────────────┤
│ [Zoom: 100%] [Girar 90°] [Alto Contraste]│ Documento: Histórico do Ensino Médio   │
│                                        │ Status: 🟡 EM ANÁLISE PELA SECRETARIA  │
│ ┌────────────────────────────────────┐ │                                        │
│ │                                    │ │ DADOS EXTRAÍDOS PELA IA:               │
│ │   [DOCUMENTO DIGITALIZADO]         │ │ • Instituição: Colégio Estadual Central│
│ │                                    │ │ • Conclusão: 15/12/2022                │
│ │   • Carimbo de Inspeção            │ │ • Carga Horária: 3.200 horas (✅ Válida)│
│ │   • Visto da Secretaria            │ │                                        │
│ │   • Notas e Cargas Horárias        │ │ CONFORMIDADE REGULATÓRIA:              │
│ │                                    │ │ [x] Tipo Documental Reconhecido        │
│ │                                    │ │ [x] Titularidade Confere com o Aluno   │
│ │                                    │ │ [!] Carimbo de Inspeção sem data       │
│ └────────────────────────────────────┘ │                                        │
│ Atalhos: [A] Aprovar | [R] Rejeitar   │ [ ✅ APROVAR (A) ]   [ ❌ REJEITAR (R) ] │
└────────────────────────────────────────┴────────────────────────────────────────┘
```

### Atalhos de Teclado (Keyboard Hotkeys)
Para acelerar a homologação contínua de dossiês:
- `A` ou `Enter`: Homologar/Aprovar documento atual.
- `R`: Abrir modal rápido de rejeição com seleção de justificativa padronizada.
- `S` ou `Space`: Marcar para reanálise / perícia sênior.
- `J` / `K` ou Setas `↑` / `↓`: Navegar para o documento anterior/seguinte.
- `+` / `-`: Zoom in / Zoom out da imagem.
- `O`: Girar imagem em 90 graus.

---

## 5. Diretrizes Mobile-First para o Portal do Aluno

O estudante frequentemente realiza o upload de documentos através de smartphones. O fluxo deve seguir o padrão "Três Passos Guiados":

### Passo 1: Orientação Prévia de Enquadramento
Apresentar ilustrações visuais simples antes de abrir a câmera ou seletor de arquivos:
- *"Fotografe em um ambiente bem iluminado."*
- *"Retire o documento do plástico protetor para evitar reflexos."*
- *"Enquadre frente e verso (se houver dados nos dois lados)."*

### Passo 2: Pré-visualização com Detecção de Falhas
Assim que o aluno seleciona o arquivo ou captura a foto:
- O sistema calcula o tamanho e resolução instantaneamente.
- Se o arquivo for menor que 200 KB ou tiver resolução inferior a 1200x800 pixels, exibir aviso preventivo:
  > *"Atenção: A imagem parece um pouco borrada. Certifique-se de que todas as letras e carimbos estão nítidos antes de enviar para evitar atrasos na sua matrícula."*

### Passo 3: Recibo Digital de Protocolo
Ao concluir o envio, gerar um comprovante visual com:
- Número de Protocolo Único.
- Data e Hora exata de envio.
- Resumo dos documentos recebidos com status *"Em Auditoria"*.
- Prazo estimado de resposta (ex: até 2 dias úteis).

---

## 6. Componentes Canônicos (HTML & Tailwind CSS)

### A. Badge de Status Documental
```html
<!-- Aprovado -->
<span class="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-800 border border-emerald-300">
  <svg class="w-3.5 h-3.5 text-emerald-600" fill="currentColor" viewBox="0 0 20 20">
    <path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd"/>
  </svg>
  Conforme (MEC 315)
</span>

<!-- Pendência / Em Análise -->
<span class="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-amber-50 text-amber-800 border border-amber-300">
  <svg class="w-3.5 h-3.5 text-amber-600" fill="currentColor" viewBox="0 0 20 20">
    <path fill-rule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clip-rule="evenodd"/>
  </svg>
  Carimbo Ilegível
</span>
```

### B. Barra de Ações Rápidas do Revisor
```html
<div class="flex items-center justify-between p-4 bg-slate-900 text-white rounded-lg shadow-lg">
  <div class="flex items-center space-x-3">
    <span class="text-xs uppercase tracking-wider text-slate-400 font-medium">Atalhos rápidos:</span>
    <kbd class="px-2 py-1 text-xs font-mono bg-slate-800 border border-slate-700 rounded text-slate-300">A</kbd>
    <span class="text-xs text-slate-400">Aprovar</span>
    <kbd class="px-2 py-1 text-xs font-mono bg-slate-800 border border-slate-700 rounded text-slate-300">R</kbd>
    <span class="text-xs text-slate-400">Rejeitar</span>
  </div>
  <div class="flex space-x-3">
    <button class="px-4 py-2 text-sm font-semibold rounded-md bg-red-600 hover:bg-red-700 text-white transition focus:ring-2 focus:ring-red-500">
      Reprovar Documento (R)
    </button>
    <button class="px-5 py-2 text-sm font-semibold rounded-md bg-emerald-600 hover:bg-emerald-700 text-white transition focus:ring-2 focus:ring-emerald-500">
      Homologar no Acervo (A)
    </button>
  </div>
</div>
```
