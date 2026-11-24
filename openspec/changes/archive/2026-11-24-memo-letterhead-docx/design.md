# Design: memo-letterhead-docx

## Context

Veja `proposal.md` para motivação e `specs/negotiation-deliverables/spec.md` para requisitos.
O arquivo `Papel timbrado.docx` na raiz do repositório possui 1 seção com cabeçalho gráfico e rodapé institucional da Nacional Indústria (`AV. CÉLIO TADASHI KOBAYASHI, 894...`), e corpo vazio com 1 parágrafo em branco. O ambiente já possui `python-docx` instalado.

## Goals / Non-Goals

**Goals:**
- Estruturar `build_carta()` como Memorando formal (mantendo todos os tokens verificados pelos testes existentes).
- Implementar `build_memorando_docx()` carregando `Papel timbrado.docx` via `python-docx` para preservar integralmente cabeçalho/rodapé originais, preenchendo o corpo com quadro de identificação do memorando, texto técnico-comercial, tabela comparativa `Atual vs 2027 (Cenário A)` e ressalva legal.
- Emitir `memorando-<numero>.docx` automaticamente nos comandos `report` e `run` da CLI (e permitir flag `--letterhead`).

**Non-Goals:**
- Alterar o arquivo original `Papel timbrado.docx`.
- Enviar e-mails ou cartas automaticamente (permanece estritamente rascunho).

## Decisions

1. **Carregamento direto do `.docx` timbrado como base (`docx.Document(letterhead_path)`)**
   - Em vez de reconstruir cabeçalho/rodapé do zero, abrir `Papel timbrado.docx` preserva exatamente margens, logotipo vetorial/imagem do cabeçalho e rodapé institucional da Nacional.
   - Limpar apenas parágrafos vazios iniciais do corpo antes de inserir o conteúdo do memorando.
   - Se o arquivo timbrado não for encontrado, instanciar `docx.Document()` limpo como fallback gracioso.

2. **Estrutura visual do Memorando no Word**
   - Faixa de título: `MEMORANDO TÉCNICO-COMERCIAL` (negrito 13pt, azul-marinho `#1B365D`) + subtítulo `RASCUNHO — USO INTERNO / NÃO ENVIADO`.
   - Tabela de cabeçalho do memorando (2 colunas, borda sutil): `De:` (`Nacional Indústria Mecânica Eireli`), `Para:` (`cliente`), `Data:`, `Referência:` (`Pedido / Contrato nº`), `Assunto:` (`Revisão de Preços — Transição Tributária 2027 (EC 132/2023 e LC 214/2025)`).
   - Corpo formal com fundamento legal/contratual, tabela financeira resumida (`Valor-base apurado`, `Total Atual (P0)`, `Nova PPU 2027 (Cenário A)`, `Variação R$ e %`), bloco destacado da `RESSALVA` e encerramento formal.

3. **Retrocompatibilidade de `carta-<numero>.md`**
   - `build_carta()` continua retornando string Markdown em formato de memorando, preservando todos os marcadores esperados por `tests/test_deliverables.py` e `tests/test_cli.py`.

## Risks / Trade-offs

- **Presença de `python-docx`** → Declarar `python-docx>=1.1` nas dependências de `pyproject.toml` (já verificado instalado na máquina).
- **Dependência do arquivo `Papel timbrado.docx` em outros ambientes/testes** → Mitigado por busca em caminhos padrão (`CWD` e raiz do pacote) com fallback para documento em branco caso ausente.
