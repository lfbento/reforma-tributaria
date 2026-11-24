# Proposal

## Why

A minuta de comunicação ao cliente (`build_carta` / `carta-<numero>.md`) é gerada hoje apenas como Markdown simples, sem estrutura formal de memorando nem aplicação da identidade institucional da empresa. Como o usuário disponibilizou o modelo oficial `Papel timbrado.docx` na raiz do projeto, precisamos evoluir a minuta para formato de **Memorando formal** e gerar automaticamente o documento Word (`memorando-<numero>.docx`) diretamente sobre o papel timbrado da Nacional Indústria.

## What Changes

- **Evolução de `build_carta()` para formato de Memorando:**
  - Estruturar o texto com cabeçalho oficial de Memorando (`MEMORANDO TÉCNICO-COMERCIAL`, `De:`, `Para:`, `Data:`, `Ref.:`, `Assunto:`), mantendo integralmente todos os elementos exigidos pela spec (fundamento EC 132/2023, LC 214/2025 e cláusula contratual, valor-base apurado, nova PPU proposta para 2027, ressalva sobre CBS/IBS na base do ICMS/ISS, pedido de aditivo/revisão e marcação `RASCUNHO — não enviado`).
- **Geração do Memorando em DOCX sobre o papel timbrado (`build_memorando_docx()`):**
  - Carregar o modelo `Papel timbrado.docx` da raiz do projeto (ou caminho customizado via `--letterhead`), preservando integralmente seu cabeçalho e rodapé oficiais da Nacional.
  - Preencher o corpo com tipografia corporativa (`Calibri`/tabela de metadados `De`/`Para`/`Data`/`Assunto` + tabela resumo de preços `Atual vs 2027 Cenário A` + corpo formal e assinatura), salvando `memorando-<numero>.docx` na pasta de saída do `report` / `run` (além de um subcomando ou flag opcional na CLI).
  - Fallback gracioso: se `Papel timbrado.docx` não existir no ambiente, criar documento Word limpo sem quebrar o pipeline.
- **Dependência:** adicionar `python-docx>=1.1` ao `pyproject.toml`.

## Capabilities

### New Capabilities

_(nenhuma — evolui o entregável de comunicação já definido em `negotiation-deliverables`)_

### Modified Capabilities

- `negotiation-deliverables`: atualiza o requisito `Minuta de carta ou e-mail ao cliente` para formato de memorando formal e adiciona geração de arquivo DOCX utilizando o modelo `Papel timbrado.docx` da empresa.

## Impact

- **Código afetado:** `src/reforma_tributaria/deliverables.py`, `src/reforma_tributaria/cli.py`, `pyproject.toml`.
- **Testes:** `tests/test_deliverables.py` e `tests/test_cli.py` (mantendo retrocompatibilidade de `carta-<numero>.md` e validando o novo `memorando-<numero>.docx`).
