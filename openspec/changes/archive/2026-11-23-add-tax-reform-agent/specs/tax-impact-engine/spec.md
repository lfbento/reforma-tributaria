# Spec Delta

## Purpose

Calcular, por item, o impacto da Reforma Tributária (EC 132/2023, LC 214/2025) no preço a partir de premissas editáveis do cenário 2027, produzindo o novo preço nos cenários A e B com fator de conferência e validações numéricas auditáveis.

## ADDED Requirements

### Requirement: Premissas editáveis e rastreadas
O sistema SHALL calcular a partir de premissas editáveis do cenário 2027, cada uma com sua fonte registrada, aplicando valores padrão quando não informados. Alterar uma premissa SHALL recalcular todos os itens a partir dela.

#### Scenario: Premissa sem override
- **WHEN** o usuário não informa um valor para uma premissa
- **THEN** o sistema aplica o valor padrão e registra a fonte daquele padrão

#### Scenario: Alteração de alíquota
- **WHEN** o usuário altera uma premissa (ex.: CBS definitiva aprovada pelo Senado)
- **THEN** o sistema recalcula todos os itens a partir da nova premissa

### Requirement: Valores padrão dos tributos atuais
O sistema SHALL aplicar, sem override: PIS 0,65% (Presumido) / 1,65% (Real) e Cofins 3,00% (Presumido) / 7,60% (Real), extintos em 2027; ICMS conforme operação, mantido em 2027 (redução a partir de 2029); ISS conforme município ou contrato, mantido em 2027; IPI 0% salvo informação diferente, zerado em 2027 com exceções (ZFM).

#### Scenario: Tributos atuais por regime
- **WHEN** o regime é Lucro Presumido e não há override
- **THEN** o sistema usa PIS 0,65% e Cofins 3,00%; para Lucro Real usa PIS 1,65% e Cofins 7,60%

#### Scenario: DIFAL indicado sem valor
- **WHEN** a PPU indica percentual de DIFAL mas o valor é "-"
- **THEN** o sistema não deduz DIFAL e registra essa condição

#### Scenario: ISS de município múltiplo Petrobras
- **WHEN** o contrato Petrobras envolve várias cidades e não há alíquota por município
- **THEN** o sistema usa ISS 5% como padrão sinalizado, a confirmar com DFP ou planilha do cliente

### Requirement: Valores padrão de CBS e IBS 2027
O sistema SHALL aplicar, sem override, CBS de referência 11,3468% (TCU, TC 006.529/2026-7) com redução transitória de 0,1 p.p. em 2027 (CBS efetiva 11,2468%) e IBS 2027 de 0,05% estadual + 0,05% municipal = 0,10%. A CBS de referência SHALL permanecer editável, sujeita a confirmação do Senado.

#### Scenario: CBS e IBS de referência
- **WHEN** não há override de CBS/IBS
- **THEN** o sistema usa CBS efetiva 11,2468% (referência 11,3468% menos 0,1 p.p.) e IBS 0,10% (0,05% estadual + 0,05% municipal)

### Requirement: Tributos atuais e valor-base por dentro
O sistema SHALL calcular os tributos atuais por dentro: PIS = P × a_PIS; Cofins = P × a_COF; ICMS ou ISS = P × a_L; IPI = P × a_IPI. SHALL calcular o valor-base Base = P − (PIS + Cofins + ICMS/ISS + IPI) = P × (1 − Σ alíquotas atuais) e Base total = Base × Q. ICMS, ISS, PIS e Cofins SHALL NOT entrar na base da CBS/IBS (LC 214, art. 12, §2º, V, 2026 a 2032).

#### Scenario: Bem com ICMS 12% no Presumido
- **WHEN** o item é bem com ICMS 12%, sem DIFAL/IPI, no Lucro Presumido
- **THEN** Σ alíquotas atuais = 15,65% e Base = P × 0,8435

#### Scenario: Serviço com ISS 3% no Presumido
- **WHEN** o item é serviço com ISS 3% no Lucro Presumido
- **THEN** Σ alíquotas atuais = 6,65% e Base = P × 0,9335

### Requirement: CBS e IBS por fora sobre a base
O sistema SHALL calcular os novos tributos por fora sobre o valor-base: CBS = Base × a_CBS; IBS = Base × a_IBS; Subtotal = Base + CBS + IBS.

#### Scenario: Bem item 1 Petrobras
- **WHEN** Base unit = 44,2167, CBS efetiva 11,2468% e IBS 0,10%
- **THEN** CBS ≈ 4,9730, IBS ≈ 0,0442 e Subtotal ≈ 49,2338

### Requirement: Recomposição de ICMS/ISS 2027 e novo preço
O sistema SHALL recompor o tributo mantido por dentro. No Cenário A (CBS/IBS na base): ICMS/ISS₂₀₂₇ = Subtotal × a_L / (1 − a_L). No Cenário B (exclusão): ICMS/ISS₂₀₂₇ = Base × a_L / (1 − a_L). SHALL calcular P₂₀₂₇ = Subtotal + ICMS/ISS₂₀₂₇, Novo total = P₂₀₂₇ × Q, Variação R$ = Novo total − Total atual e Variação % = Variação R$ / Total atual, para cada cenário.

#### Scenario: Bem item 1 no Cenário A
- **WHEN** Subtotal ≈ 49,2338 e a_L = 12% no Cenário A
- **THEN** ICMS₂₀₂₇ ≈ 6,7137 e P₂₀₂₇ ≈ 55,9475 (+6,73%)

