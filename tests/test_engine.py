"""Testes do motor de calculo (5.1 a 5.5), incluindo fixtures Petrobras."""

import json
from decimal import Decimal
from pathlib import Path

from reforma_tributaria import engine
from reforma_tributaria.models import FLAG_DIVERGENCIA, ContractHeader, LineItem
from reforma_tributaria.premises import load_premises

FIX = Path(__file__).parent / "fixtures" / "petrobras.json"
TOL = Decimal("0.01")


def load_fix():
    data = json.loads(FIX.read_text(encoding="utf-8"))
    header = ContractHeader.from_dict(data["header"])
    items = [LineItem.from_dict(i) for i in data["items"]]
    return data, header, items


def r6(v):
    return v.quantize(Decimal("0.000001"))


def bens_items(items):
    return [i for i in items if i.natureza == "BEM"]


def serv_items(items):
    return [i for i in items if i.natureza == "SERVIÇO"]


# ---- 5.1 passos 1-3 ------------------------------------------------------- #
def test_bem_sum_e_base():
    _, h, items = load_fix()
    r = engine.calc_item(items[0], h, load_premises())
    assert r.sum_atual == Decimal("0.1565")
    assert r.base_unit == Decimal("52.4205") * Decimal("0.8435")


def test_servico_sum_e_base():
    _, h, items = load_fix()
    s = serv_items(items)[0]
    r = engine.calc_item(s, h, load_premises())
    assert r.sum_atual == Decimal("0.0665")
    assert r.base_unit == Decimal("34.3528")


def test_item1_passos_1_3():
    _, h, items = load_fix()
    r = engine.calc_item(items[0], h, load_premises())
    assert engine.round_unit(r.base_unit) == Decimal("44.2167")
    assert engine.round_unit(r.cbs) == Decimal("4.9730")
    assert engine.round_unit(r.ibs) == Decimal("0.0442")
    assert abs(r.subtotal - Decimal("49.2338")) <= Decimal("0.0002")


def test_difal_indicado_sem_valor_nao_deduz():
    _, h, items = load_fix()
    it = items[0]
    it.difal_indicado = True
    it.difal_valor = None  # PPU indica % mas valor "-"
    r = engine.calc_item(it, h, load_premises())
    assert r.difal == Decimal("0")
    assert r.base_unit == Decimal("52.4205") * Decimal("0.8435")


def test_difal_com_valor_reduz_base():
    _, h, items = load_fix()
    it = items[0]
    it.difal_indicado = True
    it.difal_valor = Decimal("1.00")
    r = engine.calc_item(it, h, load_premises())
    assert r.difal == Decimal("1.00")
    assert r.base_unit == Decimal("52.4205") * Decimal("0.8435") - Decimal("1.00")


# ---- 5.2 passos 4-5 ------------------------------------------------------- #
def test_item1_cenario_a():
    _, h, items = load_fix()
    r = engine.calc_item(items[0], h, load_premises())
    assert engine.round_unit(r.icms_iss_2027_a) == Decimal("6.7137")
    assert abs(r.p2027_a - Decimal("55.9475")) <= Decimal("0.0001")
    assert abs(r.var_pct - Decimal("0.0673")) <= Decimal("0.0001")


def test_item11_cenario_a():
    _, h, items = load_fix()
    r = engine.calc_item(serv_items(items)[0], h, load_premises())
    assert engine.round_unit(r.icms_iss_2027_a) == Decimal("1.1830")
    assert abs(r.p2027_a - Decimal("39.4338")) <= Decimal("0.0001")


def test_cenario_b_distinto_de_a():
    _, h, items = load_fix()
    r = engine.calc_item(items[0], h, load_premises())
    assert r.p2027_b < r.p2027_a
    assert r.icms_iss_2027_b == r.base_unit * r.a_L / (Decimal("1") - r.a_L)


# ---- 5.3 fator ------------------------------------------------------------ #
def test_fatores_bem():
    _, h, items = load_fix()
    r = engine.calc_item(items[0], h, load_premises())
    assert r6(r.fator_a) == Decimal("1.067284")
    assert abs(r.fator_b - Decimal("1.054230")) <= Decimal("0.00001")
    assert ((r.fator_b - 1) * 100).quantize(Decimal("0.01")) == Decimal("5.42")


