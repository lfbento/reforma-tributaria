# Proposal

## Why

A análise executada na pasta `amostra` (Pedido `4515655362`) considerou a Nacional Indústria no regime **Lucro Real** (PIS `1,65%` + COFINS `7,60%`), quando na realidade a empresa é tributada pelo **Lucro Presumido** (PIS `0,65%` + COFINS `3,00%`), alterando significativamente a base líquida, as alíquotas e o impacto em 2027 (de `+R$ 128,94` para `+R$ 16.644,55` no Cenário A). É necessário fixar **Lucro Presumido (`presumido`)** como regime padrão explícito em `premises.yaml`, expor override explícito `--regime` na CLI e corrigir/regerar os entregáveis da amostra.

## What Changes

- **Regime padrão explícito em `premises.yaml` e `PremiseSet`:**
  - Adicionar `regime_padrao: presumido` em `src/reforma_tributaria/premises.yaml` (com fonte indicando Lucro Presumido da Nacional Indústria — PIS `0,65%` + COFINS `3,00%`) e expor em `PremiseSet`.
  - Garantir que `pipeline.py`, `engine.py` e `deliverables.py` utilizem `ps.regime_padrao` quando `header.regime` não for explicitamente informado (ou quando sobrescrito via CLI).
- **Flag `--regime` na CLI (`cli.py`):**
  - Adicionar `--regime {presumido,real,simples}` nos subcomandos `triage`, `calc`, `xlsx`, `report` e `run` para permitir conferência ou sobrescrita explícita sem editar o JSON de entrada.
- **Correção dos entregáveis da pasta `amostra` (`4515655362`):**
  - Atualizar a análise oficial do pedido `4515655362` para **Lucro Presumido** e regerar `4515655362.xlsx`, `parecer-4515655362.md`, `carta-4515655362.md`, `memorando-4515655362.docx` e `validacao.json`.

## Capabilities

### New Capabilities

_(nenhuma — formaliza o regime padrão da empresa na triagem existente)_

### Modified Capabilities

- `contract-triage`: explicita `Lucro Presumido` (`presumido`) como regime padrão quando não houver DFP ou indicação contrária, permitindo sobrescrita controlada via premissas/CLI.

## Impact

- **Código afetado:** `src/reforma_tributaria/premises.yaml`, `src/reforma_tributaria/premises.py`, `src/reforma_tributaria/engine.py`, `src/reforma_tributaria/pipeline.py`, `src/reforma_tributaria/deliverables.py`, `src/reforma_tributaria/cli.py`.
- **Amostra:** `amostra/4515655362-CONJUNTO DE RESFRIADOR A AR/analise_reforma_2027/`.
- **Testes:** `tests/test_premises.py`, `tests/test_engine.py`, `tests/test_cli.py`.
