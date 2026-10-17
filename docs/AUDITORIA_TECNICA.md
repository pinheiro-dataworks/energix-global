# Auditoria Técnica — Energix Global

> Revisão de código, metodologia e organização do repositório, com foco em reprodutibilidade, qualidade de engenharia e apresentação profissional do projeto no GitHub.

| Item | Valor |
|---|---|
| Repositório | `pinheiro-dataworks/energix-global` |
| Versão avaliada | `a19cecd` (8 commits) |
| Data da revisão | Outubro/2026 |
| Escopo | Pipeline Python (`scripts/`), dashboard (`dashboard/`), deploy (Vercel), documentação e histórico Git |

---

## 1. Resumo executivo

O projeto tem uma proposta clara, um dashboard visualmente bem acabado e um pipeline Python bem comentado e modular. Os pontos que mais comprometem a percepção de maturidade técnica são:

1. **As métricas publicadas não são reproduzíveis.** Rodando `python -m scripts.process_data` no estado atual, a regressão polinomial retorna **R² = 0,90** (e não 0,996) e uma projeção para 2026 **menor** que o valor real de 2025 (31,05% vs. 33,76%). A causa é numérica: o polinômio é ajustado sobre o ano bruto (2000–2025), e `ano²` ≈ 4 milhões gera uma matriz mal condicionada.
2. **Os dados do dashboard estão duplicados e desacoplados do pipeline.** O `app.js` contém uma cópia de ~85 KB do `data.json` embutida no código. O pipeline atualiza apenas o `data.json`, que não é lido pelo site — qualquer reprocessamento deixa o dashboard desatualizado sem aviso.
3. **Ausência de testes, CI, linting e licença.** Não há nenhuma garantia automática de que o pipeline continua funcionando.
4. **Inconsistências de números entre README, KPIs e dados** (190 × 191 × 195 países; tabela de clusters do README diferente da saída real).
5. **Histórico Git pouco profissional:** 8 commits, sendo 7 de correção de deploy, mensagens com erros de digitação (`.vereclignore`, `verscel.json`, `requirements. txt`) e um commit inicial com todo o projeto.

---

## 2. Achados detalhados

Legenda de severidade: 🔴 Alta · 🟠 Média · 🟡 Baixa

### 2.1 Modelagem e metodologia

| # | Sev. | Achado | Local | Recomendação |
|---|---|---|---|---|
| M1 | 🔴 | Regressão polinomial ajustada sobre o ano bruto (`PolynomialFeatures` em 2000–2025). Mal condicionamento numérico → R² 0,90 no ambiente atual, coeficientes instáveis (`β₀ ≈ 120.735`) e projeção 2026 abaixo do valor de 2025. | `scripts/forecast.py` | Centralizar o eixo temporal (`t = ano − 2000`) antes da expansão polinomial. Com isso o R² volta a 0,996 de forma estável. |
| M2 | 🔴 | Métricas apenas *in-sample* (R², MAE, RMSE no próprio treino). Não dizem nada sobre a capacidade preditiva do modelo. | `scripts/forecast.py` | Incluir backtest temporal: treinar até 2020 e medir o erro em 2021–2025. Publicar essas métricas no JSON e no README. |
| M3 | 🟠 | Delta da projeção logado com sinal duplicado (`Δ +-2.71 pp`). | `scripts/forecast.py` | Usar formatação com sinal (`%+.2f`). |
| M4 | 🟠 | K = 5 fixo, sem justificativa (cotovelo/silhueta). | `scripts/clustering.py` | Documentar a escolha e registrar o *silhouette score* no log/JSON. |
| M5 | 🟡 | Features do K-Means são composicionais e colineares (`renewables ≈ solar + wind + hydro + outras`; `fossil ≈ 100 − renewables − nuclear`). Isso dá peso extra a algumas dimensões. | `scripts/clustering.py` | Registrar a limitação no README; como evolução, testar transformação log-ratio ou remover `renewables_share_elec`. |
| M6 | 🟡 | 2025 é um ano parcial: apenas 90 países têm dado, contra 195 em 2024. KPIs “2025” usam o agregado *World* preliminar. | `dataset/` | Sinalizar no dashboard/README que 2025 é preliminar. |

### 2.2 Engenharia de dados e código Python

| # | Sev. | Achado | Local | Recomendação |
|---|---|---|---|---|
| E1 | 🔴 | `CONTINENT_MAP` duplicado em dois módulos (risco de divergência). | `process_data.py`, `clustering.py` | Centralizar em `scripts/config.py` junto com caminhos, anos e hiperparâmetros. |
| E2 | 🟠 | 15 países do ranking caem em “Outros” por divergência de nomes com o OWID (`Czechia`, `Cote d'Ivoire`, `Hong Kong`, `Puerto Rico`…). `Montserrat` (Caribe) está em Oceania. | mapa de continentes | Completar o mapeamento usando os nomes do dataset. |
| E3 | 🟠 | KPIs fixos no código: `"countries": 190`, `"years": 26`. | `build_summary` | Derivar do próprio dataset. |
| E4 | 🟠 | Código morto: `run_kmeans` e `run_forecast` nunca são chamados; imports não usados (`os`, `numpy`, `KMeans`, `LinearRegression`, `PolynomialFeatures`, `StandardScaler`). | `process_data.py` | Remover. |
| E5 | 🟠 | `warnings.filterwarnings("ignore")` global esconde avisos relevantes (ex.: depreciações do pandas/sklearn). | `process_data.py` | Remover a supressão global. |
| E6 | 🟡 | `logging.basicConfig` executado na importação do módulo; `sys.exit` dentro de função de biblioteca. | `process_data.py`, `eda.py` | Configurar logging só no `__main__` e lançar exceções nas funções. |
| E7 | 🟡 | Anos 2000/2024/2025 espalhados como literais. | todos os scripts | Usar constantes de `config.py`. |
| E8 | 🟡 | Dependências sem limite superior e sem separação dev/prod. | `requirements.txt` | Adicionar `requirements-dev.txt` (pytest, ruff) e `pyproject.toml`. |

