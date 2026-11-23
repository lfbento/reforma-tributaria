# Design

## Context

Repositório greenfield: existe apenas o prompt governante `Prompt do agente – Reforma Tributária 2027.md` e a estrutura OpenSpec (schema `spec-driven`). As convenções locais de empacotamento são skills em `.omp/skills/` e comandos em `.omp/commands/` (mesmo padrão dos skills OpenSpec). Motivação em `proposal.md` — Why; requisitos nas quatro specs delta (`contract-intake`, `contract-triage`, `tax-impact-engine`, `negotiation-deliverables`).

A restrição que molda a arquitetura é numérica: as saídas precisam reproduzir os exemplos Petrobras validados (bem item 1 e serviço item 1.1, totais de 42 e 5 itens) com reconciliação de ±R$ 0,01 e fator constante por grupo de alíquotas. Isso exige cálculo determinístico, não aritmética de LLM.

## Goals / Non-Goals

**Goals:**
- Núcleo de cálculo determinístico e testável que reproduz os fixtures validados e satisfaz as conferências da spec `tax-impact-engine`.
- Pipeline auditável intake → triagem → cálculo → entregáveis, com proveniência por número e premissas editáveis que recalculam tudo.
- XLSX com fórmulas vivas ligadas à aba `Premissas` (não valores fixos).
- Agente omp (skill + comando) que orquestra o pipeline e gera parecer/carta/priorização como rascunhos.

**Non-Goals:**
- Envio de e-mails/cartas ou integração com clientes (apenas rascunhos).
- Cálculo para Simples Nacional e contabilização de créditos de PIS/Cofins/CBS/IBS no Lucro Real (sinalizados, fora do preço).
- Aconselhamento jurídico definitivo sobre a disputa CBS/IBS na base do ICMS/ISS (o agente apresenta cenários e ressalva).

## Decisions

### 1. Arquitetura híbrida: núcleo Python determinístico + agente LLM orquestrador
O cálculo, as conferências e a geração de XLSX vivem em um pacote Python; o LLM (skill omp) faz extração assistida de documentos, julgamento de triagem (natureza, regime, cláusula) e redação dos entregáveis narrativos, invocando o núcleo por CLI e passando dados estruturados.
- **Por quê:** a aceitação é numérica e exata (±R$ 0,01, fator constante, fixtures Petrobras). LLM não garante isso; código garante. Extração de PDF/e-mail heterogêneos e redação formal exigem julgamento, que fica com o agente.
- **Alternativas rejeitadas:** agente puramente prompt (não reproduz os valores com confiabilidade); CLI pura sem agente (não lida com layouts variados nem redige parecer/carta).

### 2. Stack: Python 3.11+, `openpyxl`, `pdfplumber`, `pytest`
- `openpyxl` lê XLSX de entrada (PPU) e escreve o XLSX de saída com fórmulas reais referenciando a aba `Premissas`. Uma biblioteca para leitura e escrita.
- `pdfplumber` extrai texto/tabelas de PDF (alternativa: `PyMuPDF`, a confirmar com documentos reais).
- E-mail via biblioteca padrão (`email`); testes com `pytest`.
- **Alternativas rejeitadas:** `xlsxwriter` (escreve fórmulas mas não lê; exigiria segunda biblioteca); `pandas` (peso desnecessário para o volume de itens).

### 3. Modelo de dados estruturado e serializável
Registros JSON-serializáveis trafegam entre estágios: `Document` (metadados + proveniência), `ContractHeader` (número, cliente, emissão, vigência, pagamento, cláusula), `LineItem` (item, descrição, un, Q, P, total, natureza BEM/SERVIÇO, fonte, flags PENDENTE/RECONSTRUÍDO), `PremiseSet` (parâmetros editáveis + fonte), `CalcResult` (por item: base, CBS, IBS, subtotal, ICMS/ISS A e B, P₂₀₂₇ A e B, totais, fator, flags DIVERGÊNCIA).
- **Por quê:** estágios testáveis isoladamente; o agente passa dados estruturados ao núcleo, nunca texto livre para calcular; auditoria ponta a ponta.

