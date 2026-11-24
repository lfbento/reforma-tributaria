# Tasks

## 1. Configuração de Regime Padrão (Lucro Presumido)

- [x] 1.1 Adicionar `regime_padrao: presumido` em `src/reforma_tributaria/premises.yaml` e expor `regime_padrao` / `regime_source` em `PremiseSet` (`src/reforma_tributaria/premises.py`), validando com testes em `tests/test_premises.py`.
- [x] 1.2 Atualizar `src/reforma_tributaria/pipeline.py`, `src/reforma_tributaria/engine.py` e `src/reforma_tributaria/deliverables.py` para usar `ps.regime_padrao` quando `header.regime` for omitido, e adicionar `--regime {presumido,real,simples}` na CLI (`src/reforma_tributaria/cli.py`), validando com testes em `tests/test_engine.py` e `tests/test_cli.py`.

## 2. Recálculo e Regeneração dos Entregáveis na Pasta Amostra

- [x] 2.1 Atualizar a análise oficial do pedido `4515655362` em `amostra/4515655362-CONJUNTO DE RESFRIADOR A AR/analise_reforma_2027/` para Lucro Presumido (PIS 0,65% + COFINS 3,00%), regerando `4515655362.xlsx`, `parecer-4515655362.md`, `carta-4515655362.md`, `memorando-4515655362.docx` e `validacao.json` com `conferencias_ok: true`.
- [x] 2.2 Executar a suíte completa `pytest` e `openspec validate default-regime-presumido` confirmando que todos os testes e validações passam.
