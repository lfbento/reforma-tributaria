"""Recalculador minimo das formulas geradas (verificacao sem LibreOffice).

Resolve referencias de celula (locais e entre abas) e ``SUM(intervalo)`` e
avalia a aritmetica das formulas que o proprio pacote gera. Usado apenas em
teste para confirmar que o XLSX recalcula igual ao motor deterministico.
"""

from __future__ import annotations

import re

from openpyxl.utils import range_boundaries

_SUM_RE = re.compile(r"SUM\(([^)]+)\)")
_REF_RE = re.compile(r"(?:([A-Za-z_][A-Za-z0-9_]*)!)?\$?([A-Z]+)\$?(\d+)")


def make_resolver(wb):
    cache: dict[tuple[str, str], float] = {}

    def value(sheet: str, coord: str) -> float:
        key = (sheet, coord)
        if key in cache:
            return cache[key]
        raw = wb[sheet][coord].value
        if isinstance(raw, (int, float)):
            cache[key] = float(raw)
            return float(raw)
        if not (isinstance(raw, str) and raw.startswith("=")):
            cache[key] = 0.0
            return 0.0
        expr = raw[1:]

        def sum_repl(m):
            inner = m.group(1).strip()
            if inner == "0":
                return "0"
            sh, _, rng = inner.partition("!")
            c1, r1, c2, r2 = range_boundaries(rng)
            total = 0.0
            for r in range(r1, r2 + 1):
                for c in range(c1, c2 + 1):
                    from openpyxl.utils import get_column_letter
                    total += value(sh, f"{get_column_letter(c)}{r}")
            return repr(total)

        expr = _SUM_RE.sub(sum_repl, expr)

        def ref_repl(m):
            sh = m.group(1) or sheet
            return repr(value(sh, f"{m.group(2)}{m.group(3)}"))

        expr = _REF_RE.sub(ref_repl, expr)
        result = float(eval(expr, {"__builtins__": {}}, {}))
        cache[key] = result
        return result

    return value