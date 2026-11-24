# Tasks

## 1. Dependências, Metadados Legais e Extração de Logo do Cliente

- [x] 1.1 Adicionar `Pillow>=10.0` em `pyproject.toml`, registrar `legal_base_date` em `src/reforma_tributaria/premises.yaml` (e expor em `PremiseSet` em `src/reforma_tributaria/premises.py`) e adicionar campo opcional `client_logo_path` em `ContractHeader` / `ContractAnalysis` (`src/reforma_tributaria/models.py`), validando com testes em `tests/test_premises.py` e `tests/test_models.py`.
- [x] 1.2 Implementar `extract_pdf_logo()` em `src/reforma_tributaria/intake.py` para extrair a imagem de logotipo da página 1 do PDF (com fallback silencioso caso não haja imagem ou stream não decodificável) e integrá-la em `extract_pdf()` / `cli.py`, validando com teste unitário em `tests/test_intake.py` e extração real no PDF da pasta `amostra`.

## 2. Formatação Executiva e Identidade Visual no XLSX

- [x] 2.1 Implementar módulo/helpers de estilização executiva em `src/reforma_tributaria/deliverables.py` (paleta `#1B365D`/`#D9E1F2`/`#F7F9FC`, fontes, bordas, formatos numéricos `R$ #,##0.00` e `0.00%`, `freeze_panes`, filtro automático, largura automática de colunas, destaque de variação/flags e setup de impressão em paisagem) aplicados às 6 abas sem alterar a linha 1 nem quebrar fórmulas, validando em `tests/test_deliverables.py`.
- [x] 2.2 Implementar cabeçalho executivo na aba `Resumo` em `src/reforma_tributaria/deliverables.py` com inserção dos logos (`NNNN.png` na raiz do projeto à esquerda e logo do cliente à direita, redimensionados proporcionalmente e com fallback gracioso), nome da empresa, data do cálculo e data da base legal das premissas, além de flags opcionais `--empresa`, `--logo` e `--client-logo` em `src/reforma_tributaria/cli.py`, validando com testes em `tests/test_deliverables.py` e `tests/test_cli.py`.

## 3. Verificação Final e Geração na Pasta Amostra

- [x] 3.1 Executar a suíte completa `pytest`, `openspec validate executive-xlsx-branding` e regerar a planilha executiva do pedido `4515655362` em `amostra/4515655362-CONJUNTO DE RESFRIADOR A AR/analise_reforma_2027/` verificando presença das imagens, estilos e fórmulas.
