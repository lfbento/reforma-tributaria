# Design: enhance-contract-intake

## Context

Veja `proposal.md` para a motivação e `specs/contract-intake/spec.md` para os requisitos comportamentais.
Atualmente `src/reforma_tributaria/intake.py` possui extratores leves e determinísticos (`openpyxl` e `pdfplumber`), enquanto `src/reforma_tributaria/cli.py` roteia extensões no comando `extract`. Na prática:
- `.msg` é roteado para `extract_email()`, que usa `email.message_from_bytes` (funciona apenas para `.eml`, falhando em `.msg` binário do Outlook).
- `.docx`, `.pptx`, `.zip`, `.rar` e `.mpp` não são suportados.
- `pdfplumber` extrai apenas texto linear procurando `|`, falhando em PDFs escaneados ou tabelas sem delimitador explícito.

O ambiente da máquina já conta com `markitdown`, `docling`, `jpype1`, OpenJDK 21, `7z.exe` (`C:\Program Files\7-Zip\7z.exe`) e `mpxj.jar` (na skill `convert-office-docs`).

## Goals / Non-Goals

**Goals:**
- Unificar no módulo `intake.py` / `cli.py` a capacidade de leitura multi-formato da skill `convert-office-docs` sem abrir mão da rastreabilidade (`Source`: arquivo, aba/célula ou página).
- Manter o caminho leve (`openpyxl` + `pdfplumber`) como padrão rápido, acionando `Docling` apenas como fallback.
- Garantir degradação graciosa caso `docling`, `jpype1`/`mpxj.jar` ou `7z.exe` não estejam disponíveis em outro ambiente.

**Non-Goals:**
- Alterar o motor de cálculo tributário (`engine.py`), triagem (`triage.py`) ou geradores de entregáveis (`deliverables.py`).
- Substituir o `openpyxl` por `MarkItDown` na leitura de `.xlsx` (pois `MarkItDown` perde a coordenada exata de aba e célula).

## Decisions

1. **Extração híbrida por tipo de arquivo (Fast-path vs. Fallback)**
   - **`.xlsx`**: mantém `openpyxl` diretamente em `extract_xlsx()` e `extract_schedule()`. *Alternativa descartada:* converter `.xlsx` com MarkItDown (perderia `Source.aba` e `Source.celula`).
   - **`.pdf`**: executa `pdfplumber` primeiro (rápido, leve, página exata). Se o texto extraído for vazio (PDF escaneado) ou não houver itens estruturados identificados e o usuário/CLI habilitar fallback, aciona `Docling` em subprocesso isolado.
   - **`.docx`, `.pptx`, `.msg`**: usa `MarkItDown` para gerar texto/Markdown e alimenta `_parse_labeled_text` + tabela Markdown. Corrige o bug atual de `.msg` mantendo `email.message_from_bytes` exclusivo para `.eml`.

2. **Preservação de página (`Source.pagina`) no Docling**
   - Em vez de chamar `res.document.export_to_markdown()` em bloco único, o worker em subprocesso deve agrupar itens do `DoclingDocument` por número de página (`prov[0].page_no` quando disponível, fallback página `1`), retornando JSON `list[tuple[int, str]]` compatível com `_parse_labeled_text(pages, arquivo)`.

3. **Isolamento de processo para Docling e resolução de dependências externas**
   - `Docling` carrega modelos pesados de visão/OCR em memória; será executado em subprocesso (`subprocess.run([sys.executable, "-c", ...])`) com timeout configurável e captura de erro, evitando vazamento de RAM no processo principal.
   - **7-Zip**: buscar `"7z"`, `C:\Program Files\7-Zip\7z.exe` e `C:\Program Files (x86)\7-Zip\7z.exe` (como em `converter.py`), pois nesta máquina `7z` não está no `PATH`, mas existe em `Program Files`. Para `.zip`, pode usar `zipfile` nativo como fallback se `7z.exe` não existir.
   - **MPXJ (`.mpp`)**: localizar `mpxj.jar` via variável de ambiente `MPXJ_JAR`, diretório local do pacote (`src/reforma_tributaria/lib/mpxj.jar`) ou fallback para o caminho da skill `convert-office-docs` se presente.

4. **Parser de tabelas Markdown no `_parse_labeled_text`**
   - Documentos convertidos via `MarkItDown` ou `Docling` geram tabelas no formato `| col1 | col2 | ... |` com linha separadora `|---|---|`. O parser de itens deve ignorar linhas separadoras (`---`) e cabeçalhos repetidos de tabela Markdown, além de aceitar pipes nas extremidades (`| a | b |`).

5. **Utilitários de sistema de arquivos e cache**
   - Incorporar `safe_path()` (`\\?\` e `\\?\UNC\`) para suportar caminhos >260 caracteres no Windows.
   - Incorporar cache opcional por hash MD5 (`.intake-cache.json` ou diretório configurável) para resultados de conversão pesada (PDF/Docling).

6. **Empacotamento em `pyproject.toml`**
   - Manter `openpyxl`, `pdfplumber` e `PyYAML` nas dependências core, e adicionar `markitdown`, `docling` e `jpype1` em `optional-dependencies` (`office`, `docling`, `mpp`, `full`) para não quebrar instalações minimalistas ou CI sem GPU.

## Risks / Trade-offs

- **Tempo de execução e RAM do Docling** → Mitigado acionando Docling apenas como fallback (quando `pdfplumber` não encontra texto/itens), rodando em subprocesso isolado e usando cache por hash MD5.
- **Dependência externa de JVM e `mpxj.jar` para `.mpp`** → Mitigado validando a presença antes de iniciar a JVM (`jpype.startJVM`) e emitindo erro/aviso claro sem afetar outros formatos.
- **Testes automatizados em ambientes sem Docling/Java** → Mitigado mantendo testes unitários rápidos com mocks para Docling/MPXJ/7-Zip e marcando testes reais de integração pesados como opcionais ou condicionais.
