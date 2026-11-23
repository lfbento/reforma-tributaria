"""Registros estruturados e JSON-serializaveis do pipeline.

Decimais sao preservados como string no JSON para nao perder precisao. Cada
preco/quantidade carrega sua fonte (``Source``) e flags de auditoria.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from decimal import Decimal
from typing import Any

FLAG_PENDENTE = "PENDENTE – confirmar"
FLAG_RECONSTRUIDO = "RECONSTRUÍDO"
FLAG_DIVERGENCIA = "DIVERGÊNCIA"
FLAG_FORA_ESCOPO = "FORA DO ESCOPO"
FLAG_ALTO_RISCO = "ALTO RISCO"

NATUREZA_BEM = "BEM"
NATUREZA_SERVICO = "SERVIÇO"


def _dec(value: Any) -> Decimal:
    return Decimal(str(value))


def _stringify(obj: Any) -> Any:
    if isinstance(obj, Decimal):
        return str(obj)
    if isinstance(obj, dict):
        return {k: _stringify(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_stringify(v) for v in obj]
    return obj


@dataclass
class Source:
    """Origem de um dado: arquivo e, conforme o formato, aba/celula ou pagina."""

    arquivo: str
    aba: str | None = None
    celula: str | None = None
    pagina: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return _stringify(asdict(self))

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Source":
        return cls(
            arquivo=data["arquivo"],
            aba=data.get("aba"),
            celula=data.get("celula"),
            pagina=data.get("pagina"),
        )

    def describe(self) -> str:
        parts = [self.arquivo]
        if self.aba:
            parts.append(f"aba {self.aba}")
        if self.celula:
            parts.append(f"célula {self.celula}")
        if self.pagina is not None:
            parts.append(f"página {self.pagina}")
        return ", ".join(parts)


@dataclass
class Document:
    """Documento de entrada recebido."""

    path: str
    kind: str  # pedido | contrato | ppu | dfp | cronograma | comunicacao
    source: Source | None = None

    def to_dict(self) -> dict[str, Any]:
        return _stringify(asdict(self))

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Document":
        src = data.get("source")
        return cls(
            path=data["path"],
            kind=data["kind"],
            source=Source.from_dict(src) if src else None,
        )


@dataclass
class ContractHeader:
    """Cabecalho de pedido/contrato."""

    numero: str | None = None
    cliente: str | None = None
    data_emissao: str | None = None  # ISO yyyy-mm-dd
    vigencia: str | None = None
    condicao_pagamento: str | None = None
    clausula_revisao: str | None = None
    regime: str | None = None  # presumido | real | simples
    is_petrobras: bool = False

    def to_dict(self) -> dict[str, Any]:
        return _stringify(asdict(self))

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ContractHeader":
        return cls(**{k: data.get(k) for k in cls.__dataclass_fields__})


@dataclass
class LineItem:
    """Item de PPU/pedido com proveniencia e flags."""

    item: str
    descricao: str = ""
    unidade: str = ""
    quantidade: Decimal = Decimal("0")
    preco_unitario: Decimal = Decimal("0")
    total: Decimal = Decimal("0")
    natureza: str | None = None  # BEM | SERVICO
    fonte: Source | None = None
    flags: list[str] = field(default_factory=list)
    pendencias: list[str] = field(default_factory=list)
    aliquotas: dict[str, Decimal] = field(default_factory=dict)
    p0_original: Decimal | None = None
    preco_reajustado: Decimal | None = None
    preco_bruto_contrato: Decimal | None = None
    difal_indicado: bool = False
    difal_valor: Decimal | None = None
    origem_reconstrucao: str | None = None
    # saldo faturavel em 2027 deste item (quando conhecido)
    saldo_2027: Decimal | None = None

    def to_dict(self) -> dict[str, Any]:
        return _stringify(asdict(self))

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "LineItem":
        obj = cls(
            item=data["item"],
            descricao=data.get("descricao", ""),
            unidade=data.get("unidade", ""),
            quantidade=_dec(data.get("quantidade", "0")),
            preco_unitario=_dec(data.get("preco_unitario", "0")),
            total=_dec(data.get("total", "0")),
            natureza=data.get("natureza"),
            flags=list(data.get("flags", [])),
            pendencias=list(data.get("pendencias", [])),
            aliquotas={k: _dec(v) for k, v in data.get("aliquotas", {}).items()},
            difal_indicado=data.get("difal_indicado", False),
            origem_reconstrucao=data.get("origem_reconstrucao"),
        )
        src = data.get("fonte")
        obj.fonte = Source.from_dict(src) if src else None
        for opt in ("p0_original", "preco_reajustado", "preco_bruto_contrato", "difal_valor", "saldo_2027"):
            if data.get(opt) is not None:
                setattr(obj, opt, _dec(data[opt]))
        return obj

    def add_flag(self, flag: str) -> None:
        if flag not in self.flags:
            self.flags.append(flag)


@dataclass
class CalcResult:
    """Resultado de calculo por item (cenarios A e B)."""

    item: str
    natureza: str
    total_atual: Decimal
    a_pis: Decimal
    a_cof: Decimal
    a_L: Decimal
    a_ipi: Decimal
    a_difal: Decimal
    sum_atual: Decimal
    pis: Decimal
    cofins: Decimal
    icms_iss: Decimal
    ipi: Decimal
    difal: Decimal
    base_unit: Decimal
    base_total: Decimal
    cbs: Decimal
    ibs_est: Decimal
    ibs_mun: Decimal
    ibs: Decimal
    subtotal: Decimal
    icms_iss_2027_a: Decimal
    p2027_a: Decimal
    total_a: Decimal
    icms_iss_2027_b: Decimal
    p2027_b: Decimal
    total_b: Decimal
    var_rs: Decimal
    var_pct: Decimal
    fator_a: Decimal
    fator_b: Decimal
    flags: list[str] = field(default_factory=list)
    fonte: Source | None = None

    def to_dict(self) -> dict[str, Any]:
        return _stringify(asdict(self))

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CalcResult":
        kwargs: dict[str, Any] = {}
        for name in cls.__dataclass_fields__:
            if name in ("flags", "fonte"):
                continue
            val = data[name]
            kwargs[name] = val if name in ("item", "natureza") else _dec(val)
        kwargs["flags"] = list(data.get("flags", []))
        src = data.get("fonte")
        kwargs["fonte"] = Source.from_dict(src) if src else None
        return cls(**kwargs)


@dataclass
class Saldo:
    """Saldo a executar separado por ano de faturamento."""

    saldo_2026: Decimal = Decimal("0")
    saldo_2027: Decimal = Decimal("0")
    pendente: bool = False

    def to_dict(self) -> dict[str, Any]:
        return _stringify(asdict(self))

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Saldo":
        return cls(
            saldo_2026=_dec(data.get("saldo_2026", "0")),
            saldo_2027=_dec(data.get("saldo_2027", "0")),
            pendente=data.get("pendente", False),
        )


@dataclass
class ContractAnalysis:
    """Analise completa de um pedido/contrato, pronta para entregaveis."""

    header: ContractHeader
    items: list[LineItem] = field(default_factory=list)
    results: list[CalcResult] = field(default_factory=list)
    saldo: Saldo = field(default_factory=Saldo)
    scope: str = ""
    documents: list[Document] = field(default_factory=list)
    referencias_legais: list[str] = field(default_factory=list)
    ppu_total: Decimal = Decimal("0")
    regime_note: str | None = None
    clause_risk: bool = False

    def to_dict(self) -> dict[str, Any]:
        return _stringify(asdict(self))

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ContractAnalysis":
        return cls(
            header=ContractHeader.from_dict(data["header"]),
            items=[LineItem.from_dict(i) for i in data.get("items", [])],
            results=[CalcResult.from_dict(r) for r in data.get("results", [])],
            saldo=Saldo.from_dict(data.get("saldo", {})),
            scope=data.get("scope", ""),
            documents=[Document.from_dict(d) for d in data.get("documents", [])],
            referencias_legais=list(data.get("referencias_legais", [])),
            ppu_total=_dec(data.get("ppu_total", "0")),
            regime_note=data.get("regime_note"),
            clause_risk=data.get("clause_risk", False),
        )

    def total_atual(self) -> Decimal:
        return sum((r.total_atual for r in self.results), Decimal("0"))

    def total_a(self) -> Decimal:
        return sum((r.total_a for r in self.results), Decimal("0"))

    def total_b(self) -> Decimal:
        return sum((r.total_b for r in self.results), Decimal("0"))

    def base_total(self) -> Decimal:
        return sum((r.base_total for r in self.results), Decimal("0"))

    def var_rs(self) -> Decimal:
        return self.total_a() - self.total_atual()

    def var_pct(self) -> Decimal:
        atual = self.total_atual()
        return self.var_rs() / atual if atual else Decimal("0")

    def impacto_saldo_2027(self) -> Decimal:
        """Impacto em R$ somente sobre o saldo faturavel em 2027 (Cenario A)."""
        atual = self.total_atual()
        if any(it.saldo_2027 is not None for it in self.items):
            total = Decimal("0")
            for it, r in zip(self.items, self.results):
                saldo = it.saldo_2027 or Decimal("0")
                base = it.total if it.total else r.total_atual
                proporcao = saldo / base if base else Decimal("0")
                total += r.var_rs * proporcao
            return total
        if self.saldo.pendente or not atual:
            return self.var_rs()
        return self.var_rs() * (self.saldo.saldo_2027 / atual)