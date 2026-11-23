"""Extracao estruturada de documentos com proveniencia.

Formatos suportados pelo extrator automatico (o agente assiste em layouts
heterogeneos):
- XLSX (PPU): cabecalho ``Item | Descricao | Un | Qtd | P unit | Total``.
- PDF/e-mail: campos rotulados (``Numero:``, ``Cliente:``, ``Emissao:``,
  ``Vigencia:``, ``Pagamento:``, ``Clausula:``, ``Regime:``) e itens em linhas
  ``item | descricao | un | qtd | punit | total``.
- DFP: ``Regime:`` e aliquotas rotuladas.
- Cronograma (XLSX): ``Data | Valor``.

Nunca inventa valores: dado ausente vira ``PENDENTE – confirmar``; item estimado
vira ``RECONSTRUÍDO`` com origem.
"""

from __future__ import annotations

import unicodedata
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any

import pdfplumber
from openpyxl import load_workbook

from .models import (
    FLAG_PENDENTE,
    FLAG_RECONSTRUIDO,
    ContractHeader,
    Document,
    LineItem,
    Saldo,
    Source,
)

_CORTE_2026 = date(2026, 12, 31)


def _norm(text: str) -> str:
    text = unicodedata.normalize("NFKD", text or "")
    text = "".join(c for c in text if not unicodedata.combining(c))
    return text.strip().lower()


def _dec(value: Any) -> Decimal:
    if value is None or value == "":
        return Decimal("0")
    return Decimal(str(value))


# --------------------------------------------------------------------------- #
# XLSX (PPU)
# --------------------------------------------------------------------------- #
_XLSX_COLS = {
    "item": "item",
    "descricao": "descricao",
    "un": "unidade",
    "unidade": "unidade",
    "qtd": "quantidade",
    "quantidade": "quantidade",
    "p unit": "preco_unitario",
    "p unitario": "preco_unitario",
    "preco unitario": "preco_unitario",
    "preco unit": "preco_unitario",
    "total": "total",
}


def extract_xlsx(path: str | Path, sheet: str | None = None) -> list[LineItem]:
    """Extrai itens de uma PPU/planilha XLSX com fonte arquivo/aba/celula."""
    path = Path(path)
    wb = load_workbook(path, data_only=True)
    ws = wb[sheet] if sheet else wb.active
    rows = list(ws.iter_rows())
    if not rows:
        return []
    header = {_norm(c.value): idx for idx, c in enumerate(rows[0]) if c.value is not None}
    colmap: dict[str, int] = {}
    for label, idx in header.items():
        field = _XLSX_COLS.get(label)
        if field and field not in colmap:
            colmap[field] = idx
    if "item" not in colmap:
        raise ValueError(f"cabecalho de PPU nao encontrado em {path}")

    items: list[LineItem] = []
    for row in rows[1:]:
        def cell(field: str):
            idx = colmap.get(field)
            return row[idx] if idx is not None and idx < len(row) else None

        item_cell = cell("item")
        if item_cell is None or item_cell.value is None:
            continue
        price_cell = cell("preco_unitario")
        item = LineItem(
            item=str(item_cell.value),
            descricao=str(cell("descricao").value) if cell("descricao") else "",
            unidade=str(cell("unidade").value) if cell("unidade") else "",
            quantidade=_dec(cell("quantidade").value if cell("quantidade") else None),
            preco_unitario=_dec(price_cell.value if price_cell else None),
            total=_dec(cell("total").value if cell("total") else None),
            fonte=Source(
                arquivo=path.name,
                aba=ws.title,
                celula=price_cell.coordinate if price_cell else None,
            ),
        )
        items.append(item)
    return items


# --------------------------------------------------------------------------- #
# PDF / e-mail / DFP (texto rotulado)
# --------------------------------------------------------------------------- #
_HEADER_LABELS = {
    "numero": "numero",
    "cliente": "cliente",
    "emissao": "data_emissao",
    "data de emissao": "data_emissao",
    "vigencia": "vigencia",
    "prazo": "vigencia",
    "pagamento": "condicao_pagamento",
    "condicao de pagamento": "condicao_pagamento",
    "clausula": "clausula_revisao",
    "clausula de revisao": "clausula_revisao",
    "regime": "regime",
}


def _pdf_pages(path: Path) -> list[tuple[int, str]]:
    pages: list[tuple[int, str]] = []
    with pdfplumber.open(path) as pdf:
        for i, page in enumerate(pdf.pages, start=1):
            pages.append((i, page.extract_text() or ""))
    return pages


