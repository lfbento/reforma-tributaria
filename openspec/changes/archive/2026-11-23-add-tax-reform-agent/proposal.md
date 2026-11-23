# Proposal

## Why

A Nacional Indústria Mecânica Ltda. precisa revisar e renegociar preços de pedidos de compra (PC/OC/PV) e contratos **emitidos em 2026** com execução, entrega ou faturamento em **2027 ou depois**, por causa da Reforma Tributária do consumo (EC 132/2023, LC 214/2025). Não existe hoje ferramenta que calcule o impacto por item de forma auditável e gere a base técnica de negociação; o cálculo manual é lento, inconsistente e não reproduz os valores de referência já validados (contrato Petrobras ICJ 5900.0131958.25.2 / SAP 4600685026). A transição CBS/IBS começa em 01/01/2027, então as cartas de revisão precisam ser preparadas antes disso.

## What Changes

- Novo **agente analisador** (skill + comando omp) que orquestra intake → triagem → cálculo → entregáveis, governado pelo prompt `Prompt do agente – Reforma Tributária 2027.md`.
- **Motor de cálculo determinístico** (Python): metodologia de 6 passos por item, Cenário A (padrão, conservador) e Cenário B (sensibilidade), fator de conferência por item e premissas editáveis com fonte.
- **Extração estruturada** de PDF, XLSX e e-mail com rastreabilidade de cada preço (arquivo, aba/célula ou página) e marcação `PENDENTE – confirmar` / `RECONSTRUÍDO` quando faltar dado ou fonte.
- **Triagem** antes de calcular: escopo emissão 2026, separação saldo 2026 / saldo 2027, detecção e transcrição de cláusula de revisão, natureza BEM/SERVIÇO (itens mistos separados), regime tributário (Simples Nacional não calculado) e preço de referência (Petrobras: P0 original em serviços, preço bruto unitário em bens).
- **Planilha XLSX** com abas `Premissas`, `Calculo_Bens`, `Calculo_Servicos` (fórmulas ligadas à aba Premissas, não valores fixos), `Saldo_2027`, `Resumo` e `Fontes`.
- **Parecer executivo** (≤ 1 página), **minuta de carta/e-mail** ao cliente (apenas rascunho, nunca enviada) e **tabela de priorização** por impacto em R$ no saldo 2027, marcando pedidos sem cláusula de revisão como `ALTO RISCO`.
- **Validações obrigatórias**: reconciliação de totais (diferença máx. R$ 0,01), Q × P = total da linha, fator constante entre itens de mesmas alíquotas, valor-base total invariante entre cenários, e testes que reproduzem os exemplos Petrobras validados.
- **Lista final de pendências** a confirmar (regime, ISS do município, DIFAL, alíquota CBS final, cronograma de faturamento).

## Capabilities

### New Capabilities

- `contract-intake`: ingestão e extração estruturada dos documentos recebidos (pedido/contrato, PPU, DFP, cronograma/saldo, comunicação do cliente) em registros auditáveis, com rastreabilidade de origem por preço e sinalização de dados faltantes ou reconstruídos.
- `contract-triage`: regras de escopo e classificação aplicadas antes do cálculo — janela 2026→2027, separação de saldo, cláusula de revisão, natureza BEM/SERVIÇO, regime tributário e seleção do preço de referência por cliente.
- `tax-impact-engine`: premissas editáveis do cenário 2027 e metodologia de cálculo por item (tributos atuais por dentro, valor-base, CBS/IBS por fora, recomposição de ICMS/ISS nos cenários A e B, novo preço e fator de conferência), com as validações numéricas obrigatórias.
- `negotiation-deliverables`: geração dos entregáveis de negociação — planilha XLSX com fórmulas vivas, parecer executivo, minuta de carta/e-mail (rascunho), tabela de priorização e lista de pendências — com recálculo integral ao alterar premissas.

### Modified Capabilities

Nenhuma — projeto greenfield, sem specs existentes em `openspec/specs/`.

## Impact

- **Código novo**: pacote Python (motor de cálculo, extração de documentos, geração de XLSX e textos), skill omp em `.omp/skills/reforma-tributaria/` e comando em `.omp/commands/`.
- **Dependências novas**: `openpyxl` (XLSX com fórmulas), leitor de PDF (`pdfplumber` ou `PyMuPDF`), `pytest` (testes dos exemplos validados). Extração de XLSX via `openpyxl`; e-mail via biblioteca padrão.
- **Documentos de entrada**: PC/OC/PV e contratos (PDF/XLSX/e-mail), PPU/planilha de preços, DFP, cronograma/saldo a executar, comunicações do cliente (ex.: carta Petrobras DPBR-2026-80548 e calculadora do Canal Fornecedor).
- **Sem integração de envio**: o agente gera apenas rascunhos; não envia e-mails nem cartas.
- **Premissas legais versionadas e editáveis**: CBS de referência 11,3468% (TCU, TC 006.529/2026-7) sujeita a confirmação do Senado; alteração de alíquota recalcula tudo pela aba `Premissas`.
- **Fora do escopo**: cálculo para Simples Nacional (tratamento específico, apenas sinalizado); créditos de PIS/Cofins e CBS/IBS no Lucro Real (afetam margem, não entram no preço por esta metodologia).