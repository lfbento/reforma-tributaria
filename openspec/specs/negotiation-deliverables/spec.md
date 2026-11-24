# negotiation-deliverables Specification

## Purpose

Produzir os entregáveis de negociação — planilha XLSX com fórmulas vivas, parecer executivo, minuta de carta/e-mail e tabela de priorização — de forma auditável e apenas como rascunhos, com lista de pendências ao final.

## Requirements

### Requirement: Planilha XLSX com abas obrigatórias
O sistema SHALL gerar uma planilha XLSX contendo as abas Premissas, Calculo_Bens, Calculo_Servicos, Saldo_2027, Resumo e Fontes.

#### Scenario: Geração da planilha
- **WHEN** o agente conclui o cálculo de um pedido/contrato
- **THEN** gera um XLSX com as seis abas obrigatórias

### Requirement: Aba Premissas editável com fontes
A aba Premissas SHALL conter os parâmetros editáveis do cenário 2027, cada um com a sua fonte.

#### Scenario: Conteúdo da aba Premissas
- **WHEN** o usuário abre a aba Premissas
- **THEN** vê os parâmetros editáveis e a fonte de cada um

### Requirement: Abas de cálculo com fórmulas ligadas às premissas
As abas Calculo_Bens e Calculo_Servicos SHALL usar fórmulas ligadas à aba Premissas, não valores fixos, e SHALL conter as colunas de auditoria por item. Alterar uma premissa SHALL recalcular as células de cálculo.

#### Scenario: Colunas de auditoria por item
- **WHEN** o usuário abre Calculo_Bens ou Calculo_Servicos
- **THEN** vê as colunas Item, Fonte, Descrição, Un, Qtd, P unit, Total atual, % e R$ de PIS, Cofins, ICMS/ISS e IPI, Base unit, Base total, CBS, IBS est, IBS mun, Subtotal, ICMS/ISS 2027 (A), P₂₀₂₇ (A), Total (A), ICMS/ISS 2027 (B), P₂₀₂₇ (B), Total (B), Var R$, Var % e Flag

#### Scenario: Recálculo por fórmula
- **WHEN** o usuário altera um parâmetro na aba Premissas
- **THEN** as células de cálculo das abas Calculo_Bens e Calculo_Servicos recalculam por fórmula, sem valores fixos

### Requirement: Aba Saldo_2027
A aba Saldo_2027 SHALL apresentar o impacto somente sobre o saldo faturável em 2027.

#### Scenario: Impacto sobre o saldo 2027
- **WHEN** o pedido tem saldo faturável em 2027
- **THEN** a aba Saldo_2027 mostra o impacto calculado apenas sobre esse saldo

### Requirement: Aba Resumo
A aba Resumo SHALL apresentar cabeçalho executivo institucional (com nome da empresa, data do cálculo, data da base de dados das leis/premissas, logo da empresa quando `NNNN.png` estiver disponível e logo do cliente quando extraído do PDF) seguido de total atual, base, total 2027 nos cenários A e B, variação, conferências e a cláusula contratual de revisão.

#### Scenario: Conteúdo da aba Resumo
- **WHEN** o usuário abre a aba Resumo
- **THEN** vê o cabeçalho executivo (empresa, data do cálculo, data da base legal e logos disponíveis) e os indicadores total atual, base, total 2027 (A e B), variação, conferências e a cláusula contratual

### Requirement: Aba Fontes
A aba Fontes SHALL listar os documentos de entrada e as referências legais usadas.

#### Scenario: Conteúdo da aba Fontes
- **WHEN** o usuário abre a aba Fontes
- **THEN** vê os documentos recebidos e as referências legais (ex.: EC 132/2023, LC 214/2025, TCU TC 006.529/2026-7)

### Requirement: Parecer executivo
O sistema SHALL gerar um parecer executivo de até uma página contendo contrato ou pedido, cliente, saldo 2027, impacto em R$ e %, cláusula que permite a revisão, riscos e recomendação.

#### Scenario: Conteúdo do parecer
- **WHEN** o agente conclui a análise de um pedido/contrato
- **THEN** gera parecer de até uma página com contrato/pedido, cliente, saldo 2027, impacto em R$ e %, cláusula de revisão, riscos e recomendação

