"""Motor de calculo deterministico do impacto da Reforma Tributaria por item.

Metodologia (prompt §5), em ``Decimal`` e precisao cheia; arredondamento apenas
na exibicao. Cenário A (CBS/IBS na base do ICMS/ISS) e o preco proposto; Cenário
B e a sensibilidade. ICMS/ISS/PIS/Cofins nao entram na base da CBS/IBS (LC 214,
art. 12, §2º, V).
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from .models import (
    FLAG_DIVERGENCIA,
    NATUREZA_BEM,
    NATUREZA_SERVICO,
    CalcResult,
    ContractHeader,
    LineItem,
)
from .premises import PremiseSet
from .triage import classify_nature

MONEY_TOL = Decimal("0.01")
UNIT_TOL = Decimal("0.0001")
FACTOR_TOL = Decimal("0.000001")

REAL_CREDIT_NOTE = (
    "Lucro Real: os creditos de PIS/Cofins atuais e os futuros creditos de CBS/IBS "
    "afetam a margem, mas nao entram no preco por esta metodologia."
)


def round_unit(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.0001"))


def round_money(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"))


def _rates(item: LineItem, header: ContractHeader, ps: PremiseSet) -> dict[str, Decimal]:
    regime = header.regime or "presumido"
    a_pis, a_cof = ps.pis_cofins(regime)
    natureza = classify_nature(item)
    if natureza == NATUREZA_BEM:
        a_L = item.aliquotas.get("icms", ps.get("icms"))
    else:
        a_L = item.aliquotas.get("iss", ps.get("iss"))
    a_ipi = item.aliquotas.get("ipi", ps.get("ipi"))
    return {"a_pis": a_pis, "a_cof": a_cof, "a_L": a_L, "a_ipi": a_ipi, "natureza": natureza}


def calc_item(item: LineItem, header: ContractHeader, ps: PremiseSet) -> CalcResult:
    """Passos 1-6 por item, nos cenarios A e B."""
    P = item.preco_unitario
    Q = item.quantidade
    r = _rates(item, header, ps)
    a_pis, a_cof, a_L, a_ipi = r["a_pis"], r["a_cof"], r["a_L"], r["a_ipi"]

    # DIFAL: so deduz se houver valor; % indicado com valor "-" nao deduz.
    difal = (
        item.difal_valor
        if item.difal_indicado and item.difal_valor is not None
        else Decimal("0")
    )
    a_difal = difal / P if P else Decimal("0")

    # Passo 1 - tributos atuais por dentro
    pis = P * a_pis
    cofins = P * a_cof
    icms_iss = P * a_L
    ipi = P * a_ipi
    sum_atual = a_pis + a_cof + a_L + a_ipi + a_difal

    # Passo 2 - valor-base
    base_unit = P - (pis + cofins + icms_iss + ipi + difal)
    base_total = base_unit * Q

    # Passo 3 - CBS/IBS por fora sobre a base
    a_cbs = ps.cbs_efetiva
    a_ibs_est = ps.get("ibs_estadual")
    a_ibs_mun = ps.get("ibs_municipal")
    a_ibs = a_ibs_est + a_ibs_mun
    cbs = base_unit * a_cbs
    ibs_est = base_unit * a_ibs_est
    ibs_mun = base_unit * a_ibs_mun
    ibs = ibs_est + ibs_mun
    subtotal = base_unit + cbs + ibs

    # Passo 4 - recompor ICMS/ISS 2027 por dentro
    one_minus_L = Decimal("1") - a_L
    icms_iss_2027_a = subtotal * a_L / one_minus_L  # Cenario A
    icms_iss_2027_b = base_unit * a_L / one_minus_L  # Cenario B

    # Passo 5 - novo preco
    p2027_a = subtotal + icms_iss_2027_a
    p2027_b = subtotal + icms_iss_2027_b
    total_a = p2027_a * Q
    total_b = p2027_b * Q
    total_atual = item.total
    var_rs = total_a - total_atual
    var_pct = var_rs / total_atual if total_atual else Decimal("0")

    # Passo 6 - fator de conferencia
    fator_a = (Decimal("1") - sum_atual) * (Decimal("1") + a_cbs + a_ibs) / one_minus_L
    fator_b = (Decimal("1") - sum_atual) * (
        (Decimal("1") + a_cbs + a_ibs) + a_L / one_minus_L
    )

    flags: list[str] = []
    if P and abs(p2027_a / P - fator_a) > FACTOR_TOL:
        flags.append(FLAG_DIVERGENCIA)

    return CalcResult(
        item=item.item, natureza=r["natureza"], total_atual=total_atual,
        a_pis=a_pis, a_cof=a_cof, a_L=a_L, a_ipi=a_ipi, a_difal=a_difal,
        sum_atual=sum_atual, pis=pis, cofins=cofins, icms_iss=icms_iss, ipi=ipi,
        difal=difal, base_unit=base_unit, base_total=base_total, cbs=cbs,
        ibs_est=ibs_est, ibs_mun=ibs_mun, ibs=ibs, subtotal=subtotal,
        icms_iss_2027_a=icms_iss_2027_a, p2027_a=p2027_a, total_a=total_a,
        icms_iss_2027_b=icms_iss_2027_b, p2027_b=p2027_b, total_b=total_b,
        var_rs=var_rs, var_pct=var_pct, fator_a=fator_a, fator_b=fator_b,
        flags=flags, fonte=item.fonte,
    )


def _rate_signature(r: CalcResult) -> tuple:
    return (r.natureza, r.a_pis, r.a_cof, r.a_L, r.a_ipi, r.a_difal)


def check_factor_consistency(results: list[CalcResult]) -> list[str]:
    """Fator constante entre itens de mesmas aliquotas; divergentes -> flag.

    O fator realizado por linha e ``total_a / total_atual`` (``P2027/P``, com Q
    cancelado). Itens do mesmo grupo de aliquotas devem compartilhar o fator;
    quem divergir recebe ``DIVERGÊNCIA``.
    """
    groups: dict[tuple, Decimal] = {}
    for r in results:
        groups.setdefault(_rate_signature(r), r.fator_a)
    divergentes: list[str] = []
    for r in results:
        expected = groups[_rate_signature(r)]
        realized = r.total_a / r.total_atual if r.total_atual else r.fator_a
        if abs(realized - expected) > FACTOR_TOL or abs(r.fator_a - expected) > FACTOR_TOL:
            if FLAG_DIVERGENCIA not in r.flags:
                r.flags.append(FLAG_DIVERGENCIA)
            divergentes.append(r.item)
    return divergentes


def calc_contract(
    items: list[LineItem], header: ContractHeader, ps: PremiseSet
) -> list[CalcResult]:
    results = [calc_item(it, header, ps) for it in items]
    check_factor_consistency(results)
    return results


# --------------------------------------------------------------------------- #
# Validacoes obrigatorias (prompt §7)
# --------------------------------------------------------------------------- #
def check_line_qp(item: LineItem) -> bool:
    return abs(item.quantidade * item.preco_unitario - item.total) <= MONEY_TOL


def reconcile_totals(items: list[LineItem], ppu_total: Decimal) -> dict[str, Any]:
    soma = sum((it.quantidade * it.preco_unitario for it in items), Decimal("0"))
    diff = soma - ppu_total
    ok = abs(diff) <= MONEY_TOL
    divergentes = [it.item for it in items if not check_line_qp(it)]
    return {"ok": ok, "soma": soma, "ppu_total": ppu_total, "diff": diff, "itens_divergentes": divergentes}


def base_invariant(items: list[LineItem], results: list[CalcResult]) -> dict[str, Any]:
    base_atual = sum(
        (it.total * (Decimal("1") - r.sum_atual) for it, r in zip(items, results)),
        Decimal("0"),
    )
    base_2027 = sum((r.base_total for r in results), Decimal("0"))
    return {"ok": abs(base_atual - base_2027) <= MONEY_TOL, "base_atual": base_atual, "base_2027": base_2027}


def validate(
    items: list[LineItem], results: list[CalcResult], ppu_total: Decimal
) -> dict[str, Any]:
    rec = reconcile_totals(items, ppu_total)
    qp_fail = [it.item for it in items if not check_line_qp(it)]
    base = base_invariant(items, results)
    factor_div = [r.item for r in results if FLAG_DIVERGENCIA in r.flags]
    return {
        "reconciliacao": rec,
        "qp": {"ok": not qp_fail, "itens": qp_fail},
        "base_invariante": base,
        "fator": {"ok": not factor_div, "itens": factor_div},
    }


def real_credit_note(regime: str | None) -> str | None:
    return REAL_CREDIT_NOTE if regime == "real" else None