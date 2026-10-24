"""
╔══════════════════════════════════════════════════════════════════╗
║  ENERGIX GLOBAL — Análise Exploratória de Dados (EDA)            ║
║  Autor  : Renan Pinheiro  |  2026                                 ║
╠══════════════════════════════════════════════════════════════════╣
║  Script de análise exploratória do dataset de energia renovável. ║
║  Gera um relatório completo no terminal com:                      ║
║                                                                   ║
║  • Inspeção geral do dataset (shape, dtypes, missing values)      ║
║  • Cobertura temporal e geográfica                                ║
║  • Estatísticas descritivas das principais variáveis              ║
║  • Indicadores globais (World aggregate)                          ║
║  • Top/Bottom países em 2024                                      ║
║  • Evolução das grandes economias                                 ║
║  • Análise do Brasil                                              ║
║  • Correlações entre variáveis                                    ║
║                                                                   ║
║  Uso:                                                             ║
║    python -m scripts.eda                                          ║
║    python -m scripts.eda --dataset caminho/dataset.csv            ║
╚══════════════════════════════════════════════════════════════════╝
"""

import argparse
from pathlib import Path

import pandas as pd

from scripts.config import (
    BIG_ECONOMIES_PT,
    CLUSTER_YEAR,
    DEFAULT_DATASET,
    YEAR_END,
    YEAR_START,
    is_real_country,
)

SEP = "=" * 70
SEP2 = "─" * 70

# ── Principais colunas de interesse ────────────────────────────────
KEY_COLS = [
    "renewables_share_elec",
    "solar_share_elec",
    "wind_share_elec",
    "hydro_share_elec",
    "nuclear_share_elec",
    "fossil_share_elec",
    "electricity_generation",
]


# ══════════════════════════════════════════════════════════════════
#  FUNÇÕES DE ANÁLISE
# ══════════════════════════════════════════════════════════════════

def section(title: str) -> None:
    print(f"\n{SEP}")
    print(f"  {title}")
    print(SEP)


