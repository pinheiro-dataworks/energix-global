"""
Energix Global — configurações e constantes compartilhadas.

Centraliza caminhos, parâmetros de modelagem e mapeamentos usados pelos
módulos do pipeline (process_data, clustering, forecast e eda), evitando
duplicação e divergência entre eles.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

# ── Caminhos ───────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DATASET = ROOT / "dataset" / "dataset_renewable.csv"
DEFAULT_OUTPUT = ROOT / "dashboard" / "data"

# ── Recorte temporal ───────────────────────────────────────────────
YEAR_START = 2000
YEAR_END = 2025
CLUSTER_YEAR = 2024  # último ano com cobertura completa de países

# ── Colunas ────────────────────────────────────────────────────────
TARGET_COL = "renewables_share_elec"

REQUIRED_COLS = [
    "country", "year", "iso_code",
    "renewables_share_elec", "solar_share_elec",
    "wind_share_elec", "hydro_share_elec",
    "nuclear_share_elec", "fossil_share_elec",
]

# ── K-Means ────────────────────────────────────────────────────────
N_CLUSTERS = 5
RANDOM_STATE = 42
N_INIT = 10

CLUSTER_FEATURES = [
    "renewables_share_elec",
    "solar_share_elec",
    "wind_share_elec",
    "hydro_share_elec",
    "fossil_share_elec",
]

CLUSTER_ORDER = [
    "Hydro Leaders",
    "Wind Champions",
    "Solar Pioneers",
    "Fossil Dependent",
    "Mixed Renewables",
]

# ── Regressão polinomial ───────────────────────────────────────────
POLY_DEGREE = 2
FORECAST_YEAR_START = YEAR_END + 1
FORECAST_YEAR_END = 2030
BACKTEST_YEARS = 5  # anos finais reservados para validação temporal

# ── Grandes economias (inglês → português) ─────────────────────────
BIG_ECONOMIES_PT: dict[str, str] = {
    "Brazil":        "Brasil",
    "China":         "China",
    "Germany":       "Alemanha",
    "United States": "EUA",
    "France":        "França",
    "India":         "Índia",
}

# ── Mapeamento de continentes ──────────────────────────────────────
CONTINENT_MAP: dict[str, list[str]] = {
    "África": [
        "Algeria","Angola","Benin","Botswana","Burkina Faso","Burundi","Cameroon",
        "Cape Verde","Central African Republic","Chad","Comoros","Congo","Ivory Coast",
        "Democratic Republic of Congo","Djibouti","Egypt","Equatorial Guinea","Eritrea",
        "Eswatini","Ethiopia","Gabon","Gambia","Ghana","Guinea","Guinea-Bissau","Kenya",
        "Lesotho","Liberia","Libya","Madagascar","Malawi","Mali","Mauritania","Mauritius",
        "Morocco","Mozambique","Namibia","Niger","Nigeria","Rwanda","Sao Tome and Principe",
        "Senegal","Seychelles","Sierra Leone","Somalia","South Africa","South Sudan","Sudan",
        "Tanzania","Togo","Tunisia","Uganda","Zambia","Zimbabwe",
    ],
    "Ásia": [
        "Afghanistan","Armenia","Azerbaijan","Bahrain","Bangladesh","Bhutan","Brunei",
        "Cambodia","China","Cyprus","Georgia","India","Indonesia","Iran","Iraq","Israel",
        "Japan","Jordan","Kazakhstan","Kuwait","Kyrgyzstan","Laos","Lebanon","Malaysia",
        "Maldives","Mongolia","Myanmar","Nepal","North Korea","Oman","Pakistan","Palestine",
        "Philippines","Qatar","Saudi Arabia","Singapore","South Korea","Sri Lanka","Syria",
        "Taiwan","Tajikistan","Thailand","Timor-Leste","Turkmenistan",
        "United Arab Emirates","Uzbekistan","Vietnam","Yemen","East Timor",
    ],
    "Europa": [
        "Albania","Andorra","Austria","Belarus","Belgium","Bosnia and Herzegovina",
        "Bulgaria","Croatia","Czech Republic","Denmark","Estonia","Finland","France",
        "Germany","Greece","Hungary","Iceland","Ireland","Italy","Kosovo","Latvia",
        "Liechtenstein","Lithuania","Luxembourg","Malta","Moldova","Monaco","Montenegro",
        "Netherlands","North Macedonia","Norway","Poland","Portugal","Romania","Russia",
        "San Marino","Serbia","Slovakia","Slovenia","Spain","Sweden","Switzerland",
        "Turkey","Ukraine","United Kingdom","Vatican",
    ],
    "América do Norte": [
        "Antigua and Barbuda","Bahamas","Barbados","Belize","Canada","Costa Rica","Cuba",
        "Dominica","Dominican Republic","El Salvador","Grenada","Guatemala","Haiti",
        "Honduras","Jamaica","Mexico","Nicaragua","Panama","Saint Kitts and Nevis",
        "Saint Lucia","Saint Vincent and the Grenadines","Trinidad and Tobago",
        "United States",
    ],
    "América do Sul": [
        "Argentina","Bolivia","Brazil","Chile","Colombia","Ecuador","Guyana",
        "Paraguay","Peru","Suriname","Uruguay","Venezuela",
    ],
    "Oceania": [
        "Australia","Fiji","French Polynesia","Kiribati","Marshall Islands","Micronesia",
        "Nauru","New Zealand","Palau","Papua New Guinea","Samoa","Solomon Islands",
        "Tonga","Tuvalu","Vanuatu","Montserrat",
    ],
}

COUNTRY_TO_CONTINENT: dict[str, str] = {
    country: continent
    for continent, countries in CONTINENT_MAP.items()
    for country in countries
}

DEFAULT_CONTINENT = "Outros"


def is_real_country(df: pd.DataFrame) -> pd.Series:
    """Máscara booleana para países reais (iso_code ISO-3166 alfa-3)."""
    return df["iso_code"].notna() & (df["iso_code"].str.len() == 3)


def continent_of(country: str) -> str:
    """Retorna o continente de um país ou 'Outros' quando não mapeado."""
    return COUNTRY_TO_CONTINENT.get(country, DEFAULT_CONTINENT)
