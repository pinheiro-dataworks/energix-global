"""
╔══════════════════════════════════════════════════════════════════╗
║  ENERGIX GLOBAL — Pipeline Principal de Dados                    ║
║  Autor  : Renan Pinheiro                                         ║
║  Versão : 1.0.0  |  2026                                         ║
╠══════════════════════════════════════════════════════════════════╣
║  Descrição:                                                       ║
║  Pipeline completo de ETL + Machine Learning que processa o      ║
║  dataset de energia renovável e gera o arquivo data.json         ║
║  consumido pelo dashboard.                                        ║
║                                                                   ║
║  Etapas:                                                          ║
║  1. Carregamento e validação do dataset                           ║
║  2. Limpeza e filtragem (países reais, 2000–2025)                 ║
║  3. Cálculo dos KPIs e indicadores globais                        ║
║  4. K-Means Clustering (5 clusters)                               ║
║  5. Regressão Polinomial Grau 2 + Projeção 2026–2030             ║
║  6. Serialização para JSON                                        ║
║                                                                   ║
║  Uso:                                                             ║
║    python scripts/process_data.py                                 ║
║    python scripts/process_data.py --dataset caminho/dataset.csv  ║
║    python scripts/process_data.py --output pasta/saida           ║
╚══════════════════════════════════════════════════════════════════╝
"""

import argparse
import json
import logging
import os
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import PolynomialFeatures, StandardScaler

from scripts.config import (
    BIG_ECONOMIES_PT,
    CLUSTER_ORDER,
    CONTINENT_MAP,
    COUNTRY_TO_CONTINENT,
    DEFAULT_DATASET,
    DEFAULT_OUTPUT,
)

warnings.filterwarnings("ignore")

# ── Logging ────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("energix")

# ══════════════════════════════════════════════════════════════════
#  1. CARREGAMENTO E VALIDAÇÃO
# ══════════════════════════════════════════════════════════════════

def load_dataset(path: Path) -> pd.DataFrame:
    """Carrega e valida o dataset CSV."""
    log.info("Carregando dataset: %s", path)

    if not path.exists():
        log.error("Arquivo não encontrado: %s", path)
        sys.exit(1)

    df = pd.read_csv(path)
    log.info("Dataset carregado — shape: %s", df.shape)

    required_cols = [
        "country", "year", "iso_code",
        "renewables_share_elec", "solar_share_elec",
        "wind_share_elec", "hydro_share_elec",
        "nuclear_share_elec", "fossil_share_elec",
    ]
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        log.error("Colunas ausentes no dataset: %s", missing)
        sys.exit(1)

    return df


# ══════════════════════════════════════════════════════════════════
#  2. FILTRAGEM — países reais + período 2000–2025
# ══════════════════════════════════════════════════════════════════

def filter_real_countries(df: pd.DataFrame) -> pd.DataFrame:
    """Mantém apenas países reais (iso_code de 3 letras) entre 2000 e 2025."""
    mask = (
        df["iso_code"].notna()
        & (df["iso_code"].str.len() == 3)
        & (df["year"] >= 2000)
        & (df["year"] <= 2025)
    )
    df_real = df[mask].copy()
    log.info(
        "Países reais filtrados: %d registros | %d países únicos",
        len(df_real),
        df_real["country"].nunique(),
    )
    return df_real


def get_world(df: pd.DataFrame) -> pd.DataFrame:
    """Retorna os dados agregados do World (proxy global)."""
    world = df[df["country"] == "World"].sort_values("year").copy()
    log.info("Dados World: %d anos (%d–%d)", len(world), world["year"].min(), world["year"].max())
    return world


# ══════════════════════════════════════════════════════════════════
#  3. INDICADORES E KPIs GLOBAIS
# ══════════════════════════════════════════════════════════════════

def build_summary(world: pd.DataFrame) -> dict:
    """Calcula os indicadores-chave do painel."""
    log.info("Calculando summary / KPIs globais…")

    def _w(year: int, col: str) -> float:
        row = world[world["year"] == year]
        return float(row[col].values[0]) if len(row) else 0.0

    ren_2000  = _w(2000, "renewables_share_elec")
    ren_2025  = _w(2025, "renewables_share_elec")
    growth_pp = ren_2025 - ren_2000
    growth_pct = round((growth_pp / ren_2000) * 100, 1) if ren_2000 else 0.0

    summary = {
        "renewables_2025": round(ren_2025, 2),
        "renewables_2000": round(ren_2000, 2),
        "solar_2025":      round(_w(2025, "solar_share_elec"), 2),
        "solar_2000":      round(_w(2000, "solar_share_elec"), 2),
        "wind_2025":       round(_w(2025, "wind_share_elec"), 2),
        "wind_2000":       round(_w(2000, "wind_share_elec"), 2),
        "fossil_2025":     round(_w(2025, "fossil_share_elec"), 2),
        "fossil_2000":     round(_w(2000, "fossil_share_elec"), 2),
        "countries":       190,
        "years":           26,
        "growth_pct":      growth_pct,
    }

    log.info(
        "Renováveis 2000→2025: %.2f%% → %.2f%%  (Δ %.2f pp / +%.1f%%)",
        ren_2000, ren_2025, growth_pp, growth_pct,
    )
    return summary