def _load(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    print(f"\nArquivo carregado: {path}")
    print(f"Shape: {df.shape[0]:,} linhas × {df.shape[1]} colunas")
    return df


def inspect_general(df: pd.DataFrame) -> None:
    section("1. INSPEÇÃO GERAL")

    print(f"\nColunas ({len(df.columns)}):")
    for col in df.columns:
        miss = df[col].isna().sum()
        pct  = miss / len(df) * 100
        print(f"  {col:<40}  dtype={str(df[col].dtype):<10}  nulos={miss:>5} ({pct:5.1f}%)")

    print("\nPrimeiros registros:")
    print(df.head(3).to_string())


def inspect_coverage(df: pd.DataFrame) -> None:
    section("2. COBERTURA TEMPORAL E GEOGRÁFICA")

    real = df[is_real_country(df)]

    print(f"\nTotal de entradas:       {len(df):>6,}")
    print(f"Países/regiões únicos:   {df['country'].nunique():>6,}")
    print(f"Países reais (ISO-3):    {real['country'].nunique():>6,}")
    print(f"Faixa temporal:          {df['year'].min()} – {df['year'].max()}")
    print(f"Anos disponíveis:        {df['year'].nunique()}")
    print("\nEntidades não-países (regiões/agregados):")
    non_real = df[~is_real_country(df)]["country"].unique()
    for ent in sorted(non_real)[:20]:
        print(f"  {ent}")
    if len(non_real) > 20:
        print(f"  … e mais {len(non_real) - 20} outras")


def inspect_stats(df: pd.DataFrame) -> None:
    section("3. ESTATÍSTICAS DESCRITIVAS — PAÍSES REAIS (2000–2025)")

    real = df[is_real_country(df) & df["year"].between(YEAR_START, YEAR_END)]

    stats = real[KEY_COLS].describe().round(2)
    print(f"\n{stats.to_string()}")


def inspect_world(df: pd.DataFrame) -> None:
    section("4. INDICADORES GLOBAIS (World)")

    world = df[df["country"] == "World"].sort_values("year")

    print(
        f"\n{'Ano':<6} {'Renov%':>8} {'Solar%':>8} {'Eólica%':>9} "
        f"{'Hidro%':>8} {'Nucl%':>7} {'Fóssil%':>9}"
    )
    print(SEP2)
    for _, r in world.iterrows():
        print(
            f"{int(r['year']):<6}"
            f"{r['renewables_share_elec']:>8.2f}"
            f"{r['solar_share_elec']:>8.3f}"
            f"{r['wind_share_elec']:>9.3f}"
            f"{r['hydro_share_elec']:>8.2f}"
            f"{r['nuclear_share_elec']:>7.2f}"
            f"{r['fossil_share_elec']:>9.2f}"
        )

    # Crescimento
    ren_00 = world[world["year"] == YEAR_START]["renewables_share_elec"].values[0]
    ren_25 = world[world["year"] == YEAR_END]["renewables_share_elec"].values[0]
    print("\nCrescimento renovável 2000→2025:")
    delta_pp  = ren_25 - ren_00
    delta_pct = delta_pp / ren_00 * 100
    print(f"  {ren_00:.2f}% → {ren_25:.2f}%  (Δ {delta_pp:+.2f} pp / {delta_pct:+.1f}%)")


def inspect_ranking(df: pd.DataFrame) -> None:
    section("5. RANKING 2024 — TOP 15 e BOTTOM 10")

    mask  = is_real_country(df) & (df["year"] == CLUSTER_YEAR)
    rank  = df[mask].dropna(subset=["renewables_share_elec"])
    rank  = rank.sort_values("renewables_share_elec", ascending=False).reset_index(drop=True)

    print(f"\nTotal de países com dados em {CLUSTER_YEAR}: {len(rank)}")
    print(f"\n{'Pos':>4}  {'País':<35}  {'Renov%':>8}")
    print(SEP2)
    for i, row in rank.head(15).iterrows():
        print(f"{i+1:>4}  {row['country']:<35}  {row['renewables_share_elec']:>8.2f}%")

    print(f"\n{'...(bottom 10)':}")
    for i, row in rank.tail(10).iterrows():
        print(f"{i+1:>4}  {row['country']:<35}  {row['renewables_share_elec']:>8.2f}%")


def inspect_big_economies(df: pd.DataFrame) -> None:
    section("6. GRANDES ECONOMIAS — 2000 a 2025")

    countries = list(BIG_ECONOMIES_PT)
    data = df[df["country"].isin(countries) & df["year"].between(YEAR_START, YEAR_END)]
    pivot = (
        data.pivot(index="year", columns="country", values="renewables_share_elec")
        .round(1)
    )
    print(f"\n{pivot.to_string()}")


def inspect_brazil(df: pd.DataFrame) -> None:
    section("7. BRASIL — SÉRIE HISTÓRICA COMPLETA")

    br = df[df["country"] == "Brazil"].sort_values("year")
    cols = ["year", "renewables_share_elec", "solar_share_elec",
            "wind_share_elec", "hydro_share_elec", "fossil_share_elec"]
    print(f"\n{br[cols].to_string(index=False)}")


def inspect_correlations(df: pd.DataFrame) -> None:
    section("8. MATRIZ DE CORRELAÇÃO — PAÍSES REAIS 2024")

    mask = is_real_country(df) & (df["year"] == CLUSTER_YEAR)
    corr = df[mask][KEY_COLS].corr().round(3)
    print(f"\n{corr.to_string()}")


# ══════════════════════════════════════════════════════════════════
#  PIPELINE EDA
# ══════════════════════════════════════════════════════════════════

def run_eda(path: Path) -> None:
    print(f"\n{'#'*70}")
    print("  ENERGIX GLOBAL — Análise Exploratória de Dados (EDA)")
    print(f"{'#'*70}")

    df = _load(path)
    inspect_general(df)
    inspect_coverage(df)
    inspect_stats(df)
    inspect_world(df)
    inspect_ranking(df)
    inspect_big_economies(df)
    inspect_brazil(df)
    inspect_correlations(df)

    print(f"\n{SEP}")
    print("  EDA concluída ✓")
    print(SEP)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Energix — EDA do dataset de energia renovável")
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET,
                        help=f"Caminho para o CSV (padrão: {DEFAULT_DATASET})")
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    run_eda(args.dataset)
