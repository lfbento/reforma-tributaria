"""Gerador minimo de PDF (uma pagina, Helvetica) para fixtures de teste.

Evita dependencia de escrita de PDF no pacote: o produto apenas le PDF.
"""

from __future__ import annotations


def make_pdf(lines: list[str]) -> bytes:
    parts = ["BT", "/F1 11 Tf", "72 720 Td", "16 TL"]
    for i, ln in enumerate(lines):
        esc = ln.replace("\\", r"\\").replace("(", r"\(").replace(")", r"\)")
        if i > 0:
            parts.append("T*")
        parts.append(f"({esc}) Tj")
    parts.append("ET")
    stream = "\n".join(parts).encode("latin-1", "replace")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream",
    ]
    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for i, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += f"{i} 0 obj\n".encode() + body + b"\nendobj\n"
    xref_pos = len(out)
    out += f"xref\n0 {len(objects) + 1}\n".encode()
    out += b"0000000000 65535 f \n"
    for off in offsets:
        out += f"{off:010d} 00000 n \n".encode()
    out += (
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
        f"startxref\n{xref_pos}\n%%EOF"
    ).encode()
    return bytes(out)