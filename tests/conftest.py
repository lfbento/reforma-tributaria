"""Configuracao compartilhada da suite de testes."""

import json
from pathlib import Path

import pytest

from reforma_tributaria import pipeline
from reforma_tributaria.premises import load_premises

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def petrobras_data():
    return json.loads((FIXTURES / "petrobras.json").read_text(encoding="utf-8"))


@pytest.fixture
def premises():
    return load_premises()


@pytest.fixture
def analysis(petrobras_data, premises):
    return pipeline.analyze(petrobras_data, premises)