def test_fatores_servico():
    _, h, items = load_fix()
    r = engine.calc_item(serv_items(items)[0], h, load_premises())
    assert r6(r.fator_a) == Decimal("1.071569")
    assert abs(r.fator_b - Decimal("1.068290")) <= Decimal("0.00001")
    assert ((r.fator_b - 1) * 100).quantize(Decimal("0.01")) == Decimal("6.83")


def test_item_divergente_marcado():
    _, h, items = load_fix()
    ps = load_premises()
    results = engine.calc_contract(bens_items(items)[:2], h, ps)
    # simula um item cujo total 2027 nao bate com o fator do grupo
    results[1].total_a = results[1].total_a * Decimal("1.5")
    div = engine.check_factor_consistency(results)
    assert results[1].item in div
    assert FLAG_DIVERGENCIA in results[1].flags


# ---- 5.4 validacoes ------------------------------------------------------- #
def test_reconciliacao_ok():
    data, h, items = load_fix()
    b = bens_items(items)
    rec = engine.reconcile_totals(b, Decimal(data["ppu_total_bens"]))
    assert rec["ok"] is True
    assert abs(rec["diff"]) <= TOL


def test_reconciliacao_divergente_lista_itens():
    _, h, items = load_fix()
    b = bens_items(items)
    rec = engine.reconcile_totals(b, Decimal("99999999.99"))
    assert rec["ok"] is False
    bad = LineItem(item="X", quantidade=Decimal("2"), preco_unitario=Decimal("10"), total=Decimal("99"))
    assert engine.check_line_qp(bad) is False
    rec2 = engine.reconcile_totals([bad], Decimal("20"))
    assert "X" in rec2["itens_divergentes"]


def test_qp_por_linha():
    good = LineItem(item="1", quantidade=Decimal("1000"), preco_unitario=Decimal("52.4205"), total=Decimal("52420.50"))
    assert engine.check_line_qp(good) is True


def test_base_invariante():
    data, h, items = load_fix()
    b = bens_items(items)
    res = engine.calc_contract(b, h, load_premises())
    base = engine.base_invariant(b, res)
    assert base["ok"] is True


# ---- 5.5 fixtures completos / Lucro Real / recalculo ---------------------- #
def test_fixture_bens_totais():
    data, h, items = load_fix()
    res = engine.calc_contract(bens_items(items), h, load_premises())
    total_atual = sum(r.total_atual for r in res)
    total_a = sum(r.total_a for r in res)
    var = sum(r.var_rs for r in res)
    base = sum(r.base_total for r in res)
    assert total_atual == Decimal("38776540.91")
    assert abs(total_a - Decimal("41385596.58")) <= TOL
    assert abs(var - Decimal("2609055.67")) <= TOL
    assert abs(base - Decimal("32708012.26")) <= TOL


def test_fixture_servicos_totais():
    data, h, items = load_fix()
    res = engine.calc_contract(serv_items(items), h, load_premises())
    total_atual = sum(r.total_atual for r in res)
    total_a = sum(r.total_a for r in res)
    var = sum(r.var_rs for r in res)
    base = sum(r.base_total for r in res)
    assert total_atual == Decimal("16428186.00")
    assert abs(total_a - Decimal("17603942.43")) <= TOL
    assert abs(var - Decimal("1175756.43")) <= TOL
    assert abs(base - Decimal("15335711.63")) <= TOL


def test_lucro_real_aliquotas_e_nota():
    _, h, items = load_fix()
    h.regime = "real"
    r = engine.calc_item(items[0], h, load_premises())
    assert r.a_pis == Decimal("0.0165")
    assert r.a_cof == Decimal("0.0760")
    assert engine.real_credit_note("real") is not None
    assert engine.real_credit_note("presumido") is None


def test_recalculo_ao_mudar_premissa():
    _, h, items = load_fix()
    b = bens_items(items)
    base = engine.calc_contract(b, h, load_premises())
    changed = engine.calc_contract(b, h, load_premises(overrides={"cbs_referencia": "0.12"}))
    assert all(c.total_a != o.total_a for c, o in zip(changed, base))