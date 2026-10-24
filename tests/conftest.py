"""Fixtures compartilhadas pelos testes do pipeline."""

import numpy as np
import pandas as pd
import pytest

from scripts.config import DEFAULT_DATASET, TARGET_COL


@pytest.fixture(scope="session")
def dataset() -> pd.DataFrame:
    """Dataset real do OWID, carregado uma vez por sessão."""
    return pd.read_csv(DEFAULT_DATASET)


@pytest.fixture(scope="session")
def world(dataset: pd.DataFrame) -> pd.DataFrame:
    """Série agregada World, em ordem cronológica."""
    return dataset[dataset["country"] == "World"].sort_values("year").reset_index(drop=True)


@pytest.fixture
def quadratic_world() -> pd.DataFrame:
    """
    Série sintética sem ruído: y = 20 + 0.1·t + 0.02·t², com t = ano − 2000.

    Como o modelo é exatamente um polinômio de grau 2, a regressão tem que
    recuperar os coeficientes e o erro tem que ser zero.
    """
    years = np.arange(2000, 2026)
    t = years - 2000
    return pd.DataFrame({"year": years, TARGET_COL: 20 + 0.1 * t + 0.02 * t**2})
