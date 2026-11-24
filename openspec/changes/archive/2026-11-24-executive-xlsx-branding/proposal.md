# Proposal

## Why

A planilha XLSX gerada atualmente por `deliverables.py` não possui formatação executiva nem identidade visual — é exportada com células cruas, sem formatação monetária/percentual, sem largura de colunas ajustada, sem logos e sem metadados de governança (nome da empresa, data do cálculo e data da base legal). Como o relatório será apresentado diretamente para a Diretoria, é necessário transformar o XLSX em um entregável corporativo de alto padrão visual, incorporando o logo da empresa (`NNNN.png` na raiz do projeto) e o logo do cliente extraído automaticamente do PDF do pedido de compra.

## What Changes

- **Extração automática de logo do cliente (`intake.py` / `models.py`):**
  - Extrair imagem/logo embutido da primeira página do PDF do pedido de compra via `pdfplumber` / `pypdf` (ou renderização segura em PNG via `Pillow`), salvando ou referenciando como asset para a planilha.
- **Formatação executiva e identidade visual na planilha XLSX (`deliverables.py`):**
  - **Cabeçalho corporativo na aba `Resumo`:** inserção do logo da empresa (`NNNN.png` na raiz do projeto ou caminho configurável via CLI/opção) à esquerda e do logo do cliente (extraído do PDF do pedido) à direita, acompanhados de:
    - Nome da empresa (padrão configurável, ex.: `Nacional Indústria Mecânica Eireli`),
    - Título executivo com número do pedido e nome do cliente,
    - **Data do cálculo** (data/hora de geração),
    - **Data da base de dados das leis / premissas** (ex.: referência da versão/data das normas EC 132/2023, LC 214/2025 e TCU TC 006.529/2026-7 em `premises.yaml`).
  - **Estilização executiva em todas as 6 abas (`Premissas`, `Calculo_Bens`, `Calculo_Servicos`, `Saldo_2027`, `Resumo`, `Fontes`):**
    - Paleta corporativa (cabeçalhos azul-marinho `#1B365D` com fonte branca em negrito), linhas zebradas (`#F7F9FC`), bordas sutis, congelamento de painéis (`freeze_panes`), auto-ajuste de largura de colunas com quebra de texto, formatação numérica (`R$ #,##0.00`, `0,00%`, `0,0000%`), destaque condicional/visual para variações e flags (`ALTO RISCO`, `PENDENTE – confirmar`), e configuração de impressão em paisagem ajustada à largura da página.
- **Preservação integral das fórmulas vivas e compatibilidade:**
  - Manter exatamente os nomes das 6 abas (`SHEETS`), a estrutura da linha 1 nas abas de cálculo/premissas/saldo/fontes e todas as fórmulas ligadas à aba `Premissas`.

## Capabilities

### New Capabilities

_(nenhuma — evolui a extração de ativos visuais do pedido e a apresentação dos entregáveis em XLSX)_

### Modified Capabilities

- `negotiation-deliverables`: adiciona requisitos de formatação executiva no XLSX (paleta, formatos numéricos, larguras, congelamento, impressão) e cabeçalho institucional na aba `Resumo` com logo da empresa (`NNNN.png`), logo do cliente, nome da empresa, data do cálculo e data da base legal.
- `contract-intake`: adiciona extração opcional da imagem/logo do cliente a partir da primeira página do PDF do pedido de compra.

## Impact

- **Código afetado:** `src/reforma_tributaria/deliverables.py`, `src/reforma_tributaria/intake.py`, `src/reforma_tributaria/models.py`, `src/reforma_tributaria/premises.yaml`, `src/reforma_tributaria/cli.py` e `pyproject.toml` (inclusão de `Pillow>=10.0` como dependência para inserção de imagens no `openpyxl`).
- **Testes:** novos testes em `tests/test_deliverables.py` e `tests/test_intake.py` validando estilos, formatos numéricos, metadados executivos e inserção/extração de logos (com fallback gracioso quando `NNNN.png` ou logo do PDF não existir).
