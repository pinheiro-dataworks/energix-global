import json

import pandas as pd
import pytest

from scripts.config import CONTINENT_MAP, DEFAULT_CONTINENT, DEFAULT_OUTPUT, REQUIRED_COLS
from scripts.process_data import (
    DATA_JS_HEADER,
    build_data,
    filter_real_countries,
    load_dataset,
    write_outputs,
)


@pytest.fixture(scope="module")
def data(dataset):
    return build_data(dataset)


def _read_data_js(path):
    text = path.read_text(encoding="utf-8")
    assert text.startswith(DATA_JS_HEADER)
    payload = text[len(DATA_JS_HEADER):].strip()
    assert payload.startswith("window.ENERGIX_DATA = ") and payload.endswith(";")
    return json.loads(payload[len("window.ENERGIX_DATA = "):-1])


# ── Carregamento ───────────────────────────────────────────────────

def test_load_dataset_arquivo_inexistente(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_dataset(tmp_path / "nao_existe.csv")


def test_load_dataset_coluna_ausente(tmp_path):
    csv = tmp_path / "incompleto.csv"
    pd.DataFrame(columns=REQUIRED_COLS[:-1]).to_csv(csv, index=False)

    with pytest.raises(ValueError, match=REQUIRED_COLS[-1]):
        load_dataset(csv)


def test_filtro_remove_agregados(dataset):
    real = filter_real_countries(dataset)

    assert "World" not in set(real["country"])
    assert real["iso_code"].str.len().eq(3).all()
    assert real["year"].between(2000, 2025).all()


# ── Conteúdo do payload ────────────────────────────────────────────

def test_summary_vem_do_dataset(data):
    summary = data["summary"]

    assert summary["countries"] == len(data["ranking"])
    assert summary["years"] == len(data["global_trend"])


def test_nenhum_pais_do_ranking_fica_sem_continente(data):
    sem_continente = [r["country"] for r in data["ranking"] if r["continent"] == DEFAULT_CONTINENT]
    assert sem_continente == []


def test_nenhum_pais_em_dois_continentes():
    paises = [c for countries in CONTINENT_MAP.values() for c in countries]
    duplicados = {c for c in paises if paises.count(c) > 1}
    assert duplicados == set()


# ── Artefatos ──────────────────────────────────────────────────────

def test_data_json_e_data_js_tem_o_mesmo_conteudo(data, tmp_path):
    json_path, js_path = write_outputs(data, tmp_path)

    assert json.loads(json_path.read_text(encoding="utf-8")) == _read_data_js(js_path)


def test_artefatos_versionados_estao_sincronizados(data, tmp_path):
    """Falha se alguém mudar o pipeline e esquecer de regenerar dashboard/data/."""
    json_path, js_path = write_outputs(data, tmp_path)

    for generated in (json_path, js_path):
        versioned = DEFAULT_OUTPUT / generated.name
        assert versioned.read_bytes() == generated.read_bytes(), (
            f"{versioned} está desatualizado. Rode: python -m scripts.process_data"
        )
