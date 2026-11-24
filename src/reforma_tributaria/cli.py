"""CLI do nucleo deterministico.

Subcomandos: ``extract`` (documento -> JSON), ``triage``, ``calc``, ``xlsx``,
``report``, ``validate`` e ``run`` (pipeline completo -> entregaveis). O agente
omp orquestra estes comandos passando dados estruturados; nunca texto livre
para calcular.
"""

from __future__ import annotations

import argparse
import json
import sys
from decimal import Decimal
from pathlib import Path
from typing import Any

from . import deliverables as dv
from . import engine, intake, pipeline, triage
from .models import ContractHeader, LineItem
from .premises import load_premises


def _premises(args: argparse.Namespace):
    overrides: dict[str, Any] = {}
    for item in getattr(args, "override", []) or []:
        key, _, value = item.partition("=")
        overrides[key] = value
    return load_premises(getattr(args, "premises", None), overrides or None)


def _write_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _extract_archive(path: Path) -> dict[str, Any]:
    import tempfile

    merged: dict[str, Any] = {"header": {}, "items": [], "documentos": []}
    supported = {".xlsx", ".pdf", ".eml", ".msg", ".doc", ".docx", ".pptx", ".txt", ".dfp", ".mpp", ".zip", ".rar"}
    with tempfile.TemporaryDirectory() as tmp:
        tmp_root = Path(tmp)
        files = intake.extract_archive_files(path, tmp_root)
        for fp in files:
            if fp.suffix.lower() not in supported:
                continue
            rel = fp.relative_to(tmp_root).as_posix()
            sub = _extract(fp)
            if not merged["header"] and sub.get("header"):
                merged["header"] = sub["header"]
            merged["items"].extend(sub.get("items", []))
            for doc in sub.get("documentos", []):
                doc_copy = dict(doc)
                doc_copy["path"] = f"{path.name}!/{rel}"
                merged["documentos"].append(doc_copy)
            if "dfp" in sub:
                merged["dfp"] = sub["dfp"]
            if "mpp" in sub:
                merged["mpp"] = sub["mpp"]
    return merged


def _extract(path: Path) -> dict[str, Any]:
    suffix = path.suffix.lower()
    if suffix == ".xlsx":
        items = intake.extract_xlsx(path)
        return {"header": {}, "items": [i.to_dict() for i in items],
                "documentos": [{"path": str(path), "kind": "ppu"}]}
    if suffix == ".pdf":
        header, items = intake.extract_pdf(path)
        return {"header": header.to_dict(), "items": [i.to_dict() for i in items],
                "documentos": [{"path": str(path), "kind": "contrato"}]}
    if suffix in (".eml", ".msg"):
        header, items = intake.extract_email(path)
        return {"header": header.to_dict(), "items": [i.to_dict() for i in items],
                "documentos": [{"path": str(path), "kind": "pedido"}]}
    if suffix in (".doc", ".docx", ".pptx"):
        header, items = intake.extract_office(path)
        return {"header": header.to_dict(), "items": [i.to_dict() for i in items],
                "documentos": [{"path": str(path), "kind": "contrato"}]}
    if suffix in (".txt", ".dfp"):
        return {"dfp": intake.extract_dfp(path), "documentos": [{"path": str(path), "kind": "dfp"}]}
    if suffix == ".mpp":
        return {"mpp": intake.extract_mpp(path), "documentos": [{"path": str(path), "kind": "cronograma"}]}
    if suffix in (".zip", ".rar"):
        return _extract_archive(path)
    raise SystemExit(f"formato nao suportado para extract: {suffix}")


def cmd_extract(args) -> int:
    data = _extract(Path(args.input))
    out = Path(args.out) if args.out else None
    if out:
        _write_json(out, data)
    else:
        print(json.dumps(data, ensure_ascii=False, indent=2))
    return 0


def _load_with_regime(path: str | Path, args: argparse.Namespace) -> dict[str, Any]:
    data = pipeline.load_input(path)
    regime = getattr(args, "regime", None)
    if regime:
        data.setdefault("header", {})["regime"] = regime
    return data