### 4. Precisão numérica: `Decimal`, arredondamento só na exibição
Cálculo em precisão cheia com `Decimal`; arredondamento apenas para exibição (unitários 4 casas, moeda 2 casas). Tolerância de aceitação: unitários ±0,0001 e totais ±R$ 0,01 (conforme spec). Os exemplos do prompt arredondam intermediários a 4 casas; o cálculo em precisão cheia reproduz os totais publicados dentro de R$ 0,01.
- **Por quê:** reconciliação de centavos em dezenas de itens não pode acumular drift de ponto flutuante.
- **Alternativa rejeitada:** `float` (drift ao somar 42 itens).

### 5. XLSX com fórmulas vivas + núcleo computa em paralelo
A aba `Premissas` holds células nomeadas (CBS_efetiva, IBS_est, IBS_mun, PIS/Cofins por regime, ICMS/ISS, IPI). `Calculo_Bens`/`Calculo_Servicos` implementam os 6 passos por linha com referências absolutas a `Premissas`; `Resumo` agrega com `SUM`; `Saldo_2027` considera só o saldo 2027; `Fontes` lista documentos e referências legais. Alterar uma premissa recalcula ao abrir no Excel/LibreOffice.
- **Limitação:** `openpyxl` escreve fórmulas mas não as avalia. O núcleo Python computa os mesmos números de forma determinística e são esses valores que alimentam parecer/carta e os testes. A corretude das fórmulas é verificada por estrutura (referências a `Premissas`) e, opcionalmente, recálculo headless no LibreOffice.
- **Por quê:** atende "fórmulas ligadas à Premissas, não valores fixos" sem depender de avaliação pelo gerador.

### 6. Empacotamento do agente: skill + comando omp
Skill `.omp/skills/reforma-tributaria/SKILL.md` com o prompt governante (adaptado do arquivo fonte) e o fluxo que invoca a CLI; comando `.omp/commands/reforma-tributaria.md`. O arquivo de prompt original permanece como referência canônica.
- **Por quê:** segue a convenção existente do repositório (skills/comandos OpenSpec).

### 7. Superfície da CLI e layout do pacote
Pacote `src/reforma_tributaria/` com módulos `intake`, `triage`, `premises`, `engine`, `deliverables`, `cli`; subcomandos `extract`, `triage`, `calc`, `xlsx`, `report`, `validate` (e um `run` que encadeia o pipeline). Premissas padrão versionadas em `premises.yaml` com fonte por parâmetro; overrides por arquivo ou pela aba `Premissas`. Parecer e carta gerados a partir de templates Markdown preenchidos com `CalcResult`; ressalva da base ICMS/ISS conforme §6 do prompt.

## Risks / Trade-offs

- [Incerteza legal: CBS definitiva pendente do Senado; disputa CBS/IBS na base do ICMS/ISS (PLP 16/2025, liminares)] → premissas editáveis, Cenário A padrão + B sensibilidade, ressalva de revisão na carta; recálculo integral ao mudar premissa.
- [Layouts heterogêneos de PDF/PPU/DFP quebram extração automática] → extração assistida pelo agente com proveniência e flags `PENDENTE – confirmar`/`RECONSTRUÍDO`; nunca inventar; caminho de confirmação humana.
- [`openpyxl` não avalia fórmulas] → núcleo determinístico computa os números autoritativos; testes contra fixtures; verificação opcional de recálculo no LibreOffice headless.
- [Drift de arredondamento vs exemplos publicados] → `Decimal` em precisão cheia, arredondamento só na exibição, tolerância ±R$ 0,01; fixtures assertam os totais.
- [Classificação errada de natureza/regime (Simples, itens mistos)] → triagem marca Simples como não calculado e separa itens mistos; agente confirma antes de calcular.
- [Percepção de aconselhamento jurídico ou envio indevido] → agente gera apenas base técnica e rascunhos; lista final de pendências para confirmação humana.

## Migration Plan

Greenfield, sem migração de dados. Implantação: instalar dependências do pacote e registrar skill/comando omp. Rollback: remover skill/comando e o pacote; nenhum dado persistente é criado além dos artefatos de saída gerados pelo usuário.

## Open Questions

- Biblioteca PDF final (`pdfplumber` vs `PyMuPDF`) a confirmar pelo comportamento com os documentos reais (PPU Petrobras, DFP); não altera specs nem o breakdown de tarefas.