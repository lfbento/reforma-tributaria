# Tasks

## 1. Dependência e Formato Memorando em Texto

- [x] 1.1 Adicionar `python-docx>=1.1` em `pyproject.toml` e atualizar `build_carta()` em `src/reforma_tributaria/deliverables.py` para formato de Memorando (`MEMORANDO TÉCNICO-COMERCIAL`, `De`, `Para`, `Data`, `Ref.`, `Assunto`) preservando todos os elementos exigidos pela spec, validando com os testes em `tests/test_deliverables.py`.

## 2. Geração do Memorando DOCX em Papel Timbrado

- [x] 2.1 Implementar `build_memorando_docx()` em `src/reforma_tributaria/deliverables.py` carregando `Papel timbrado.docx` (ou caminho customizado, com fallback limpo se ausente), preservando cabeçalho/rodapé da Nacional e inserindo quadro de memorando, tabela comparativa financeira, ressalva e assinatura; validar com testes unitários em `tests/test_deliverables.py`.
- [x] 2.2 Integrar a geração de `memorando-<numero>.docx` em `_emit_reports()` (`report` e `run`) e adicionar a flag opcional `--letterhead` em `src/reforma_tributaria/cli.py`, validando com testes em `tests/test_cli.py`.

## 3. Verificação Final e Geração na Pasta Amostra

- [x] 3.1 Executar a suíte completa `pytest`, `openspec validate memo-letterhead-docx` e regerar os entregáveis do pedido `4515655362` em `amostra/4515655362-CONJUNTO DE RESFRIADOR A AR/analise_reforma_2027/saida_real/` verificando o arquivo `memorando-4515655362.docx` gerado sobre `Papel timbrado.docx`.
