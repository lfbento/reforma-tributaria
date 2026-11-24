"""Testes dos entregaveis (6.1 a 6.5)."""

from decimal import Decimal

from reforma_tributaria import deliverables as dv
from reforma_tributaria import pipeline
from reforma_tributaria.models import FLAG_ALTO_RISCO


# ---- 6.1 XLSX / formulas -------------------------------------------------- #
def test_workbook_tem_seis_abas(analysis, premises):
    wb = dv.build_workbook(analysis, premises)
    assert wb.sheetnames == dv.SHEETS


def test_calculo_usa_formulas_ligadas_a_premissas(analysis, premises):
    wb = dv.build_workbook(analysis, premises)
    ws = wb["Calculo_Bens"]
    for col in ("H", "J", "N", "R", "S", "T"):  # %PIS, %Cofins, %IPI, CBS, IBS
        val = ws[f"{col}2"].value
        assert isinstance(val, str) and val.startswith("=")
        assert "Premissas" in val
    assert ws["W2"].value.startswith("=")  # P2027 (A)
    assert ws["P2"].value.startswith("=")  # Base unit


def test_calculo_colunas_de_auditoria(analysis, premises):
    wb = dv.build_workbook(analysis, premises)
    header = [c.value for c in wb["Calculo_Bens"][1]]
    assert header == dv.CALC_COLS
    assert "P₂₀₂₇ (A)" in header and "P₂₀₂₇ (B)" in header and "Flag" in header


def test_premissas_editavel_com_fonte(analysis, premises):
    wb = dv.build_workbook(analysis, premises)
    ws = wb["Premissas"]
    rows = {ws.cell(r, 1).value: (ws.cell(r, 2).value, ws.cell(r, 3).value)
            for r in range(2, ws.max_row + 1)}
    assert "cbs_referencia" in rows
    assert rows["cbs_referencia"][1]  # fonte presente
    assert rows["cbs_efetiva"][0].startswith("=")  # derivado por formula


# ---- 6.2 Saldo_2027 / Resumo / Fontes ------------------------------------- #
def test_saldo_2027_impacto_so_sobre_saldo(analysis, premises):
    wb = dv.build_workbook(analysis, premises)
    ws = wb["Saldo_2027"]
    header = [c.value for c in ws[1]]
    assert "Saldo 2027 (R$)" in header and "Impacto A (R$)" in header
    last = [c.value for c in ws[ws.max_row]]
    assert last[0] == "TOTAL"
    # todo o saldo e 2027 -> impacto A total = varicao total
    assert abs(Decimal(str(last[3])) - analysis.var_rs()) <= Decimal("0.01")


def test_resumo_conteudo(analysis, premises):
    wb = dv.build_workbook(analysis, premises)
    ws = wb["Resumo"]
    labels = {ws.cell(r, 1).value: ws.cell(r, 2).value for r in range(2, ws.max_row + 1)}
    for k in ("Total atual", "Base total", "Total 2027 (A)", "Total 2027 (B)",
              "Variação R$ (A)", "Cláusula de revisão"):
        assert k in labels
    assert labels["Total atual"].startswith("=SUM(Calculo_Bens")
    assert labels["Cláusula de revisão"] == "15.3"


def test_fontes_conteudo(analysis, premises):
    wb = dv.build_workbook(analysis, premises)
    ws = wb["Fontes"]
    refs = [ws.cell(r, 2).value for r in range(2, ws.max_row + 1)]
    assert "EC 132/2023" in refs
    assert "contrato-petrobras.pdf" in refs


# ---- 6.3 parecer / carta -------------------------------------------------- #
def test_parecer_campos_e_tamanho(analysis, premises):
    txt = dv.build_parecer(analysis, premises)
    for token in ("4600685026", "Petrobras", "Saldo 2027", "Cláusula de revisão",
                  "Recomendação", "15.3"):
        assert token in txt
    assert len(txt.splitlines()) <= 40  # ate uma pagina


def test_carta_campos_e_ressalva(analysis, premises):
    txt = dv.build_carta(analysis, premises)
    for token in ("EC 132/2023", "LC 214/2025", "15.3", "Valor-base apurado",
                  "Nova PPU proposta para 2027", "aditivo", "RASCUNHO"):
        assert token in txt
    assert "CBS/IBS na base do ICMS/ISS" in txt
    assert "revisado caso lei ou decisão judicial" in txt


def test_apenas_rascunho_sem_envio(analysis, premises):
    txt = dv.build_carta(analysis, premises)
    assert "RASCUNHO" in txt and "não enviado" in txt
    assert not hasattr(dv, "send") and not hasattr(dv, "enviar")


# ---- 6.4 priorizacao / pendencias ----------------------------------------- #
def test_priorizacao_ordem_e_alto_risco(analysis, petrobras_data, premises):
    sem_clausula = dict(petrobras_data)
    sem_clausula["header"] = dict(petrobras_data["header"], numero="PC-999",
                                  clausula_revisao=None)
    sem_clausula["items"] = [petrobras_data["items"][0]]
    sem_clausula["saldo"] = {"saldo_2026": "0", "saldo_2027": "52420.50"}
    other = pipeline.analyze(sem_clausula, premises)
    assert other.clause_risk is True
    table = dv.build_priorizacao([other, analysis], premises)
    lines = [l for l in table.splitlines() if l.startswith("|")]
    assert lines[2].split("|")[1].strip() == "4600685026"  # maior impacto primeiro
    assert FLAG_ALTO_RISCO in table
    assert "PC-999" in table


