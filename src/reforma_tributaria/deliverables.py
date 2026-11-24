"""Geracao dos entregaveis de negociacao (apenas rascunhos, nunca envio).

XLSX com formulas vivas ligadas a aba Premissas, parecer executivo, minuta de
carta/e-mail, tabela de priorizacao e lista de pendencias. Cada numero e
auditavel ate a planilha, a premissa ou o documento de origem.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from openpyxl import Workbook
from openpyxl.drawing.image import Image as XLImage
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from . import engine
from .models import ContractAnalysis, FLAG_ALTO_RISCO
from .premises import PremiseSet

DEFAULT_EMPRESA = "Nacional Indústria Mecânica Eireli"
DEFAULT_COMPANY_LOGO = "NNNN.png"
DEFAULT_LETTERHEAD = "Papel timbrado.docx"

_NAVY = "1B365D"
_ACCENT = "2C5282"
_SUBHEADER = "D9E1F2"
_ZEBRA = "F7F9FC"
_BANNER_BG = "F0F4F8"
_OK_BG = "E2EFDA"
_OK_FG = "1E4620"
_WARN_BG = "FCE4D6"
_WARN_FG = "833C0C"

_BORDER_THIN = Side(style="thin", color="D0D7DE")
_BORDER_NAVY = Side(style="medium", color=_NAVY)
_BORDER_DOUBLE = Side(style="double", color=_NAVY)
_CELL_BORDER = Border(left=_BORDER_THIN, right=_BORDER_THIN, top=_BORDER_THIN, bottom=_BORDER_THIN)
_TOTAL_BORDER = Border(left=_BORDER_THIN, right=_BORDER_THIN, top=_BORDER_THIN, bottom=_BORDER_DOUBLE)

_FONT_HEADER = Font(name="Calibri", size=10, bold=True, color="FFFFFF")
_FONT_TITLE = Font(name="Calibri", size=14, bold=True, color=_NAVY)
_FONT_SUBTITLE = Font(name="Calibri", size=10, bold=True, color=_ACCENT)
_FONT_BODY = Font(name="Calibri", size=10, color="1F2937")
_FONT_BOLD = Font(name="Calibri", size=10, bold=True, color="1F2937")
_FONT_OK = Font(name="Calibri", size=10, bold=True, color=_OK_FG)
_FONT_WARN = Font(name="Calibri", size=10, bold=True, color=_WARN_FG)

_FILL_HEADER = PatternFill("solid", fgColor=_NAVY)
_FILL_SUBHEADER = PatternFill("solid", fgColor=_SUBHEADER)
_FILL_ZEBRA = PatternFill("solid", fgColor=_ZEBRA)
_FILL_WHITE = PatternFill("solid", fgColor="FFFFFF")
_FILL_BANNER = PatternFill("solid", fgColor=_BANNER_BG)
_FILL_OK = PatternFill("solid", fgColor=_OK_BG)
_FILL_WARN = PatternFill("solid", fgColor=_WARN_BG)

_FMT_MONEY = 'R$ #,##0.00'
_FMT_PCT_2 = '0.00%'
_FMT_PCT_4 = '0.0000%'
_FMT_QTY = '#,##0.###'

SHEETS = ["Premissas", "Calculo_Bens", "Calculo_Servicos", "Saldo_2027", "Resumo", "Fontes"]

PARAM_ORDER = [
    "pis_presumido", "pis_real", "cofins_presumido", "cofins_real", "icms", "iss",
    "iss_petrobras_multi", "ipi", "difal", "cbs_referencia", "cbs_reducao_transitoria",
    "ibs_estadual", "ibs_municipal",
]

CALC_COLS = [
    "Item", "Fonte", "Descrição", "Un", "Qtd", "P unit", "Total atual",
    "% PIS", "R$ PIS", "% Cofins", "R$ Cofins", "% ICMS/ISS", "R$ ICMS/ISS",
    "% IPI", "R$ IPI", "Base unit", "Base total", "CBS", "IBS est", "IBS mun",
    "Subtotal", "ICMS/ISS 2027 (A)", "P₂₀₂₇ (A)", "Total (A)",
    "ICMS/ISS 2027 (B)", "P₂₀₂₇ (B)", "Total (B)", "Var R$", "Var %", "Flag",
]


def _f(value: Decimal) -> float:
    return float(value)


def fmt_money(value: Decimal) -> str:
    s = f"{value:,.2f}"
    return "R$ " + s.replace(",", "X").replace(".", ",").replace("X", ".")


def fmt_pct(value: Decimal) -> str:
    return f"{value * 100:.4f}%".replace(".", ",")


# --------------------------------------------------------------------------- #
# Helpers de estilizacao executiva e logos
# --------------------------------------------------------------------------- #
def _setup_print(ws) -> None:
    ws.views.sheetView[0].showGridLines = True
    ws.page_setup.orientation = ws.ORIENTATION_LANDSCAPE
    ws.page_setup.paperSize = ws.PAPERSIZE_A4
    ws.sheet_properties.pageSetUpPr.fitToPage = True
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 0


def _style_header_row(ws, row_idx: int = 1, max_col: int | None = None) -> None:
    ncols = max_col or ws.max_column
    ws.row_dimensions[row_idx].height = 28
    for col in range(1, ncols + 1):
        c = ws.cell(row=row_idx, column=col)
        c.font = _FONT_HEADER
        c.fill = _FILL_HEADER
        c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        c.border = _CELL_BORDER


def _style_data_row(ws, row_idx: int, ncols: int, zebra: bool = False) -> None:
    fill = _FILL_ZEBRA if zebra else _FILL_WHITE
    ws.row_dimensions[row_idx].height = 20
    for col in range(1, ncols + 1):
        c = ws.cell(row=row_idx, column=col)
        c.font = _FONT_BODY
        c.fill = fill
        c.border = _CELL_BORDER
        if c.alignment is None or c.alignment.vertical is None:
            c.alignment = Alignment(vertical="center")


def _auto_fit_columns(ws, min_width: int = 10, max_width: int = 55) -> None:
    for col_idx in range(1, ws.max_column + 1):
        letter = get_column_letter(col_idx)
        best = min_width
        for row_idx in range(1, ws.max_row + 1):
            val = ws.cell(row=row_idx, column=col_idx).value
            if val is None:
                continue
            s = str(val)
            if s.startswith("="):
                best = max(best, 14)
            else:
                best = max(best, min(len(s) + 4, max_width))
        ws.column_dimensions[letter].width = best


def _resolve_company_logo(logo_path: str | Path | None) -> Path | None:
    if logo_path is not None:
        p = Path(logo_path)
        return p if p.is_file() else None
    for cand in (
        Path.cwd() / DEFAULT_COMPANY_LOGO,
        Path(__file__).resolve().parents[2] / DEFAULT_COMPANY_LOGO,
    ):
        if cand.is_file():
            return cand
    return None


def _add_logo(ws, image_path: str | Path | None, anchor: str, max_w: int = 160, max_h: int = 56) -> bool:
    if not image_path:
        return False
    p = Path(image_path)
    if not p.is_file():
        return False
    try:
        img = XLImage(str(p))
        if img.width and img.height:
            scale = min(max_w / img.width, max_h / img.height, 1.0)
            img.width = max(1, int(img.width * scale))
            img.height = max(1, int(img.height * scale))
        ws.add_image(img, anchor)
        return True
    except Exception:
        return False


# --------------------------------------------------------------------------- #
# XLSX
# --------------------------------------------------------------------------- #
def _premissas_sheet(wb: Workbook, ps: PremiseSet) -> dict[str, str]:
    ws = wb.create_sheet("Premissas")
    ws.append(["Parâmetro", "Valor", "Fonte"])
    _style_header_row(ws, 1, 3)
    cells: dict[str, str] = {}
    row = 2
    for key in PARAM_ORDER:
        ws.append([key, _f(ps.get(key)), ps.source(key)])
        _style_data_row(ws, row, 3, zebra=(row % 2 == 1))
        ws.cell(row, 2).number_format = _FMT_PCT_4
        ws.cell(row, 2).alignment = Alignment(horizontal="right", vertical="center")
        ws.cell(row, 3).alignment = Alignment(vertical="center", wrap_text=True)
        cells[key] = f"Premissas!$B${row}"
        row += 1
    # derivados por formula (editar a referencia recalcula)
    ws.append(["cbs_efetiva", f"={cells['cbs_referencia']}-{cells['cbs_reducao_transitoria']}",
               "CBS referência menos redução transitória 2027"])
    _style_data_row(ws, row, 3, zebra=(row % 2 == 1))
    ws.cell(row, 1).font = _FONT_BOLD
    ws.cell(row, 2).font = _FONT_BOLD
    ws.cell(row, 2).number_format = _FMT_PCT_4
    cells["cbs_efetiva"] = f"Premissas!$B${row}"
    row += 1
    ws.append(["ibs_total", f"={cells['ibs_estadual']}+{cells['ibs_municipal']}",
               "IBS estadual + municipal"])
    _style_data_row(ws, row, 3, zebra=(row % 2 == 1))
    ws.cell(row, 1).font = _FONT_BOLD
    ws.cell(row, 2).font = _FONT_BOLD
    ws.cell(row, 2).number_format = _FMT_PCT_4
    cells["ibs_total"] = f"Premissas!$B${row}"
    row += 1
    ws.append(["cenario_padrao", ps.cenario, ps.cenario_source])
    _style_data_row(ws, row, 3, zebra=(row % 2 == 1))
    ws.cell(row, 2).alignment = Alignment(horizontal="center", vertical="center")
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = f"A1:C{row}"
    ws.column_dimensions["A"].width = 26
    ws.column_dimensions["B"].width = 16
    ws.column_dimensions["C"].width = 76
    _setup_print(ws)
    return cells


_CALC_MONEY_COLS = {6, 7, 9, 11, 13, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28}
_CALC_PCT4_COLS = {8, 10, 12, 14}


def _calculo_sheet(wb: Workbook, name: str, analysis: ContractAnalysis,
                   ps: PremiseSet, cells: dict[str, str], natureza: str) -> None:
    ws = wb.create_sheet(name)
    ws.append(CALC_COLS)
    _style_header_row(ws, 1, len(CALC_COLS))
    regime = analysis.header.regime or ps.regime_padrao
    pis_cell = cells["pis_real" if regime == "real" else "pis_presumido"]
    cof_cell = cells["cofins_real" if regime == "real" else "cofins_presumido"]
    ipi_cell = cells["ipi"]
    cbs_cell = cells["cbs_efetiva"]
    ibs_est_cell = cells["ibs_estadual"]
    ibs_mun_cell = cells["ibs_municipal"]

    pairs = [(it, r) for it, r in zip(analysis.items, analysis.results) if r.natureza == natureza]
    for idx, (it, r) in enumerate(pairs):
        row = idx + 2
        ws.cell(row=row, column=1, value=it.item)
        ws.cell(row=row, column=2, value=it.fonte.describe() if it.fonte else "")
        ws.cell(row=row, column=3, value=it.descricao)
        ws.cell(row=row, column=4, value=it.unidade)
        ws.cell(row=row, column=5, value=_f(it.quantidade))
        ws.cell(row=row, column=6, value=_f(it.preco_unitario))
        formulas = {
            7: f"=E{row}*F{row}",
            8: f"={pis_cell}",
            9: f"=F{row}*H{row}",
            10: f"={cof_cell}",
            11: f"=F{row}*J{row}",
            12: _f(r.a_L),  # aliquota do item (dado de entrada)
            13: f"=F{row}*L{row}",
            14: f"={ipi_cell}",
            15: f"=F{row}*N{row}",
            16: f"=F{row}-(I{row}+K{row}+M{row}+O{row})",
            17: f"=P{row}*E{row}",
            18: f"=P{row}*{cbs_cell}",
            19: f"=P{row}*{ibs_est_cell}",
            20: f"=P{row}*{ibs_mun_cell}",
            21: f"=P{row}+R{row}+S{row}+T{row}",
            22: f"=U{row}*L{row}/(1-L{row})",
            23: f"=U{row}+V{row}",
            24: f"=W{row}*E{row}",
            25: f"=P{row}*L{row}/(1-L{row})",
            26: f"=U{row}+Y{row}",
            27: f"=Z{row}*E{row}",
            28: f"=X{row}-G{row}",
            29: f"=AB{row}/G{row}",
        }
        for col, val in formulas.items():
            ws.cell(row=row, column=col, value=val)
        flags_txt = "; ".join(r.flags)
        ws.cell(row=row, column=30, value=flags_txt)
        _style_data_row(ws, row, len(CALC_COLS), zebra=(row % 2 == 1))
        ws.cell(row, 4).alignment = Alignment(horizontal="center", vertical="center")
        ws.cell(row, 5).number_format = _FMT_QTY
        for mc in _CALC_MONEY_COLS:
            ws.cell(row, mc).number_format = _FMT_MONEY
        for pc in _CALC_PCT4_COLS:
            ws.cell(row, pc).number_format = _FMT_PCT_4
        ws.cell(row, 29).number_format = _FMT_PCT_2
        if flags_txt:
            ws.cell(row, 30).fill = _FILL_WARN
            ws.cell(row, 30).font = _FONT_WARN

    ws.freeze_panes = "A2"
    ws.auto_filter.ref = f"A1:{get_column_letter(len(CALC_COLS))}{max(1, ws.max_row)}"
    _auto_fit_columns(ws, min_width=13, max_width=42)
    ws.column_dimensions["A"].width = 8
    ws.column_dimensions["D"].width = 7
    ws.column_dimensions["E"].width = 10
    ws.column_dimensions["B"].width = 34
    ws.column_dimensions["C"].width = 38
    _setup_print(ws)


def _saldo_sheet(wb: Workbook, analysis: ContractAnalysis) -> None:
    ws = wb.create_sheet("Saldo_2027")
    ws.append(["Item", "Descrição", "Saldo 2027 (R$)", "Impacto A (R$)", "Impacto B (R$)"])
    _style_header_row(ws, 1, 5)
    tot_s = tot_a = tot_b = Decimal("0")
    atual = analysis.total_atual()
    global_prop = (
        analysis.saldo.saldo_2027 / atual
        if atual and not analysis.saldo.pendente
        else Decimal("1")
    )
    for idx, (it, r) in enumerate(zip(analysis.items, analysis.results)):
        row = idx + 2
        base = it.total if it.total else r.total_atual
        if it.saldo_2027 is not None:
            saldo = it.saldo_2027
            prop = saldo / base if base else Decimal("0")
        else:
            prop = global_prop
            saldo = base * prop
        imp_a = r.var_rs * prop
        imp_b = (r.total_b - r.total_atual) * prop
        ws.append([it.item, it.descricao, _f(saldo), _f(imp_a), _f(imp_b)])
        _style_data_row(ws, row, 5, zebra=(row % 2 == 1))
        for mc in (3, 4, 5):
            ws.cell(row, mc).number_format = _FMT_MONEY
        tot_s += saldo
        tot_a += imp_a
        tot_b += imp_b

    tot_row = ws.max_row + 1
    ws.append(["TOTAL", "", _f(tot_s), _f(tot_a), _f(tot_b)])
    ws.row_dimensions[tot_row].height = 24
    for col in range(1, 6):
        c = ws.cell(tot_row, col)
        c.font = _FONT_BOLD
        c.fill = _FILL_SUBHEADER
        c.border = _TOTAL_BORDER
        if col >= 3:
            c.number_format = _FMT_MONEY
    ws.freeze_panes = "A2"
    _auto_fit_columns(ws, min_width=14, max_width=48)
    ws.column_dimensions["A"].width = 10
    _setup_print(ws)


def _resumo_sheet(
    wb: Workbook,
    analysis: ContractAnalysis,
    ps: PremiseSet,
    *,
    empresa: str = DEFAULT_EMPRESA,
    logo_path: str | Path | None = None,
    client_logo_path: str | Path | None = None,
    calculation_date: str | None = None,
) -> None:
    ws = wb.create_sheet("Resumo")
    h = analysis.header
    calc_dt = calculation_date or datetime.now().strftime("%d/%m/%Y %H:%M")
    legal_dt = ps.legal_base_date or "EC 132/2023 e LC 214/2025"

    # Faixa 1..4: Banner institucional com logos (esquerda: empresa, direita: cliente)
    for r in range(1, 5):
        ws.row_dimensions[r].height = 19
        for col in range(1, 6):
            ws.cell(r, col).fill = _FILL_BANNER
    ws.merge_cells("B1:D2")
    ws["B1"] = "ANÁLISE DE IMPACTO — REFORMA TRIBUTÁRIA 2027"
    ws["B1"].font = _FONT_TITLE
    ws["B1"].alignment = Alignment(horizontal="center", vertical="center")
    ws.merge_cells("B3:D4")
    ws["B3"] = f"Pedido / Contrato: {h.numero or '-'}   |   Cliente: {h.cliente or '-'}"
    ws["B3"].font = _FONT_SUBTITLE
    ws["B3"].alignment = Alignment(horizontal="center", vertical="center")

    comp_logo = _resolve_company_logo(logo_path)
    cli_logo = client_logo_path or h.client_logo_path
    _add_logo(ws, comp_logo, "A1")
    _add_logo(ws, cli_logo, "E1")

    # Linhas 5..8: Governanca (Empresa, Data do calculo, Base das leis, Regime)
    meta_rows = [
        ("Empresa", empresa),
        ("Data do cálculo", calc_dt),
        ("Base de dados das leis", legal_dt),
        ("Regime tributário", (h.regime or ps.regime_padrao).upper()),
    ]
    for offset, (m_label, m_val) in enumerate(meta_rows):
        r = 5 + offset
        ws.row_dimensions[r].height = 20
        ws.cell(r, 1, m_label).font = _FONT_BOLD
        ws.cell(r, 1).fill = _FILL_ZEBRA
        ws.cell(r, 1).border = _CELL_BORDER
        ws.merge_cells(start_row=r, start_column=2, end_row=r, end_column=5)
        ws.cell(r, 2, m_val).font = _FONT_BODY
        for col in range(2, 6):
            ws.cell(r, col).fill = _FILL_WHITE
            ws.cell(r, col).border = _CELL_BORDER

    # Linha 10: Cabecalho da tabela de indicadores executivos
    tbl_hdr = 10
    ws.cell(tbl_hdr, 1, "Campo")
    ws.cell(tbl_hdr, 2, "Valor")
    ws.merge_cells(start_row=tbl_hdr, start_column=3, end_row=tbl_hdr, end_column=5)
    ws.cell(tbl_hdr, 3, "Referência / Observação")
    _style_header_row(ws, tbl_hdr, 5)

    nb = sum(1 for r in analysis.results if r.natureza == "BEM")
    ns = sum(1 for r in analysis.results if r.natureza == "SERVIÇO")

    def rng(sheet: str, col: str, n: int) -> str:
        return f"SUM({sheet}!{col}2:{col}{n + 1})" if n else "0"

    bens, serv = "Calculo_Bens", "Calculo_Servicos"
    total_atual = f"={rng(bens, 'G', nb)}+{rng(serv, 'G', ns)}"
    base = f"={rng(bens, 'Q', nb)}+{rng(serv, 'Q', ns)}"
    total_a = f"={rng(bens, 'X', nb)}+{rng(serv, 'X', ns)}"
    total_b = f"={rng(bens, 'AA', nb)}+{rng(serv, 'AA', ns)}"
    r_atual = tbl_hdr + 1
    r_a = tbl_hdr + 3
    r_var = tbl_hdr + 5
    val = engine.validate(analysis.items, analysis.results, analysis.ppu_total)

    kpi_rows = [
        ("Total atual", total_atual, _FMT_MONEY, "Valor bruto contratado (P0)"),
        ("Base total", base, _FMT_MONEY, "Base líquida sem tributos"),
        ("Total 2027 (A)", total_a, _FMT_MONEY, "Cenário A: CBS/IBS na base do ICMS/ISS"),
        ("Total 2027 (B)", total_b, _FMT_MONEY, "Cenário B: ICMS/ISS fora da base"),
        ("Variação R$ (A)", f"=B{r_a}-B{r_atual}", _FMT_MONEY, "Impacto financeiro no preço (Cenário A)"),
        ("Variação % (A)", f"=B{r_var}/B{r_atual}", _FMT_PCT_2, "Impacto percentual sobre P0"),
        ("Saldo 2027", _f(analysis.saldo.saldo_2027), _FMT_MONEY, f"Escopo: {analysis.scope}"),
        ("Conferência reconciliação (±R$0,01)", "OK" if val["reconciliacao"]["ok"] else "DIVERGE", None, "Soma dos itens vs PPU"),
        ("Conferência Q×P", "OK" if val["qp"]["ok"] else "DIVERGE", None, "Quantidade × Preço unitário"),
        ("Conferência base invariante", "OK" if val["base_invariante"]["ok"] else "DIVERGE", None, "Base líquida preservada em 2027"),
        ("Conferência fator", "OK" if val["fator"]["ok"] else "DIVERGE", None, "Consistência do fator multiplicador"),
        ("Cláusula de revisão", analysis.header.clausula_revisao or "ausente (ALTO RISCO)", None, "Amparo contratual para reequilíbrio"),
        ("CBS efetiva (premissa)", _f(ps.cbs_efetiva), _FMT_PCT_4, ps.source("cbs_referencia")),
        ("Fonte CBS", ps.source("cbs_referencia"), None, "Referência normativa da premissa"),
    ]

    for idx, (label, value, num_fmt, note) in enumerate(kpi_rows):
        r = tbl_hdr + 1 + idx
        ws.cell(r, 1, label)
        ws.cell(r, 2, value)
        ws.merge_cells(start_row=r, start_column=3, end_row=r, end_column=5)
        ws.cell(r, 3, note)
        _style_data_row(ws, r, 5, zebra=(idx % 2 == 1))
        ws.cell(r, 1).font = _FONT_BOLD
        if num_fmt:
            ws.cell(r, 2).number_format = num_fmt
            ws.cell(r, 2).font = _FONT_BOLD
        if value == "OK":
            ws.cell(r, 2).fill = _FILL_OK
            ws.cell(r, 2).font = _FONT_OK
            ws.cell(r, 2).alignment = Alignment(horizontal="center", vertical="center")
        elif value in ("DIVERGE", "ausente (ALTO RISCO)"):
            ws.cell(r, 2).fill = _FILL_WARN
            ws.cell(r, 2).font = _FONT_WARN
            ws.cell(r, 2).alignment = Alignment(horizontal="center", vertical="center")

    ws.column_dimensions["A"].width = 36
    ws.column_dimensions["B"].width = 24
    ws.column_dimensions["C"].width = 22
    ws.column_dimensions["D"].width = 22
    ws.column_dimensions["E"].width = 26
    _setup_print(ws)


def _fontes_sheet(wb: Workbook, analysis: ContractAnalysis) -> None:
    ws = wb.create_sheet("Fontes")
    ws.append(["Tipo", "Referência"])
    _style_header_row(ws, 1, 2)
    row = 2
    for doc in analysis.documents:
        ws.append([doc.kind, doc.path])
        _style_data_row(ws, row, 2, zebra=(row % 2 == 1))
        ws.cell(row, 2).alignment = Alignment(vertical="center", wrap_text=True)
        row += 1
    for ref in analysis.referencias_legais:
        ws.append(["Legal", ref])
        _style_data_row(ws, row, 2, zebra=(row % 2 == 1))
        ws.cell(row, 2).alignment = Alignment(vertical="center", wrap_text=True)
        row += 1
    ws.freeze_panes = "A2"
    ws.column_dimensions["A"].width = 18
    ws.column_dimensions["B"].width = 92
    _setup_print(ws)


def build_workbook(
    analysis: ContractAnalysis,
    ps: PremiseSet,
    *,
    empresa: str = DEFAULT_EMPRESA,
    logo_path: str | Path | None = None,
    client_logo_path: str | Path | None = None,
    calculation_date: str | None = None,
) -> Workbook:
    """Gera o XLSX com as seis abas estilizadas e formulas ligadas a Premissas."""
    wb = Workbook()
    wb.remove(wb.active)
    cells = _premissas_sheet(wb, ps)
    _calculo_sheet(wb, "Calculo_Bens", analysis, ps, cells, "BEM")
    _calculo_sheet(wb, "Calculo_Servicos", analysis, ps, cells, "SERVIÇO")
    _saldo_sheet(wb, analysis)
    _resumo_sheet(
        wb,
        analysis,
        ps,
        empresa=empresa,
        logo_path=logo_path,
        client_logo_path=client_logo_path,
        calculation_date=calculation_date,
    )
    _fontes_sheet(wb, analysis)
    return wb


# --------------------------------------------------------------------------- #
# Parecer / carta / priorizacao / pendencias
# --------------------------------------------------------------------------- #
def build_parecer(analysis: ContractAnalysis, ps: PremiseSet) -> str:
    h = analysis.header
    impacto = analysis.impacto_saldo_2027()
    clause = h.clausula_revisao or "ausente"
    risco = "ALTO RISCO: sem cláusula de revisão, repasse incerto." if analysis.clause_risk else \
        f"Revisão amparada na cláusula {clause}."
    lines = [
        f"# Parecer executivo — {h.numero or 'pedido'} ({h.cliente or 'cliente'})",
        "",
        f"- **Saldo 2027:** {fmt_money(analysis.saldo.saldo_2027)}",
        f"- **Impacto no saldo 2027 (Cenário A):** {fmt_money(impacto)} "
        f"({fmt_pct(analysis.var_pct())} sobre o total)",
        f"- **Total atual → 2027 (A):** {fmt_money(analysis.total_atual())} → "
        f"{fmt_money(analysis.total_a())} (B: {fmt_money(analysis.total_b())})",
        f"- **Cláusula de revisão:** {clause}. {risco}",
        f"- **Premissa CBS efetiva:** {fmt_pct(ps.cbs_efetiva)} "
        f"(fonte: {ps.source('cbs_referencia')}; aba Premissas)",
        f"- **Base total apurada:** {fmt_money(analysis.base_total())} "
        "(fonte: aba Resumo / Calculo_Bens e Calculo_Servicos)",
    ]
    if analysis.regime_note:
        lines.append(f"- **Nota de regime:** {analysis.regime_note}")
    lines += [
        "",
        "**Recomendação:** propor revisão pelo Cenário A (conservador), apresentar o "
        "Cenário B como sensibilidade e formalizar aditivo com ressalva de revisão da "
        "base do ICMS/ISS. Confirmar pendências antes da emissão.",
        "",
        "_Rascunho técnico — números auditáveis na planilha (abas Premissas/Calculo/Resumo)._",
    ]
    return "\n".join(lines)


RESSALVA = (
    "Ressalva: a inclusão da CBS/IBS na base do ICMS/ISS (Cenário A, posição "
    "Sefaz-SP RC 33.083/2026 e Sefaz-PR) está em disputa (PLP 16/2025 e liminares). "
    "O preço proposto será revisado caso lei ou decisão judicial altere a base de cálculo."
)


def build_carta(
    analysis: ContractAnalysis,
    ps: PremiseSet,
    *,
    empresa: str = DEFAULT_EMPRESA,
    calculation_date: str | None = None,
) -> str:
    h = analysis.header
    clause = h.clausula_revisao or "cláusula de reequilíbrio aplicável"
    dt = calculation_date or datetime.now().strftime("%d/%m/%Y")
    return "\n".join([
        "# MEMORANDO TÉCNICO-COMERCIAL",
        "",
        f"**De:** {empresa}",
        f"**Para:** {h.cliente or 'Cliente'}",
        f"**Data:** {dt}",
        f"**Ref.:** Pedido / Contrato {h.numero or 'N/D'}",
        "**Assunto:** Revisão de Preços — Transição Tributária 2027 (EC 132/2023 e LC 214/2025)",
        "",
        "**RASCUNHO — não enviado.**",
        "",
        "Prezados,",
        "",
        "Com fundamento na EC 132/2023, na LC 214/2025 e na cláusula contratual "
        f"{clause}, apresentamos a revisão de preços para o saldo faturável a partir "
        "de 01/01/2027, em razão da transição da tributação sobre o consumo.",
        "",
        f"- **Valor-base apurado:** {fmt_money(analysis.base_total())}.",
        f"- **Nova PPU proposta para 2027 (Cenário A):** {fmt_money(analysis.total_a())} "
        f"(total atual {fmt_money(analysis.total_atual())}; variação "
        f"{fmt_money(analysis.var_rs())}, {fmt_pct(analysis.var_pct())}).",
        f"- **CBS efetiva considerada:** {fmt_pct(ps.cbs_efetiva)}; IBS 0,10%.",
        "",
        RESSALVA,
        "",
        "Solicitamos a formalização de aditivo contratual ou revisão da PPU para 2027, "
        "permanecendo à disposição para conciliar os valores e o cronograma de faturamento.",
        "",
        "Atenciosamente,",
        empresa,
    ])


def _resolve_letterhead(letterhead_path: str | Path | None) -> Path | None:
    if letterhead_path is not None:
        p = Path(letterhead_path)
        return p if p.is_file() else None
    for cand in (
        Path.cwd() / DEFAULT_LETTERHEAD,
        Path(__file__).resolve().parents[2] / DEFAULT_LETTERHEAD,
    ):
        if cand.is_file():
            return cand
    return None


def _shade_docx_cell(cell, hex_color: str) -> None:
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn

    tc_pr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:fill"), hex_color)
    tc_pr.append(shd)


def build_memorando_docx(
    analysis: ContractAnalysis,
    ps: PremiseSet,
    *,
    empresa: str = DEFAULT_EMPRESA,
    letterhead_path: str | Path | None = None,
    calculation_date: str | None = None,
) -> Any:
    """Gera Memorando formal em DOCX usando o papel timbrado da empresa."""
    from docx import Document as DocxDocument
    from docx.shared import Pt, RGBColor

    tpl = _resolve_letterhead(letterhead_path)
    doc = DocxDocument(str(tpl)) if tpl else DocxDocument()

    # Remove paragrafo inicial em branco do modelo para evitar espaco extra
    if len(doc.paragraphs) == 1 and not doc.paragraphs[0].text.strip():
        p_elem = doc.paragraphs[0]._element
        p_elem.getparent().remove(p_elem)

    h = analysis.header
    clause = h.clausula_revisao or "cláusula de reequilíbrio aplicável"
    dt = calculation_date or datetime.now().strftime("%d/%m/%Y")

    title_p = doc.add_paragraph()
    title_p.paragraph_format.space_before = Pt(6)
    title_p.paragraph_format.space_after = Pt(2)
    r_title = title_p.add_run("MEMORANDO TÉCNICO-COMERCIAL")
    r_title.bold = True
    r_title.font.name = "Calibri"
    r_title.font.size = Pt(13)
    r_title.font.color.rgb = RGBColor(0x1B, 0x36, 0x5D)

    draft_p = doc.add_paragraph()
    draft_p.paragraph_format.space_after = Pt(8)
    r_draft = draft_p.add_run("RASCUNHO — não enviado.")
    r_draft.italic = True
    r_draft.bold = True
    r_draft.font.name = "Calibri"
    r_draft.font.size = Pt(9)
    r_draft.font.color.rgb = RGBColor(0x83, 0x3C, 0x0C)

    # Quadro de identificacao do Memorando
    meta_rows = [
        ("De:", empresa),
        ("Para:", h.cliente or "Cliente"),
        ("Data:", dt),
        ("Referência:", f"Pedido / Contrato nº {h.numero or 'N/D'}"),
        ("Assunto:", "Revisão de Preços — Transição Tributária 2027 (EC 132/2023 e LC 214/2025)"),
    ]
    tbl_meta = doc.add_table(rows=len(meta_rows), cols=2)
    tbl_meta.style = "Table Grid"
    for i, (k, v) in enumerate(meta_rows):
        c0, c1 = tbl_meta.rows[i].cells
        _shade_docx_cell(c0, "F0F4F8")
        r0 = c0.paragraphs[0].add_run(k)
        r0.bold = True
        r0.font.name = "Calibri"
        r0.font.size = Pt(10)
        r1 = c1.paragraphs[0].add_run(v)
        r1.font.name = "Calibri"
        r1.font.size = Pt(10)

    intro = doc.add_paragraph()
    intro.paragraph_format.space_before = Pt(10)
    intro.paragraph_format.space_after = Pt(6)
    r_intro = intro.add_run(
        "Prezados,\n\n"
        "Com fundamento na EC 132/2023, na LC 214/2025 e na cláusula contratual "
        f"{clause}, apresentamos a análise e revisão de preços referente ao saldo "
        "faturável a partir de 01/01/2027, em decorrência da transição da tributação sobre o consumo:"
    )
    r_intro.font.name = "Calibri"
    r_intro.font.size = Pt(10.5)

    # Tabela resumo de valores
    fin_rows = [
        ("Indicador", "Valor"),
        ("Valor-base apurado (líquido sem tributos)", fmt_money(analysis.base_total())),
        ("Total atual contratado (P0)", fmt_money(analysis.total_atual())),
        ("Nova PPU proposta para 2027 (Cenário A)", fmt_money(analysis.total_a())),
        ("Variação (Cenário A)", f"{fmt_money(analysis.var_rs())} ({fmt_pct(analysis.var_pct())})"),
        ("Saldo faturável em 2027", fmt_money(analysis.saldo.saldo_2027)),
        ("Premissa tributária 2027", f"CBS efetiva {fmt_pct(ps.cbs_efetiva)}; IBS 0,10%"),
    ]
    tbl_fin = doc.add_table(rows=len(fin_rows), cols=2)
    tbl_fin.style = "Table Grid"
    for i, (k, v) in enumerate(fin_rows):
        c0, c1 = tbl_fin.rows[i].cells
        if i == 0:
            _shade_docx_cell(c0, "1B365D")
            _shade_docx_cell(c1, "1B365D")
        elif i % 2 == 1:
            _shade_docx_cell(c0, "F7F9FC")
            _shade_docx_cell(c1, "F7F9FC")
        for cell, txt in ((c0, k), (c1, v)):
            run = cell.paragraphs[0].add_run(txt)
            run.font.name = "Calibri"
            run.font.size = Pt(10)
            if i == 0:
                run.bold = True
                run.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
            elif i == 3:
                run.bold = True

    res_p = doc.add_paragraph()
    res_p.paragraph_format.space_before = Pt(8)
    res_p.paragraph_format.space_after = Pt(8)
    r_res = res_p.add_run(RESSALVA)
    r_res.italic = True
    r_res.font.name = "Calibri"
    r_res.font.size = Pt(9.5)

    close_p = doc.add_paragraph()
    close_p.paragraph_format.space_after = Pt(14)
    r_close = close_p.add_run(
        "Solicitamos a formalização de aditivo contratual ou revisão da PPU para 2027, "
        "permanecendo à disposição para conciliar os valores e o cronograma de faturamento."
    )
    r_close.font.name = "Calibri"
    r_close.font.size = Pt(10.5)

    sig_p = doc.add_paragraph()
    r_sig = sig_p.add_run(f"Atenciosamente,\n{empresa}")
    r_sig.bold = True
    r_sig.font.name = "Calibri"
    r_sig.font.size = Pt(10.5)
    return doc


def build_priorizacao(analyses: list[ContractAnalysis], ps: PremiseSet) -> str:
    rows = sorted(analyses, key=lambda a: a.impacto_saldo_2027(), reverse=True)
    out = [
        "| Pedido | Cliente | Saldo 2027 | Impacto R$ (A) | Cláusula | Risco |",
        "|---|---|---|---|---|---|",
    ]
    for a in rows:
        risco = FLAG_ALTO_RISCO if a.clause_risk else "—"
        out.append(
            f"| {a.header.numero or '—'} | {a.header.cliente or '—'} | "
            f"{fmt_money(a.saldo.saldo_2027)} | {fmt_money(a.impacto_saldo_2027())} | "
            f"{a.header.clausula_revisao or 'ausente'} | {risco} |"
        )
    return "\n".join(out)


def build_pendencias(analysis: ContractAnalysis, ps: PremiseSet) -> list[str]:
    pend = [
        "Confirmar regime tributário (Presumido / Real / Simples).",
        "Confirmar ISS do município (ou padrão Petrobras multi-cidade 5%).",
        "Confirmar DIFAL (deduzir somente se houver valor no preço).",
        f"Confirmar alíquota CBS final (referência atual {fmt_pct(ps.cbs_efetiva)}, sujeita ao Senado).",
        "Confirmar cronograma de faturamento e saldo 2027.",
    ]
    for it in analysis.items:
        for p in it.pendencias:
            if p not in pend:
                pend.append(f"Item {it.item}: {p}")
    return pend