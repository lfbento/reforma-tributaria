"""Orquestracao do pipeline: dados estruturados -> analise calculada.

O agente extrai documentos (intake) e produz o JSON estruturado; este modulo
aplica triagem (preco de referencia), calculo e monta a ``ContractAnalysis``
pronta para os entregaveis.
"""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path
from typing import Any

from . import engine, triage
from .models import ContractAnalysis, ContractHeader, Document, LineItem, Saldo
from .premises import PremiseSet


def load_input(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def analyze(data: dict[str, Any], ps: PremiseSet) -> ContractAnalysis:
    header = ContractHeader.from_dict(data["header"])
    items = [LineItem.from_dict(i) for i in data["items"]]
    # triagem: o preco de referencia vira o P do item (Petrobras P0 / bruto)
    for it in items:
        price, _label = triage.reference_price(it, header)
        it.preco_unitario = price
        it.total = it.quantidade * price
    results = engine.calc_contract(items, header, ps)
    saldo = Saldo.from_dict(data.get("saldo", {}))
    scope = triage.scope_status(header, saldo)
    docs = [Document.from_dict(d) for d in data.get("documentos", [])]
    ppu_total = (
        Decimal(str(data["ppu_total"]))
        if "ppu_total" in data
        else sum((it.total for it in items), Decimal("0"))
    )
    return ContractAnalysis(
        header=header,
        items=items,
        results=results,
        saldo=saldo,
        scope=scope,
        documents=docs,
        referencias_legais=list(data.get("referencias_legais", [])),
        ppu_total=ppu_total,
        regime_note=engine.real_credit_note(header.regime),
        clause_risk=triage.clause_risk(header),
    )