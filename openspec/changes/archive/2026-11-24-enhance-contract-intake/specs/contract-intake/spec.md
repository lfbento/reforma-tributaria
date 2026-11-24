# Spec Delta: contract-intake

## MODIFIED Requirements

### Requirement: Extração estruturada dos documentos de entrada
O sistema SHALL aceitar pedidos de compra (PC/OC/PV) e contratos em PDF (nativo ou escaneado), XLSX, DOCX, PPTX, EML e MSG, além de PPU, DFP, cronograma/saldo e comunicações do cliente, extraindo cabeçalho (número, cliente, emissão, vigência, pagamento), itens (item, descrição, unidade, quantidade, preço unitário e total) e alíquotas/regime do DFP. Para PDFs sem texto ou tabelas legíveis via `pdfplumber`, SHALL acionar `Docling` em subprocesso preservando a página de origem.

#### Scenario: Pedido de compra em PDF
- **WHEN** o agente recebe um PC/OC/PV em PDF
- **THEN** extrai número, cliente, data de emissão, vigência/prazo e condição de pagamento, e a lista de itens com descrição, unidade, quantidade, preço unitário e total

#### Scenario: PDF escaneado ou com layout complexo (fallback Docling)
- **WHEN** o extrator leve (`pdfplumber`) retorna texto vazio ou não extrai itens de um PDF
- **THEN** o sistema aciona o `Docling` em subprocesso isolado, extrai o conteúdo estruturado preservando a página de origem (`Source.pagina`) e sinaliza caso o extra opcional não esteja instalado

#### Scenario: E-mail do Outlook em formato binário (.msg)
- **WHEN** o sistema recebe um arquivo `.msg` do Outlook
- **THEN** utiliza `MarkItDown` para extrair remetente, destinatário, assunto e corpo e processa o texto rotulado preservando a fonte do arquivo

#### Scenario: Contrato ou documento em DOCX ou PPTX
- **WHEN** o sistema recebe um arquivo `.docx` ou `.pptx`
- **THEN** utiliza `MarkItDown` para converter o conteúdo em texto/tabelas estruturadas preservando a fonte do arquivo

#### Scenario: PPU em XLSX
- **WHEN** o agente recebe uma PPU ou planilha de preços em XLSX
- **THEN** extrai, por item, item, descrição, unidade, quantidade, preço unitário e total via `openpyxl`, preservando arquivo, aba e célula

#### Scenario: DFP presente
- **WHEN** o documento inclui um DFP (Demonstrativo de Formação de Preços)
- **THEN** extrai o regime tributário e as alíquotas usadas na proposta

#### Scenario: Comunicação do cliente sobre a reforma
- **WHEN** o agente recebe comunicação do cliente sobre a reforma (ex.: carta Petrobras DPBR-2026-80548 ou calculadora do Canal Fornecedor)
- **THEN** registra a comunicação como documento de entrada associado ao pedido/contrato

### Requirement: Extração de cronograma e saldo a executar
O sistema SHALL extrair do cronograma ou saldo a executar (em XLSX ou MS Project `.mpp`) as medições já faturadas e o saldo remanescente, distinguindo o que foi faturado até 31/12/2026 do que fica para 2027 ou depois. Para arquivos `.mpp`, o sistema SHALL extrair tarefas, datas de início/término, duração e percentual concluído via MPXJ (`JPype`), sinalizando quando valores financeiros precisarem de confirmação. Quando não houver cronograma, SHALL marcar o saldo 2027 como "PENDENTE – confirmar".

#### Scenario: Cronograma com medições faturadas
- **WHEN** o documento traz cronograma ou saldo em XLSX com medições já faturadas
- **THEN** o sistema separa o saldo faturável até 31/12/2026 do saldo faturável a partir de 01/01/2027

#### Scenario: Cronograma em MS Project (.mpp)
- **WHEN** o sistema recebe um cronograma `.mpp` e o ambiente possui Java + `mpxj.jar`
- **THEN** extrai as tarefas com suas datas de início/término, duração e percentual concluído para identificação de atividades que atravessam 01/01/2027, marcando valores financeiros ausentes como "PENDENTE – confirmar"

#### Scenario: Ausência de cronograma
- **WHEN** não há cronograma nem saldo a executar nos documentos
- **THEN** o sistema marca o saldo 2027 como "PENDENTE – confirmar" e sinaliza a premissa adotada

## ADDED Requirements

### Requirement: Ingestão recursiva de pacotes compactados (.zip e .rar)
O sistema SHALL aceitar pacotes compactados `.zip` e `.rar`, extraindo seu conteúdo de forma segura para diretório temporário (via 7-Zip para `.rar` ou `zipfile`/7-Zip para `.zip`) e processando recursivamente todos os documentos suportados, preservando o caminho relativo original na rastreabilidade.

#### Scenario: Pacote compactado com múltiplos documentos
- **WHEN** o usuário fornece um arquivo `.zip` ou `.rar` contendo PDFs, planilhas XLSX e e-mails `.msg`
- **THEN** o sistema extrai os arquivos em diretório temporário, executa o extrator adequado para cada extensão e retorna os documentos e itens consolidados com referência ao pacote de origem

### Requirement: Resiliência de caminhos Windows e cache incremental por hash
O sistema SHALL suportar caminhos longos no Windows (`>260` caracteres via prefixo `\\?\`) durante leitura e cache de arquivos, e SHALL manter um cache incremental opcional baseado em hash MD5 do arquivo para evitar reprocessamento custoso de documentos já convertidos (especialmente PDFs via Docling).

#### Scenario: Arquivo em caminho longo no Windows
- **WHEN** o caminho completo do documento excede 260 caracteres no Windows
- **THEN** o sistema normaliza o caminho com prefixo estendido (`\\?\`) e lê o arquivo sem erro de I/O

#### Scenario: Reprocessamento de documento inalterado com cache ativo
- **WHEN** um documento já processado possui o mesmo hash MD5 registrado no cache incremental
- **THEN** o sistema reutiliza o resultado em cache sem reexecutar a conversão pesada