def _parse_labeled_text(
    pages: list[tuple[int, str]], arquivo: str
) -> tuple[ContractHeader, list[LineItem]]:
    header = ContractHeader()
    items: list[LineItem] = []
    in_items = False
    for pagina, text in pages:
        for raw in text.splitlines():
            line = raw.strip()
            if not line:
                continue
            low = _norm(line)
            if low in ("itens:", "itens"):
                in_items = True
                continue
            if ":" in line and not in_items:
                label, _, value = line.partition(":")
                field = _HEADER_LABELS.get(_norm(label))
                if field:
                    setattr(header, field, value.strip())
                    continue
            if in_items and "|" in line:
                parts = [p.strip() for p in line.split("|")]
                if len(parts) >= 6:
                    items.append(
                        LineItem(
                            item=parts[0],
                            descricao=parts[1],
                            unidade=parts[2],
                            quantidade=_dec(parts[3]),
                            preco_unitario=_dec(parts[4]),
                            total=_dec(parts[5]),
                            fonte=Source(arquivo=arquivo, pagina=pagina),
                        )
                    )
    if header.cliente:
        header.is_petrobras = "petrobras" in _norm(header.cliente)
    if header.regime:
        header.regime = _norm_regime(header.regime)
    return header, items


def _norm_regime(value: str) -> str:
    low = _norm(value)
    if "simples" in low:
        return "simples"
    if "real" in low:
        return "real"
    if "presumido" in low:
        return "presumido"
    return low


def extract_pdf(path: str | Path) -> tuple[ContractHeader, list[LineItem]]:
    path = Path(path)
    return _parse_labeled_text(_pdf_pages(path), path.name)


def extract_email(path: str | Path) -> tuple[ContractHeader, list[LineItem]]:
    import email
    from email import policy

    path = Path(path)
    msg = email.message_from_bytes(path.read_bytes(), policy=policy.default)
    body = msg.get_body(preferencelist=("plain",))
    text = body.get_content() if body else msg.get_content()
    return _parse_labeled_text([(1, text)], path.name)


def extract_dfp(path: str | Path) -> dict[str, Any]:
    """Extrai regime e aliquotas de um DFP (PDF ou texto)."""
    path = Path(path)
    if path.suffix.lower() == ".pdf":
        text = "\n".join(t for _, t in _pdf_pages(path))
    else:
        text = path.read_text(encoding="utf-8")
    regime = None
    aliquotas: dict[str, Decimal] = {}
    for raw in text.splitlines():
        line = raw.strip()
        if ":" not in line:
            continue
        label, _, value = line.partition(":")
        low = _norm(label)
        value = value.strip()
        if low == "regime":
            regime = _norm_regime(value)
        elif low in ("pis", "cofins", "icms", "iss", "ipi"):
            aliquotas[low] = _dec(value.replace("%", "")) / Decimal("100")
    return {"regime": regime, "aliquotas": aliquotas}


def register_communication(path: str | Path) -> Document:
    path = Path(path)
    return Document(path=str(path), kind="comunicacao", source=Source(arquivo=path.name))


# --------------------------------------------------------------------------- #
# Flags de auditoria (3.4)
# --------------------------------------------------------------------------- #
def mark_missing(item: LineItem, campo: str, premissa: str | None = None) -> LineItem:
    """Sinaliza dado ausente sem inventar valor."""
    item.add_flag(FLAG_PENDENTE)
    nota = f"{campo}: confirmar"
    if premissa:
        nota += f" (premissa padrao sinalizada: {premissa})"
    if nota not in item.pendencias:
        item.pendencias.append(nota)
    return item


def mark_reconstructed(item: LineItem, origem: str) -> LineItem:
    """Sinaliza item reconstruido/estimado e registra a origem."""
    item.add_flag(FLAG_RECONSTRUIDO)
    item.origem_reconstrucao = origem
    return item


# --------------------------------------------------------------------------- #
# Cronograma / saldo (3.4)
# --------------------------------------------------------------------------- #
def compute_saldo(entries: list[dict[str, Any]]) -> Saldo:
    """Separa faturado ate 31/12/2026 do saldo a partir de 01/01/2027."""
    if not entries:
        return Saldo(pendente=True)
    saldo_2026 = Decimal("0")
    saldo_2027 = Decimal("0")
    for entry in entries:
        data = entry["data"]
        if isinstance(data, str):
            data = date.fromisoformat(data)
        valor = _dec(entry["valor"])
        if data <= _CORTE_2026:
            saldo_2026 += valor
        else:
            saldo_2027 += valor
    return Saldo(saldo_2026=saldo_2026, saldo_2027=saldo_2027)


def extract_schedule(path: str | Path) -> Saldo:
    """Le cronograma XLSX (``Data | Valor``); sem dados -> saldo PENDENTE."""
    path = Path(path)
    if not path.exists():
        return Saldo(pendente=True)
    wb = load_workbook(path, data_only=True)
    ws = wb.active
    rows = list(ws.iter_rows())
    if not rows:
        return Saldo(pendente=True)
    header = {_norm(c.value): idx for idx, c in enumerate(rows[0]) if c.value is not None}
    di, vi = header.get("data"), header.get("valor")
    if di is None or vi is None:
        return Saldo(pendente=True)
    entries = []
    for row in rows[1:]:
        if row[di].value is None:
            continue
        entries.append({"data": row[di].value, "valor": row[vi].value})
    return compute_saldo(entries)