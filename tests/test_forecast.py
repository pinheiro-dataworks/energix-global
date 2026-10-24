import numpy as np
import pytest

from scripts.config import BACKTEST_YEARS, TARGET_COL
from scripts.forecast import run_polynomial_forecast, temporal_backtest


def test_recupera_coeficientes_de_serie_quadratica(quadratic_world):
    result = run_polynomial_forecast(quadratic_world)

    assert result["time_offset"] == 2000
    np.testing.assert_allclose(result["coefficients"], [20, 0.1, 0.02], atol=1e-6)
    assert result["r2"] == pytest.approx(1.0)
    assert result["mae"] == pytest.approx(0.0, abs=1e-6)


def test_horizonte_comeca_no_ano_seguinte_ao_ultimo_observado(quadratic_world):
    result = run_polynomial_forecast(quadratic_world, forecast_end=2030)
    assert [row["year"] for row in result["forecast"]] == [2026, 2027, 2028, 2029, 2030]

    result = run_polynomial_forecast(quadratic_world, forecast_end=2035)
    assert result["forecast"][-1]["year"] == 2035


def test_projecao_no_dataset_real_e_estavel(world):
    result = run_polynomial_forecast(world)
    last_observed = float(world[TARGET_COL].iloc[-1])

    assert result["r2"] > 0.99
    # A tendência de alta precisa continuar no primeiro ano projetado.
    assert result["forecast"][0]["value"] > last_observed
    # β₀ próximo do valor de 2000 indica que o eixo está centralizado.
    assert result["coefficients"][0] == pytest.approx(world[TARGET_COL].iloc[0], abs=1.5)


def test_backtest_separa_treino_e_teste(quadratic_world):
    bt = temporal_backtest(quadratic_world["year"], quadratic_world[TARGET_COL])

    assert bt["train_end"] == 2020
    assert bt["test_years"] == [2021, 2022, 2023, 2024, 2025]
    assert len(bt["predicted"]) == len(bt["actual"]) == BACKTEST_YEARS
    assert bt["mae"] == pytest.approx(0.0, abs=1e-6)


def test_backtest_entra_no_resultado_do_forecast(world):
    bt = run_polynomial_forecast(world)["backtest"]

    assert bt["train_end"] == 2020
    # Fora da amostra o erro é maior, mas tem que continuar pequeno.
    assert 0 < bt["mae"] < 2.0


@pytest.mark.parametrize("holdout", [0, 24])
def test_backtest_rejeita_serie_curta_ou_holdout_invalido(quadratic_world, holdout):
    with pytest.raises(ValueError):
        temporal_backtest(
            quadratic_world["year"], quadratic_world[TARGET_COL], holdout=holdout
        )