### Requirement: Minuta de carta ou e-mail ao cliente
O sistema SHALL gerar minuta de comunicação ao cliente em formato de Memorando formal e técnico, contendo cabeçalho de memorando (`De`, `Para`, `Data`, `Ref.`, `Assunto`), fundamento (EC 132/2023, LC 214/2025 e cláusula contratual), valor-base apurado, nova PPU proposta para 2027, ressalva sobre CBS/IBS na base do ICMS/ISS e pedido de aditivo ou revisão, além de gerar o documento Word (`memorando-<numero>.docx`) utilizando o modelo `Papel timbrado.docx` da empresa quando disponível.

#### Scenario: Conteúdo da minuta
- **WHEN** o agente prepara a comunicação ao cliente
- **THEN** a minuta em formato de memorando inclui cabeçalho (`De`, `Para`, `Data`, `Ref.`, `Assunto`), fundamento legal e contratual, valor-base apurado, nova PPU proposta para 2027, ressalva sobre CBS/IBS na base do ICMS/ISS e pedido de aditivo ou revisão

#### Scenario: Ressalva de revisão da base
- **WHEN** a minuta é gerada
- **THEN** inclui ressalva de revisão caso a lei ou decisão judicial altere a base de cálculo do ICMS/ISS

#### Scenario: Geração do memorando DOCX em papel timbrado
- **WHEN** o sistema gera os entregáveis de negociação e o arquivo `Papel timbrado.docx` está presente na raiz do projeto (ou caminho informado)
- **THEN** gera `memorando-<numero>.docx` preservando o cabeçalho e o rodapé do modelo timbrado com o conteúdo completo do memorando, operando com fallback limpo caso o modelo não esteja presente

### Requirement: Apenas rascunhos, sem envio
O sistema SHALL NOT enviar e-mails nem cartas; SHALL gerar apenas rascunhos.

#### Scenario: Geração de comunicação
- **WHEN** o agente produz uma carta ou e-mail
- **THEN** o resultado é um rascunho e nenhum envio é realizado

### Requirement: Tabela de priorização de pedidos
Quando houver vários pedidos, o sistema SHALL ordená-los por impacto em R$ no saldo de 2027 e SHALL marcar os pedidos sem cláusula de revisão como "ALTO RISCO".

#### Scenario: Vários pedidos priorizados
- **WHEN** o agente analisa múltiplos pedidos
- **THEN** gera tabela ordenada por impacto em R$ no saldo 2027

#### Scenario: Pedido sem cláusula de revisão
- **WHEN** um pedido na tabela não tem cláusula de revisão
- **THEN** o sistema o marca como "ALTO RISCO"

### Requirement: Lista final de pendências
Ao terminar, o sistema SHALL listar todas as pendências que precisam ser confirmadas, incluindo regime, ISS do município, DIFAL, alíquota CBS final e cronograma de faturamento.

#### Scenario: Encerramento da análise
- **WHEN** o agente conclui a análise
- **THEN** apresenta lista de pendências a confirmar (regime, ISS do município, DIFAL, alíquota CBS final, cronograma de faturamento)

### Requirement: Auditabilidade dos números entregues
O sistema SHALL mostrar premissas e fórmulas de forma transparente; cada número nos entregáveis SHALL ser auditável até uma premissa, fórmula ou fonte.

#### Scenario: Número no parecer ou carta
- **WHEN** um valor aparece no parecer, na carta ou no Resumo
- **THEN** o valor é rastreável até a planilha de cálculo, a premissa ou o documento de origem

### Requirement: Formatação executiva corporativa na planilha XLSX
O sistema SHALL aplicar formatação visual executiva em todas as abas da planilha XLSX, incluindo cabeçalhos estilizados, formatação monetária brasileira (`R$`) e percentual, largura de colunas ajustada, congelamento de painéis, linhas zebradas, destaque visual de alertas/flags e configuração de impressão em paisagem, mantendo inalteradas a linha de cabeçalho das tabelas de cálculo/premissas e todas as fórmulas vivas.

#### Scenario: Estilização e formatos numéricos nas abas
- **WHEN** o sistema gera o arquivo XLSX
- **THEN** todas as abas possuem cabeçalho estilizado, células monetárias formatadas em Real, alíquotas em percentual, painéis congelados e larguras de coluna ajustadas sem quebrar fórmulas

#### Scenario: Inserção de logos com fallback gracioso
- **WHEN** o arquivo `NNNN.png` está presente na raiz do projeto e/ou o logo do cliente foi extraído do PDF
- **THEN** o sistema insere as imagens redimensionadas no cabeçalho da aba Resumo sem sobrepor células de dados, e gera a planilha normalmente caso algum logo esteja ausente