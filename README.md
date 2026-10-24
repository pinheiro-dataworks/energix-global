# Energix Global — Inteligência em Energia Renovável

[![CI](https://github.com/pinheiro-dataworks/Energix-Global/actions/workflows/ci.yml/badge.svg)](https://github.com/pinheiro-dataworks/Energix-Global/actions/workflows/ci.yml)
[![Demo](https://img.shields.io/badge/demo-energix--global.vercel.app-3DBE6C)](https://energix-global.vercel.app)
![Python](https://img.shields.io/badge/python-3.10%20%7C%203.12-3776AB)
![scikit-learn](https://img.shields.io/badge/scikit--learn-1.3%2B-F7931E)
[![Licença: MIT](https://img.shields.io/badge/licen%C3%A7a-MIT-blue)](LICENSE)

Dashboard interativo sobre a participação das energias renováveis na geração elétrica mundial entre 2000 e 2025. Os países são agrupados por perfil energético com K-Means, e uma regressão polinomial projeta a tendência global até 2030.

**[Abrir o dashboard →](https://energix-global.vercel.app)**

---

## Principais resultados

| Indicador | Valor |
|---|---|
| Participação renovável na eletricidade mundial em 2025 | **33,8%** (era 18,7% em 2000, +80,4%) |
| Projeção para 2030 (regressão polinomial de grau 2) | **41,0%** |
| Ajuste do modelo em 2000–2025 | R² = 0,996 · MAE = 0,24 pp · RMSE = 0,31 pp |
| Erro fora da amostra (treino até 2020, teste 2021–2025) | MAE = 0,62 pp · RMSE = 0,66 pp |
| Países analisados (ranking 2024) | 195 |
| Perfis energéticos (K-Means, K = 5) | 191 países agrupados · silhouette = 0,42 |

Todos os números acima saem de `python -m scripts.process_data` e ficam gravados em `dashboard/data/data.json`. Um teste do CI falha se esse arquivo divergir do que o pipeline gera.

---

## Como funciona

```
dataset/dataset_renewable.csv          (Our World in Data)
            │
            ▼
scripts/process_data.py                limpeza, KPIs, K-Means, regressão
            │
            ├──► dashboard/data/data.json   versão legível, para inspeção
            └──► dashboard/data/data.js     window.ENERGIX_DATA
                          │
                          ▼
              dashboard/index.html + js/app.js   (Chart.js)
                          │
                          ▼
                 Vercel (site estático)
```

O dashboard não faz `fetch`: os dados chegam por um `<script>` que define `window.ENERGIX_DATA`. Assim o site funciona em qualquer hospedagem estática e até abrindo o `index.html` direto do disco. Para atualizar o site, basta rodar o pipeline e commitar `dashboard/data/`.

---

## Executar localmente

Requer Python 3.10 ou superior.

```bash
git clone https://github.com/pinheiro-dataworks/Energix-Global.git
cd Energix-Global

python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
```

### Regenerar os dados

```bash
python -m scripts.process_data
```

Opções: `--dataset caminho/para/arquivo.csv` e `--output pasta/de/saida`.

> Rode os scripts sempre como módulo (`python -m scripts.x`) a partir da raiz do repositório. `python scripts/x.py` não encontra o pacote `scripts`.

### Ver o dashboard

```bash
python -m http.server 8080 --directory dashboard
# http://localhost:8080
```

### Testes e lint

```bash
pytest                      # 21 testes, ~4 s
ruff check scripts tests
```

### Módulos isolados

```bash
python -m scripts.forecast   [--degree 2] [--horizon 2030]
python -m scripts.clustering [--year 2024] [--k 5]
python -m scripts.eda                       # relatório exploratório no terminal
```

---

## Metodologia

### Regressão polinomial (tendência global)

- **Alvo:** `renewables_share_elec` do agregado *World*, 2000–2025 (26 pontos).
- **Modelo:** ŷ = β₀ + β₁·t + β₂·t², com **t = ano − 2000**. Centralizar o eixo é essencial: com o ano bruto, ano² passa de 4 milhões, a matriz fica mal condicionada e o resultado muda conforme a versão do numpy.
- **Estimador:** `PolynomialFeatures(degree=2)` + `LinearRegression(fit_intercept=False)`.
- **Validação:** além das métricas no próprio treino, um backtest temporal treina até 2020 e prevê 2021–2025. O modelo superestimou esses cinco anos em média 0,6 pp.

| Ano | 2026 | 2027 | 2028 | 2029 | 2030 |
|---|---:|---:|---:|---:|---:|
| Projeção | 34,80% | 36,25% | 37,76% | 39,34% | 40,98% |

### K-Means (perfis energéticos)

- **Features:** participação na eletricidade de renováveis, solar, eólica, hidrelétrica e fóssil, padronizadas com `StandardScaler`.
- **Dados:** 2024, o último ano com cobertura completa. São 191 países com todas as features.
- **K = 5**, `random_state=42`, `n_init=10`. Os clusters são nomeados automaticamente pelo perfil médio.
- **Por que K = 5:** é uma escolha de interpretabilidade, com um grupo por perfil. O silhouette é 0,42. Com K = 3 ele sobe para 0,49, mas solar e eólica caem no mesmo grupo.

| Cluster | Países | Renov% | Solar% | Eólica% | Hidro% | Fóssil% |
|---|---:|---:|---:|---:|---:|---:|
| Hydro Leaders | 33 | 88,5 | 2,7 | 1,9 | 78,7 | 10,5 |
| Wind Champions | 16 | 65,5 | 10,9 | 30,5 | 11,6 | 25,3 |
| Solar Pioneers | 20 | 42,6 | 22,5 | 4,5 | 11,0 | 53,3 |
| Fossil Dependent | 86 | 10,8 | 3,7 | 1,6 | 4,2 | 87,3 |
| Mixed Renewables | 36 | 48,4 | 4,1 | 3,9 | 36,7 | 44,6 |

---

## Limitações

- **2025 é preliminar.** No dataset, só 90 países têm dado de 2025, contra 195 em 2024. Os KPIs de 2025 usam o agregado *World* do OWID, que pode ser revisado. Por isso o ranking e o clustering usam 2024.
- **A projeção é uma extrapolação de tendência.** O modelo não considera políticas, preços ou capacidade instalada e não tem intervalo de confiança. Leia o número de 2030 como "se a curva de 2000–2025 continuar", não como previsão de mercado.
- **Features composicionais no K-Means.** As participações somam aproximadamente 100% (renováveis ≈ solar + eólica + hídrica + outras; fóssil ≈ 100 − renováveis − nuclear), o que dá peso extra a algumas dimensões. Uma transformação log-ratio seria mais adequada.

---

## Estrutura

```
Energix-Global/
├── dashboard/                  site estático (publicado na Vercel)
│   ├── index.html
│   ├── css/style.css
│   ├── js/app.js               gráficos, filtros e interação
│   ├── data/
│   │   ├── data.js             gerado pelo pipeline — lido pelo site
│   │   └── data.json           gerado pelo pipeline — mesmo conteúdo
│   └── assets/img/
├── scripts/                    pipeline Python
│   ├── config.py               caminhos, anos, hiperparâmetros, continentes
│   ├── process_data.py         orquestra tudo e grava os artefatos
│   ├── forecast.py             regressão polinomial + backtest
│   ├── clustering.py           K-Means + silhouette
│   └── eda.py                  análise exploratória
├── tests/                      pytest
├── dataset/dataset_renewable.csv
├── docs/
│   ├── GUIA_DIDATICO_SCRIPTS.md
│   └── AUDITORIA_TECNICA.md
├── .github/workflows/ci.yml    lint, testes e pipeline (Python 3.10 e 3.12)
├── pyproject.toml              metadados, ruff e pytest
├── requirements.txt / requirements-dev.txt
└── vercel.json
```

## Stack

| Camada | Tecnologia |
|---|---|
| Dados e ML | pandas, numpy, scikit-learn |
| Qualidade | pytest, ruff, GitHub Actions |
| Frontend | HTML, CSS e JavaScript puro, Chart.js 4.4 |
| Deploy | Vercel (site estático) |

## Fonte de dados

[Our World in Data — Energy Dataset](https://github.com/owid/energy-data) (licença CC BY 4.0). O recorte em `dataset/` cobre 2000–2025, 309 entidades (países e agregados regionais) e 33 colunas.

## Documentação

- [Guia didático dos scripts](docs/GUIA_DIDATICO_SCRIPTS.md): explicação passo a passo do pipeline.
- [Auditoria técnica](docs/AUDITORIA_TECNICA.md): revisão do projeto e o que foi corrigido.

## Autor

**Renan Pinheiro** · [GitHub](https://github.com/pinheiro-dataworks)

Código sob licença [MIT](LICENSE).
