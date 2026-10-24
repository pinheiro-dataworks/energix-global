"""
╔══════════════════════════════════════════════════════════════════╗
║  ENERGIX GLOBAL — Módulo de Regressão Polinomial & Forecast      ║
║  Autor  : Renan Pinheiro  |  2026                                 ║
╠══════════════════════════════════════════════════════════════════╣
║  Aplica Regressão Polinomial de Grau 2 sobre a série histórica   ║
║  de participação renovável global (2000–2025) e projeta          ║
║  os valores até 2030.                                             ║
║                                                                   ║
║  Modelo:                                                          ║
║    ŷ = β₀ + β₁·t + β₂·t²,  com t = ano − 2000                    ║
║    Estimador: OLS via scikit-learn                                ║
║    Features:  PolynomialFeatures(degree=2, include_bias=True)    ║
║                                                                   ║
║  Métricas reportadas:                                             ║
║    R²  — coeficiente de determinação                              ║
║    MAE — erro absoluto médio                                      ║
║    RMSE — raiz do erro quadrático médio                           ║
║                                                                   ║
║  Uso standalone:                                                  ║
║    python -m scripts.forecast                                     ║
║    python -m scripts.forecast --degree 3 --horizon 2035          ║
╚══════════════════════════════════════════════════════════════════╝
"""

import argparse
import json
import logging
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.preprocessing import PolynomialFeatures

from scripts.config import (
    DEFAULT_DATASET,
    DEFAULT_OUTPUT,
    FORECAST_YEAR_END,
    POLY_DEGREE,
    TARGET_COL,
    YEAR_START,
)

log = logging.getLogger("energix.forecast")

# O polinômio é ajustado sobre t = ano − TIME_OFFSET. Com o ano bruto,
# ano² passa de 4 milhões e a matriz de features fica mal condicionada:
# os coeficientes e o próprio R² passam a depender da versão do numpy/BLAS.
TIME_OFFSET = YEAR_START


# ══════════════════════════════════════════════════════════════════
#  FUNÇÃO PRINCIPAL
# ══════════════════════════════════════════════════════════════════

def run_polynomial_forecast(
    world: pd.DataFrame,
    degree: int = POLY_DEGREE,
    forecast_end: int = FORECAST_YEAR_END,
) -> dict:
    """
    Ajusta Regressão Polinomial sobre a série World (2000–2025) e
    projeta até `forecast_end`.

    Args:
        world        — DataFrame filtrado para country='World'
        degree       — grau do polinômio (padrão: 2)
        forecast_end — último ano da projeção (padrão: 2030)

    Returns:
        dict com:
            r2               — coeficiente de determinação
            mae              — erro absoluto médio (histórico)
            rmse             — raiz do erro quadrático médio (histórico)
            time_offset      — ano usado como origem do eixo (t = ano − time_offset)
            coefficients     — coeficientes [β₀, β₁, β₂, …] em função de t
            historical_fitted— valores ajustados para os anos históricos
            forecast         — projeção para cada ano futuro
    """
    # Preparar dados
    series = world.sort_values("year").dropna(subset=[TARGET_COL])
    years  = series["year"].values.reshape(-1, 1)
    y      = series[TARGET_COL].values

    log.info(
        "Regressão Polinomial Grau %d | anos: %d–%d | n=%d",
        degree, int(years.min()), int(years.max()), len(y),
    )

    # Transformação polinomial sobre o eixo temporal centralizado
    t      = years - TIME_OFFSET
    poly   = PolynomialFeatures(degree=degree, include_bias=True)
    X_poly = poly.fit_transform(t)

    # Ajuste OLS
    model  = LinearRegression(fit_intercept=False)
    model.fit(X_poly, y)

    # Métricas históricas
    y_pred = model.predict(X_poly)
    r2     = model.score(X_poly, y)
    mae    = mean_absolute_error(y, y_pred)
    rmse   = float(np.sqrt(mean_squared_error(y, y_pred)))

    log.info("R²=%.4f  |  MAE=%.4f  |  RMSE=%.4f", r2, mae, rmse)

    # Valores ajustados históricos
    historical_fitted = [
        {"year": int(yr), "fitted": round(float(f), 3)}
        for yr, f in zip(series["year"].values, y_pred)
    ]

    # Projeção futura (a partir do ano seguinte ao último observado)
    last_year    = int(years.max())
    future_years = np.arange(last_year + 1, forecast_end + 1).reshape(-1, 1)
    X_fut        = poly.transform(future_years - TIME_OFFSET)
    y_fut        = model.predict(X_fut)

    prev_val = float(y[-1])
    forecast_list = []
    for yr, val in zip(future_years.flatten(), y_fut):
        forecast_list.append({
            "year":  int(yr),
            "value": round(float(val), 2),
            "delta": round(float(val) - prev_val, 2),
        })
        prev_val = float(val)

    log.info("Projeção %d–%d:", last_year + 1, forecast_end)
    for row in forecast_list:
        log.info("  %d → %.2f%%  (Δ %+.2f pp)", row["year"], row["value"], row["delta"])

    return {
        "r2":               round(r2,   4),
        "mae":              round(mae,  4),
        "rmse":             round(rmse, 4),
        "degree":           degree,
        "time_offset":      TIME_OFFSET,
        "coefficients":     [round(float(c), 6) for c in model.coef_],
        "historical_fitted": historical_fitted,
        "forecast":         [{"year": r["year"], "value": r["value"]} for r in forecast_list],
    }


# ══════════════════════════════════════════════════════════════════
#  ENTRY POINT STANDALONE
# ══════════════════════════════════════════════════════════════════

def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Energix — Regressão Polinomial & Forecast")
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--degree",  type=int, default=POLY_DEGREE,
                        help=f"Grau do polinômio (padrão: {POLY_DEGREE})")
    parser.add_argument("--horizon", type=int, default=FORECAST_YEAR_END,
                        help=f"Último ano da projeção (padrão: {FORECAST_YEAR_END})")
    parser.add_argument("--output",  type=Path,
                        default=DEFAULT_OUTPUT / "forecast.json")
    return parser.parse_args()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s  %(levelname)-8s  %(message)s",
                        datefmt="%H:%M:%S")

    args = _parse_args()

    df    = pd.read_csv(args.dataset)
    world = df[df["country"] == "World"].sort_values("year")

    result = run_polynomial_forecast(world, degree=args.degree, forecast_end=args.horizon)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    log.info("Resultado salvo em: %s", args.output)

    print("\n──────────────────────────────────────────")
    print(f"  Regressão Polinomial Grau {result['degree']}")
    print(f"  R²   = {result['r2']}")
    print(f"  MAE  = {result['mae']}")
    print(f"  RMSE = {result['rmse']}")
    print("\n  Projeção:")
    for row in result["forecast"]:
        print(f"    {row['year']} → {row['value']:.2f}%")
    print("──────────────────────────────────────────\n")