def test_pendencias_lista_confirmacoes(analysis, premises):
    pend = dv.build_pendencias(analysis, premises)
    joined = " ".join(pend)
    for token in ("regime", "ISS do município", "DIFAL", "CBS final", "cronograma"):
        assert token in joined


# ---- 6.5 auditabilidade --------------------------------------------------- #
def test_numeros_auditaveis(analysis, premises):
    txt = dv.build_parecer(analysis, premises)
    assert dv.fmt_pct(premises.cbs_efetiva) in txt
    assert "Premissas" in txt and "Calculo" in txt
    assert dv.fmt_money(analysis.base_total()) in txt


def test_formulas_recalculam_igual_ao_motor(analysis, premises):
    from tests.xlsxutil import make_resolver

    wb = dv.build_workbook(analysis, premises)
    val = make_resolver(wb)
    r0 = next(r for r in analysis.results if r.natureza == "BEM")
    assert abs(Decimal(str(val("Calculo_Bens", "R2"))) - r0.cbs) <= Decimal("0.0001")
    nb = sum(1 for r in analysis.results if r.natureza == "BEM")
    ns = sum(1 for r in analysis.results if r.natureza == "SERVIÇO")
    tot = sum(Decimal(str(val("Calculo_Bens", f"X{r}"))) for r in range(2, nb + 2))
    tot += sum(Decimal(str(val("Calculo_Servicos", f"X{r}"))) for r in range(2, ns + 2))
    assert abs(tot - analysis.total_a()) <= Decimal("0.01")
    ws_resumo = wb["Resumo"]
    row_a = next(
        r for r in range(1, ws_resumo.max_row + 1)
        if ws_resumo.cell(r, 1).value == "Total 2027 (A)"
    )
    assert abs(Decimal(str(val("Resumo", f"B{row_a}"))) - analysis.total_a()) <= Decimal("0.01")


def test_resumo_executivo_branding_e_logos(analysis, premises, tmp_path):
    from PIL import Image

    comp_logo = tmp_path / "NNNN.png"
    cli_logo = tmp_path / "cliente.png"
    Image.new("RGB", (200, 60), color=(27, 54, 93)).save(comp_logo)
    Image.new("RGB", (180, 45), color=(0, 128, 64)).save(cli_logo)

    wb = dv.build_workbook(
        analysis,
        premises,
        empresa="Empresa Teste S.A.",
        logo_path=comp_logo,
        client_logo_path=cli_logo,
        calculation_date="24/11/2026 09:00",
    )
    ws = wb["Resumo"]
    meta = {ws.cell(r, 1).value: ws.cell(r, 2).value for r in range(1, ws.max_row + 1)}
    assert meta["Empresa"] == "Empresa Teste S.A."
    assert meta["Data do cálculo"] == "24/11/2026 09:00"
    assert "EC 132/2023" in meta["Base de dados das leis"]
    assert len(ws._images) == 2

    # Formatacao executiva aplicada
    ws_bens = wb["Calculo_Bens"]
    assert ws_bens.cell(1, 1).fill.fgColor.rgb.endswith("1B365D")
    assert ws_bens.cell(2, 6).number_format == dv._FMT_MONEY
    assert ws_bens.page_setup.orientation == ws_bens.ORIENTATION_LANDSCAPE

    # Fallback gracioso sem logos
    wb_no_logo = dv.build_workbook(
        analysis,
        premises,
        logo_path=tmp_path / "nao-existe.png",
        client_logo_path=None,
    )
    assert len(wb_no_logo["Resumo"]._images) == 0


def test_memorando_formato_e_docx_timbrado(analysis, premises, tmp_path):
    memo_md = dv.build_carta(analysis, premises, empresa="Nacional Teste", calculation_date="24/11/2026")
    for token in ("MEMORANDO", "**De:** Nacional Teste", "**Para:** Petrobras", "**Data:** 24/11/2026", "**Assunto:**"):
        assert token in memo_md

    # Usando Papel timbrado.docx real da raiz
    doc = dv.build_memorando_docx(analysis, premises, calculation_date="24/11/2026")
    out_docx = tmp_path / "memorando.docx"
    doc.save(out_docx)
    assert out_docx.exists()

    import docx
    reloaded = docx.Document(str(out_docx))
    body_text = "\n".join(p.text for p in reloaded.paragraphs)
    assert "MEMORANDO TÉCNICO-COMERCIAL" in body_text
    assert "EC 132/2023" in body_text
    assert len(reloaded.tables) == 2
    footer_text = " ".join(p.text for p in reloaded.sections[0].footer.paragraphs)
    assert "NACIONALINDUSTRIA" in footer_text.upper()

    # Fallback gracioso sem papel timbrado
    doc_fb = dv.build_memorando_docx(
        analysis,
        premises,
        letterhead_path=tmp_path / "inexistente.docx",
    )
    assert len(doc_fb.tables) == 2