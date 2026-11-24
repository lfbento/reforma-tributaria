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

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import unicodedata
import zipfile
from datetime import date
from decimal import Decimal, InvalidOperation
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
CACHE_FILENAME = ".intake-cache.json"

_SEVENZIP_CANDIDATES = [
    "7z",
    r"C:\Program Files\7-Zip\7z.exe",
    r"C:\Program Files (x86)\7-Zip\7z.exe",
]


def safe_path(path: str | Path) -> Path:
    """Garante suporte a caminhos longos (>260 chars) no Windows."""
    p = Path(path)
    if sys.platform != "win32":
        return p
    p_str = str(p.resolve())
    if not p_str.startswith("\\\\?\\"):
        if p_str.startswith("\\\\"):
            p_str = "\\\\?\\UNC\\" + p_str[2:]
        else:
            p_str = "\\\\?\\" + p_str
    return Path(p_str)


def file_hash(path: str | Path) -> str:
    """Calcula hash MD5 do conteudo do arquivo em blocos."""
    h = hashlib.md5()
    with open(safe_path(path), "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def load_cache(cache_path: str | Path) -> dict[str, Any]:
    """Carrega cache incremental JSON, retornando dict vazio se ausente ou invalido."""
    cp = safe_path(cache_path)
    if cp.exists():
        try:
            return json.loads(cp.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def save_cache(cache_path: str | Path, cache: dict[str, Any]) -> None:
    """Salva cache incremental JSON usando caminho seguro."""
    target = safe_path(cache_path)
    safe_path(target.parent).mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(cache, indent=2, ensure_ascii=False), encoding="utf-8")


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
    "pedido de compra": "numero",
    "cliente": "cliente",
    "emissao": "data_emissao",
    "data de emissao": "data_emissao",
    "pedido enviado em": "data_emissao",
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
    with pdfplumber.open(safe_path(path)) as pdf:
        for i, page in enumerate(pdf.pages, start=1):
            pages.append((i, page.extract_text() or ""))
    return pages


_DOCLING_WORKER = """
import json, pathlib, sys
def safe_p(p):
    s = str(pathlib.Path(p).resolve())
    if sys.platform == "win32" and not s.startswith("\\\\\\\\?\\\\"):
        return pathlib.Path("\\\\\\\\?\\\\UNC\\\\" + s[2:]) if s.startswith("\\\\\\\\") else pathlib.Path("\\\\\\\\?\\\\" + s)
    return pathlib.Path(s)
from docling.document_converter import DocumentConverter
converter = DocumentConverter()
res = converter.convert(str(safe_p(sys.argv[1])))
doc = res.document
by_page = {}
for item, _level in doc.iterate_items():
    prov = getattr(item, "prov", None) or []
    page_no = getattr(prov[0], "page_no", 1) if prov else 1
    if hasattr(item, "export_to_markdown"):
        try:
            chunk = item.export_to_markdown(doc=doc)
        except TypeError:
            chunk = item.export_to_markdown()
    else:
        chunk = getattr(item, "text", "") or ""
    if chunk and chunk.strip():
        by_page.setdefault(int(page_no), []).append(chunk.strip())
if not by_page:
    md = doc.export_to_markdown()
    if md.strip():
        by_page[1] = [md]
pages = [[p, "\\n".join(chunks)] for p, chunks in sorted(by_page.items())]
print(json.dumps(pages, ensure_ascii=False))
""".strip()


def _docling_pages(path: Path, timeout: int = 180) -> list[tuple[int, str]]:
    """Executa Docling em subprocesso isolado preservando o numero da pagina."""
    res = subprocess.run(
        [sys.executable, "-c", _DOCLING_WORKER, str(path)],
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    if res.returncode != 0:
        raise RuntimeError(f"Docling falhou em {path.name}: {res.stderr.strip()[:200]}")
    raw_pages = json.loads(res.stdout)
    return [(int(p), text) for p, text in raw_pages]


_MD_SEP_RE = re.compile(r"^:?-{2,}:?$")


def _split_pipe_row(line: str) -> list[str]:
    stripped = line.strip()
    if stripped.startswith("|"):
        stripped = stripped[1:]
    if stripped.endswith("|"):
        stripped = stripped[:-1]
    return [p.strip() for p in stripped.split("|")]


def _is_md_separator(parts: list[str]) -> bool:
    return bool(parts) and all(_MD_SEP_RE.match(p.replace(" ", "")) for p in parts if p != "")


def _dec_br_or_us(raw: str) -> Decimal:
    s = raw.strip().replace("R$", "").replace("BRL", "").strip()
    if "," in s and "." in s:
        if s.rfind(",") > s.rfind("."):
            s = s.replace(".", "").replace(",", ".")
        else:
            s = s.replace(",", "")
    elif "," in s:
        s = s.replace(",", ".")
    return Decimal(s)


_ARIBA_LINE_RE = re.compile(
    r"^\s*(\d+)\s+\d+\s+\S+\s+(?:Material|Servi[cç]o)\s+([\d.,]+)\s+.*?R\$\s*([\d.,]+)\s+R\$\s*([\d.,]+)"
)
_UNIT_RE = re.compile(r"\(([A-Za-z0-9]{1,6})\)")


def _parse_ariba_items(
    pages: list[tuple[int, str]], arquivo: str
) -> list[LineItem]:
    items: list[LineItem] = []
    for pagina, text in pages:
        lines = [ln.strip() for ln in text.splitlines()]
        for idx, line in enumerate(lines):
            m = _ARIBA_LINE_RE.match(line)
            if not m:
                continue
            item_no, qtd_s, punit_s, tot_s = m.groups()
            unidade = ""
            descricao = ""
            for look in lines[idx + 1 : idx + 4]:
                if not unidade:
                    um = _UNIT_RE.search(look)
                    if um:
                        unidade = um.group(1)
                        continue
                if not descricao and look and not look.upper().startswith("STATUS"):
                    descricao = look
                    break
            items.append(
                LineItem(
                    item=item_no,
                    descricao=descricao,
                    unidade=unidade,
                    quantidade=_dec_br_or_us(qtd_s),
                    preco_unitario=_dec_br_or_us(punit_s),
                    total=_dec_br_or_us(tot_s),
                    fonte=Source(arquivo=arquivo, pagina=pagina),
                )
            )
    return items


def _parse_labeled_text(
    pages: list[tuple[int, str]], arquivo: str
) -> tuple[ContractHeader, list[LineItem]]:
    header = ContractHeader()
    items: list[LineItem] = []
    in_items = False
    full_norm_chunks: list[str] = []
    for pagina, text in pages:
        full_norm_chunks.append(_norm(text))
        for raw in text.splitlines():
            line = raw.strip()
            if not line:
                continue
            low = _norm(line)
            if low in ("itens:", "itens"):
                in_items = True
                continue
            if "|" in line:
                parts = _split_pipe_row(line)
                if _is_md_separator(parts):
                    continue
                if len(parts) >= 6 and _norm(parts[0]) == "item" and _norm(parts[1]).startswith("descr"):
                    in_items = True
                    continue
                if in_items and len(parts) >= 6:
                    try:
                        qtd = _dec(parts[3])
                        punit = _dec(parts[4])
                        tot = _dec(parts[5])
                    except InvalidOperation:
                        continue
                    items.append(
                        LineItem(
                            item=parts[0],
                            descricao=parts[1],
                            unidade=parts[2],
                            quantidade=qtd,
                            preco_unitario=punit,
                            total=tot,
                            fonte=Source(arquivo=arquivo, pagina=pagina),
                        )
                    )
                    continue
            if ":" in line and not in_items:
                label, _, value = line.partition(":")
                field = _HEADER_LABELS.get(_norm(label))
                if field and not getattr(header, field):
                    setattr(header, field, value.strip())
                    continue
    if not items:
        items = _parse_ariba_items(pages, arquivo)
    if header.cliente:
        header.is_petrobras = "petrobras" in _norm(header.cliente)
    elif any("petrobras" in chunk for chunk in full_norm_chunks):
        header.is_petrobras = True
        header.cliente = "Petrobras"
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


def extract_pdf_logo(
    path: str | Path,
    out_dir: str | Path | None = None,
) -> Path | None:
    """Extrai o primeiro logotipo embutido na pagina 1 do PDF como PNG.

    Retorna o Path do PNG salvo ou None se o PDF nao tiver imagens decodificaveis.
    """
    path = Path(path)
    try:
        from PIL import Image
    except ImportError:
        return None

    try:
        with pdfplumber.open(safe_path(path)) as pdf:
            if not pdf.pages:
                return None
            images = pdf.pages[0].images
            if not images:
                return None
            for img_meta in images:
                stream = img_meta.get("stream")
                if stream is None:
                    continue
                try:
                    raw = stream.get_data()
                    width = int(img_meta.get("srcsize", (0, 0))[0] or stream.attrs.get("Width", 0))
                    height = int(img_meta.get("srcsize", (0, 0))[1] or stream.attrs.get("Height", 0))
                    filt = str(stream.attrs.get("Filter", ""))
                    if "DCTDecode" in filt or "JPXDecode" in filt:
                        from io import BytesIO
                        pil_img = Image.open(BytesIO(raw))
                    elif width > 0 and height > 0:
                        cs = str(stream.attrs.get("ColorSpace", ""))
                        if "Gray" in cs and len(raw) == width * height:
                            pil_img = Image.frombytes("L", (width, height), raw)
                        elif len(raw) == width * height * 3:
                            pil_img = Image.frombytes("RGB", (width, height), raw)
                        elif len(raw) == width * height * 4:
                            pil_img = Image.frombytes("CMYK", (width, height), raw).convert("RGB")
                        else:
                            from io import BytesIO
                            pil_img = Image.open(BytesIO(raw))
                    else:
                        continue
                    target_dir = Path(out_dir) if out_dir else path.parent / ".intake-logos"
                    target_dir.mkdir(parents=True, exist_ok=True)
                    out_path = target_dir / f"{path.stem}_client_logo.png"
                    pil_img.save(out_path, format="PNG")
                    return out_path
                except Exception:
                    continue
    except Exception:
        return None
    return None


def extract_pdf(
    path: str | Path,
    *,
    use_docling_fallback: bool = True,
    cache_path: str | Path | None = None,
    extract_logo: bool = True,
) -> tuple[ContractHeader, list[LineItem]]:
    """Extrai PDF com pdfplumber e usa Docling em subprocesso como fallback."""
    path = Path(path)
    pages = _pdf_pages(path)
    header, items = _parse_labeled_text(pages, path.name)

    needs_fallback = use_docling_fallback and all(
        len(text.strip()) < 20 for _, text in pages
    )
    if needs_fallback:
        doc_pages: list[tuple[int, str]] | None = None
        cache: dict[str, Any] = {}
        cache_key = ""
        if cache_path is not None:
            cache = load_cache(cache_path)
            cache_key = f"docling:{file_hash(path)}"
            cached = cache.get(cache_key)
            if isinstance(cached, list):
                doc_pages = [(int(p), str(t)) for p, t in cached]

        if doc_pages is None:
            try:
                doc_pages = _docling_pages(path)
                if cache_path is not None and cache_key:
                    cache[cache_key] = [[p, t] for p, t in doc_pages]
                    save_cache(cache_path, cache)
            except (RuntimeError, OSError, subprocess.SubprocessError):
                doc_pages = None

        if doc_pages:
            header, items = _parse_labeled_text(doc_pages, path.name)

    if extract_logo and not header.client_logo_path:
        logo_path = extract_pdf_logo(path)
        if logo_path is not None:
            header.client_logo_path = str(logo_path)

    return header, items


def _extract_with_markitdown(path: Path) -> str:
    try:
        from markitdown import MarkItDown
    except ImportError as exc:
        raise RuntimeError(
            "Biblioteca 'markitdown' nao instalada. Instale com: pip install .[office]"
        ) from exc
    result = MarkItDown().convert(str(safe_path(path)))
    return result.text_content or ""


def extract_office(path: str | Path) -> tuple[ContractHeader, list[LineItem]]:
    """Extrai documentos Office (.docx, .pptx) e e-mails .msg via MarkItDown."""
    path = Path(path)
    text = _extract_with_markitdown(path)
    return _parse_labeled_text([(1, text)], path.name)


def extract_email(path: str | Path) -> tuple[ContractHeader, list[LineItem]]:
    """Extrai e-mail (.eml via stdlib ou .msg via MarkItDown)."""
    path = Path(path)
    if path.suffix.lower() == ".msg":
        return extract_office(path)

    import email
    from email import policy

    msg = email.message_from_bytes(safe_path(path).read_bytes(), policy=policy.default)
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


# --------------------------------------------------------------------------- #
# MS Project (.mpp) e Pacotes Compactados (.zip / .rar)
# --------------------------------------------------------------------------- #
def _find_mpxj_jar() -> Path | None:
    env_jar = os.environ.get("MPXJ_JAR")
    candidates = [
        Path(env_jar) if env_jar else None,
        Path(__file__).parent / "lib" / "mpxj.jar",
        Path.home()
        / ".gemini"
        / "config"
        / "skills"
        / "convert-office-docs"
        / "scripts"
        / "lib"
        / "mpxj.jar",
    ]
    for cand in candidates:
        if cand is not None and cand.exists():
            return cand
    return None


def _parse_mpxj_date(raw: Any) -> date | None:
    if raw is None:
        return None
    text = str(raw).strip()
    if not text:
        return None
    m = re.search(r"(\d{4}-\d{2}-\d{2})", text)
    if m:
        return date.fromisoformat(m.group(1))
    return None


def extract_mpp(path: str | Path) -> dict[str, Any]:
    """Extrai tarefas e corte temporal 2026/2027 de cronograma MS Project (.mpp)."""
    path = Path(path)
    jar = _find_mpxj_jar()
    if jar is None:
        raise FileNotFoundError(
            "mpxj.jar nao encontrado. Defina MPXJ_JAR ou salve em src/reforma_tributaria/lib/mpxj.jar."
        )
    try:
        import jpype
        import jpype.imports  # noqa: F401
    except ImportError as exc:
        raise RuntimeError(
            "Biblioteca 'jpype1' nao instalada. Instale com: pip install .[mpp]"
        ) from exc

    if not jpype.isJVMStarted():
        jpype.startJVM(classpath=[str(jar)])

    from net.sf.mpxj.reader import UniversalProjectReader  # type: ignore

    project = UniversalProjectReader().read(str(safe_path(path)))
    tasks: list[dict[str, Any]] = []
    pre_2027 = 0
    post_2027 = 0
    for task in project.getTasks():
        name = task.getName()
        if name is None:
            continue
        finish_raw = task.getFinish()
        finish_dt = _parse_mpxj_date(finish_raw)
        corte = "PENDENTE"
        if finish_dt is not None:
            if finish_dt <= _CORTE_2026:
                corte = "ate_2026"
                pre_2027 += 1
            else:
                corte = "2027_ou_posterior"
                post_2027 += 1
        tasks.append(
            {
                "id": str(task.getID() or ""),
                "nome": str(name),
                "inicio": str(task.getStart() or ""),
                "termino": str(finish_raw or ""),
                "duracao": str(task.getDuration() or ""),
                "percentual_concluido": str(task.getPercentageComplete() or ""),
                "corte": corte,
            }
        )

    return {
        "tasks": tasks,
        "resumo_corte": {"ate_2026": pre_2027, "2027_ou_posterior": post_2027},
        "saldo": Saldo(pendente=True).to_dict(),
        "pendencias": [
            f"{FLAG_PENDENTE}: cronograma .mpp ({path.name}) nao traz valores financeiros de faturamento"
        ],
    }


def find_7zip() -> str | None:
    """Localiza executavel 7-Zip no PATH ou caminhos padrao no Windows."""
    for candidate in _SEVENZIP_CANDIDATES:
        if shutil.which(candidate) or Path(candidate).exists():
            return candidate
    return None


def extract_archive_files(path: str | Path, dest_dir: str | Path) -> list[Path]:
    """Extrai pacote .zip ou .rar para dest_dir e retorna lista de arquivos extraidos."""
    path = Path(path)
    dest = Path(dest_dir)
    dest.mkdir(parents=True, exist_ok=True)
    ext = path.suffix.lower()

    if ext == ".zip":
        dest_resolved = dest.resolve()
        with zipfile.ZipFile(safe_path(path), "r") as zf:
            for member in zf.infolist():
                if member.is_dir():
                    continue
                target = (dest_resolved / member.filename).resolve()
                target.relative_to(dest_resolved)  # previne zip-slip
                target.parent.mkdir(parents=True, exist_ok=True)
                with zf.open(member) as src, open(target, "wb") as dst:
                    shutil.copyfileobj(src, dst)
    elif ext == ".rar":
        sevenzip = find_7zip()
        if sevenzip is None:
            raise RuntimeError(
                "7-Zip nao encontrado para extrair arquivo .rar. Instale o 7-Zip ou adicione ao PATH."
            )
        res = subprocess.run(
            [sevenzip, "x", str(safe_path(path)), f"-o{dest}", "-y"],
            capture_output=True,
            text=True,
        )
        if res.returncode != 0:
            raise RuntimeError(f"Falha ao extrair {path.name}: {res.stderr.strip()}")
    else:
        raise ValueError(f"Formato de arquivo compactado nao suportado: {ext}")

    return sorted(p for p in dest.rglob("*") if p.is_file())