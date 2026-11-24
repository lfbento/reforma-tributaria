# Tasks

## 1. Empacotamento e Utilitários de Sistema de Arquivos

- [x] 1.1 Atualizar `pyproject.toml` adicionando os extras opcionais `[office]` (`markitdown`), `[docling]` (`docling`), `[mpp]` (`jpype1`) e `[full]`, e verificar com `python -m pip check` ou importação que as dependências opcionais não quebram o núcleo leve.
- [x] 1.2 Implementar utilitários `safe_path()` (suporte a caminhos longos `\\?\` e `\\?\UNC\` no Windows), `file_hash()` (MD5 em chunks) e camada de cache incremental (`.intake-cache.json`) em `src/reforma_tributaria/intake.py`, cobrindo com testes unitários em `tests/test_intake.py`.

## 2. Suporte a Office (.docx, .pptx, .msg) e Tabelas Markdown

- [x] 2.1 Evoluir `_parse_labeled_text()` em `src/reforma_tributaria/intake.py` para aceitar linhas de tabelas Markdown (`| ... |` com pipes nas extremidades) ignorando separadores `|---|`, e validar com teste unitário em `tests/test_intake.py`.
- [x] 2.2 Implementar extração via `MarkItDown` para `.docx`, `.pptx` e `.msg` (corrigindo o roteamento de `.msg` que antes chamava `email.message_from_bytes` exclusivo de `.eml`), com tratamento claro caso `markitdown` não esteja instalado; validar com testes unitários em `tests/test_intake.py`.

## 3. Fallback Docling para PDFs Complexos / Escaneados

- [x] 3.1 Implementar fallback `Docling` em subprocesso isolado dentro de `extract_pdf()` quando `pdfplumber` retornar páginas vazias ou nenhum item estruturado, extraindo blocos agrupados por `page_no` para preservar `Source.pagina`, além de usar o cache MD5 para evitar reprocessamento; validar com teste unitário mockado em `tests/test_intake.py` e verificar funcionamento real com `pytest`.

## 4. Cronogramas MS Project (.mpp) e Pacotes Compactados (.zip/.rar)

- [x] 4.1 Implementar `extract_mpp()` em `src/reforma_tributaria/intake.py` usando `JPype` + `mpxj.jar` (buscando via `MPXJ_JAR`, `lib/mpxj.jar` ou caminho da skill `convert-office-docs`) para extrair tarefas e identificar corte temporal 2026/2027 sinalizando valores financeiros ausentes como `PENDENTE – confirmar`, validando com testes unitários em `tests/test_intake.py`.
- [x] 4.2 Implementar extração recursiva de `.zip` e `.rar` (via `7z.exe` nos caminhos padrão ou `zipfile` como fallback para `.zip`) e integrar o roteamento de `.docx`, `.pptx`, `.msg`, `.mpp`, `.zip` e `.rar` no comando `extract` de `src/reforma_tributaria/cli.py`, validando com testes em `tests/test_cli.py`.

## 5. Verificação de Integração

- [x] 5.1 Executar a suíte completa de testes (`pytest`) e `openspec validate enhance-contract-intake` para garantir retrocompatibilidade com todos os fluxos existentes e conformidade com a spec.