def build_global_trend(world: pd.DataFrame) -> list[dict]:
    """Série histórica das principais fontes (World, 2000–2025)."""
    cols = [
        "year", "renewables_share_elec", "solar_share_elec",
        "wind_share_elec", "hydro_share_elec",
        "nuclear_share_elec", "fossil_share_elec",
    ]
    trend = []
    for _, row in world[cols].iterrows():
        trend.append({k: (int(v) if k == "year" else round(float(v), 3)) for k, v in row.items()})
    return trend


def build_matrix_2025(world: pd.DataFrame) -> dict:
    """Composição da matriz elétrica global em 2025."""
    w25 = world[world["year"] == 2025].iloc[0]
    other = (
        float(w25["renewables_share_elec"])
        - float(w25["solar_share_elec"])
        - float(w25["wind_share_elec"])
        - float(w25["hydro_share_elec"])
    )
    return {
        "fossil":  round(float(w25["fossil_share_elec"]),  2),
        "hydro":   round(float(w25["hydro_share_elec"]),   2),
        "nuclear": round(float(w25["nuclear_share_elec"]), 2),
        "solar":   round(float(w25["solar_share_elec"]),   2),
        "wind":    round(float(w25["wind_share_elec"]),    2),
        "other":   round(other, 2),
    }


def build_solar_wind_series(world: pd.DataFrame) -> tuple[list[dict], list[dict]]:
    """Séries temporais de participação solar e eólica globais."""
    solar = [{"year": int(r["year"]), "value": round(float(r["solar_share_elec"]), 3)}
             for _, r in world.iterrows()]
    wind  = [{"year": int(r["year"]), "value": round(float(r["wind_share_elec"]),  3)}
             for _, r in world.iterrows()]
    return solar, wind


def build_composition(world: pd.DataFrame) -> list[dict]:
    """Composição empilhada da matriz elétrica global por ano."""
    result = []
    for _, r in world.iterrows():
        other = (
            float(r["renewables_share_elec"])
            - float(r["solar_share_elec"])
            - float(r["wind_share_elec"])
            - float(r["hydro_share_elec"])
        )
        result.append({
            "year":       int(r["year"]),
            "solar":      round(float(r["solar_share_elec"]),   2),
            "wind":       round(float(r["wind_share_elec"]),    2),
            "hydro":      round(float(r["hydro_share_elec"]),   2),
            "nuclear":    round(float(r["nuclear_share_elec"]), 2),
            "fossil":     round(float(r["fossil_share_elec"]),  2),
            "other_renew": round(other, 2),
        })
    return result


def build_annual_growth(world: pd.DataFrame) -> list[dict]:
    """Variação anual (YoY) da participação renovável global."""
    ws = world.sort_values("year").copy()
    ws["yoy"] = ws["renewables_share_elec"].diff()
    return [
        {"year": int(r["year"]), "yoy": round(float(r["yoy"]), 3)}
        for _, r in ws[ws["year"] >= 2001].dropna(subset=["yoy"]).iterrows()
    ]


def build_big_economies(df: pd.DataFrame) -> dict:
    """Série histórica das grandes economias (renováveis % elétrica)."""
    result = {}
    for eng, pt in BIG_ECONOMIES_PT.items():
        data = (
            df[(df["country"] == eng) & (df["year"].between(2000, 2025))]
            [["year", "renewables_share_elec"]]
            .dropna()
        )
        result[pt] = [
            {"year": int(r["year"]), "value": round(float(r["renewables_share_elec"]), 2)}
            for _, r in data.iterrows()
        ]
    return result


def build_brazil_highlight(df: pd.DataFrame) -> dict:
    """Indicadores do Brasil em 2025."""
    br = df[(df["country"] == "Brazil") & (df["year"] == 2025)].iloc[0]
    return {
        "renewables": round(float(br["renewables_share_elec"]), 1),
        "solar":      round(float(br["solar_share_elec"]),      1),
        "wind":       round(float(br["wind_share_elec"]),       1),
        "hydro":      round(float(br["hydro_share_elec"]),      1),
    }


# ══════════════════════════════════════════════════════════════════
#  4. K-MEANS CLUSTERING
# ══════════════════════════════════════════════════════════════════

