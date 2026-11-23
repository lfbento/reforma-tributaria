"""Geracao dos entregaveis de negociacao (apenas rascunhos, nunca envio).

XLSX com formulas vivas ligadas a aba Premissas, parecer executivo, minuta de
carta/e-mail, tabela de priorizacao e lista de pendencias. Cada numero e
auditavel ate a planilha, a premissa ou o documento de origem.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from openpyxl import Workbook
from openpyxl.utils import get_column_letter

from . import engine
from .models import ContractAnalysis, FLAG_ALTO_RISCO
from .premises import PremiseSet

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
# XLSX
# --------------------------------------------------------------------------- #
def _premissas_sheet(wb: Workbook, ps: PremiseSet) -> dict[str, str]:
    ws = wb.create_sheet("Premissas")
    ws.append(["Parâmetro", "Valor", "Fonte"])
    cells: dict[str, str] = {}
    row = 2
    for key in PARAM_ORDER:
        ws.append([key, _f(ps.get(key)), ps.source(key)])
        cells[key] = f"Premissas!$B${row}"
        row += 1
    # derivados por formula (editar a referencia recalcula)
    ws.append(["cbs_efetiva", f"={cells['cbs_referencia']}-{cells['cbs_reducao_transitoria']}",
               "CBS referência menos redução transitória 2027"])
    cells["cbs_efetiva"] = f"Premissas!$B${row}"
    row += 1
    ws.append(["ibs_total", f"={cells['ibs_estadual']}+{cells['ibs_municipal']}",
               "IBS estadual + municipal"])
    cells["ibs_total"] = f"Premissas!$B${row}"
    row += 1
    ws.append(["cenario_padrao", ps.cenario, ps.cenario_source])
    return cells


def _calculo_sheet(wb: Workbook, name: str, analysis: ContractAnalysis,
                   ps: PremiseSet, cells: dict[str, str], natureza: str) -> None:
    ws = wb.create_sheet(name)
    ws.append(CALC_COLS)
    regime = analysis.header.regime or "presumido"
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
        ws.cell(row=row, column=30, value="; ".join(r.flags))
    ws.freeze_panes = "A2"


def _saldo_sheet(wb: Workbook, analysis: ContractAnalysis) -> None:
    ws = wb.create_sheet("Saldo_2027")
    ws.append(["Item", "Descrição", "Saldo 2027 (R$)", "Impacto A (R$)", "Impacto B (R$)"])
    tot_s = tot_a = tot_b = Decimal("0")
    atual = analysis.total_atual()
    global_prop = (
        analysis.saldo.saldo_2027 / atual
        if atual and not analysis.saldo.pendente
        else Decimal("1")
    )
    for it, r in zip(analysis.items, analysis.results):
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
        tot_s += saldo
        tot_a += imp_a
        tot_b += imp_b
    ws.append(["TOTAL", "", _f(tot_s), _f(tot_a), _f(tot_b)])


def _resumo_sheet(wb: Workbook, analysis: ContractAnalysis, ps: PremiseSet) -> None:
    ws = wb.create_sheet("Resumo")
    nb = sum(1 for r in analysis.results if r.natureza == "BEM")
    ns = sum(1 for r in analysis.results if r.natureza == "SERVIÇO")
    def rng(sheet, col, n):
        return f"SUM({sheet}!{col}2:{col}{n + 1})" if n else "0"
    bens, serv = "Calculo_Bens", "Calculo_Servicos"
    total_atual = f"={rng(bens, 'G', nb)}+{rng(serv, 'G', ns)}"
    base = f"={rng(bens, 'Q', nb)}+{rng(serv, 'Q', ns)}"
    total_a = f"={rng(bens, 'X', nb)}+{rng(serv, 'X', ns)}"
    total_b = f"={rng(bens, 'AA', nb)}+{rng(serv, 'AA', ns)}"
    val = engine.validate(analysis.items, analysis.results, analysis.ppu_total)
    rows = [
        ("Total atual", total_atual),
        ("Base total", base),
        ("Total 2027 (A)", total_a),
        ("Total 2027 (B)", total_b),
        ("Variação R$ (A)", "=B4-B2"),
        ("Variação % (A)", "=B6/B2"),
        ("Conferência reconciliação (±R$0,01)", "OK" if val["reconciliacao"]["ok"] else "DIVERGE"),
        ("Conferência Q×P", "OK" if val["qp"]["ok"] else "DIVERGE"),
        ("Conferência base invariante", "OK" if val["base_invariante"]["ok"] else "DIVERGE"),
        ("Conferência fator", "OK" if val["fator"]["ok"] else "DIVERGE"),
        ("Cláusula de revisão", analysis.header.clausula_revisao or "ausente (ALTO RISCO)"),
        ("CBS efetiva (premissa)", fmt_pct(ps.cbs_efetiva)),
        ("Fonte CBS", ps.source("cbs_referencia")),
    ]
    ws.append(["Campo", "Valor"])
    for label, value in rows:
        ws.append([label, value])


def _fontes_sheet(wb: Workbook, analysis: ContractAnalysis) -> None:
    ws = wb.create_sheet("Fontes")
    ws.append(["Tipo", "Referência"])
    for doc in analysis.documents:
        ws.append([doc.kind, doc.path])
    for ref in analysis.referencias_legais:
        ws.append(["Legal", ref])


def build_workbook(analysis: ContractAnalysis, ps: PremiseSet) -> Workbook:
    """Gera o XLSX com as seis abas e formulas ligadas a Premissas."""
    wb = Workbook()
    wb.remove(wb.active)
    cells = _premissas_sheet(wb, ps)
    _calculo_sheet(wb, "Calculo_Bens", analysis, ps, cells, "BEM")
    _calculo_sheet(wb, "Calculo_Servicos", analysis, ps, cells, "SERVIÇO")
    _saldo_sheet(wb, analysis)
    _resumo_sheet(wb, analysis, ps)
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


def build_carta(analysis: ContractAnalysis, ps: PremiseSet) -> str:
    h = analysis.header
    clause = h.clausula_revisao or "cláusula de reequilíbrio aplicável"
    return "\n".join([
        f"À {h.cliente or 'Cliente'} — Ref.: {h.numero or 'pedido/contrato'}",
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
        "Nacional Indústria Mecânica Ltda.",
    ])


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