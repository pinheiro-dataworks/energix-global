/* ===================================================
   ENERGIX GLOBAL — Main Application JS
   Os dados vêm de data/data.js (window.ENERGIX_DATA),
   gerado por scripts/process_data.py.
   =================================================== */

// ── State ──────────────────────────────────────────
let DATA = null;
let activeFilters = { years: [], clusters: [], continents: [] };
let charts = {};

// ── Color Maps ──────────────────────────────────────
const COLORS = {
  green:   '#3DBE6C',
  greenDk: '#2A9350',
  solar:   '#F5C518',
  wind:    '#4A90D9',
  hydro:   '#2EBFA5',
  nuclear: '#9B6FCF',
  fossil:  '#E05252',
  other:   '#7BC67E',
  clusters: {
    'Hydro Leaders':    '#2EBFA5',
    'Wind Champions':   '#4A90D9',
    'Solar Pioneers':   '#F5C518',
    'Fossil Dependent': '#E05252',
    'Mixed Renewables': '#9B6FCF'
  },
  continents: {
    'África':          '#F5C518',
    'Ásia':            '#4A90D9',
    'Europa':          '#3DBE6C',
    'América do Norte':'#E05252',
    'América do Sul':  '#2EBFA5',
    'Oceania':         '#9B6FCF',
    'Outros':          '#8C9BB0'
  }
};

const CLUSTER_PT = {
  'Hydro Leaders':    'Hydro Leaders',
  'Wind Champions':   'Wind Champions',
  'Solar Pioneers':   'Solar Pioneers',
  'Fossil Dependent': 'Fossil Dependent',
  'Mixed Renewables': 'Mixed Renewables'
};

// ── Init ────────────────────────────────────────────
async function init() {
  try {
    // Carregado por <script src="./data/data.js"> — sem dependência de fetch
    DATA = window.ENERGIX_DATA;
    if (!DATA) throw new Error('data/data.js não carregado');
    setupFilters();
    buildDashboard();
    setupFilterUI();
  } catch (e) {
    console.error('Erro ao inicializar dashboard:', e);
    document.getElementById('loading').innerHTML =
      '<p style="color:#E05252;padding:40px;text-align:center">Erro ao inicializar o dashboard. Verifique o console.</p>';
  }
}

// ── Setup Filters UI ────────────────────────────────
function setupFilters() {
  const { years, clusters, continents } = DATA.filters;

  renderChips('filter-years',      years,      activeFilters.years,      'year');
  renderChips('filter-clusters',   clusters,   activeFilters.clusters,   'cluster');
  renderChips('filter-continents', continents, activeFilters.continents, 'continent');
}

function renderChips(containerId, items, activeArr, type) {
  const el = document.getElementById(containerId);
  if (!el) return;
  el.innerHTML = '';
  items.forEach(item => {
    const chip = document.createElement('span');
    chip.className = 'filter-chip' + (activeArr.includes(item) ? ' selected' : '');
    chip.textContent = item;
    chip.addEventListener('click', () => {
      chip.classList.toggle('selected');
      const idx = activeArr.indexOf(item);
      if (idx > -1) activeArr.splice(idx, 1);
      else activeArr.push(item);
    });
    el.appendChild(chip);
  });
}

function setupFilterUI() {
  const btn = document.getElementById('btn-filtros');
  const dropdown = document.getElementById('filter-dropdown');

  btn.addEventListener('click', (e) => {
    e.stopPropagation();
    dropdown.classList.toggle('active');
  });

  document.addEventListener('click', (e) => {
    if (!dropdown.contains(e.target) && e.target !== btn)
      dropdown.classList.remove('active');
  });

  document.getElementById('btn-aplicar').addEventListener('click', () => {
    dropdown.classList.remove('active');
    applyFilters();
  });

  document.getElementById('btn-limpar').addEventListener('click', () => {
    activeFilters.years = [];
    activeFilters.clusters = [];
    activeFilters.continents = [];
    document.querySelectorAll('.filter-chip').forEach(c => c.classList.remove('selected'));
    applyFilters();
  });
}

function applyFilters() {
  updateActiveFilterBar();
  updateRanking();
  updateScatter();
}

