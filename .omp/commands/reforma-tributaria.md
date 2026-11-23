---
description: "Analisa pedidos/contratos 2026→2027 e gera entregáveis de revisão da Reforma Tributária (XLSX, parecer, carta, priorização)"
---

Use a skill `reforma-tributaria` para analisar os documentos informados e gerar a
base técnica de revisão de preço da Reforma Tributária 2027 (EC 132/2023, LC 214/2025).

**Input**: `$@` — caminhos de documentos (PDF/XLSX/e-mail) ou de JSON estruturado;
opcionalmente um diretório de saída. Se nada for informado, pergunte quais
pedidos/contratos analisar.

**Steps**

1. Leia a skill `reforma-tributaria` e o prompt governante
   `Prompt do agente – Reforma Tributária 2027.md`.
2. Faça o intake dos documentos para JSON estruturado com proveniência
   (`python -m reforma_tributaria extract <doc> --out entrada.json`), completando
   manualmente layouts heterogêneos. Sinalize `PENDENTE – confirmar` /
   `RECONSTRUÍDO`; nunca invente valores.
3. Triagem antes de calcular (escopo 2026→2027, saldo 2027, cláusula, natureza
   BEM/SERVIÇO, regime, preço de referência Petrobras P0/bruto).
4. Rode o pipeline e gere os entregáveis:
   ```bash
   python -m reforma_tributaria run entrada.json --outdir saida/
   ```
   Para vários pedidos: `run a.json b.json --outdir saida/`.
5. Revise os rascunhos (parecer, carta, priorização, pendências). **Não envie**
   e-mails nem cartas. Apresente o Cenário A como proposto e o B como
   sensibilidade, com ressalva de revisão da base do ICMS/ISS.
6. Liste as pendências finais (regime, ISS do município, DIFAL, CBS final,
   cronograma) e confirme que os totais batem com os exemplos validados quando
   aplicável.

**Provided arguments**: $@