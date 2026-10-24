"""
╔══════════════════════════════════════════════════════════════════╗
║  ENERGIX GLOBAL — Módulo de Clustering K-Means                   ║
║  Autor  : Renan Pinheiro  |  2026                                ║
╠══════════════════════════════════════════════════════════════════╣
║  Aplica K-Means (k=5) nos dados de geração elétrica de 2024      ║
║  e classifica os países em 5 perfis energéticos:                 ║
║                                                                  ║
║  • Hydro Leaders    — dominância hidrelétrica                    ║
║  • Wind Champions   — liderança eólica                           ║
║  • Solar Pioneers   — destaque solar                             ║
║  • Fossil Dependent — alta dependência de combustíveis fósseis   ║
║  • Mixed Renewables — mix equilibrado de renováveis              ║
║                                                                  ║
║  Uso standalone:                                                 ║
║    python -m scripts.clustering                                  ║
║    python -m scripts.clustering --year 2023 --k 6                ║
╚══════════════════════════════════════════════════════════════════╝
"""

import argparse
import json
import logging
from pathlib import Path

import pandas as pd
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler

from scripts.config import (
    CLUSTER_FEATURES,
    CLUSTER_ORDER,
    CLUSTER_YEAR,
    DEFAULT_DATASET,
    DEFAULT_OUTPUT,
    N_CLUSTERS,
    N_INIT,
    RANDOM_STATE,
    continent_of,
    is_real_country,
)

log = logging.getLogger("energix.clustering")

# Constantes compartilhadas (ver scripts/config.py)
FEATURES = CLUSTER_FEATURES

# A nomeação automática precisa de um cluster para cada perfil.
MIN_CLUSTERS = len(CLUSTER_ORDER)


# ══════════════════════════════════════════════════════════════════
#  FUNÇÃO PRINCIPAL
# ══════════════════════════════════════════════════════════════════

def run_clustering(
    df: pd.DataFrame,
    year: int = CLUSTER_YEAR,
    n_clusters: int = N_CLUSTERS,
) -> tuple[pd.DataFrame, dict, list[dict]]:
    """
    Executa K-Means nos dados de um dado ano e retorna:

    Args:
        df          — DataFrame completo do dataset
        year        — ano de referência para o clustering (padrão: 2024)
        n_clusters  — número de clusters K (padrão: 5)

    Returns:
        df_clust        — DataFrame filtrado com coluna 'cluster_name'.
                          As métricas do agrupamento ficam em
                          df_clust.attrs["metrics"].
        cluster_profiles — dict com perfis médios e top-5 por cluster
        scatter_data    — lista de dicts para o scatter plot

    Raises:
        ValueError — se n_clusters for menor que o número de perfis nomeados.
    """
    if n_clusters < MIN_CLUSTERS:
        raise ValueError(
            f"n_clusters deve ser pelo menos {MIN_CLUSTERS} para nomear os perfis "
            f"{', '.join(CLUSTER_ORDER)} (recebido: {n_clusters})."
        )

    log.info("Preparando dados para clustering — ano: %d  |  k: %d", year, n_clusters)

    # Filtrar ano e países reais
    mask = is_real_country(df) & (df["year"] == year)
    df_year = df[mask].copy()
    df_clust = df_year.dropna(subset=FEATURES).copy()

    log.info("Países disponíveis para clustering: %d", len(df_clust))

    # Normalização
    scaler = StandardScaler()
    X = scaler.fit_transform(df_clust[FEATURES])

    # K-Means
    km = KMeans(n_clusters=n_clusters, random_state=RANDOM_STATE, n_init=N_INIT)
    df_clust = df_clust.copy()
    df_clust["cluster_id"] = km.fit_predict(X)

    silhouette = float(silhouette_score(X, df_clust["cluster_id"]))
    log.info(
        "Inertia: %.2f  |  Silhouette: %.3f  |  Iterações: %d",
        km.inertia_, silhouette, km.n_iter_,
    )

    # Nomeação automática dos clusters com base nos perfis
    df_clust, cluster_name_map = _name_clusters(df_clust)
    df_clust.attrs["metrics"] = {
        "k":           n_clusters,
        "year":        year,
        "n_countries": int(len(df_clust)),
        "inertia":     round(float(km.inertia_), 2),
        "silhouette":  round(silhouette, 4),
    }

    log.info("Clusters nomeados:")
    for cid, cname in cluster_name_map.items():
        n = (df_clust["cluster_id"] == cid).sum()
        log.info("  Cluster %d → %-22s  (%d países)", cid, cname, n)

    # Perfis dos clusters
    cluster_profiles = _build_profiles(df_clust)

    # Scatter data
    scatter_data = _build_scatter(df_clust)

    return df_clust, cluster_profiles, scatter_data


# ── Helpers internos ────────────────────────────────────────────────