function updateActiveFilterBar() {
  const bar = document.getElementById('active-filters-bar');
  const all = [
    ...activeFilters.years.map(y => ({ label: y, type: 'year' })),
    ...activeFilters.clusters.map(c => ({ label: c, type: 'cluster' })),
    ...activeFilters.continents.map(c => ({ label: c, type: 'continent' }))
  ];
  if (all.length === 0) { bar.classList.remove('visible'); return; }
  bar.classList.add('visible');
  bar.innerHTML = '<span>Filtros ativos:</span>';
  all.forEach(f => {
    const tag = document.createElement('div');
    tag.className = 'active-filter-tag';
    tag.innerHTML = `${f.label} <button onclick="removeFilter('${f.type}','${f.label}')">×</button>`;
    bar.appendChild(tag);
  });
}

function removeFilter(type, value) {
  if (type === 'year')      { const i = activeFilters.years.indexOf(+value || value);      if (i > -1) activeFilters.years.splice(i, 1); }
  if (type === 'cluster')   { const i = activeFilters.clusters.indexOf(value);   if (i > -1) activeFilters.clusters.splice(i, 1); }
  if (type === 'continent') { const i = activeFilters.continents.indexOf(value); if (i > -1) activeFilters.continents.splice(i, 1); }
  document.querySelectorAll('.filter-chip').forEach(c => {
    const v = c.textContent.trim();
    if (v == value) c.classList.remove('selected');
  });
  applyFilters();
}

// ── Filter helpers ───────────────────────────────────
function getFilteredRanking() {
  let data = [...DATA.ranking];
  if (activeFilters.clusters.length)   data = data.filter(r => activeFilters.clusters.includes(r.cluster));
  if (activeFilters.continents.length) data = data.filter(r => activeFilters.continents.includes(r.continent));
  return data;
}

function getFilteredScatter() {
  let data = [...DATA.scatter_data];
  if (activeFilters.clusters.length)   data = data.filter(r => activeFilters.clusters.includes(r.cluster));
  if (activeFilters.continents.length) data = data.filter(r => activeFilters.continents.includes(r.continent));
  return data;
}

// ── Build Dashboard ──────────────────────────────────
function buildDashboard() {
  document.getElementById('loading').style.display = 'none';
  document.getElementById('dashboard').style.display = 'block';

  buildHeroKPIs();
  buildIndicators();
  buildTrendChart();
  buildDonutChart();
  buildForecastTable();
  buildSolarChart();
  buildWindChart();
  buildBigEconomiesChart();
  buildBrazilHighlight();
  buildRanking();
  buildScatterChart();
  buildClusterProfiles();
  buildDistributionChart();
  buildCompositionChart();
  buildAnnualGrowthChart();
}

// ── KPIs ─────────────────────────────────────────────
function buildHeroKPIs() {
  const s = DATA.summary;
  document.getElementById('kpi-renew').textContent   = s.renewables_2025.toFixed(1) + '%';
  document.getElementById('kpi-countries').textContent = s.countries;
  document.getElementById('kpi-years').textContent   = s.years;
  document.getElementById('kpi-growth').textContent  = '+' + s.growth_pct.toFixed(1) + '%';
}

// ── Indicators ───────────────────────────────────────
function buildIndicators() {
  const s = DATA.summary;
  const deltaRen   = (s.renewables_2025 - s.renewables_2000).toFixed(1);
  const deltaSolar = (s.solar_2025 - s.solar_2000).toFixed(1);
  const deltaWind  = (s.wind_2025 - s.wind_2000).toFixed(1);
  const deltaFoss  = (s.fossil_2025 - s.fossil_2000).toFixed(1);

  document.getElementById('ind-renew-val').textContent   = s.renewables_2025.toFixed(1) + '%';
  document.getElementById('ind-solar-val').textContent   = s.solar_2025.toFixed(2) + '%';
  document.getElementById('ind-wind-val').textContent    = s.wind_2025.toFixed(2) + '%';
  document.getElementById('ind-fossil-val').textContent  = s.fossil_2025.toFixed(1) + '%';

  document.getElementById('ind-renew-delta').textContent  = '▲ +' + deltaRen + ' pp desde 2000';
  document.getElementById('ind-solar-delta').textContent  = '▲ +' + deltaSolar + ' pp desde 2000';
  document.getElementById('ind-wind-delta').textContent   = '▲ +' + deltaWind + ' pp desde 2000';
  document.getElementById('ind-fossil-delta').textContent = '▼ ' + deltaFoss + ' pp desde 2000';
}

