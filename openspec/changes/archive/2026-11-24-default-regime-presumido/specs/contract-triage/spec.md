# Spec Delta: contract-triage

## MODIFIED Requirements

### Requirement: Identificação do regime tributário
O sistema SHALL identificar o regime como Lucro Presumido (cumulativo), Lucro Real (não cumulativo) ou Simples Nacional, adotando **Lucro Presumido (`presumido`)** como regime padrão configurável quando não houver indicação explícita ou DFP em contrário. Para Simples Nacional o sistema SHALL NOT calcular impacto e SHALL marcar o pedido para tratamento específico.

#### Scenario: Lucro Presumido
- **WHEN** o regime é Lucro Presumido
- **THEN** o sistema usa o tratamento cumulativo de PIS/Cofins (0,65% e 3,00%)

#### Scenario: Regime padrão sem DFP explícito
- **WHEN** os documentos não especificam o regime tributário
- **THEN** o sistema adota o regime padrão configurado (`presumido`, Lucro Presumido) e sinaliza a premissa adotada

#### Scenario: Lucro Real
- **WHEN** o regime é Lucro Real
- **THEN** o sistema usa o tratamento não cumulativo de PIS/Cofins (1,65% e 7,60%)

#### Scenario: Simples Nacional
- **WHEN** o regime é Simples Nacional
- **THEN** o sistema não calcula impacto e marca o pedido para tratamento específico
