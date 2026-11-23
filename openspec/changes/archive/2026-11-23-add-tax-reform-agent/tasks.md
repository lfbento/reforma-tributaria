# Tasks

## 1. Setup do projeto

- [x] 1.1 Criar o pacote `src/reforma_tributaria/` (módulos `intake`, `triage`, `premises`, `engine`, `deliverables`, `cli`) e `pyproject.toml` com dependências (`openpyxl`, `pdfplumber`, `pyyaml`, `pytest`); verificar que `pip install -e .` instala e `python -c "import reforma_tributaria"` importa sem erro.
- [x] 1.2 Configurar `pytest` e o diretório `tests/` com pasta de fixtures; verificar que `pytest` coleta e executa a suíte vazia sem erro.

## 2. Premissas editáveis

- [x] 2.1 Criar `premises.yaml` versionado com os padrões e fonte por parâmetro (PIS 0,65%/1,65%, Cofins 3,00%/7,60% por regime; ICMS conforme operação; ISS município/contrato, padrão Petrobras multi-cidade 5% sinalizado; IPI 0%; CBS referência 11,3468% com redução 0,1 p.p. → efetiva 11,2468%; IBS 0,05%+0,05%=0,10%) e o loader com overrides; verificar teste unitário: defaults conferem com a spec `tax-impact-engine`, cada parâmetro tem fonte, e um override altera o valor aplicado.

## 3. Modelo de dados e intake

- [x] 3.1 Implementar os registros JSON-serializáveis (`Document`, `ContractHeader`, `LineItem` com fonte e flags, `PremiseSet`, `CalcResult`); verificar teste de round-trip JSON preservando campos e proveniência.
- [x] 3.2 Implementar extração de PPU/planilha XLSX via `openpyxl` com proveniência arquivo/aba/célula; verificar teste com fixture XLSX que extrai item, descrição, unidade, quantidade, preço unitário, total e a fonte por célula.
- [x] 3.3 Implementar extração de PDF via `pdfplumber` (cabeçalho: número, cliente, emissão, vigência/prazo, pagamento; itens; página) e de e-mail via biblioteca padrão, além de DFP (regime e alíquotas) e comunicação do cliente; verificar teste com fixtures PDF/e-mail que extrai os campos e registra arquivo/página.
- [x] 3.4 Implementar sinalização `PENDENTE – confirmar` (dado ausente, com premissa padrão sinalizada, sem inventar) e `RECONSTRUÍDO` (item estimado com origem), e extração de cronograma/saldo separando faturado até 31/12/2026 do saldo 2027; verificar testes: dado ausente → PENDENTE; item estimado → RECONSTRUÍDO + origem; cronograma → saldos separados; sem cronograma → saldo 2027 PENDENTE.

## 4. Triagem

- [x] 4.1 Implementar regras de escopo (emissão fora de 2026 → `FORA DO ESCOPO`; tudo faturado até 31/12/2026 → sem impacto; cálculo só sobre saldo a partir de 01/01/2027, separando saldo 2026/2027); verificar testes cobrindo os três cenários da spec `contract-triage`.
- [x] 4.2 Implementar detecção/transcrição de cláusula de revisão (ausência → risco de repasse), natureza BEM/SERVIÇO (item misto separado), regime (Simples Nacional não calculado, marcado para tratamento específico) e preço de referência (Petrobras: P0 original em serviços, bruto unitário em bens; outros: contratual vigente informado); verificar testes por cenário, incluindo P0 vs reajustado e Simples sem cálculo.

## 5. Motor de cálculo