// ── Trend Chart ──────────────────────────────────────
function buildTrendChart() {
  const trend = DATA.global_trend;
  const fitted = DATA.forecast.historical_fitted;
  const fc = DATA.forecast.forecast;
  const r2 = DATA.forecast.r2;

  const years    = trend.map(d => d.year);
  const renew    = trend.map(d => d.renewables_share_elec);
  const fossil   = trend.map(d => d.fossil_share_elec);
  const fittedY  = fitted.map(d => d.fitted);
  const fcYears  = fc.map(d => d.year);
  const fcVals   = fc.map(d => d.value);

  document.getElementById('r2-value').textContent = 'R² = ' + r2.toFixed(4);

  const allYears = [...years, ...fcYears];
  const allFitted = [...fittedY, ...fcVals];

  const ctx = document.getElementById('trendChart').getContext('2d');
  charts.trend = new Chart(ctx, {
    type: 'line',
    data: {
      labels: allYears,
      datasets: [
        {
          label: 'Renováveis %',
          data: [...renew, ...Array(fcYears.length).fill(null)],
          borderColor: COLORS.green,
          backgroundColor: hexAlpha(COLORS.green, 0.08),
          borderWidth: 2.5,
          pointRadius: 0,
          pointHoverRadius: 4,
          fill: true,
          tension: 0.35,
          order: 2
        },
        {
          label: 'Fóssil %',
          data: [...fossil, ...Array(fcYears.length).fill(null)],
          borderColor: COLORS.fossil,
          backgroundColor: 'transparent',
          borderWidth: 1.8,
          pointRadius: 0,
          pointHoverRadius: 4,
          fill: false,
          tension: 0.35,
          borderDash: [0],
          order: 3
        },
        {
          label: 'Regressão Polinomial',
          data: allFitted,
          borderColor: '#E05252',
          backgroundColor: 'transparent',
          borderWidth: 1.5,
          borderDash: [5, 4],
          pointRadius: 0,
          fill: false,
          tension: 0.35,
          order: 1
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: 'index', intersect: false },
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: 'rgba(17,24,39,0.92)',
          titleColor: '#fff',
          bodyColor: 'rgba(255,255,255,0.75)',
          padding: 12,
          borderColor: 'rgba(255,255,255,0.1)',
          borderWidth: 1,
          callbacks: {
            label: ctx => ` ${ctx.dataset.label}: ${ctx.parsed.y !== null ? ctx.parsed.y.toFixed(2) + '%' : 'N/A'}`
          }
        }
      },
      scales: {
        x: {
          grid: { color: 'rgba(220,228,240,0.4)', drawBorder: false },
          ticks: { color: '#8C9BB0', font: { family: 'Roboto', size: 11 }, maxTicksLimit: 8 }
        },
        y: {
          grid: { color: 'rgba(220,228,240,0.4)', drawBorder: false },
          ticks: { color: '#8C9BB0', font: { family: 'Roboto', size: 11 }, callback: v => v + '%' },
          min: 10, max: 75
        }
      }
    }
  });
}

// ── Donut Chart ──────────────────────────────────────
function buildDonutChart() {
  const m = DATA.matrix_2025;
  const ctx = document.getElementById('donutChart').getContext('2d');
  const labels = ['Fóssil', 'Hidro', 'Nuclear', 'Eólica', 'Solar', 'Outras Renov.'];
  const values = [m.fossil, m.hydro, m.nuclear, m.wind, m.solar, m.other];
  const colors = [COLORS.fossil, COLORS.hydro, COLORS.nuclear, COLORS.wind, COLORS.solar, COLORS.other];

  charts.donut = new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels,
      datasets: [{ data: values, backgroundColor: colors, borderWidth: 2, borderColor: '#fff', hoverOffset: 6 }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      cutout: '68%',
      plugins: {
        legend: {
          position: 'right',
          labels: {
            color: '#5A6A7A',
            font: { family: 'Roboto', size: 11.5 },
            padding: 12,
            usePointStyle: true,
            pointStyleWidth: 8
          }
        },
        tooltip: {
          backgroundColor: 'rgba(17,24,39,0.92)',
          titleColor: '#fff',
          bodyColor: 'rgba(255,255,255,0.75)',
          padding: 10,
          callbacks: { label: ctx => ` ${ctx.label}: ${ctx.parsed.toFixed(2)}%` }
        }
      }
    }
  });
}

