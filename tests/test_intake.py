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


def test_safe_path_hash_and_cache(tmp_path):
    f = tmp_path / "doc.txt"
    f.write_text("conteudo teste", encoding="utf-8")
    sp = intake.safe_path(f)
    assert sp.exists()
    h1 = intake.file_hash(f)
    h2 = intake.file_hash(f)
    assert len(h1) == 32 and h1 == h2

    cache_file = tmp_path / intake.CACHE_FILENAME
    intake.save_cache(cache_file, {"k": "v"})
    assert intake.load_cache(cache_file) == {"k": "v"}


def test_parse_markdown_table():
    md = (
        "Numero: 4600999000\n"
        "Cliente: Petrobras\n"
        "| Item | Descricao | Un | Qtd | P unit | Total |\n"
        "|---|---|---|---|---|---|\n"
        "| 1 | Valvula Esfera | un | 2 | 150.00 | 300.00 |\n"
    )
    header, items = intake._parse_labeled_text([(3, md)], "contrato.docx")
    assert header.numero == "4600999000"
    assert header.is_petrobras is True
    assert len(items) == 1
    assert items[0].preco_unitario == Decimal("150.00")
    assert items[0].fonte.pagina == 3


def test_extract_office_and_msg(tmp_path, monkeypatch):
    class _FakeRes:
        text_content = (
            "Numero: 12345\n"
            "Cliente: Vale\n"
            "| Item | Descricao | Un | Qtd | P unit | Total |\n"
            "|---|---|---|---|---|---|\n"
            "| 1 | Flange | un | 4 | 50.00 | 200.00 |\n"
        )

    monkeypatch.setattr(intake, "_extract_with_markitdown", lambda _p: _FakeRes.text_content)

    docx_file = tmp_path / "contrato.docx"
    docx_file.write_bytes(b"fake-docx")
    h1, it1 = intake.extract_office(docx_file)
    assert h1.numero == "12345"
    assert it1[0].fonte.arquivo == "contrato.docx"

    msg_file = tmp_path / "pedido.msg"
    msg_file.write_bytes(b"\xd0\xcf\x11\xe0")  # cabecalho binario OLE2
    h2, it2 = intake.extract_email(msg_file)
    assert h2.numero == "12345"
    assert it2[0].fonte.arquivo == "pedido.msg"


def test_extract_pdf_docling_fallback_and_cache(tmp_path, monkeypatch):
    pdf_file = tmp_path / "scan.pdf"
    pdf_file.write_bytes(make_pdf([""]))  # PDF sem texto extraivel pelo pdfplumber
    cache_file = tmp_path / ".intake-cache.json"

    calls = {"n": 0}

    def _fake_docling(_p):
        calls["n"] += 1
        return [
            (
                2,
                "Numero: 777\n"
                "| Item | Descricao | Un | Qtd | P unit | Total |\n"
                "|---|---|---|---|---|---|\n"
                "| 1 | Tubo Aco | m | 5 | 20.00 | 100.00 |\n",
            )
        ]

    monkeypatch.setattr(intake, "_docling_pages", _fake_docling)

    h1, it1 = intake.extract_pdf(pdf_file, cache_path=cache_file)
    assert calls["n"] == 1
    assert h1.numero == "777"
    assert len(it1) == 1
    assert it1[0].fonte.pagina == 2

    # Segunda chamada deve usar cache MD5 sem acionar Docling novamente
    h2, it2 = intake.extract_pdf(pdf_file, cache_path=cache_file)
    assert calls["n"] == 1
    assert h2.numero == "777"
    assert it2[0].fonte.pagina == 2