def run_kmeans(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """
    Aplica K-Means (k=5) nos dados de 2024.

    Features: renewables, solar, wind, hydro, fossil share_elec.
    Normalização: StandardScaler.

    Retorna:
        df_clust   — DataFrame com coluna 'cluster_name'
        profiles   — dicionário com perfis dos clusters
    """
    from scripts.clustering import run_clustering  # importa módulo dedicado
    return run_clustering(df)


# ══════════════════════════════════════════════════════════════════
#  5. REGRESSÃO POLINOMIAL + FORECAST
# ══════════════════════════════════════════════════════════════════

def run_forecast(world: pd.DataFrame) -> dict:
    """
    Regressão Polinomial de Grau 2 sobre a série histórica do World.
    Projeta 2026–2030.

    Retorna dict com r2, fitted histórico e previsões.
    """
    from scripts.forecast import run_polynomial_forecast  # importa módulo dedicado
    return run_polynomial_forecast(world)


# ══════════════════════════════════════════════════════════════════
#  6. RANKING 2024
# ══════════════════════════════════════════════════════════════════

def build_ranking(df: pd.DataFrame, df_clust: pd.DataFrame) -> list[dict]:
    """Ranking de todos os países por participação renovável em 2024."""
    mask = (
        df["iso_code"].notna()
        & (df["iso_code"].str.len() == 3)
        & (df["year"] == 2024)
    )
    df_rank = df[mask].dropna(subset=["renewables_share_elec"]).copy()
    df_rank["continent"]    = df_rank["country"].map(COUNTRY_TO_CONTINENT).fillna("Outros")
    df_rank = df_rank.merge(
        df_clust[["country", "cluster_name"]], on="country", how="left"
    )
    df_rank["cluster_name"] = df_rank["cluster_name"].fillna("Outros")
    df_rank = df_rank.sort_values("renewables_share_elec", ascending=False).reset_index(drop=True)
    df_rank["rank"] = df_rank.index + 1

    log.info("Ranking gerado: %d países", len(df_rank))
    return [
        {
            "rank":      int(r["rank"]),
            "country":   r["country"],
            "value":     round(float(r["renewables_share_elec"]), 2),
            "continent": r["continent"],
            "cluster":   r["cluster_name"],
        }
        for _, r in df_rank.iterrows()
    ]


# ══════════════════════════════════════════════════════════════════
#  7. FILTROS DISPONÍVEIS
# ══════════════════════════════════════════════════════════════════

def build_filters(df: pd.DataFrame, cluster_names: list[str]) -> dict:
    real = df[df["iso_code"].notna() & (df["iso_code"].str.len() == 3)]
    return {
        "years":      sorted(real["year"].unique().tolist()),
        "clusters":   cluster_names,
        "continents": list(CONTINENT_MAP.keys()),
    }


# ══════════════════════════════════════════════════════════════════
#  PIPELINE PRINCIPAL
# ══════════════════════════════════════════════════════════════════

def run_pipeline(dataset_path: Path, output_dir: Path) -> None:
    log.info("=" * 60)
    log.info("ENERGIX GLOBAL — Pipeline de Processamento de Dados")
    log.info("=" * 60)

    # 1. Carregar
    df = load_dataset(dataset_path)

    # 2. Filtrar países reais
    df_real = filter_real_countries(df)

    # 3. Dados World
    world = get_world(df)

    # 4. KPIs e séries
    summary      = build_summary(world)
    global_trend = build_global_trend(world)
    matrix_2025  = build_matrix_2025(world)
    solar_series, wind_series = build_solar_wind_series(world)
    composition  = build_composition(world)
    annual_growth = build_annual_growth(world)
    big_economies = build_big_economies(df)
    brazil        = build_brazil_highlight(df)

    # 5. K-Means
    log.info("Executando K-Means Clustering…")
    from scripts.clustering import run_clustering
    df_clust, cluster_profiles, scatter_data = run_clustering(df_real)

    # 6. Regressão Polinomial
    log.info("Executando Regressão Polinomial…")
    from scripts.forecast import run_polynomial_forecast
    forecast = run_polynomial_forecast(world)

    # 7. Ranking
    ranking = build_ranking(df, df_clust)

    # 8. Filtros
    filters = build_filters(df, CLUSTER_ORDER)

    # 9. Montar JSON
    data = {
        "global_trend":    global_trend,
        "forecast":        forecast,
        "matrix_2025":     matrix_2025,
        "solar_series":    solar_series,
        "wind_series":     wind_series,
        "big_economies":   big_economies,
        "brazil_highlight": brazil,
        "scatter_data":    scatter_data,
        "cluster_profiles": cluster_profiles,
        "ranking":         ranking,
        "annual_growth":   annual_growth,
        "composition":     composition,
        "filters":         filters,
        "summary":         summary,
    }

    # 10. Salvar
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "data.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    size_kb = output_path.stat().st_size / 1024
    log.info("=" * 60)
    log.info("data.json salvo em: %s  (%.1f KB)", output_path, size_kb)
    log.info("Ranking: %d países  |  Clusters: %d países no scatter",
             len(data["ranking"]), len(data["scatter_data"]))
    log.info("Pipeline concluído com sucesso ✓")
    log.info("=" * 60)


# ══════════════════════════════════════════════════════════════════
#  ENTRY POINT
# ══════════════════════════════════════════════════════════════════

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Energix Global — Pipeline de processamento de dados",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--dataset", type=Path, default=DEFAULT_DATASET,
        help=f"Caminho para o CSV (padrão: {DEFAULT_DATASET})",
    )
    parser.add_argument(
        "--output", type=Path, default=DEFAULT_OUTPUT,
        help=f"Pasta de saída para data.json (padrão: {DEFAULT_OUTPUT})",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    run_pipeline(args.dataset, args.output)
