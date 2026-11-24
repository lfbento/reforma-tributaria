"""Testes da CLI (7.1), incluindo run sobre a fixture Petrobras."""

import json
import subprocess
import sys
from pathlib import Path

from openpyxl import Workbook, load_workbook

FIX = Path(__file__).parent / "fixtures" / "petrobras.json"
SHEETS = ["Premissas", "Calculo_Bens", "Calculo_Servicos", "Saldo_2027", "Resumo", "Fontes"]


def run_cli(*args):
    return subprocess.run(
        [sys.executable, "-m", "reforma_tributaria", *args],
        capture_output=True, text=True,
    )


def test_run_produz_quatro_entregaveis(tmp_path):
    r = run_cli("run", str(FIX), "--outdir", str(tmp_path))
    assert r.returncode == 0, r.stderr
    assert (tmp_path / "4600685026.xlsx").exists()
    assert (tmp_path / "parecer-4600685026.md").exists()
    assert (tmp_path / "carta-4600685026.md").exists()
    assert (tmp_path / "memorando-4600685026.docx").exists()
    assert (tmp_path / "priorizacao.md").exists()
    wb = load_workbook(tmp_path / "4600685026.xlsx")
    assert wb.sheetnames == SHEETS
    summary = json.loads((tmp_path / "validacao.json").read_text())
    assert summary["4600685026"]["conferencias_ok"] is True


def test_validate_exit_zero():
    r = run_cli("validate", str(FIX))
    assert r.returncode == 0, r.stderr


def test_xlsx_command(tmp_path):
    out = tmp_path / "out.xlsx"
    r = run_cli("xlsx", str(FIX), "--out", str(out))
    assert r.returncode == 0 and out.exists()
    assert load_workbook(out).sheetnames == SHEETS


def test_extract_xlsx_command(tmp_path):
    p = tmp_path / "ppu.xlsx"
    wb = Workbook()
    ws = wb.active
    ws.append(["Item", "Descricao", "Un", "Qtd", "P unit", "Total"])
    ws.append(["1", "Estrutura", "kg", 10, 100, 1000])
    wb.save(p)
    out = tmp_path / "extraido.json"
    r = run_cli("extract", str(p), "--out", str(out))
    assert r.returncode == 0, r.stderr
    data = json.loads(out.read_text())
    assert data["items"][0]["item"] == "1"
    assert data["items"][0]["fonte"]["celula"] == "E2"


def test_override_recalcula_tudo(tmp_path):
    run_cli("run", str(FIX), "--outdir", str(tmp_path / "base"))
    run_cli("run", str(FIX), "--outdir", str(tmp_path / "novo"),
            "--override", "cbs_referencia=0.12")
    base = json.loads((tmp_path / "base" / "validacao.json").read_text())
    novo = json.loads((tmp_path / "novo" / "validacao.json").read_text())
    assert base["4600685026"]["total_2027_a"] != novo["4600685026"]["total_2027_a"]


def test_extract_zip_command(tmp_path):
    import zipfile

    p = tmp_path / "ppu.xlsx"
    wb = Workbook()
    ws = wb.active
    ws.append(["Item", "Descricao", "Un", "Qtd", "P unit", "Total"])
    ws.append(["1", "Estrutura", "kg", 10, 100, 1000])
    wb.save(p)

    z = tmp_path / "pacote.zip"
    with zipfile.ZipFile(z, "w") as zf:
        zf.write(p, arcname="docs/ppu.xlsx")

    out = tmp_path / "extraido_zip.json"
    r = run_cli("extract", str(z), "--out", str(out))
    assert r.returncode == 0, r.stderr
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["items"][0]["item"] == "1"
    assert data["documentos"][0]["path"] == "pacote.zip!/docs/ppu.xlsx"


def test_regime_flag_sobrescreve_calculo(tmp_path):
    r_pres = run_cli("calc", str(FIX), "--regime", "presumido")
    r_real = run_cli("calc", str(FIX), "--regime", "real")
    assert r_pres.returncode == 0 and r_real.returncode == 0
    d_pres = json.loads(r_pres.stdout)
    d_real = json.loads(r_real.stdout)
    assert d_pres["header"]["regime"] == "presumido"
    assert d_real["header"]["regime"] == "real"
    assert d_pres["results"][0]["a_pis"] == "0.0065"
    assert d_real["results"][0]["a_pis"] == "0.0165"