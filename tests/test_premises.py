"""Testes das premissas editaveis (spec tax-impact-engine)."""

from decimal import Decimal

import pytest

from reforma_tributaria.premises import load_premises


def test_defaults_match_spec():
    ps = load_premises()
    assert ps.get("pis_presumido") == Decimal("0.0065")
    assert ps.get("pis_real") == Decimal("0.0165")
    assert ps.get("cofins_presumido") == Decimal("0.0300")
    assert ps.get("cofins_real") == Decimal("0.0760")
    assert ps.get("ipi") == Decimal("0")
    assert ps.get("iss_petrobras_multi") == Decimal("0.05")
    assert ps.cbs_efetiva == Decimal("0.112468")
    assert ps.ibs_total == Decimal("0.0010")
    assert ps.cenario == "A"


def test_every_parameter_has_source():
    ps = load_premises()
    assert ps.parameters
    for premise in ps.parameters.values():
        assert premise.source.strip(), premise.key
    assert ps.cenario_source.strip()


def test_override_changes_applied_value():
    ps = load_premises(overrides={"cbs_referencia": "0.12"})
    assert ps.get("cbs_referencia") == Decimal("0.12")
    assert ps.cbs_efetiva == Decimal("0.119")
    assert "override" in ps.source("cbs_referencia")
    # o padrao original permanece intacto
    assert load_premises().get("cbs_referencia") == Decimal("0.113468")


def test_pis_cofins_by_regime():
    ps = load_premises()
    assert ps.pis_cofins("presumido") == (Decimal("0.0065"), Decimal("0.0300"))
    assert ps.pis_cofins("real") == (Decimal("0.0165"), Decimal("0.0760"))


def test_unknown_override_rejected():
    with pytest.raises(KeyError):
        load_premises(overrides={"inexistente": "1"})


def test_json_roundtrip():
    ps = load_premises(overrides={"iss": "0.05"})
    restored = type(ps).from_dict(ps.to_dict())
    assert restored.get("iss") == Decimal("0.05")
    assert restored.cbs_efetiva == ps.cbs_efetiva
    assert restored.source("iss") == ps.source("iss")
    assert restored.regime_padrao == "presumido"


def test_regime_padrao_e_presumido():
    ps = load_premises()
    assert ps.regime_padrao == "presumido"
    assert "Presumido" in ps.regime_source
    ps_over = load_premises(overrides={"regime_padrao": "real"})
    assert ps_over.regime_padrao == "real"