// ── Forecast Table ────────────────────────────────────
function buildForecastTable() {
  const fc = DATA.forecast.forecast;
  const tbody = document.getElementById('forecast-tbody');
  let prev = DATA.summary.renewables_2025;
  tbody.innerHTML = '';
  fc.forEach(row => {
    const delta = (row.value - prev).toFixed(2);
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td class="year-cell">${row.year}</td>
      <td class="val-cell">${row.value.toFixed(2)}%</td>
      <td class="delta-cell">+${delta}pp</td>`;
    tbody.appendChild(tr);
    prev = row.value;
  });
}

// ── Solar Chart ───────────────────────────────────────
function buildSolarChart() {
  const data = DATA.solar_series;
  const ctx  = document.getElementById('solarChart').getContext('2d');
  charts.solar = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: data.map(d => d.year),
      datasets: [{
        label: 'Solar %',
        data: data.map(d => d.value),
        backgroundColor: data.map(d => hexAlpha(COLORS.solar, d.year >= 2020 ? 1 : 0.75)),
        borderRadius: 4,
        borderSkipped: false
      }]
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { display: false }, tooltip: tooltipDefaults('Solar %') },
      scales: {
        x: { grid: { display: false }, ticks: { color: '#8C9BB0', font: { size: 10 }, maxTicksLimit: 7 } },
        y: { grid: { color: 'rgba(220,228,240,0.4)', drawBorder: false }, ticks: { color: '#8C9BB0', font: { size: 11 }, callback: v => v + '%' } }
      }
    }
  });
}

// ── Wind Chart ────────────────────────────────────────
function buildWindChart() {
  const data = DATA.wind_series;
  const ctx  = document.getElementById('windChart').getContext('2d');
  charts.wind = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: data.map(d => d.year),
      datasets: [{
        label: 'Eólica %',
        data: data.map(d => d.value),
        backgroundColor: data.map(d => hexAlpha(COLORS.wind, d.year >= 2020 ? 1 : 0.75)),
        borderRadius: 4,
        borderSkipped: false
      }]
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { display: false }, tooltip: tooltipDefaults('Eólica %') },
      scales: {
        x: { grid: { display: false }, ticks: { color: '#8C9BB0', font: { size: 10 }, maxTicksLimit: 7 } },
        y: { grid: { color: 'rgba(220,228,240,0.4)', drawBorder: false }, ticks: { color: '#8C9BB0', font: { size: 11 }, callback: v => v + '%' } }
      }
    }
  });
}

// ── Big Economies Chart ───────────────────────────────
function buildBigEconomiesChart() {
  const econ = DATA.big_economies;
  const ECON_COLORS = {
    'Brasil':   COLORS.green,
    'China':    '#E05252',
    'Alemanha': COLORS.wind,
    'EUA':      COLORS.solar,
    'França':   COLORS.nuclear,
    'Índia':    COLORS.hydro
  };
  const firstKey = Object.keys(econ)[0];
  const years = econ[firstKey].map(d => d.year);

  const datasets = Object.entries(econ).map(([name, series]) => ({
    label: name,
    data: series.map(d => d.value),
    borderColor: ECON_COLORS[name],
    backgroundColor: 'transparent',
    borderWidth: 2,
    pointRadius: 0,
    pointHoverRadius: 4,
    tension: 0.35
  }));

  const ctx = document.getElementById('economiesChart').getContext('2d');
  charts.economies = new Chart(ctx, {
    type: 'line',
    data: { labels: years, datasets },
    options: {
      responsive: true, maintainAspectRatio: false,
      interaction: { mode: 'index', intersect: false },
      plugins: {
        legend: {
          position: 'bottom',
          labels: { color: '#5A6A7A', font: { family: 'Roboto', size: 11 }, padding: 14, usePointStyle: true }
        },
        tooltip: {
          backgroundColor: 'rgba(17,24,39,0.92)',
          titleColor: '#fff',
          bodyColor: 'rgba(255,255,255,0.75)',
          padding: 12,
          callbacks: { label: ctx => ` ${ctx.dataset.label}: ${ctx.parsed.y.toFixed(1)}%` }
        }
      },
      scales: {
        x: { grid: { color: 'rgba(220,228,240,0.4)', drawBorder: false }, ticks: { color: '#8C9BB0', font: { size: 10 }, maxTicksLimit: 7 } },
        y: { grid: { color: 'rgba(220,228,240,0.4)', drawBorder: false }, ticks: { color: '#8C9BB0', font: { size: 11 }, callback: v => v + '%' } }
      }
    }
  });
}

// ── Brazil Highlight ──────────────────────────────────
function buildBrazilHighlight() {
  const b = DATA.brazil_highlight;
  document.getElementById('br-renew').textContent = b.renewables + '%';
  document.getElementById('br-solar').textContent = b.solar + '%';
  document.getElementById('br-wind').textContent  = b.wind + '%';
  document.getElementById('br-hydro').textContent = b.hydro + '%';
}

// ── Ranking ───────────────────────────────────────────
function buildRanking() { updateRanking(); }

function updateRanking() {
  const items = getFilteredRanking();
  const container = document.getElementById('ranking-list');
  container.innerHTML = '';

  items.forEach((item, idx) => {
    const div = document.createElement('div');
    div.className = 'ranking-item';

    let rankClass = '';
    if (item.rank === 1) rankClass = 'gold';
    else if (item.rank === 2) rankClass = 'silver';
    else if (item.rank === 3) rankClass = 'bronze';

    const barColor = item.value === 100 ? COLORS.green :
                     item.value >= 50   ? hexAlpha(COLORS.green, 0.75) :
                     item.value >= 25   ? COLORS.solar :
                     COLORS.fossil;

    div.innerHTML = `
      <span class="rank-num ${rankClass}">${item.rank}</span>
      <span class="rank-country" title="${item.country}">${item.country}</span>
      <div class="rank-bar-wrap">
        <div class="rank-bar" style="width:${item.value}%;background:${barColor}"></div>
      </div>
      <span class="rank-value">${item.value.toFixed(1)}%</span>`;
    container.appendChild(div);
  });
}

// ── Scatter Chart ─────────────────────────────────────
function buildScatterChart() {
  renderScatter(getFilteredScatter());
}

function renderScatter(data) {
  const ctx = document.getElementById('scatterChart').getContext('2d');
  if (charts.scatter) { charts.scatter.destroy(); }

  const grouped = {};
  data.forEach(d => {
    if (!grouped[d.cluster]) grouped[d.cluster] = [];
    grouped[d.cluster].push({ x: d.fossil, y: d.renewables, country: d.country });
  });

  const datasets = Object.entries(grouped).map(([cluster, pts]) => ({
    label: cluster,
    data: pts,
    backgroundColor: hexAlpha(COLORS.clusters[cluster] || '#8C9BB0', 0.7),
    borderColor: COLORS.clusters[cluster] || '#8C9BB0',
    borderWidth: 1,
    pointRadius: 5,
    pointHoverRadius: 7
  }));

  charts.scatter = new Chart(ctx, {
    type: 'scatter',
    data: { datasets },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: {
        legend: {
          position: 'bottom',
          labels: { color: '#5A6A7A', font: { family: 'Roboto', size: 11 }, padding: 12, usePointStyle: true }
        },
        tooltip: {
          backgroundColor: 'rgba(17,24,39,0.92)',
          titleColor: '#fff',
          bodyColor: 'rgba(255,255,255,0.75)',
          padding: 10,
          callbacks: {
            title: items => items[0].raw.country,
            label: item => ` Renov: ${item.parsed.y}% | Fóssil: ${item.parsed.x}%`
          }
        }
      },
      scales: {
        x: {
          title: { display: true, text: 'Fóssil %', color: '#8C9BB0', font: { size: 11 } },
          grid: { color: 'rgba(220,228,240,0.4)', drawBorder: false },
          ticks: { color: '#8C9BB0', font: { size: 10 } }
        },
        y: {
          title: { display: true, text: 'Renováveis %', color: '#8C9BB0', font: { size: 11 } },
          grid: { color: 'rgba(220,228,240,0.4)', drawBorder: false },
          ticks: { color: '#8C9BB0', font: { size: 10 }, callback: v => v + '%' }
        }
      }
    }
  });
}

function updateScatter() { renderScatter(getFilteredScatter()); }

// ── Cluster Profiles ──────────────────────────────────
function buildClusterProfiles() {
  const profiles = DATA.cluster_profiles;
  const container = document.getElementById('cluster-profiles-grid');
  container.innerHTML = '';

  const order = ['Hydro Leaders','Wind Champions','Solar Pioneers','Fossil Dependent','Mixed Renewables'];
  order.forEach(name => {
    const p = profiles[name];
    if (!p) return;
    const color = COLORS.clusters[name];
    const card = document.createElement('div');
    card.className = 'cluster-profile-card';
    card.style.background = hexAlpha(color, 0.06);
    card.style.borderColor = hexAlpha(color, 0.25);
    card.innerHTML = `
      <div class="cluster-profile-header">
        <div class="cluster-dot" style="background:${color}"></div>
        <span class="cluster-profile-name">${name}</span>
        <span style="margin-left:auto;font-size:10.5px;color:#8C9BB0">${p.count} países</span>
      </div>
      <div class="cluster-profile-stats">
        <div class="cluster-stat-row"><span class="label">Renov.</span><span class="val" style="color:${color}">${p.renewables}%</span></div>
        <div class="cluster-stat-row"><span class="label">Solar</span><span class="val">${p.solar}%</span></div>
        <div class="cluster-stat-row"><span class="label">Eólica</span><span class="val">${p.wind}%</span></div>
        <div class="cluster-stat-row"><span class="label">Hidro</span><span class="val">${p.hydro}%</span></div>
        <div class="cluster-stat-row"><span class="label">Fóssil</span><span class="val">${p.fossil}%</span></div>
      </div>
      <div class="cluster-countries">Top: ${p.top5.join(', ')}</div>`;
    container.appendChild(card);
  });
}

// ── Distribution Chart ────────────────────────────────
function buildDistributionChart() {
  const profiles = DATA.cluster_profiles;
  const total = Object.values(profiles).reduce((a,b) => a + b.count, 0);
  const order = ['Hydro Leaders','Wind Champions','Solar Pioneers','Mixed Renewables','Fossil Dependent'];
  const container = document.getElementById('dist-bars');
  container.innerHTML = '';
  order.forEach(name => {
    const p = profiles[name];
    if (!p) return;
    const pct = (p.count / total * 100).toFixed(1);
    const color = COLORS.clusters[name];
    const row = document.createElement('div');
    row.className = 'dist-row';
    row.innerHTML = `
      <span class="dist-label">${name}</span>
      <div class="dist-bar-wrap">
        <div class="dist-bar" style="width:${pct}%;background:${hexAlpha(color,0.75)}"></div>
      </div>
      <span class="dist-count">${p.count}</span>`;
    container.appendChild(row);
  });
}

// ── Composition Chart ─────────────────────────────────
function buildCompositionChart() {
  const comp = DATA.composition;
  const years = comp.map(d => d.year);
  const ctx = document.getElementById('compositionChart').getContext('2d');

  charts.composition = new Chart(ctx, {
    type: 'line',
    data: {
      labels: years,
      datasets: [
        { label: 'Fóssil',      data: comp.map(d => d.fossil),      borderColor: COLORS.fossil,  backgroundColor: hexAlpha(COLORS.fossil, 0.55),  fill: true, borderWidth: 1, pointRadius: 0, tension: 0.3 },
        { label: 'Hidro',       data: comp.map(d => d.hydro),       borderColor: COLORS.hydro,   backgroundColor: hexAlpha(COLORS.hydro, 0.6),    fill: true, borderWidth: 1, pointRadius: 0, tension: 0.3 },
        { label: 'Solar',       data: comp.map(d => d.solar),       borderColor: COLORS.solar,   backgroundColor: hexAlpha(COLORS.solar, 0.7),    fill: true, borderWidth: 1, pointRadius: 0, tension: 0.3 },
        { label: 'Eólica',      data: comp.map(d => d.wind),        borderColor: COLORS.wind,    backgroundColor: hexAlpha(COLORS.wind, 0.6),     fill: true, borderWidth: 1, pointRadius: 0, tension: 0.3 },
        { label: 'Nuclear',     data: comp.map(d => d.nuclear),     borderColor: COLORS.nuclear, backgroundColor: hexAlpha(COLORS.nuclear, 0.5),  fill: true, borderWidth: 1, pointRadius: 0, tension: 0.3 },
        { label: 'Outras Renov.', data: comp.map(d => d.other_renew), borderColor: COLORS.other, backgroundColor: hexAlpha(COLORS.other, 0.6),   fill: true, borderWidth: 1, pointRadius: 0, tension: 0.3 }
      ]
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      interaction: { mode: 'index', intersect: false },
      plugins: {
        legend: {
          position: 'bottom',
          labels: { color: '#5A6A7A', font: { family:'Roboto', size:11 }, padding:10, usePointStyle:true }
        },
        tooltip: {
          backgroundColor:'rgba(17,24,39,0.92)', titleColor:'#fff', bodyColor:'rgba(255,255,255,0.75)', padding:10,
          callbacks: { label: ctx => ` ${ctx.dataset.label}: ${ctx.parsed.y.toFixed(2)}%` }
        }
      },
      scales: {
        x: { stacked: true, grid: { display: false }, ticks: { color:'#8C9BB0', font:{size:10}, maxTicksLimit:7 } },
        y: { stacked: true, grid: { color:'rgba(220,228,240,0.4)', drawBorder:false }, ticks: { color:'#8C9BB0', font:{size:11}, callback: v => v+'%' }, max: 100 }
      }
    }
  });
}

// ── Annual Growth Chart ───────────────────────────────
function buildAnnualGrowthChart() {
  const ag = DATA.annual_growth;
  const ctx = document.getElementById('growthChart').getContext('2d');

  charts.growth = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: ag.map(d => d.year),
      datasets: [{
        label: 'Var. anual (pp)',
        data: ag.map(d => d.yoy),
        backgroundColor: ag.map(d => d.yoy >= 0 ? hexAlpha(COLORS.green, 0.8) : hexAlpha(COLORS.fossil, 0.7)),
        borderRadius: 3,
        borderSkipped: false
      }]
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor:'rgba(17,24,39,0.92)', titleColor:'#fff', bodyColor:'rgba(255,255,255,0.75)', padding:10,
          callbacks: { label: ctx => ` ${ctx.parsed.y > 0 ? '+' : ''}${ctx.parsed.y.toFixed(2)} pp` }
        }
      },
      scales: {
        x: { grid:{ display:false }, ticks:{ color:'#8C9BB0', font:{size:10}, maxTicksLimit:8 } },
        y: {
          grid:{ color:'rgba(220,228,240,0.4)', drawBorder:false },
          ticks:{ color:'#8C9BB0', font:{size:11}, callback: v => (v>0?'+':'')+v+' pp' },
          afterDataLimits: scale => { scale.min = scale.min - 0.2; scale.max = scale.max + 0.1; }
        }
      }
    }
  });
}

// ── Helpers ───────────────────────────────────────────
function hexAlpha(hex, alpha) {
  const r = parseInt(hex.slice(1,3),16);
  const g = parseInt(hex.slice(3,5),16);
  const b = parseInt(hex.slice(5,7),16);
  return `rgba(${r},${g},${b},${alpha})`;
}

function tooltipDefaults(label) {
  return {
    backgroundColor: 'rgba(17,24,39,0.92)',
    titleColor: '#fff',
    bodyColor: 'rgba(255,255,255,0.75)',
    padding: 10,
    callbacks: { label: ctx => ` ${label}: ${ctx.parsed.y.toFixed(3)}%` }
  };
}

// ── Start ─────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', init);
