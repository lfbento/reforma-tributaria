# Design: default-regime-presumido

## Context

Veja `proposal.md` para motivação e `specs/contract-triage/spec.md` para os requisitos.
Hoje `engine.py` e `deliverables.py` usam fallback inline `header.regime or "presumido"`, mas `premises.yaml` não declara `regime_padrao` e a CLI não possui `--regime`, o que levou à execução da amostra com `"regime": "real"` no JSON de entrada.

## Goals / Non-Goals

**Goals:**
- Tornar explícito `regime_padrao: presumido` em `premises.yaml` e `PremiseSet`.
- Permitir sobrescrita de regime diretamente via CLI (`--regime {presumido,real,simples}`).
- Corrigir a análise e todos os entregáveis do pedido `4515655362` na pasta `amostra/` para **Lucro Presumido** (PIS 0,65% + COFINS 3,00%).

**Non-Goals:**
- Alterar as fórmulas de cálculo do Lucro Presumido ou Lucro Real no `engine.py`.

## Decisions

1. **Centralização em `premises.yaml` (`regime_padrao`)**
   - Adicionar `regime_padrao` em `premises.yaml` (valor `"presumido"`) e expor `PremiseSet.regime_padrao` e `PremiseSet.regime_source` (análogos a `cenario` / `cenario_source`).
   - `pipeline.analyze()`, `engine._rates()` e `deliverables._calculo_sheet()` usam `header.regime or ps.regime_padrao`.

2. **Flag `--regime` na CLI (`cli.py`)**
   - Adicionar `--regime` com `choices=["presumido", "real", "simples"]` nos subcomandos `triage`, `calc`, `xlsx`, `report` e `run`, aplicando o valor ao `header.regime` antes da análise.

3. **Regeneração oficial da amostra (`4515655362`)**
   - Executar `run` e `validate` com `input_4515655362_presumido.json` para que `4515655362.xlsx`, `parecer-4515655362.md`, `carta-4515655362.md`, `memorando-4515655362.docx` e `validacao.json` em `saida_real/` reflitam **Lucro Presumido**.

## Risks / Trade-offs

- **Divergência entre o líquido citado no TAP (R$ 197.956,99) e o líquido de Lucro Presumido (R$ 211.484,28)** → Sinalizar claramente na pendência/observação do item que a empresa é Lucro Presumido (3,65% PIS/COFINS) e que o líquido do TAP deve ser conferido com a contabilidade/orçamento.
