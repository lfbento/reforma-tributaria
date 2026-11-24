# Spec Delta: contract-intake

## ADDED Requirements

### Requirement: Extração de logo do cliente do PDF do pedido
O sistema SHALL extrair a primeira imagem embutida elegível da primeira página do PDF do pedido de compra (quando houver) e disponibilizá-la em formato PNG para uso nos entregáveis executivos, sem falhar caso o PDF não contenha imagens.

#### Scenario: Pedido PDF com logo embutido na primeira página
- **WHEN** o PDF do pedido de compra possui imagem de logotipo na página 1
- **THEN** o sistema extrai a imagem para PNG e registra o caminho no resultado da ingestão

#### Scenario: Pedido PDF sem imagens
- **WHEN** o PDF do pedido de compra não possui imagens embutidas
- **THEN** o sistema conclui a extração normalmente sem erro e deixa o logo do cliente ausente
