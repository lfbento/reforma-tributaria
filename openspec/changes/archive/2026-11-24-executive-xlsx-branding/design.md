# Design: executive-xlsx-branding

## Context

Veja `proposal.md` para motivação e `specs/` para requisitos.
Atualmente `src/reforma_tributaria/deliverables.py` cria as 6 abas (`Premissas`, `Calculo_Bens`, `Calculo_Servicos`, `Saldo_2027`, `Resumo`, `Fontes`) usando `ws.append(...)` sem qualquer estilo (`Font`, `PatternFill`, `Border`, `Alignment`, `number_format`, `column_dimensions`, `freeze_panes`) nem imagens.
Além disso, `tests/test_deliverables.py` valida contratos estruturais específicos:
- `wb.sheetnames == dv.SHEETS` (exatamente as 6 abas).
- `wb["Calculo_Bens"][1]` == `dv.CALC_COLS` e `ws["H2"]`, `ws["W2"]`, `ws["P2"]` com fórmulas.
- `wb["Saldo_2027"][1]` sendo o cabeçalho da tabela.
- `wb["Resumo"]` consultado por `ws.cell(r, 1).value` (rótulo) e `ws.cell(r, 2).value` (valor/fórmula) para `r >= 2`.

## Goals / Non-Goals

**Goals:**
- Elevar o padrão visual do XLSX para apresentação à Diretoria mantendo 100% de compatibilidade com os testes e contratos existentes.
- Inserir logo da empresa (`NNNN.png` na raiz do projeto, ou caminho configurável) e logo do cliente (extraído da página 1 do PDF do pedido via `pdfplumber`/`Pillow`).
- Exibir na aba `Resumo` o nome da empresa, data do cálculo e data da base legal das normas (`premises.yaml`).

**Non-Goals:**
- Alterar a lista ou nomes das 6 abas (`SHEETS`).
- Alterar fórmulas de cálculo em `engine.py` ou a estrutura da linha 1 nas abas `Premissas`, `Calculo_Bens`, `Calculo_Servicos`, `Saldo_2027` e `Fontes`.

## Decisions

1. **Preservação de coordenadas nas abas de dados + Banner executivo no `Resumo`**
   - Nas abas `Premissas`, `Calculo_Bens`, `Calculo_Servicos`, `Saldo_2027` e `Fontes`, a linha 1 permanece como cabeçalho da tabela para não quebrar referências (`Premissas!$B$2`, `Calculo_Bens!H2`, etc.), recebendo estilização corporativa (fundo `#1B365D`, fonte branca negrito, altura 28, `freeze_panes = "A2"`, filtro automático).
   - Na aba `Resumo`:
     - Linhas 1 a 5: faixa de cabeçalho executivo (título da análise, logo da empresa à esquerda em `A1`, logo do cliente à direita em `D1`, mesclagem visual limpa com altura adequada para as imagens).
     - Linhas 6 a 9: metadados de governança em colunas `A`/`B` (`Empresa`, `Pedido / Cliente`, `Data do cálculo`, `Base legal das premissas`), preservando a leitura `ws.cell(r, 1) -> ws.cell(r, 2)` esperada por `test_resumo_conteudo`.
     - A partir da linha 11: tabela de indicadores financeiros (`Total atual`, `Base total`, `Total 2027 (A)`, `Total 2027 (B)`, `Variação R$ (A)`, `Variação % (A)`, `Saldo 2027`, `Impacto no saldo 2027`, `Cláusula de revisão`, `Conferências`).

2. **Extração do logo do cliente a partir do PDF (`extract_pdf_logo`)**
   - `pdfplumber` expõe `page.images` com `stream` (`PDFStream`) na página 1. Usando `Pillow` (`PIL.Image`), decodificamos o stream (ou `pypdf`/`pdfplumber` XObject) e salvamos como PNG temporário/persistido (ex.: ao lado do JSON extraído ou em cache), gravando o caminho em `ContractHeader.client_logo_path` ou `Document` / campo de entrada `client_logo_path`.
   - Caso a extração do stream XObject bruto precise de reconstrução de paleta/máscara (como `/DeviceRGB` com `FlateDecode` ou `DCTDecode`), usar `PIL.Image.frombytes` / `BytesIO` com fallback seguro caso o formato do XObject não seja diretamente decodificável.

3. **Configuração de empresa e base legal**
   - Adicionar campo `legal_base_date` em `src/reforma_tributaria/premises.yaml` (ex.: `"2026-10-01 — EC 132/2023, LC 214/2025 e TCU TC 006.529/2026-7"`).
   - Nome da empresa padrão `"Nacional Indústria Mecânica Eireli"` e caminho do logo padrão `"NNNN.png"` buscado na raiz do projeto (CWD ou raiz do pacote), ambos sobrescrevíveis via parâmetros em `build_workbook()` e flags opcionais na CLI (`--empresa`, `--logo`, `--client-logo`).

4. **Paleta e Formatação Numérica**
   - Paleta: Azul-marinho corporativo `#1B365D` (cabeçalhos), Azul-claro `#D9E1F2` (subtítulos/totais), Cinza-gelo `#F7F9FC` (zebra), Verde suave `#E2EFDA` / Vermelho suave `#FCE4D6` para variação e flags de risco (`ALTO RISCO` / `PENDENTE`).
   - Formatos: `R$ #,##0.00` (moeda), `0.00%` / `0.0000%` (alíquotas), `#,##0.###` (quantidades).

## Risks / Trade-offs

- **Streams de imagem variados em PDFs** → Mitigado encapsulando a decodificação em `try/except` com `Pillow` e fallback silencioso (planilha nunca falha se o logo não puder ser extraído).
- **Sobreposição de logos com texto no Excel** → Mitigado reservando altura explícita nas linhas 1–4 da aba `Resumo` (`row_dimensions[1..4].height`) e redimensionando proporcionalmente os logos para altura máxima fixa (~56 px).
