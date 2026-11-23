"""Testes de triagem (4.1 escopo, 4.2 classificacao)."""

from decimal import Decimal

from reforma_tributaria import triage
from reforma_tributaria.models import ContractHeader, LineItem, Saldo


def _header(emissao="2026-05-10", petrobras=False, clausula=None):
    return ContractHeader(
        numero="X", cliente="Petrobras" if petrobras else "Cliente A",
        data_emissao=emissao, is_petrobras=petrobras, clausula_revisao=clausula,
    )


# ---- 4.1 escopo ----------------------------------------------------------- #
def test_emissao_fora_de_2026():
    assert triage.scope_status(_header("2025-12-01"), Saldo(saldo_2027=Decimal("10"))) == triage.SCOPE_FORA
    assert triage.scope_status(_header("2027-01-01"), Saldo(saldo_2027=Decimal("10"))) == triage.SCOPE_FORA


def test_tudo_faturado_ate_2026_sem_impacto():
    saldo = Saldo(saldo_2026=Decimal("1000"), saldo_2027=Decimal("0"))
    assert triage.scope_status(_header(), saldo) == triage.SCOPE_SEM_IMPACTO


def test_execucao_dividida_calcula_so_saldo_2027():
    saldo = Saldo(saldo_2026=Decimal("1000"), saldo_2027=Decimal("2300"))
    assert triage.scope_status(_header(), saldo) == triage.SCOPE_EM_ESCOPO
    assert saldo.saldo_2027 == Decimal("2300")


# ---- 4.2 clausula --------------------------------------------------------- #
def test_clausula_presente_transcrita():
    assert triage.clause_risk(_header(clausula="15.3")) is False
    assert triage.find_clause("Reequilibrio: cl. 15.3 revisao proporcional") == "15.3"


def test_clausula_ausente_risco():
    assert triage.clause_risk(_header()) is True


# ---- 4.2 natureza --------------------------------------------------------- #
def test_natureza_bem_e_servico():
    assert triage.classify_nature(LineItem(item="1", descricao="Estrutura Metalica")) == "BEM"
    assert triage.classify_nature(LineItem(item="1.1", descricao="Beneficiamento de Tubulacao")) == "SERVIÇO"


def test_item_misto_separado():
    mixed = LineItem(item="9", descricao="Fornecimento e montagem")
    parts = triage.split_mixed(
        mixed,
        {"descricao": "Estrutura", "quantidade": "10", "preco_unitario": "100", "total": "1000"},
        {"descricao": "Montagem", "quantidade": "5", "preco_unitario": "50", "total": "250"},
    )
    assert [p.natureza for p in parts] == ["BEM", "SERVIÇO"]
    assert parts[0].total == Decimal("1000")
    assert parts[1].total == Decimal("250")


# ---- 4.2 regime ----------------------------------------------------------- #
def test_simples_nao_calcula():
    assert triage.regime_treatment("simples")["calcula"] is False
    assert triage.regime_treatment("presumido")["calcula"] is True
    assert triage.regime_treatment("real")["calcula"] is True


# ---- 4.2 preco de referencia ---------------------------------------------- #
def test_petrobras_servico_usa_p0_nunca_reajustado():
    item = LineItem(
        item="1.1", descricao="Beneficiamento", natureza="SERVIÇO",
        preco_unitario=Decimal("40.00"), p0_original=Decimal("36.80"),
        preco_reajustado=Decimal("40.00"),
    )
    price, label = triage.reference_price(item, _header(petrobras=True))
    assert price == Decimal("36.80")
    assert "P0" in label


def test_petrobras_bem_usa_bruto_contrato():
    item = LineItem(
        item="1", descricao="Estrutura", natureza="BEM",
        preco_unitario=Decimal("52.4205"), preco_bruto_contrato=Decimal("52.4205"),
    )
    price, label = triage.reference_price(item, _header(petrobras=True))
    assert price == Decimal("52.4205")
    assert "bruto" in label


def test_outro_cliente_usa_contratual_vigente():
    item = LineItem(item="1", descricao="Estrutura", natureza="BEM", preco_unitario=Decimal("10"))
    price, label = triage.reference_price(item, _header(petrobras=False))
    assert price == Decimal("10")
    assert "contratual vigente" in label