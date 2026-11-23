# Reforma Tributária 2027 — Agente Analisador

Núcleo determinístico de cálculo do impacto da Reforma Tributária do consumo
(EC 132/2023, LC 214/2025) em pedidos de compra (PC/OC/PV) e contratos **emitidos
em 2026** com execução, entrega ou faturamento em **2027 ou depois**, orquestrado
por um agente omp. Gera a base técnica para revisar e negociar o preço.

O contrato de comportamento está em `openspec/changes/add-tax-reform-agent/`
(proposal, specs, design, tasks). O prompt governante do agente está em
`Prompt do agente – Reforma Tributária 2027.md`.

## Arquitetura

- **Núcleo Python determinístico** (`src/reforma_tributaria/`): cálculo em
  `Decimal`, conferências e geração de XLSX com fórmulas vivas. Reproduz os
  exemplos Petrobras validados com tolerância de R$ 0,01 nos totais.
- **Agente omp** (skill `.omp/skills/reforma-tributaria/` + comando
  `.omp/commands/reforma-tributaria.md`): extração assistida de documentos,
  julgamento de triagem e redação dos entregáveis, invocando a CLI.

Módulos: `intake`, `triage`, `premises`, `engine`, `deliverables`, `pipeline`, `cli`.

## Instalação

```bash
python3 -m venv .venv            # ou: uv venv --seed .venv
.venv/bin/pip install -e ".[dev]"
.venv/bin/python -c "import reforma_tributaria; print(reforma_tributaria.__version__)"
```

Dependências: `openpyxl`, `pdfplumber`, `PyYAML`; testes com `pytest`.

## Premissas editáveis

Os padrões do cenário 2027 (com fonte por parâmetro) estão em
`src/reforma_tributaria/premises.yaml`:

- PIS 0,65% (Presumido) / 1,65% (Real); Cofins 3,00% / 7,60% — extintos em 2027.
- ICMS/ISS mantidos em 2027; IPI 0% (salvo exceções ZFM).
- CBS referência **11,3468%** (TCU TC 006.529/2026-7), redução transitória 0,1 p.p.
  → **CBS efetiva 11,2468%**; IBS 0,10% (0,05% estadual + 0,05% municipal).
- Cenário **A** (CBS/IBS na base do ICMS/ISS) é o preço proposto; **B** é a
  sensibilidade.

Alterar uma premissa recalcula tudo. Pela CLI:

```bash
.venv/bin/python -m reforma_tributaria run entrada.json --outdir saida/ \
    --override cbs_referencia=0.12
```

Ou edite a aba **Premissas** do XLSX gerado (as fórmulas recalculam ao abrir no
Excel/LibreOffice).

## Fluxo (CLI)

| Comando | Função |
|---|---|
| `extract <doc> --out entrada.json` | PDF/XLSX/e-mail/DFP → JSON estruturado com proveniência |
| `triage entrada.json` | escopo 2026→2027, natureza, regime, cláusula |
| `calc entrada.json` | cálculo por item (cenários A e B) |
| `validate entrada.json` | conferências obrigatórias (exit 1 se divergir) |
| `xlsx entrada.json --out planilha.xlsx` | planilha com as seis abas |
| `report a.json b.json --outdir saida/` | parecer, carta, priorização, pendências |
| `run a.json b.json --outdir saida/` | pipeline completo → todos os entregáveis |

`run` gera, por pedido: `<numero>.xlsx`, `parecer-<numero>.md`,
`carta-<numero>.md`, `pendencias-<numero>.md`; e ainda `priorizacao.md` (ordenada
por impacto no saldo 2027; sem cláusula → `ALTO RISCO`) e `validacao.json`.

**Apenas rascunhos — o agente nunca envia e-mails nem cartas.**

### Exemplo documentado (fixture Petrobras validada)

```bash
.venv/bin/python -m reforma_tributaria run tests/fixtures/petrobras.json --outdir saida/
```

Produz `saida/4600685026.xlsx`, `saida/parecer-4600685026.md`,
`saida/carta-4600685026.md`, `saida/priorizacao.md` e `saida/validacao.json` com
`conferencias_ok: true`.

## Valores de referência (Lucro Presumido, CBS 11,2468%, IBS 0,1%)

| Tipo | Fator A | Fator B |
|---|---|---|
| Bens (ICMS 12%, sem DIFAL/IPI) | 1,067284 (+6,73%) | ≈1,054230 (+5,42%) |
| Serviços (ISS 3%) | 1,071569 (+7,16%) | ≈1,068290 (+6,83%) |

Contrato Petrobras ICJ 5900.0131958.25.2 / SAP 4600685026:
- Bens (42 itens): R$ 38.776.540,91 → R$ 41.385.596,58 (+R$ 2.609.055,67); base R$ 32.708.012,26.
- Serviços (5 itens): R$ 16.428.186,00 → R$ 17.603.942,43 (+R$ 1.175.756,43); base R$ 15.335.711,63.

## Testes

```bash
.venv/bin/pytest
```

Cobrem premissas, modelos, intake, triagem, motor (incluindo os fixtures
Petrobras), entregáveis (com recálculo das fórmulas do XLSX) e a CLI de ponta a
ponta.

## Fora do escopo

- Cálculo para Simples Nacional (apenas sinalizado para tratamento específico).
- Créditos de PIS/Cofins e CBS/IBS no Lucro Real (afetam a margem, não o preço).
- Envio de comunicações (somente rascunhos).