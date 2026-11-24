# Spec Delta: negotiation-deliverables

## MODIFIED Requirements

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
