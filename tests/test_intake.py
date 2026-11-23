"""Testes de extracao e auditoria de intake (3.2, 3.3, 3.4)."""

from decimal import Decimal

from openpyxl import Workbook

from reforma_tributaria import intake
from reforma_tributaria.models import FLAG_PENDENTE, FLAG_RECONSTRUIDO, LineItem
from tests.pdfutil import make_pdf


def _make_ppu(path):
    wb = Workbook()
    ws = wb.active
    ws.title = "PPU"
    ws.append(["Item", "Descricao", "Un", "Qtd", "P unit", "Total"])
    ws.append(["1", "Estrutura Metalica", "kg", 1000, 52.4205, 52420.50])
    ws.append(["1.1", "Beneficiamento", "h", 100, 36.80, 3680.00])
    wb.save(path)


def test_extract_xlsx_provenance(tmp_path):
    p = tmp_path / "ppu.xlsx"
    _make_ppu(p)
    items = intake.extract_xlsx(p)
    assert len(items) == 2
    first = items[0]
    assert first.item == "1"
    assert first.descricao == "Estrutura Metalica"
    assert first.unidade == "kg"
    assert first.quantidade == Decimal("1000")
    assert first.preco_unitario == Decimal("52.4205")
    assert first.total == Decimal("52420.50")
    assert first.fonte.arquivo == "ppu.xlsx"
    assert first.fonte.aba == "PPU"
    assert first.fonte.celula == "E2"  # celula do preco unitario


_PDF_LINES = [
    "Numero: 4600685026",
    "Cliente: Petrobras",
    "Emissao: 2026-05-10",
    "Vigencia: 2026-2028",
    "Pagamento: 30 dias",
    "Clausula: 15.3",
    "Regime: Lucro Presumido",
    "Itens:",
    "1 | Estrutura Metalica | kg | 1000 | 52.4205 | 52420.50",
    "1.1 | Beneficiamento | h | 100 | 36.80 | 3680.00",
]


def test_extract_pdf_header_and_items(tmp_path):
    p = tmp_path / "pedido.pdf"
    p.write_bytes(make_pdf(_PDF_LINES))
    header, items = intake.extract_pdf(p)
    assert header.numero == "4600685026"
    assert header.cliente == "Petrobras"
    assert header.is_petrobras is True
    assert header.data_emissao == "2026-05-10"
    assert header.vigencia == "2026-2028"
    assert header.condicao_pagamento == "30 dias"
    assert header.clausula_revisao == "15.3"
    assert header.regime == "presumido"
    assert len(items) == 2
    assert items[0].preco_unitario == Decimal("52.4205")
    assert items[0].fonte.arquivo == "pedido.pdf"
    assert items[0].fonte.pagina == 1


def test_extract_email(tmp_path):
    p = tmp_path / "pc.eml"
    body = "\n".join(_PDF_LINES)
    p.write_text(
        "From: cliente@example.com\nTo: fornecedor@example.com\n"
        "Subject: PC 4600685026\nContent-Type: text/plain; charset=utf-8\n\n" + body,
        encoding="utf-8",
    )
    header, items = intake.extract_email(p)
    assert header.numero == "4600685026"
    assert header.regime == "presumido"
    assert len(items) == 2
    assert items[0].fonte.arquivo == "pc.eml"


def test_extract_dfp(tmp_path):
    p = tmp_path / "dfp.txt"
    p.write_text(
        "Regime: Lucro Presumido\nPIS: 0.65%\nCofins: 3.00%\nICMS: 12%\nISS: 3%\nIPI: 0%\n",
        encoding="utf-8",
    )
    dfp = intake.extract_dfp(p)
    assert dfp["regime"] == "presumido"
    assert dfp["aliquotas"]["pis"] == Decimal("0.0065")
    assert dfp["aliquotas"]["icms"] == Decimal("0.12")


def test_register_communication(tmp_path):
    p = tmp_path / "carta-petrobras.pdf"
    p.write_bytes(make_pdf(["DPBR-2026-80548"]))
    doc = intake.register_communication(p)
    assert doc.kind == "comunicacao"
    assert doc.source.arquivo == "carta-petrobras.pdf"


def test_mark_missing_does_not_invent():
    item = LineItem(item="1", preco_unitario=Decimal("0"))
    intake.mark_missing(item, "ISS do municipio", premissa="3%")
    assert FLAG_PENDENTE in item.flags
    assert any("ISS do municipio" in p for p in item.pendencias)
    assert item.preco_unitario == Decimal("0")  # nada inventado


def test_mark_reconstructed_records_origin():
    item = LineItem(item="2")
    intake.mark_reconstructed(item, "estimado a partir do total / quantidade da PPU")
    assert FLAG_RECONSTRUIDO in item.flags
    assert "PPU" in item.origem_reconstrucao


def test_compute_saldo_splits_years():
    saldo = intake.compute_saldo(
        [
            {"data": "2026-06-30", "valor": "1000"},
            {"data": "2026-12-31", "valor": "500"},
            {"data": "2027-01-15", "valor": "2000"},
            {"data": "2027-06-01", "valor": "300"},
        ]
    )
    assert saldo.saldo_2026 == Decimal("1500")
    assert saldo.saldo_2027 == Decimal("2300")
    assert saldo.pendente is False


def test_extract_schedule_xlsx(tmp_path):
    p = tmp_path / "cronograma.xlsx"
    wb = Workbook()
    ws = wb.active
    ws.append(["Data", "Valor"])
    ws.append(["2026-08-01", 1000])
    ws.append(["2027-02-01", 2500])
    wb.save(p)
    saldo = intake.extract_schedule(p)
    assert saldo.saldo_2026 == Decimal("1000")
    assert saldo.saldo_2027 == Decimal("2500")


def test_absent_schedule_is_pending(tmp_path):
    assert intake.extract_schedule(tmp_path / "nao-existe.xlsx").pendente is True
    assert intake.compute_saldo([]).pendente is True