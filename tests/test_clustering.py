import pytest

from scripts.clustering import run_clustering
from scripts.config import CLUSTER_ORDER


@pytest.fixture(scope="module")
def clustering(dataset):
    return run_clustering(dataset)


def test_todos_os_perfis_aparecem(clustering):
    df_clust, profiles, _ = clustering

    assert list(profiles) == CLUSTER_ORDER
    assert set(df_clust["cluster_name"]) == set(CLUSTER_ORDER)


def test_contagens_batem_com_o_scatter(clustering):
    df_clust, profiles, scatter = clustering

    assert sum(p["count"] for p in profiles.values()) == len(df_clust) == len(scatter)
    assert df_clust.attrs["metrics"]["n_countries"] == len(df_clust)


def test_resultado_e_deterministico(dataset, clustering):
    df_clust, _, _ = clustering
    df_again, _, _ = run_clustering(dataset)

    first = df_clust.set_index("country")["cluster_name"].sort_index()
    second = df_again.set_index("country")["cluster_name"].sort_index()
    assert first.equals(second)


def test_metricas_sao_registradas(clustering):
    metrics = clustering[0].attrs["metrics"]

    assert metrics["k"] == 5
    assert metrics["year"] == 2024
    assert -1 <= metrics["silhouette"] <= 1
    assert metrics["inertia"] > 0


def test_k_menor_que_cinco_lanca_erro(dataset):
    with pytest.raises(ValueError, match="n_clusters"):
        run_clustering(dataset, n_clusters=4)


def test_k_maior_que_cinco_nomeia_clusters_extras(dataset):
    _, profiles, _ = run_clustering(dataset, n_clusters=6)

    assert list(profiles)[:5] == CLUSTER_ORDER
    assert "Mixed Renewables 2" in profiles
