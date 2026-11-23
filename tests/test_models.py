"""Round-trip JSON dos registros preservando campos e proveniencia (3.1)."""

import json
from decimal import Decimal

from reforma_tributaria.models import (
    CalcResult,
    ContractHeader,
    Document,
    LineItem,
    Saldo,
    Source,
    FLAG_PENDENTE,
)
from reforma_tributaria.premises import load_premises


def test_source_roundtrip():
    src = Source(arquivo="ppu.xlsx", aba="PPU", celula="E2", pagina=None)
    back = Source.from_dict(json.loads(json.dumps(src.to_dict())))
    assert back == src
    assert "célula E2" in src.describe()


def test_document_roundtrip():
    doc = Document(path="contrato.pdf", kind="contrato", source=Source("contrato.pdf", pagina=3))
    back = Document.from_dict(json.loads(json.dumps(doc.to_dict())))
    assert back == doc


def test_contract_header_roundtrip():
    h = ContractHeader(
        numero="4600685026",
        cliente="Petrobras",
        data_emissao="2026-05-10",
        vigencia="2026-2028",
        condicao_pagamento="30 dias",
        clausula_revisao="15.3",
        regime="presumido",
        is_petrobras=True,
    )
    back = ContractHeader.from_dict(json.loads(json.dumps(h.to_dict())))
    assert back == h


def test_line_item_roundtrip_preserves_provenance_and_decimals():
    item = LineItem(
        item="1",
        descricao="Estrutura Metálica",
        unidade="kg",
        quantidade=Decimal("1000"),
        preco_unitario=Decimal("52.4205"),
        total=Decimal("52420.50"),
        natureza="BEM",
        fonte=Source("ppu.xlsx", aba="PPU", celula="E2"),
        flags=[FLAG_PENDENTE],
        pendencias=["ISS do município"],
        aliquotas={"icms": Decimal("0.12"), "ipi": Decimal("0")},
        p0_original=Decimal("36.80"),
        difal_indicado=True,
        difal_valor=None,
        saldo_2027=Decimal("10000.00"),
    )
    back = LineItem.from_dict(json.loads(json.dumps(item.to_dict())))
    assert back == item
    assert back.preco_unitario == Decimal("52.4205")
    assert back.fonte.celula == "E2"
    assert back.aliquotas["icms"] == Decimal("0.12")
    assert back.difal_valor is None


def test_calc_result_roundtrip():
    r = CalcResult(
        item="1", natureza="BEM", total_atual=Decimal("52420.50"),
        a_pis=Decimal("0.0065"), a_cof=Decimal("0.03"), a_L=Decimal("0.12"),
        a_ipi=Decimal("0"), a_difal=Decimal("0"), sum_atual=Decimal("0.1565"),
        pis=Decimal("340.73"), cofins=Decimal("1572.62"), icms_iss=Decimal("6290.46"),
        ipi=Decimal("0"), difal=Decimal("0"), base_unit=Decimal("44.2167"),
        base_total=Decimal("44216.70"), cbs=Decimal("4973.0"), ibs_est=Decimal("22.1"),
        ibs_mun=Decimal("22.1"), ibs=Decimal("44.2"), subtotal=Decimal("49233.8"),
        icms_iss_2027_a=Decimal("6713.7"), p2027_a=Decimal("55.9475"),
        total_a=Decimal("55947.5"), icms_iss_2027_b=Decimal("6029.5"),
        p2027_b=Decimal("55.2632"), total_b=Decimal("55263.2"),
        var_rs=Decimal("3527.0"), var_pct=Decimal("0.0673"),
        fator_a=Decimal("1.067284"), fator_b=Decimal("1.054230"),
        fonte=Source("ppu.xlsx", aba="PPU", celula="E2"),
    )
    back = CalcResult.from_dict(json.loads(json.dumps(r.to_dict())))
    assert back == r


def test_saldo_and_premises_roundtrip():
    s = Saldo(saldo_2026=Decimal("100"), saldo_2027=Decimal("200"), pendente=True)
    assert Saldo.from_dict(json.loads(json.dumps(s.to_dict()))) == s
    ps = load_premises()
    assert type(ps).from_dict(json.loads(json.dumps(ps.to_dict()))) == ps