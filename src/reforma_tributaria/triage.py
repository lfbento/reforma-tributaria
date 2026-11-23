"""Regras de escopo e classificacao aplicadas antes do calculo.

Escopo (emissao 2026, saldo 2027), clausula de revisao, natureza BEM/SERVICO,
regime tributario e selecao do preco de referencia por cliente.
"""

from __future__ import annotations

import re
from decimal import Decimal
from typing import Any

from .models import (
    FLAG_FORA_ESCOPO,
    NATUREZA_BEM,
    NATUREZA_SERVICO,
    ContractHeader,
    LineItem,
    Saldo,
)

SCOPE_FORA = "FORA DO ESCOPO"
SCOPE_SEM_IMPACTO = "SEM IMPACTO"
SCOPE_EM_ESCOPO = "EM ESCOPO"

_SERVICE_WORDS = (
    "servico", "beneficiamento", "montagem", "instalacao", "usinagem",
    "solda", "pintura", "jateamento", "caldeiraria", "mao de obra", "hora",
)


def scope_status(header: ContractHeader, saldo: Saldo | None) -> str:
    """Decide o escopo do pedido a partir da emissao e do saldo 2027."""
    if header.data_emissao:
        year = int(str(header.data_emissao)[:4])
        if year != 2026:
            return SCOPE_FORA
    if saldo is not None and not saldo.pendente and saldo.saldo_2027 == 0:
        return SCOPE_SEM_IMPACTO
    return SCOPE_EM_ESCOPO


_CLAUSE_RE = re.compile(r"cl(?:[aá]usula)?\.?\s*(\d+(?:\.\d+)+)", re.IGNORECASE)
_CLAUSE_KEYWORDS = ("incidencias tributarias", "reequilibrio", "incidência tributária")


def find_clause(text: str) -> str | None:
    """Transcreve o numero de clausula de revisao/reequilibrio, se houver."""
    low = text.lower()
    if not any(k in low for k in _CLAUSE_KEYWORDS) and "clausula" not in low and "cl." not in low:
        match = _CLAUSE_RE.search(text)
        return match.group(1) if match else None
    match = _CLAUSE_RE.search(text)
    return match.group(1) if match else None


def clause_risk(header: ContractHeader) -> bool:
    """Sem clausula de revisao -> risco de nao conseguir repassar o impacto."""
    return not header.clausula_revisao


def classify_nature(item: LineItem) -> str:
    """Classifica BEM (ICMS/IPI) ou SERVICO (ISS); natureza explicita prevalece."""
    if item.natureza in (NATUREZA_BEM, NATUREZA_SERVICO):
        return item.natureza
    desc = item.descricao.lower()
    if any(w in desc for w in _SERVICE_WORDS):
        return NATUREZA_SERVICO
    return NATUREZA_BEM


def split_mixed(item: LineItem, bem: dict[str, Any], servico: dict[str, Any]) -> list[LineItem]:
    """Separa item misto em componentes BEM e SERVICO para calculo distinto."""
    parts = []
    for natureza, comp in ((NATUREZA_BEM, bem), (NATUREZA_SERVICO, servico)):
        parts.append(
            LineItem(
                item=f"{item.item}-{natureza}",
                descricao=comp.get("descricao", item.descricao),
                unidade=comp.get("unidade", item.unidade),
                quantidade=Decimal(str(comp.get("quantidade", "0"))),
                preco_unitario=Decimal(str(comp.get("preco_unitario", "0"))),
                total=Decimal(str(comp.get("total", "0"))),
                natureza=natureza,
                fonte=item.fonte,
                flags=list(item.flags),
            )
        )
    return parts


def regime_treatment(regime: str | None) -> dict[str, Any]:
    """Simples Nacional nao e calculado; demais regimes seguem a metodologia."""
    if regime == "simples":
        return {"calcula": False, "tratamento": "Simples Nacional: tratamento especifico"}
    if regime == "real":
        return {"calcula": True, "tratamento": "Lucro Real (nao cumulativo)"}
    return {"calcula": True, "tratamento": "Lucro Presumido (cumulativo)"}


def reference_price(item: LineItem, header: ContractHeader) -> tuple[Decimal, str]:
    """Seleciona o preco de referencia e informa qual foi usado.

    Petrobras: servicos usam o P0 original da PPU (nunca o reajustado); bens usam
    o preco bruto unitario do contrato. Outros clientes: preco contratual vigente.
    """
    natureza = classify_nature(item)
    if header.is_petrobras:
        if natureza == NATUREZA_SERVICO:
            if item.p0_original is not None:
                return item.p0_original, "P0 original da PPU (Petrobras servico)"
            return item.preco_unitario, "preco unitario (P0 ausente: confirmar)"
        if item.preco_bruto_contrato is not None:
            return item.preco_bruto_contrato, "preco bruto unitario do contrato (Petrobras bem)"
        return item.preco_unitario, "preco unitario (bruto do contrato ausente: confirmar)"
    return item.preco_unitario, "preco contratual vigente"