### 2.3 Dashboard e deploy

| # | Sev. | Achado | Local | Recomendação |
|---|---|---|---|---|
| D1 | 🔴 | Dados embutidos no `app.js` (~85 KB) duplicando o `data.json`; o pipeline não atualiza o arquivo efetivamente usado. | `dashboard/js/app.js` | Pipeline passa a gerar `dashboard/data/data.js` (`window.ENERGIX_DATA`), carregado antes do `app.js`. Mantém o site sem `fetch` e elimina a duplicação. |
| D2 | 🟡 | Rewrite `/(.*) → /$1` no `vercel.json` é redundante. | `vercel.json` | Remover. |
| D3 | 🟡 | `.vercelignore` não cobre arquivos de desenvolvimento novos (testes, CI, configs). | `.vercelignore` | Atualizar. |

### 2.4 Documentação e apresentação

| # | Sev. | Achado | Recomendação |
|---|---|---|---|
| R1 | 🟠 | README com placeholders (`SEU_USUARIO`), instruções de `git init` desnecessárias e sem link para a demo publicada. | Link da demo no topo, badges, comandos corretos. |
| R2 | 🟠 | Números divergentes (190/191/195 países; tabela de clusters do README não confere com a saída real). | Atualizar com a saída do pipeline. |
| R3 | 🟠 | Sem `LICENSE`. Sem licença, o código é “todos os direitos reservados” por padrão. | Adicionar licença (MIT sugerida). |
| R4 | 🟡 | Sem seção de limitações e próximos passos. | Adicionar ao README. |
| R5 | 🟡 | About do GitHub sem *topics*. | ✅ Topics adicionados. |

### 2.5 Histórico Git

| # | Sev. | Achado | Recomendação |
|---|---|---|---|
| G1 | 🟠 | 8 commits; commit inicial monolítico; 7 commits de ajuste de deploy. | Evoluir com commits pequenos e atômicos, um por mudança lógica. |
| G2 | 🟡 | Mensagens com erros de digitação e padrão inconsistente (`fix:correção…`, `ajuste no verscel.json`). | Adotar *Conventional Commits* em português: `tipo(escopo): descrição no imperativo`. |

---

## 3. Plano de ação (commits)

Cada linha abaixo corresponde a um commit atômico, em ordem, mantendo o site funcional entre cada um deles.

| # | Commit | Achados |
|---|---|---|
| 1 | `docs: adiciona relatório de auditoria técnica do projeto` | — |
| 2 | `refactor(scripts): centraliza constantes e configurações em config.py` | E1, E7 |
| 3 | `fix(scripts): completa o mapeamento de continentes com os nomes do OWID` | E2 |
| 4 | `fix(forecast): centraliza o eixo temporal para estabilizar a regressão` | M1, M3 |
| 5 | `feat(forecast): adiciona backtest temporal às métricas do modelo` | M2 |
| 6 | `feat(clustering): registra silhouette score do agrupamento` | M4 |
| 7 | `refactor(pipeline): remove código morto e deriva KPIs do dataset` | E3, E4, E5, E6 |
| 8 | `feat(pipeline): exporta data.js consumido pelo dashboard` | D1 |
| 9 | `chore(data): regenera artefatos de dados com o pipeline corrigido` | M1, D1 |
| 10 | `feat(dashboard): carrega data.js antes do app.js` | D1 |
| 11 | `refactor(dashboard): remove dados embutidos do app.js` | D1 |
| 12 | `build: adiciona pyproject.toml e dependências de desenvolvimento` | E8 |
| 13 | `test: adiciona testes unitários do pipeline com pytest` | — |
| 14 | `ci: adiciona workflow de lint, testes e validação dos dados` | — |
| 15 | `chore(deploy): ajusta vercel.json e .vercelignore` | D2, D3 |
| 16 | `docs: adiciona licença MIT` | R3 |
| 17 | `docs: atualiza README com métricas reproduzíveis e instruções` | R1, R2, R4 |
| 18 | `docs: atualiza status da auditoria técnica` | — |

---

## 4. Evoluções sugeridas (fora do escopo desta revisão)

- Comparar a regressão polinomial com modelos de série temporal (ETS, ARIMA) e publicar intervalos de previsão.
- Gerar o dashboard por país (seleção dinâmica) a partir do mesmo `data.js`.
- Traduzir os nomes dos clusters para português no dashboard (mantendo os identificadores em inglês no JSON).
- Automatizar a atualização anual do dataset do OWID via GitHub Actions agendado.
- Adicionar screenshot/GIF do dashboard ao README.
