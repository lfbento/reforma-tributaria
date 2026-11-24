# Proposal

## Why

O módulo atual de ingestão (`intake.py` / `cli.py`) suporta apenas planilhas `.xlsx`, texto rotulado em `.pdf` via `pdfplumber` (com exigência rígida do separador `|`) e e-mails `.eml` em texto puro — falhando em arquivos `.msg` binários do Outlook, documentos `.docx`/`.pptx`, pacotes compactados `.zip`/`.rar`, cronogramas `.mpp` e PDFs escaneados ou com tabelas complexas. Já possuímos na máquina e na skill `convert-office-docs` ferramentas validadas (`markitdown`, `docling`, `jpype1`/`mpxj.jar`, `7z.exe`) que podem ser integradas em uma arquitetura híbrida preservando a rastreabilidade estrita (`arquivo`, `aba`/`célula` ou `página`) exigida por `contract-intake`.

## What Changes

- Suporte nativo a novos formatos na ingestão de documentos:
  - `.docx`, `.pptx` e `.msg` (Outlook binário, corrigindo a limitação atual de `extract_email`) via `MarkItDown`.
  - `.zip` e `.rar` via extração recursiva com 7-Zip (`7z.exe`) em diretório temporário.
  - `.mpp` (MS Project) via `MPXJ` + `JPype` (Java), convertendo tarefas e datas para análise de cronograma/corte 2026-2027.
- Fallback inteligente para `.pdf`: mantém `pdfplumber` como fast-path leve e aciona `Docling` em subprocesso isolado quando o PDF for escaneado ou sem texto/tabelas extraíveis, preservando o número da página (`Source.pagina`) a partir dos metadados do `DoclingDocument`.
- Preservação do extrator `openpyxl` para `.xlsx` (PPU e cronograma), mantendo rastreabilidade exata de `aba` e `célula`.
- Adição de utilitários de robustez inspirados no `convert-office-docs`: suporte a caminhos longos no Windows (`\\?\`) e cache incremental por hash MD5 para evitar reprocessamento de PDFs pesados.
- Organização de dependências em extras opcionais no `pyproject.toml` (`[office]`, `[docling]`, `[mpp]`, `[full]`) mantendo degradação graciosa caso algum extra não esteja instalado em outro ambiente.

## Capabilities

### New Capabilities

_(nenhuma — a mudança expande os formatos e a resiliência da capacidade existente de ingestão)_

### Modified Capabilities

- `contract-intake`: ampliação dos formatos aceitos (`.docx`, `.pptx`, `.msg`, `.zip`, `.rar`, `.mpp` e PDFs escaneados/complexos), preservação de rastreabilidade por página no fallback Docling, extração de datas de corte em `.mpp` e suporte a pacotes compactados mantendo a regra de não inventar valores.

## Impact

- **Código afetado:** `src/reforma_tributaria/intake.py`, `src/reforma_tributaria/cli.py`, `pyproject.toml`, e novos testes em `tests/test_intake.py` / `tests/test_cli.py`.
- **Dependências:** `markitdown`, `docling`, `jpype1` declaradas como extras opcionais em `pyproject.toml`; dependências externas opcionais `7z.exe` e `Java (JRE 11+) + mpxj.jar`.
- **Compatibilidade:** Retrocompatível com todos os fluxos, schemas JSON e testes existentes.
