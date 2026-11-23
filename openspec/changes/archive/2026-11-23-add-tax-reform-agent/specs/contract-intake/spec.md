# Spec Delta

## Purpose

Transformar os documentos recebidos (pedido/contrato, PPU, DFP, cronograma/saldo e comunicações do cliente) em registros estruturados e auditáveis, preservando a origem de cada dado e sinalizando lacunas sem inventar valores.

## ADDED Requirements

### Requirement: Extração estruturada dos documentos de entrada
O sistema SHALL aceitar pedidos de compra (PC/OC/PV) e contratos em PDF, XLSX ou e-mail, além de PPU/planilha de preços, DFP, cronograma/saldo e comunicações do cliente, e extrair deles registros estruturados. Do cabeçalho SHALL extrair número, cliente, data de emissão, vigência ou prazo e condição de pagamento; de cada item SHALL extrair item, descrição, unidade, quantidade, preço unitário e total. Do DFP, quando houver, SHALL extrair o regime tributário e as alíquotas usadas na proposta.

#### Scenario: Pedido de compra em PDF
- **WHEN** o agente recebe um PC/OC/PV em PDF
- **THEN** extrai número, cliente, data de emissão, vigência/prazo e condição de pagamento, e a lista de itens com descrição, unidade, quantidade, preço unitário e total

#### Scenario: PPU em XLSX
- **WHEN** o agente recebe uma PPU ou planilha de preços em XLSX
- **THEN** extrai, por item, item, descrição, unidade, quantidade, preço unitário e total

#### Scenario: DFP presente
- **WHEN** o documento inclui um DFP (Demonstrativo de Formação de Preços)
- **THEN** extrai o regime tributário e as alíquotas usadas na proposta

#### Scenario: Comunicação do cliente sobre a reforma
- **WHEN** o agente recebe comunicação do cliente sobre a reforma (ex.: carta Petrobras DPBR-2026-80548 ou calculadora do Canal Fornecedor)
- **THEN** registra a comunicação como documento de entrada associado ao pedido/contrato

### Requirement: Rastreabilidade de origem por dado
O sistema SHALL registrar a origem de cada preço e quantidade extraídos, identificando arquivo e, conforme o formato, aba e célula (XLSX) ou página (PDF/e-mail). Nenhum número SHALL ser apresentado sem fonte identificável.

#### Scenario: Preço extraído de PPU XLSX
- **WHEN** um preço unitário é extraído de uma planilha XLSX
- **THEN** o registro do item carrega a fonte como arquivo, aba e célula

#### Scenario: Preço extraído de contrato PDF
- **WHEN** um preço é extraído de um contrato ou pedido em PDF
- **THEN** o registro do item carrega a fonte como arquivo e página

### Requirement: Sinalização de dados faltantes e reconstruídos
Quando faltar um dado necessário, o sistema SHALL marcá-lo como "PENDENTE – confirmar" e seguir com uma premissa padrão sinalizada. O sistema SHALL NOT inventar alíquota, preço, quantidade ou cláusula. Quando um item for reconstruído ou estimado, o sistema SHALL marcá-lo como "RECONSTRUÍDO" e mostrar de onde veio a estimativa.

#### Scenario: Dado obrigatório ausente
- **WHEN** um dado necessário (ex.: alíquota, quantidade ou preço) não está nos documentos
- **THEN** o sistema marca "PENDENTE – confirmar", adota uma premissa padrão sinalizada e não inventa o valor

#### Scenario: Item estimado sem fonte direta
- **WHEN** um item precisa ser reconstruído ou estimado por falta de fonte direta
- **THEN** o sistema marca "RECONSTRUÍDO" e registra a origem da estimativa

#### Scenario: Dado presente e sourced
- **WHEN** o dado está presente e tem fonte identificável
- **THEN** o sistema usa o valor do documento sem marcação de pendência ou reconstrução

### Requirement: Extração de cronograma e saldo a executar
O sistema SHALL extrair do cronograma ou saldo a executar as medições já faturadas e o saldo remanescente, distinguindo o que foi faturado até 31/12/2026 do que fica para 2027 ou depois. Quando não houver cronograma, SHALL marcar o saldo 2027 como "PENDENTE – confirmar".

#### Scenario: Cronograma com medições faturadas
- **WHEN** o documento traz cronograma ou saldo com medições já faturadas
- **THEN** o sistema separa o saldo faturável até 31/12/2026 do saldo faturável a partir de 01/01/2027

#### Scenario: Ausência de cronograma
- **WHEN** não há cronograma nem saldo a executar nos documentos
- **THEN** o sistema marca o saldo 2027 como "PENDENTE – confirmar" e sinaliza a premissa adotada