def _name_clusters(df_clust: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """
    Nomeia automaticamente cada cluster com base em seus perfis médios.

    Regra de nomeação (prioridade):
    1. Hydro Leaders   → maior hydro_share_elec
    2. Wind Champions  → maior wind_share_elec
    3. Fossil Dependent→ maior fossil_share_elec
    4. Solar Pioneers  → maior solar_share_elec (dos restantes)
    5. Mixed Renewables→ o que sobrar

    Com K > 5, os clusters excedentes viram "Mixed Renewables 2", "3"…,
    em ordem decrescente de participação renovável.
    """
    profiles = df_clust.groupby("cluster_id")[FEATURES].mean()

    assigned: dict[int, str] = {}

    hydro_c  = int(profiles["hydro_share_elec"].idxmax())
    assigned[hydro_c] = "Hydro Leaders"

    wind_c   = int(profiles[~profiles.index.isin(assigned)]["wind_share_elec"].idxmax())
    assigned[wind_c]  = "Wind Champions"

    fossil_c = int(profiles[~profiles.index.isin(assigned)]["fossil_share_elec"].idxmax())
    assigned[fossil_c] = "Fossil Dependent"

    solar_c  = int(profiles[~profiles.index.isin(assigned)]["solar_share_elec"].idxmax())
    assigned[solar_c]  = "Solar Pioneers"

    remaining = (
        profiles[~profiles.index.isin(assigned)]
        .sort_values("renewables_share_elec", ascending=False)
        .index
    )
    for i, cid in enumerate(remaining):
        assigned[int(cid)] = "Mixed Renewables" if i == 0 else f"Mixed Renewables {i + 1}"

    df_clust = df_clust.copy()
    df_clust["cluster_name"] = df_clust["cluster_id"].map(assigned)

    return df_clust, assigned


def _build_profiles(df_clust: pd.DataFrame) -> dict:
    """Gera o perfil médio e top-5 países de cada cluster."""
    profiles = {}
    extra = sorted(set(df_clust["cluster_name"]) - set(CLUSTER_ORDER))
    for name in [*CLUSTER_ORDER, *extra]:
        grp = df_clust[df_clust["cluster_name"] == name]
        if grp.empty:
            continue
        top5 = (
            grp.sort_values("renewables_share_elec", ascending=False)["country"]
            .head(5)
            .tolist()
        )
        profiles[name] = {
            "count":      int(len(grp)),
            "renewables": round(float(grp["renewables_share_elec"].mean()), 1),
            "solar":      round(float(grp["solar_share_elec"].mean()),      1),
            "wind":       round(float(grp["wind_share_elec"].mean()),       1),
            "hydro":      round(float(grp["hydro_share_elec"].mean()),      1),
            "fossil":     round(float(grp["fossil_share_elec"].mean()),     1),
            "top5":       top5,
        }
    return profiles


def _build_scatter(df_clust: pd.DataFrame) -> list[dict]:
    """Gera os dados do scatter plot (país, renováveis, fóssil, cluster, continente)."""
    return [
        {
            "country":    r["country"],
            "renewables": round(float(r["renewables_share_elec"]), 1),
            "fossil":     round(float(r["fossil_share_elec"]),     1),
            "cluster":    r["cluster_name"],
            "continent":  continent_of(r["country"]),
        }
        for _, r in df_clust.iterrows()
    ]


# ══════════════════════════════════════════════════════════════════
#  ENTRY POINT STANDALONE
# ══════════════════════════════════════════════════════════════════

def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Energix — K-Means Clustering")
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--year",    type=int, default=CLUSTER_YEAR,
                        help="Ano de referência para o clustering")
    parser.add_argument("--k",       type=int, default=N_CLUSTERS,
                        help="Número de clusters K (padrão: 5)")
    parser.add_argument("--output",  type=Path,
                        default=DEFAULT_OUTPUT / "clusters.json",
                        help="Arquivo JSON de saída")
    return parser.parse_args()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s  %(levelname)-8s  %(message)s",
                        datefmt="%H:%M:%S")

    args = _parse_args()

    df = pd.read_csv(args.dataset)
    df_clust, profiles, scatter = run_clustering(df, year=args.year, n_clusters=args.k)

    result = {
        "metrics":          df_clust.attrs["metrics"],
        "cluster_profiles": profiles,
        "scatter_data":     scatter,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    log.info("Resultado salvo em: %s", args.output)

    # Resumo por cluster
    print("\n──────────────────────────────────────────")
    print(f"{'Cluster':<22} {'Países':>7}  {'Renov%':>7}  {'Solar%':>6}  {'Eólica%':>7}  {'Hidro%':>6}  {'Fóssil%':>7}")
    print("──────────────────────────────────────────")
    for name, p in profiles.items():
        print(f"{name:<22} {p['count']:>7}  {p['renewables']:>7.1f}  {p['solar']:>6.1f}  {p['wind']:>7.1f}  {p['hydro']:>6.1f}  {p['fossil']:>7.1f}")
    print("──────────────────────────────────────────\n")
