"""
╔══════════════════════════════════════════════════════════════════╗
║  ENERGIX GLOBAL — Pipeline Principal de Dados                    ║
║  Autor  : Renan Pinheiro                                         ║
║  Versão : 1.0.0  |  2026                                         ║
╠══════════════════════════════════════════════════════════════════╣
║  Descrição:                                                       ║
║  Pipeline completo de ETL + Machine Learning que processa o      ║
║  dataset de energia renovável e gera os arquivos data.json e     ║
║  data.js (este último é o que o dashboard carrega).              ║
║                                                                   ║
║  Etapas:                                                          ║
║  1. Carregamento e validação do dataset                           ║
║  2. Limpeza e filtragem (países reais, 2000–2025)                 ║
║  3. Cálculo dos KPIs e indicadores globais                        ║
║  4. K-Means Clustering (5 clusters)                               ║
║  5. Regressão Polinomial Grau 2 + Projeção 2026–2030             ║
║  6. Serialização para data.json e data.js                        ║
║                                                                   ║
║  Uso (a partir da raiz do repositório):                           ║
║    python -m scripts.process_data                                 ║
║    python -m scripts.process_data --dataset caminho/dataset.csv  ║
║    python -m scripts.process_data --output pasta/saida           ║
╚══════════════════════════════════════════════════════════════════╝
"""

import argparse
import json
import logging
from pathlib import Path

import pandas as pd

from scripts.clustering import run_clustering
from scripts.config import (
    BIG_ECONOMIES_PT,
    CLUSTER_ORDER,
    CLUSTER_YEAR,
    CONTINENT_MAP,
    DEFAULT_DATASET,
    DEFAULT_OUTPUT,
    REQUIRED_COLS,
    YEAR_END,
    YEAR_START,
    continent_of,
    is_real_country,
)
from scripts.forecast import run_polynomial_forecast

log = logging.getLogger("energix")

# ══════════════════════════════════════════════════════════════════
#  1. CARREGAMENTO E VALIDAÇÃO
# ══════════════════════════════════════════════════════════════════

def load_dataset(path: Path) -> pd.DataFrame:
    """
    Carrega e valida o dataset CSV.

    Raises:
        FileNotFoundError — se o arquivo não existir
        ValueError        — se faltar alguma coluna obrigatória
    """
    log.info("Carregando dataset: %s", path)

    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Dataset não encontrado: {path}")

    df = pd.read_csv(path)
    log.info("Dataset carregado — shape: %s", df.shape)

    missing = [c for c in REQUIRED_COLS if c not in df.columns]
    if missing:
        raise ValueError(f"Colunas ausentes no dataset: {missing}")

    return df


# ══════════════════════════════════════════════════════════════════
#  2. FILTRAGEM — países reais + período 2000–2025
# ══════════════════════════════════════════════════════════════════

def filter_real_countries(df: pd.DataFrame) -> pd.DataFrame:
    """Mantém apenas países reais (iso_code de 3 letras) entre 2000 e 2025."""
    mask = is_real_country(df) & df["year"].between(YEAR_START, YEAR_END)
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

def count_countries(df: pd.DataFrame, year: int = CLUSTER_YEAR) -> int:
    """
    Número de países reais com participação renovável informada no ano.

    Usa 2024 por padrão porque 2025 ainda é parcial no OWID (cerca de
    metade dos países tem dado). É o mesmo universo do ranking.
    """
    mask = is_real_country(df) & (df["year"] == year)
    return int(df.loc[mask, "renewables_share_elec"].notna().sum())