def test_extract_mpp_mocked(tmp_path, monkeypatch):
    import types

    mpp_file = tmp_path / "crono.mpp"
    mpp_file.write_bytes(b"fake-mpp")
    jar_file = tmp_path / "mpxj.jar"
    jar_file.write_bytes(b"fake-jar")

    class _FakeTask:
        def __init__(self, tid, name, start, finish, dur, pct):
            self._id = tid
            self._name = name
            self._start = start
            self._finish = finish
            self._dur = dur
            self._pct = pct

        def getID(self): return self._id
        def getName(self): return self._name
        def getStart(self): return self._start
        def getFinish(self): return self._finish
        def getDuration(self): return self._dur
        def getPercentageComplete(self): return self._pct

    class _FakeProject:
        def getTasks(self):
            return [
                _FakeTask(1, "Mobilizacao", "2026-09-01", "2026-11-30", "60d", 100),
                _FakeTask(2, "Montagem", "2026-12-01", "2027-03-15", "90d", 10),
            ]

    class _FakeReader:
        def read(self, _p):
            return _FakeProject()

    fake_jpype = types.ModuleType("jpype")
    fake_jpype.isJVMStarted = lambda: True
    fake_jpype.startJVM = lambda **kw: None
    fake_jpype_imports = types.ModuleType("jpype.imports")

    fake_net = types.ModuleType("net")
    fake_net_sf = types.ModuleType("net.sf")
    fake_net_sf_mpxj = types.ModuleType("net.sf.mpxj")
    fake_net_sf_mpxj_reader = types.ModuleType("net.sf.mpxj.reader")
    fake_net_sf_mpxj_reader.UniversalProjectReader = _FakeReader

    monkeypatch.setattr(intake, "_find_mpxj_jar", lambda: jar_file)
    monkeypatch.setitem(__import__("sys").modules, "jpype", fake_jpype)
    monkeypatch.setitem(__import__("sys").modules, "jpype.imports", fake_jpype_imports)
    monkeypatch.setitem(__import__("sys").modules, "net", fake_net)
    monkeypatch.setitem(__import__("sys").modules, "net.sf", fake_net_sf)
    monkeypatch.setitem(__import__("sys").modules, "net.sf.mpxj", fake_net_sf_mpxj)
    monkeypatch.setitem(__import__("sys").modules, "net.sf.mpxj.reader", fake_net_sf_mpxj_reader)

    res = intake.extract_mpp(mpp_file)
    assert res["resumo_corte"] == {"ate_2026": 1, "2027_ou_posterior": 1}
    assert res["saldo"]["pendente"] is True
    assert any(FLAG_PENDENTE in p for p in res["pendencias"])


def test_extract_archive_zip(tmp_path):
    import zipfile

    xlsx_path = tmp_path / "ppu.xlsx"
    _make_ppu(xlsx_path)
    zip_path = tmp_path / "lote.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.write(xlsx_path, arcname="sub/ppu.xlsx")

    extracted = intake.extract_archive_files(zip_path, tmp_path / "out")
    assert len(extracted) == 1
    assert extracted[0].name == "ppu.xlsx"


def test_parse_ariba_petrobras_layout():
    p1 = "Pedido de compra: 4515655362\nOBRIGAÇÕES DA PETROBRAS\nPedido enviado em: 2026-10-06"
    p26 = (
        "Itens de linha\n"
        "10 1 000000000030329019 Material 1,000 15 abr. R$241.558,84 R$241.558,84\n"
        "(UN) 2027 BRL BRL\n"
        "Conjunto do resfriador a ar\n"
        "STATUS\n"
    )
    header, items = intake._parse_labeled_text([(1, p1), (26, p26)], "pedido.pdf")
    assert header.numero == "4515655362"
    assert header.is_petrobras is True
    assert len(items) == 1
    assert items[0].item == "10"
    assert items[0].unidade == "UN"
    assert items[0].descricao == "Conjunto do resfriador a ar"
    assert items[0].preco_unitario == Decimal("241558.84")
    assert items[0].fonte.pagina == 26


def test_extract_pdf_logo_sem_imagem_retorna_none(tmp_path):
    p = tmp_path / "sem-logo.pdf"
    p.write_bytes(make_pdf(["Pedido de compra: 123"]))
    assert intake.extract_pdf_logo(p, out_dir=tmp_path / "logos") is None