def cmd_triage(args) -> int:
    data = _load_with_regime(args.input, args)
    header = ContractHeader.from_dict(data["header"])
    items = [LineItem.from_dict(i) for i in data["items"]]
    for it in items:
        it.natureza = triage.classify_nature(it)
    from .models import Saldo
    saldo = Saldo.from_dict(data.get("saldo", {}))
    result = {
        "header": header.to_dict(),
        "items": [i.to_dict() for i in items],
        "scope": triage.scope_status(header, saldo),
        "clause_risk": triage.clause_risk(header),
        "regime": triage.regime_treatment(header.regime),
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def cmd_calc(args) -> int:
    analysis = pipeline.analyze(_load_with_regime(args.input, args), _premises(args))
    print(json.dumps(analysis.to_dict(), ensure_ascii=False, indent=2))
    return 0


def _branding_kwargs(args: argparse.Namespace) -> dict[str, Any]:
    kw: dict[str, Any] = {}
    if getattr(args, "empresa", None):
        kw["empresa"] = args.empresa
    if getattr(args, "logo", None):
        kw["logo_path"] = args.logo
    if getattr(args, "client_logo", None):
        kw["client_logo_path"] = args.client_logo
    if getattr(args, "letterhead", None):
        kw["letterhead_path"] = args.letterhead
    return kw


def cmd_xlsx(args) -> int:
    ps = _premises(args)
    analysis = pipeline.analyze(_load_with_regime(args.input, args), ps)
    xlsx_kw = {k: v for k, v in _branding_kwargs(args).items() if k != "letterhead_path"}
    wb = dv.build_workbook(analysis, ps, **xlsx_kw)
    wb.save(args.out)
    print(f"XLSX: {args.out}")
    return 0


def _emit_reports(analyses, ps, outdir: Path, branding: dict[str, Any] | None = None) -> None:
    outdir.mkdir(parents=True, exist_ok=True)
    bkw = dict(branding or {})
    letterhead_path = bkw.pop("letterhead_path", None)
    empresa_kw = {"empresa": bkw["empresa"]} if "empresa" in bkw else {}
    for a in analyses:
        tag = a.header.numero or "pedido"
        wb = dv.build_workbook(a, ps, **bkw)
        wb.save(outdir / f"{tag}.xlsx")
        (outdir / f"parecer-{tag}.md").write_text(dv.build_parecer(a, ps), encoding="utf-8")
        (outdir / f"carta-{tag}.md").write_text(dv.build_carta(a, ps, **empresa_kw), encoding="utf-8")
        memo_doc = dv.build_memorando_docx(a, ps, letterhead_path=letterhead_path, **empresa_kw)
        memo_doc.save(outdir / f"memorando-{tag}.docx")
        pend = dv.build_pendencias(a, ps)
        (outdir / f"pendencias-{tag}.md").write_text(
            "# Pendências a confirmar\n\n" + "\n".join(f"- {p}" for p in pend), encoding="utf-8"
        )
    (outdir / "priorizacao.md").write_text(
        "# Priorização de pedidos\n\n" + dv.build_priorizacao(analyses, ps), encoding="utf-8"
    )


def cmd_report(args) -> int:
    ps = _premises(args)
    analyses = [pipeline.analyze(_load_with_regime(p, args), ps) for p in args.input]
    _emit_reports(analyses, ps, Path(args.outdir), _branding_kwargs(args))
    print(f"Entregaveis em: {args.outdir}")
    return 0


def cmd_validate(args) -> int:
    ps = _premises(args)
    analysis = pipeline.analyze(_load_with_regime(args.input, args), ps)
    report = engine.validate(analysis.items, analysis.results, analysis.ppu_total)
    ok = (report["reconciliacao"]["ok"] and report["qp"]["ok"]
          and report["base_invariante"]["ok"] and report["fator"]["ok"])
    print(json.dumps(report, ensure_ascii=False, indent=2, default=str))
    return 0 if ok else 1


def cmd_run(args) -> int:
    ps = _premises(args)
    analyses = [pipeline.analyze(_load_with_regime(p, args), ps) for p in args.input]
    outdir = Path(args.outdir)
    _emit_reports(analyses, ps, outdir, _branding_kwargs(args))
    summary = {}
    for a in analyses:
        report = engine.validate(a.items, a.results, a.ppu_total)
        summary[a.header.numero or "pedido"] = {
            "scope": a.scope,
            "total_atual": str(a.total_atual()),
            "total_2027_a": str(a.total_a()),
            "total_2027_b": str(a.total_b()),
            "var_rs": str(a.var_rs()),
            "impacto_saldo_2027": str(a.impacto_saldo_2027()),
            "conferencias_ok": all(
                report[k]["ok"] for k in ("reconciliacao", "qp", "base_invariante", "fator")
            ),
        }
    _write_json(outdir / "validacao.json", summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


def _add_premises_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--premises", help="caminho de premises.yaml alternativo")
    p.add_argument("--override", action="append", metavar="KEY=VALUE",
                   help="override de premissa (repetivel)")
    p.add_argument("--regime", choices=["presumido", "real", "simples"],
                   help="sobrescreve o regime tributario (padrao: presumido)")


def _add_branding_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--empresa", help="nome da empresa para o cabecalho executivo")
    p.add_argument("--logo", help="caminho do logo da empresa (padrao: NNNN.png)")
    p.add_argument("--client-logo", help="caminho do logo do cliente")
    p.add_argument("--letterhead", help="caminho do papel timbrado DOCX (padrao: Papel timbrado.docx)")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="reforma-tributaria",
                                     description="Analise de Reforma Tributaria 2027")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("extract", help="documento (PDF/XLSX/e-mail/DFP) -> JSON estruturado")
    p.add_argument("input")
    p.add_argument("--out")
    p.set_defaults(func=cmd_extract)

    p = sub.add_parser("triage", help="escopo e classificacao")
    p.add_argument("input")
    p.set_defaults(func=cmd_triage)

    p = sub.add_parser("calc", help="calculo por item (cenarios A e B)")
    p.add_argument("input")
    _add_premises_args(p)
    p.set_defaults(func=cmd_calc)

    p = sub.add_parser("xlsx", help="gera planilha XLSX")
    p.add_argument("input")
    p.add_argument("--out", required=True)
    _add_premises_args(p)
    _add_branding_args(p)
    p.set_defaults(func=cmd_xlsx)

    p = sub.add_parser("report", help="parecer, carta, priorizacao e pendencias")
    p.add_argument("input", nargs="+")
    p.add_argument("--outdir", required=True)
    _add_premises_args(p)
    _add_branding_args(p)
    p.set_defaults(func=cmd_report)

    p = sub.add_parser("validate", help="conferencias obrigatorias")
    p.add_argument("input")
    _add_premises_args(p)
    p.set_defaults(func=cmd_validate)

    p = sub.add_parser("run", help="pipeline completo -> entregaveis")
    p.add_argument("input", nargs="+")
    p.add_argument("--outdir", required=True)
    _add_premises_args(p)
    _add_branding_args(p)
    p.set_defaults(func=cmd_run)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())