- [x] 5.1 Implementar Passos 1–3 em `Decimal` (tributos atuais por dentro; Base = P×(1−Σ atuais); Base total = Base×Q; CBS/IBS por fora; Subtotal), tratando DIFAL indicated sem valor como não deduzido e registrado; verificar testes: bem ICMS 12% Presumido Σ=15,65% Base=P×0,8435; serviço ISS 3% Σ=6,65%; item 1 Base 44,2167, CBS 4,9730, IBS 0,0442, Subtotal 49,2338; DIFAL "-" não deduzido.
- [x] 5.2 Implementar Passos 4–5 nos cenários A e B (ICMS/ISS₂₀₂₇ = Subtotal×a_L/(1−a_L) em A, Base×a_L/(1−a_L) em B; P₂₀₂₇, novo total, variação R$ e %), com A como preço proposto e B como sensibilidade; verificar testes: item 1 A ICMS 6,7137 P₂₀₂₇ 55,9475 (+6,73%); item 1.1 A ISS 1,1830 P₂₀₂₇ 39,4338 (+7,16%); B distinto de A.
- [x] 5.3 Implementar Passo 6 (fator F_A e F_B, conferência P₂₀₂₇/P=F por linha, fator constante por grupo de alíquotas, flag `DIVERGÊNCIA`); verificar testes: bens F_A 1,067284 / F_B 1,054230; serviços F_A 1,071569 / F_B 1,068290; item divergente marcado.
- [x] 5.4 Implementar validações obrigatórias (reconciliação de totais ±R$0,01 listando itens divergentes; Q×P=total da linha; valor-base total invariante entre atual e 2027); verificar testes para cada conferência, incluindo o caso de divergência que lista os itens.
- [x] 5.5 Criar fixtures Petrobras completos (42 bens / 5 serviços) e o tratamento Lucro Real (PIS 1,65%/Cofins 7,6% + nota de créditos fora do preço) e o recálculo integral ao alterar premissa; verificar testes que reproduzem totais R$38.776.540,91→R$41.385.596,58 (+R$2.609.055,67, base R$32.708.012,26) e R$16.428.186,00→R$17.603.942,43 (+R$1.175.756,43, base R$15.335.711,63) dentro de ±R$0,01, e que mudar a CBS recalcula todos os itens.

## 6. Entregáveis

- [x] 6.1 Implementar gerador XLSX com as seis abas; aba `Premissas` editável com fonte por parâmetro; abas `Calculo_Bens`/`Calculo_Servicos` com fórmulas referenciando `Premissas` (não valores fixos) e todas as colunas de auditoria por item; verificar teste: abas presentes, células de cálculo são fórmulas com referência a `Premissas`, e o conjunto de colunas confere com a spec `negotiation-deliverables`.
- [x] 6.2 Implementar abas `Saldo_2027` (impacto só sobre saldo 2027), `Resumo` (total atual, base, total 2027 A/B, variação, conferências, cláusula) e `Fontes` (documentos + referências legais); verificar teste de conteúdo de cada aba.
- [x] 6.3 Implementar parecer executivo (≤1 página: contrato/pedido, cliente, saldo 2027, impacto R$/%, cláusula, riscos, recomendação) e minuta de carta/e-mail (fundamento EC 132/2023 + LC 214/2025 + cláusula, valor-base, nova PPU 2027, ressalva CBS/IBS na base ICMS/ISS, pedido de aditivo) via templates, apenas como rascunho; verificar testes: campos presentes, ressalva incluída, nenhum envio realizado.
- [x] 6.4 Implementar tabela de priorização (ordenar por impacto R$ no saldo 2027; sem cláusula → `ALTO RISCO`) e lista final de pendências (regime, ISS município, DIFAL, CBS final, cronograma); verificar testes de ordenação, flag de alto risco e presença das pendências.
- [x] 6.5 Garantir auditabilidade dos números entregues (parecer/carta/Resumo rastreáveis à planilha, premissa ou fonte); verificar teste que liga um valor do parecer à célula/premissa de origem.

## 7. CLI e agente omp

- [x] 7.1 Implementar a CLI (`extract`, `triage`, `calc`, `xlsx`, `report`, `validate`, `run`); verificar que `python -m reforma_tributaria run` sobre a fixture Petrobras produz XLSX + parecer + carta + priorização.
- [x] 7.2 Criar a skill `.omp/skills/reforma-tributaria/SKILL.md` (prompt governante adaptado do arquivo fonte + fluxo que invoca a CLI) e o comando `.omp/commands/reforma-tributaria.md`; verificar que skill e comando existem e o fluxo documentado executa ponta a ponta sobre a fixture.
- [x] 7.3 Documentar uso no README do pacote (instalação, premissas editáveis, fluxo, exemplos validados); verificar que o comando documentado roda como escrito.

## 8. Integração

- [x] 8.1 Verificação ponta a ponta: pipeline completo sobre os exemplos Petrobras reproduz os valores validados e gera os quatro entregáveis, com reconciliação de totais e fator constante conferidos; verificar execução integrada com assertions sobre totais, fator e presença dos entregáveis.

## Workflow follow-up

- Arquivar o change depois que os requisitos de review do projeto forem satisfeitos (`/opsx-archive`).
- Verificar o resultado arquivado (specs principais atualizadas em `openspec/specs/`).