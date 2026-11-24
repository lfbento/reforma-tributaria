# Spec Delta: negotiation-deliverables

## MODIFIED Requirements

### Requirement: Aba Resumo
A aba Resumo SHALL apresentar cabeçalho executivo institucional (com nome da empresa, data do cálculo, data da base de dados das leis/premissas, logo da empresa quando `NNNN.png` estiver disponível e logo do cliente quando extraído do PDF) seguido de total atual, base, total 2027 nos cenários A e B, variação, conferências e a cláusula contratual de revisão.

#### Scenario: Conteúdo da aba Resumo
- **WHEN** o usuário abre a aba Resumo
- **THEN** vê o cabeçalho executivo (empresa, data do cálculo, data da base legal e logos disponíveis) e os indicadores total atual, base, total 2027 (A e B), variação, conferências e a cláusula contratual

## ADDED Requirements

### Requirement: Formatação executiva corporativa na planilha XLSX
O sistema SHALL aplicar formatação visual executiva em todas as abas da planilha XLSX, incluindo cabeçalhos estilizados, formatação monetária brasileira (`R$`) e percentual, largura de colunas ajustada, congelamento de painéis, linhas zebradas, destaque visual de alertas/flags e configuração de impressão em paisagem, mantendo inalteradas a linha de cabeçalho das tabelas de cálculo/premissas e todas as fórmulas vivas.

#### Scenario: Estilização e formatos numéricos nas abas
- **WHEN** o sistema gera o arquivo XLSX
- **THEN** todas as abas possuem cabeçalho estilizado, células monetárias formatadas em Real, alíquotas em percentual, painéis congelados e larguras de coluna ajustadas sem quebrar fórmulas

#### Scenario: Inserção de logos com fallback gracioso
- **WHEN** o arquivo `NNNN.png` está presente na raiz do projeto e/ou o logo do cliente foi extraído do PDF
- **THEN** o sistema insere as imagens redimensionadas no cabeçalho da aba Resumo sem sobrepor células de dados, e gera a planilha normalmente caso algum logo esteja ausente
