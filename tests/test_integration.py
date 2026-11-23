"""Verificacao ponta a ponta (8.1): pipeline + entregaveis + conferencias."""

import json
import subprocess
import sys
from decimal import Decimal
from pathlib import Path

from reforma_tributaria import deliverables as dv
from reforma_tributaria import engine
from reforma_tributaria.models import FLAG_DIVERGENCIA

FIX = Path(__file__).parent / "fixtures" / "petrobras.json"
TOL = Decimal("0.01")


def test_pipeline_reproduz_valores_fator_e_entregaveis(analysis, premises):
    bens = [r for r in analysis.results if r.natureza == "BEM"]
    serv = [r for r in analysis.results if r.natureza == "SERVIÇO"]
    assert len(bens) == 42 and len(serv) == 5

    # totais validados
    assert abs(sum(r.total_a for r in bens) - Decimal("41385596.58")) <= TOL
    assert abs(sum(r.total_a for r in serv) - Decimal("17603942.43")) <= TOL
    assert abs(sum(r.base_total for r in bens) - Decimal("32708012.26")) <= TOL
    assert abs(sum(r.base_total for r in serv) - Decimal("15335711.63")) <= TOL

    # fator constante por grupo de aliquotas, sem divergencia
    assert len({r.fator_a for r in bens}) == 1
    assert len({r.fator_a for r in serv}) == 1
    assert all(FLAG_DIVERGENCIA not in r.flags for r in analysis.results)

    # conferencias obrigatorias
    val = engine.validate(analysis.items, analysis.results, analysis.ppu_total)
    assert all(val[k]["ok"] for k in ("reconciliacao", "qp", "base_invariante", "fator"))

    # quatro entregaveis
    assert dv.build_workbook(analysis, premises).sheetnames == dv.SHEETS
    assert "4600685026" in dv.build_parecer(analysis, premises)
    assert "RASCUNHO" in dv.build_carta(analysis, premises)
    assert "4600685026" in dv.build_priorizacao([analysis], premises)


def test_cli_run_ponta_a_ponta(tmp_path):
    r = subprocess.run(
        [sys.executable, "-m", "reforma_tributaria", "run", str(FIX), "--outdir", str(tmp_path)],
        capture_output=True, text=True,
    )
    assert r.returncode == 0, r.stderr
    for f in ("4600685026.xlsx", "parecer-4600685026.md",
              "carta-4600685026.md", "priorizacao.md"):
        assert (tmp_path / f).exists(), f
    s = json.loads((tmp_path / "validacao.json").read_text())["4600685026"]
    assert s["conferencias_ok"] is True
    assert abs(Decimal(s["total_2027_a"]) - Decimal("58989539.01")) <= TOL
    assert abs(Decimal(s["var_rs"]) - Decimal("3784812.10")) <= TOL