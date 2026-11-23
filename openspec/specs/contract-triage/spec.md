# contract-triage Specification

## Purpose

Aplicar, antes de qualquer cálculo, as regras de escopo e classificação que decidem quais pedidos têm impacto em 2027 e como cada item deve ser tratado: natureza, regime tributário, preço de referência e cláusula de revisão.

## Requirements

### Requirement: Escopo por data de emissão
O sistema SHALL analisar apenas pedidos e contratos emitidos em 2026. Documento com data de emissão fora de 2026 SHALL ser marcado como "FORA DO ESCOPO" e não calculado.

#### Scenario: Emissão em 2026
- **WHEN** a data de emissão do pedido/contrato é de 2026
- **THEN** o documento segue para as demais verificações de triagem

#### Scenario: Emissão fora de 2026
- **WHEN** a data de emissão é anterior a 2026 ou posterior a 2026
- **THEN** o sistema marca "FORA DO ESCOPO" e não calcula impacto

### Requirement: Escopo por execução e faturamento
O sistema SHALL calcular impacto apenas sobre a parte faturada a partir de 01/01/2027, separando o saldo de 2026 do saldo de 2027. Se tudo for entregue e faturado até 31/12/2026, o pedido SHALL ser tratado como sem impacto.

#### Scenario: Tudo faturado até 31/12/2026
- **WHEN** todas as entregas e faturamentos ocorrem até 31/12/2026
- **THEN** o sistema registra que o pedido não tem impacto da reforma

#### Scenario: Execução dividida entre 2026 e 2027
- **WHEN** parte é faturada em 2026 e parte a partir de 01/01/2027
- **THEN** o sistema separa saldo 2026 e saldo 2027 e calcula impacto somente sobre o saldo 2027

### Requirement: Detecção de cláusula de revisão
O sistema SHALL procurar cláusulas de "Incidências Tributárias" ou de reequilíbrio (ex.: Petrobras cl. 15.3, revisão proporcional se tributos forem criados, extintos ou alterados) e transcrever o número da cláusula. Quando não houver cláusula, SHALL indicar o risco de não conseguir repassar o impacto.

#### Scenario: Cláusula de reequilíbrio presente
- **WHEN** o contrato contém cláusula de incidências tributárias ou reequilíbrio
- **THEN** o sistema transcreve o número da cláusula e a associa ao pedido

#### Scenario: Ausência de cláusula de revisão
- **WHEN** o contrato não contém cláusula de revisão tributária
- **THEN** o sistema indica o risco de não conseguir repassar o impacto ao cliente

### Requirement: Classificação da natureza do item
O sistema SHALL classificar cada item como BEM (sujeito a ICMS/IPI) ou SERVIÇO (sujeito a ISS). Itens mistos SHALL ser separados em componentes de bem e de serviço.

#### Scenario: Item de bem
- **WHEN** o item é um bem (ex.: estrutura metálica)
- **THEN** o sistema classifica como BEM, sujeito a ICMS/IPI

#### Scenario: Item de serviço
- **WHEN** o item é um serviço (ex.: beneficiamento de tubulação)
- **THEN** o sistema classifica como SERVIÇO, sujeito a ISS

#### Scenario: Item misto
- **WHEN** o item combina bem e serviço
- **THEN** o sistema separa os componentes BEM e SERVIÇO para cálculo distinto

### Requirement: Identificação do regime tributário
O sistema SHALL identificar o regime como Lucro Presumido (cumulativo), Lucro Real (não cumulativo) ou Simples Nacional. Para Simples Nacional o sistema SHALL NOT calcular impacto e SHALL marcar o pedido para tratamento específico.

#### Scenario: Lucro Presumido
- **WHEN** o regime é Lucro Presumido
- **THEN** o sistema usa o tratamento cumulativo de PIS/Cofins

#### Scenario: Lucro Real
- **WHEN** o regime é Lucro Real
- **THEN** o sistema usa o tratamento não cumulativo de PIS/Cofins

#### Scenario: Simples Nacional
- **WHEN** o regime é Simples Nacional
- **THEN** o sistema não calcula impacto e marca o pedido para tratamento específico

### Requirement: Seleção do preço de referência
Para Petrobras, o sistema SHALL usar, em serviços, o P0 original da PPU (nunca o valor reajustado) e, em bens, o preço bruto unitário do contrato. Para outros clientes, SHALL usar o preço contratual vigente e informar qual preço foi usado.

#### Scenario: Serviço Petrobras com P0 e valor reajustado
- **WHEN** o item é serviço Petrobras e a PPU traz P0 original e valor reajustado
- **THEN** o sistema usa o P0 original como preço de referência

#### Scenario: Bem Petrobras
- **WHEN** o item é bem Petrobras
- **THEN** o sistema usa o preço bruto unitário do contrato como referência

#### Scenario: Cliente não Petrobras
- **WHEN** o cliente não é Petrobras
- **THEN** o sistema usa o preço contratual vigente e informa qual preço foi usado