#### Scenario: Serviço item 1.1 no Cenário A
- **WHEN** Subtotal ≈ 38,2507 e a_L = 3% no Cenário A
- **THEN** ISS₂₀₂₇ ≈ 1,1830 e P₂₀₂₇ ≈ 39,4338 (+7,16%)

#### Scenario: Cenário B como sensibilidade
- **WHEN** o mesmo item é calculado no Cenário B
- **THEN** ICMS/ISS₂₀₂₇ usa Base × a_L / (1 − a_L) e o sistema reporta P₂₀₂₇ (B) e Total (B) distintos do Cenário A

### Requirement: Fator de conferência por item
O sistema SHALL calcular o fator F e conferir que P₂₀₂₇ / P = F em cada linha. Cenário A: F = (1 − Σ atuais) × (1 + a_CBS + a_IBS) / (1 − a_L). Cenário B: F = (1 − Σ atuais) × [(1 + a_CBS + a_IBS) + a_L / (1 − a_L)]. Itens com as mesmas alíquotas SHALL compartilhar o mesmo fator; item que divergir SHALL ser marcado como "DIVERGÊNCIA".

#### Scenario: Fatores de referência para bens
- **WHEN** bem com ICMS 12%, Presumido, CBS 11,2468% e IBS 0,1%
- **THEN** Fator A ≈ 1,067284 (+6,73%) e Fator B ≈ 1,054230 (+5,42%)

#### Scenario: Fatores de referência para serviços
- **WHEN** serviço com ISS 3%, Presumido, CBS 11,2468% e IBS 0,1%
- **THEN** Fator A ≈ 1,071569 (+7,16%) e Fator B ≈ 1,068290 (+6,83%)

#### Scenario: Item divergente
- **WHEN** P₂₀₂₇ / P de um item difere do fator esperado para suas alíquotas
- **THEN** o sistema marca o item como "DIVERGÊNCIA"

### Requirement: Cenário A como preço proposto
O sistema SHALL usar o Cenário A como preço proposto (mais conservador, protege a margem) e apresentar o Cenário B como sensibilidade. A posição padrão SHALL refletir que a CBS/IBS entra na base do ICMS/ISS a partir de 2027 (Sefaz-SP RC 33.083/2026 e Sefaz-PR), sem regra inversa na LC 214/2025.

#### Scenario: Saída de cálculo por item
- **WHEN** o sistema calcula um item
- **THEN** apresenta o Cenário A como preço proposto e o Cenário B como sensibilidade

### Requirement: Reconciliação de totais
A soma dos totais calculados SHALL bater com o total da PPU ou do pedido, com diferença máxima de R$ 0,01. Quando não bater, o sistema SHALL listar os itens com diferença.

#### Scenario: Totais reconciliados
- **WHEN** a soma dos totais calculados difere do total da PPU em até R$ 0,01
- **THEN** a conferência de totais passa

#### Scenario: Totais divergentes
- **WHEN** a soma dos totais calculados difere do total da PPU em mais de R$ 0,01
- **THEN** o sistema lista os itens com diferença

### Requirement: Consistência de quantidade e preço por linha
O sistema SHALL conferir que Q × P = total de cada linha.

#### Scenario: Linha consistente
- **WHEN** Q × P iguala o total da linha
- **THEN** a conferência por linha passa

#### Scenario: Linha inconsistente
- **WHEN** Q × P não iguala o total da linha
- **THEN** o sistema sinaliza a inconsistência daquela linha

### Requirement: Valor-base total invariante
O valor-base total SHALL ser igual no cenário atual e no de 2027.

#### Scenario: Base total preservada
- **WHEN** o sistema compara o valor-base total atual e o de 2027
- **THEN** os dois são iguais

### Requirement: Reprodução dos exemplos validados
O sistema SHALL reproduzir os exemplos validados do contrato Petrobras ICJ 5900.0131958.25.2 / SAP 4600685026, dentro da tolerância de arredondamento de R$ 0,01 nos totais.

#### Scenario: Exemplo de bem (Estrutura Metálica)
- **WHEN** calcula o item 1 (P 52,4205) e o conjunto de 42 itens de bens
- **THEN** P₂₀₂₇ ≈ 55,9475 (+6,73%); total dos 42 itens passa de R$ 38.776.540,91 para R$ 41.385.596,58 (+R$ 2.609.055,67); base total R$ 32.708.012,26

#### Scenario: Exemplo de serviço (Beneficiamento – Tubulação)
- **WHEN** calcula o item 1.1 (P 36,80) e o conjunto de 5 itens de serviços
- **THEN** P₂₀₂₇ ≈ 39,4338 (+7,16%); total dos 5 itens passa de R$ 16.428.186,00 para R$ 17.603.942,43 (+R$ 1.175.756,43); base total R$ 15.335.711,63

### Requirement: Lucro Real com créditos fora do preço
Para Lucro Real (não cumulativo), o sistema SHALL usar PIS 1,65% e Cofins 7,6% no cálculo dos tributos atuais e SHALL informar que os créditos de PIS/Cofins atuais e os futuros créditos de CBS/IBS afetam a margem, mas não entram no preço por esta metodologia.

#### Scenario: Item no Lucro Real
- **WHEN** o regime é Lucro Real
- **THEN** o sistema usa PIS 1,65% e Cofins 7,6% e registra a nota de que créditos não entram no preço