def build_summary(world: pd.DataFrame, n_countries: int) -> dict:
    """Calcula os indicadores-chave do painel."""
    log.info("Calculando summary / KPIs globais…")

    def _w(year: int, col: str) -> float:
        row = world[world["year"] == year]
        return float(row[col].values[0]) if len(row) else 0.0

    ren_2000  = _w(YEAR_START, "renewables_share_elec")
    ren_2025  = _w(YEAR_END, "renewables_share_elec")
    growth_pp = ren_2025 - ren_2000
    growth_pct = round((growth_pp / ren_2000) * 100, 1) if ren_2000 else 0.0

    summary = {
        "renewables_2025": round(ren_2025, 2),
        "renewables_2000": round(ren_2000, 2),
        "solar_2025":      round(_w(YEAR_END, "solar_share_elec"), 2),
        "solar_2000":      round(_w(YEAR_START, "solar_share_elec"), 2),
        "wind_2025":       round(_w(YEAR_END, "wind_share_elec"), 2),
        "wind_2000":       round(_w(YEAR_START, "wind_share_elec"), 2),
        "fossil_2025":     round(_w(YEAR_END, "fossil_share_elec"), 2),
        "fossil_2000":     round(_w(YEAR_START, "fossil_share_elec"), 2),
        "countries":       n_countries,
        "years":           int(world["year"].nunique()),
        "growth_pct":      growth_pct,
    }

    log.info(
        "Renováveis 2000→2025: %.2f%% → %.2f%%  (Δ %+.2f pp / %+.1f%%)",
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
    w25 = world[world["year"] == YEAR_END].iloc[0]
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
            df[(df["country"] == eng) & (df["year"].between(YEAR_START, YEAR_END))]
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
    br = df[(df["country"] == "Brazil") & (df["year"] == YEAR_END)].iloc[0]
    return {
        "renewables": round(float(br["renewables_share_elec"]), 1),
        "solar":      round(float(br["solar_share_elec"]),      1),
        "wind":       round(float(br["wind_share_elec"]),       1),
        "hydro":      round(float(br["hydro_share_elec"]),      1),
    }


# ══════════════════════════════════════════════════════════════════
#  4. RANKING 2024
# ══════════════════════════════════════════════════════════════════

def build_ranking(df: pd.DataFrame, df_clust: pd.DataFrame) -> list[dict]:
    """Ranking de todos os países por participação renovável em 2024."""
    mask = is_real_country(df) & (df["year"] == CLUSTER_YEAR)
    df_rank = df[mask].dropna(subset=["renewables_share_elec"]).copy()
    df_rank["continent"] = df_rank["country"].map(continent_of)
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
#  5. FILTROS DISPONÍVEIS
# ══════════════════════════════════════════════════════════════════

def build_filters(df: pd.DataFrame, cluster_names: list[str]) -> dict:
    real = df[is_real_country(df)]
    return {
        "years":      sorted(real["year"].unique().tolist()),
        "clusters":   cluster_names,
        "continents": list(CONTINENT_MAP.keys()),
    }


# ══════════════════════════════════════════════════════════════════
#  6. SAÍDA
# ══════════════════════════════════════════════════════════════════

DATA_JS_HEADER = (
    "/* Arquivo gerado automaticamente por scripts/process_data.py.\n"
    " * Não edite manualmente — execute o pipeline para atualizar. */\n"
)


def write_outputs(data: dict, output_dir: Path) -> tuple[Path, Path]:
    """
    Grava o payload em dois formatos com o mesmo conteúdo:

    - data.json — legível, para inspeção e consumo por outras ferramentas;
    - data.js   — define window.ENERGIX_DATA e é carregado pelo dashboard
                  via <script>, o que dispensa fetch() e funciona até
                  abrindo o index.html direto do disco.
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    json_path = output_dir / "data.json"
    json_path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",  # mesmo conteúdo byte a byte em qualquer SO
    )

    js_path = output_dir / "data.js"
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    js_path.write_text(
        f"{DATA_JS_HEADER}window.ENERGIX_DATA = {payload};\n",
        encoding="utf-8",
        newline="\n",
    )
    return json_path, js_path


# ══════════════════════════════════════════════════════════════════
#  PIPELINE PRINCIPAL
# ══════════════════════════════════════════════════════════════════

def build_data(df: pd.DataFrame) -> dict:
    """Executa todas as etapas sobre o dataset e devolve o payload do dashboard."""
    # Filtrar países reais e extrair o agregado World
    df_real = filter_real_countries(df)
    world   = get_world(df)

    # KPIs e séries
    summary       = build_summary(world, count_countries(df))
    global_trend  = build_global_trend(world)
    matrix_2025   = build_matrix_2025(world)
    solar_series, wind_series = build_solar_wind_series(world)
    composition   = build_composition(world)
    annual_growth = build_annual_growth(world)
    big_economies = build_big_economies(df)
    brazil        = build_brazil_highlight(df)

    # K-Means
    log.info("Executando K-Means Clustering…")
    df_clust, cluster_profiles, scatter_data = run_clustering(df_real)

    # Regressão Polinomial
    log.info("Executando Regressão Polinomial…")
    forecast = run_polynomial_forecast(world)

    # Ranking e filtros
    ranking = build_ranking(df, df_clust)
    filters = build_filters(df, CLUSTER_ORDER)

    return {
        "global_trend":     global_trend,
        "forecast":         forecast,
        "matrix_2025":      matrix_2025,
        "solar_series":     solar_series,
        "wind_series":      wind_series,
        "big_economies":    big_economies,
        "brazil_highlight": brazil,
        "scatter_data":     scatter_data,
        "cluster_profiles": cluster_profiles,
        "cluster_metrics":  df_clust.attrs.get("metrics", {}),
        "ranking":          ranking,
        "annual_growth":    annual_growth,
        "composition":      composition,
        "filters":          filters,
        "summary":          summary,
    }


def run_pipeline(dataset_path: Path, output_dir: Path) -> dict:
    log.info("=" * 60)
    log.info("ENERGIX GLOBAL — Pipeline de Processamento de Dados")
    log.info("=" * 60)

    df   = load_dataset(dataset_path)
    data = build_data(df)

    json_path, js_path = write_outputs(data, Path(output_dir))

    log.info("=" * 60)
    for path in (json_path, js_path):
        log.info("%s salvo em: %s  (%.1f KB)", path.name, path, path.stat().st_size / 1024)
    log.info("Ranking: %d países  |  Clusters: %d países no scatter",
             len(data["ranking"]), len(data["scatter_data"]))
    log.info("Pipeline concluído com sucesso ✓")
    log.info("=" * 60)
    return data


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
        help=f"Pasta de saída para data.json e data.js (padrão: {DEFAULT_OUTPUT})",
    )
    return parser.parse_args()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(levelname)-8s  %(message)s",
        datefmt="%H:%M:%S",
    )
    args = parse_args()
    run_pipeline(args.dataset, args.output)
