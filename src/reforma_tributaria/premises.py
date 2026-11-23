"""Premissas editaveis do cenario 2027, com fonte por parametro.

Carrega os padroes versionados de ``premises.yaml`` e aplica overrides. Alterar
uma premissa recalcula todos os itens (o motor le sempre do ``PremiseSet``).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path
from typing import Any

import yaml

DEFAULT_PATH = Path(__file__).with_name("premises.yaml")

REGIME_PRESUMIDO = "presumido"
REGIME_REAL = "real"
REGIME_SIMPLES = "simples"


def _dec(value: Any) -> Decimal:
    return Decimal(str(value))


@dataclass
class Premise:
    """Um parametro editavel com sua fonte."""

    key: str
    value: Decimal
    source: str

    def to_dict(self) -> dict[str, Any]:
        return {"key": self.key, "value": str(self.value), "source": self.source}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Premise":
        return cls(key=data["key"], value=_dec(data["value"]), source=data["source"])


@dataclass
class PremiseSet:
    """Conjunto de premissas do cenario 2027."""

    parameters: dict[str, Premise] = field(default_factory=dict)
    cenario: str = "A"
    cenario_source: str = ""

    def get(self, key: str) -> Decimal:
        return self.parameters[key].value

    def source(self, key: str) -> str:
        return self.parameters[key].source

    @property
    def cbs_efetiva(self) -> Decimal:
        return self.get("cbs_referencia") - self.get("cbs_reducao_transitoria")

    @property
    def ibs_total(self) -> Decimal:
        return self.get("ibs_estadual") + self.get("ibs_municipal")

    def pis_cofins(self, regime: str) -> tuple[Decimal, Decimal]:
        if regime == REGIME_REAL:
            return self.get("pis_real"), self.get("cofins_real")
        return self.get("pis_presumido"), self.get("cofins_presumido")

    def with_overrides(self, overrides: dict[str, Any]) -> "PremiseSet":
        """Retorna um novo conjunto com os overrides aplicados (fonte sinalizada)."""
        params = {k: Premise(k, p.value, p.source) for k, p in self.parameters.items()}
        cenario = self.cenario
        cenario_source = self.cenario_source
        for key, value in overrides.items():
            if key == "cenario_padrao":
                cenario = str(value)
                cenario_source = f"override do usuario (padrao: {self.cenario_source})"
                continue
            if key not in params:
                raise KeyError(f"premissa desconhecida: {key}")
            old = params[key]
            params[key] = Premise(
                key, _dec(value), f"override do usuario (padrao: {old.source})"
            )
        return PremiseSet(params, cenario, cenario_source)

    def to_dict(self) -> dict[str, Any]:
        return {
            "parameters": {k: p.to_dict() for k, p in self.parameters.items()},
            "cenario": self.cenario,
            "cenario_source": self.cenario_source,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PremiseSet":
        params = {k: Premise.from_dict(v) for k, v in data["parameters"].items()}
        return cls(params, data.get("cenario", "A"), data.get("cenario_source", ""))


def load_premises(
    path: str | Path | None = None, overrides: dict[str, Any] | None = None
) -> PremiseSet:
    """Carrega premissas de ``path`` (padrao: ``premises.yaml``) com overrides."""
    data = yaml.safe_load(Path(path or DEFAULT_PATH).read_text(encoding="utf-8"))
    params = {
        key: Premise(key, _dec(spec["value"]), spec["source"])
        for key, spec in data["parameters"].items()
    }
    cenario = data.get("cenario_padrao", {})
    ps = PremiseSet(params, str(cenario.get("value", "A")), cenario.get("source", ""))
    if overrides:
        ps = ps.with_overrides(overrides)
    return ps