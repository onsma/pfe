/* ═══════════════════════════════════════════════════════════════════════
   BFPME Risk Platform — app.js
═══════════════════════════════════════════════════════════════════════ */

// ── Config ──────────────────────────────────────────────────────────────
const apiBase = () => document.getElementById('apiBase').value.trim().replace(/\/$/, '');

async function api(path, method = 'GET', body = null) {
  const res = await fetch(`${apiBase()}${path}`, {
    method,
    headers: { 'Content-Type': 'application/json' },
    body: body ? JSON.stringify(body) : null
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail || JSON.stringify(data));
  return data;
}

// ── Chart registry (destroy before recreate) ─────────────────────────────
const charts = {};
function makeChart(id, config) {
  if (charts[id]) { charts[id].destroy(); }
  charts[id] = new Chart(document.getElementById(id), config);
  return charts[id];
}

// ── Toast ─────────────────────────────────────────────────────────────────
function toast(msg, type = '') {
  const el = document.createElement('div');
  el.className = `toast ${type}`;
  el.textContent = msg;
  document.body.appendChild(el);
  setTimeout(() => el.remove(), 3200);
}

// ── Risk-class labels (backend values stay low/medium/high — only the
// displayed text is localised; CSS class suffixes must stay untranslated) ──
const RISK_LABEL_FR = { low: 'FAIBLE', medium: 'MOYEN', high: 'ÉLEVÉ' };

// ── Shared state ──────────────────────────────────────────────────────────
let lastFeatures = null;
let lastPrediction = null;

// ══════════════════════════════════════════════════════════════════════════
// NAVIGATION
// ══════════════════════════════════════════════════════════════════════════
const pills = document.querySelectorAll('.nav-pill');
const pages = document.querySelectorAll('.page');

function goTo(pageId) {
  pills.forEach(p => p.classList.toggle('active', p.dataset.page === pageId));
  pages.forEach(p => {
    p.classList.toggle('active', p.id === `page-${pageId}`);
  });
  if (pageId === 'home') initHome();
}

pills.forEach(p => p.addEventListener('click', () => goTo(p.dataset.page)));

// ══════════════════════════════════════════════════════════════════════════
// HEALTH CHECK
// ══════════════════════════════════════════════════════════════════════════
const dot   = document.getElementById('statusDot');
const label = document.getElementById('statusLabel');

async function checkHealth() {
  try {
    await api('/health');
    dot.className = 'status-dot ok';
    label.textContent = 'En ligne';
  } catch {
    dot.className = 'status-dot err';
    label.textContent = 'Hors ligne';
  }
}
checkHealth();
setInterval(checkHealth, 30000);

// ══════════════════════════════════════════════════════════════════════════
// HOME PAGE — DATA / EDA OVERVIEW
// ══════════════════════════════════════════════════════════════════════════
let homeLoaded = false;

// Pastel palette (soft, professional)
const PALETTE = ['#93C5FD', '#6EE7B7', '#FDE68A', '#FCA5A5', '#C4B5FD', '#7DD3FC', '#F9A8D4', '#A7F3D0'];
const RISK_HUE = { Excellent: '#10B981', Bon: '#34D399', Moyen: '#FBBF24', Risque: '#F59E0B', Tres_Risque: '#EF4444', Rejete: '#F87171' };
const COMMON_DONUT = {
  responsive: true, maintainAspectRatio: false, cutout: '62%',
  plugins: { legend: { position: 'bottom', labels: { font: { size: 11 }, boxWidth: 11, padding: 12, usePointStyle: true } } }
};

const labelTidy = s => s.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());

async function initHome() {
  if (homeLoaded) return;

  let eda = null;
  try {
    eda = await api('/metadata/eda');
  } catch { /* offline — leave shimmer */ }

  if (!eda || !eda.available) return;
  homeLoaded = true;

  const s = eda.summary;
  const setKpi = (cardId, valId, text) => {
    document.getElementById(valId).textContent = text;
    const card = document.getElementById(cardId);
    card.classList.remove('shimmer');
    card.classList.add('loaded');
  };
  setKpi('kpiRows',     'kpiRowsVal',     s.rows.toLocaleString());
  setKpi('kpiFeats',    'kpiFeatsVal',    s.features);
  setKpi('kpiDefault',  'kpiDefaultVal',  s.default_rate != null ? `${(s.default_rate * 100).toFixed(1)}%` : '—');
  setKpi('kpiSectors',  'kpiSectorsVal',  s.n_sectors ?? '—');
  setKpi('kpiComplete', 'kpiCompleteVal', s.completeness != null ? `${(s.completeness * 100).toFixed(1)}%` : '—');

  drawHomeCharts(eda);
}

function drawHomeCharts(eda) {
  const s = eda.summary;

  // ── Credit risk distribution (default vs non-default) ──
  document.getElementById('dcDefault').textContent =
    s.default_rate != null ? `${(s.default_rate * 100).toFixed(0)}%` : '—';

  makeChart('chartTarget', {
    type: 'doughnut',
    data: {
      labels: ['Défaut', 'Non-Défaut'],
      datasets: [{ data: [s.default_count, s.non_default_count], backgroundColor: ['#F87171', '#34D399'], borderWidth: 3, borderColor: '#fff', hoverOffset: 8 }]
    },
    options: { ...COMMON_DONUT, cutout: '72%', plugins: { legend: { display: false } } }
  });
  const tot = (s.default_count || 0) + (s.non_default_count || 0) || 1;
  document.getElementById('targetLegend').innerHTML = [
    ['Défaut', s.default_count, '#F87171'], ['Non-Défaut', s.non_default_count, '#34D399']
  ].map(([l, c, col]) => `<div class="legend-item"><div class="legend-dot" style="background:${col}"></div>${l} — ${c.toLocaleString()} (${(c / tot * 100).toFixed(0)}%)</div>`).join('');

  // ── Risk class breakdown (horizontal bar, rating-coloured) ──
  const rc = eda.risk_class;
  makeChart('chartRiskClass', {
    type: 'bar',
    data: {
      labels: rc.map(d => labelTidy(d.label)),
      datasets: [{
        data: rc.map(d => d.count),
        backgroundColor: rc.map(d => RISK_HUE[d.label] || '#93C5FD'),
        borderRadius: 6, borderSkipped: false
      }]
    },
    options: {
      indexAxis: 'y', responsive: true, maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: { x: { grid: { color: '#EFF6FF' }, ticks: { font: { size: 10 } } }, y: { grid: { display: false }, ticks: { font: { size: 11 } } } }
    }
  });

  // ── Economic scenario mix (donut) ──
  drawCatDonut('chartScenario', eda.scenario, ['#7DD3FC', '#FDE68A', '#FCA5A5']);

  // ── Sector distribution (vertical bar) ──
  const sec = eda.sector;
  makeChart('chartSector', {
    type: 'bar',
    data: {
      labels: sec.map(d => labelTidy(d.label)),
      datasets: [{ data: sec.map(d => d.count), backgroundColor: '#93C5FD', borderRadius: 6, borderSkipped: false }]
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: { x: { grid: { display: false }, ticks: { font: { size: 10 } } }, y: { grid: { color: '#EFF6FF' }, ticks: { font: { size: 10 } } } }
    }
  });

  // ── SME classification (donut) ──
  drawCatDonut('chartClassification', eda.classification, ['#C4B5FD', '#93C5FD', '#A7F3D0']);

  // ── Regional spread (vertical bar) ──
  const reg = eda.region;
  makeChart('chartRegion', {
    type: 'bar',
    data: {
      labels: reg.map(d => labelTidy(d.label)),
      datasets: [{ data: reg.map(d => d.count), backgroundColor: '#6EE7B7', borderRadius: 6, borderSkipped: false }]
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: { x: { grid: { display: false }, ticks: { font: { size: 10 } } }, y: { grid: { color: '#EFF6FF' }, ticks: { font: { size: 10 } } } }
    }
  });

  // ── Loan amount histogram ──
  const lh = eda.loan_hist;
  const edges = lh.edges || [];
  const histLabels = (lh.counts || []).map((_, i) => {
    const lo = edges[i] ?? 0;
    return `${(lo / 1000).toFixed(0)}k`;
  });
  makeChart('chartLoanHist', {
    type: 'bar',
    data: {
      labels: histLabels,
      datasets: [{ data: lh.counts || [], backgroundColor: '#7DD3FC', borderRadius: 5, borderSkipped: false }]
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { display: false }, tooltip: { callbacks: { title: items => `≈ ${items[0].label} TND`, label: ctx => ` ${ctx.parsed.y} clients` } } },
      scales: { x: { grid: { display: false }, ticks: { font: { size: 9 }, maxRotation: 0 } }, y: { grid: { color: '#EFF6FF' }, ticks: { font: { size: 10 } } } }
    }
  });
}

function drawCatDonut(id, items, colors) {
  makeChart(id, {
    type: 'doughnut',
    data: {
      labels: items.map(d => labelTidy(d.label)),
      datasets: [{ data: items.map(d => d.count), backgroundColor: colors || PALETTE, borderWidth: 3, borderColor: '#fff', hoverOffset: 8 }]
    },
    options: COMMON_DONUT
  });
}

// ══════════════════════════════════════════════════════════════════════════
// PREDICTION PAGE
// ══════════════════════════════════════════════════════════════════════════
// Coerce a raw form string to number / string / null, matching the model's
// expected types ('' → null so it can fall back to a baseline default).
function coerceFormValue(val) {
  if (val === '' || val == null) return null;
  const num = Number(val);
  return isNaN(num) ? val : num;
}

// Snapshot of the form's *default* values — a complete, coherent payload that
// covers every model feature. Read lazily from the controls' defaults
// (defaultValue / first option), so it is unaffected by later user edits.
let baselineFeatures = null;
function getBaselineFeatures() {
  if (baselineFeatures) return baselineFeatures;
  const form = document.getElementById('predForm');
  const out = {};
  form.querySelectorAll('input[name], select[name], textarea[name]').forEach(el => {
    let raw;
    if (el.tagName === 'SELECT') {
      const opt = [...el.options].find(o => o.defaultSelected) || el.options[0];
      raw = opt ? opt.value : '';
    } else {
      raw = el.defaultValue;
    }
    out[el.name] = coerceFormValue(raw);
  });
  baselineFeatures = out;
  return baselineFeatures;
}

// Numeric mapping of BFPME risk class -> risk index, per
// texts/dataset_final_variable_dictionary.txt.
const RISK_CLASS_INDEX = {
  Excellent: 0.08, Bon: 0.22, Moyen: 0.45, Risque: 0.68, Tres_Risque: 0.85, Rejete: 0.97
};

// Build a FULL feature payload: start from the complete baseline, then overlay
// whatever the user actually filled in. This way changing only a few fields
// still yields a complete prediction — blank fields fall back to the baseline
// instead of becoming null (which the model would silently median-impute).
function formToFeatures() {
  const form = document.getElementById('predForm');
  const merged = { ...getBaselineFeatures() };
  new FormData(form).forEach((val, key) => {
    const v = coerceFormValue(val);
    if (v !== null) merged[key] = v;   // only override when the user provided a value
  });
  merged.bfpme_risk_index = RISK_CLASS_INDEX[merged.risk_class] ?? 0.45;
  return merged;
}

let gaugeChart = null;

function renderGauge(pd) {
  const pct = Math.round(pd * 100);
  document.getElementById('gaugePct').textContent = `${pct}%`;

  const color = pd >= 0.7 ? '#EF4444' : pd >= 0.4 ? '#F59E0B' : '#10B981';
  const remaining = 1 - pd;

  if (gaugeChart) gaugeChart.destroy();
  gaugeChart = new Chart(document.getElementById('chartGauge'), {
    type: 'doughnut',
    data: {
      datasets: [{
        data: [pd, remaining],
        backgroundColor: [color, '#EFF6FF'],
        borderWidth: 0,
        circumference: 180,
        rotation: 270
      }]
    },
    options: {
      responsive: false,
      cutout: '78%',
      plugins: { legend: { display: false }, tooltip: { enabled: false } },
      animation: { duration: 800 }
    }
  });
}

function showResult(data) {
  document.getElementById('resultPlaceholder').classList.add('hidden');
  const panel = document.getElementById('resultPanel');
  panel.classList.remove('hidden');

  const pd  = data.probability_default;
  const pnd = data.probability_non_default;
  const rc  = data.risk_class;

  renderGauge(pd);

  document.getElementById('resPD').textContent  = `${(pd  * 100).toFixed(1)}%`;
  document.getElementById('resPND').textContent = `${(pnd * 100).toFixed(1)}%`;
  document.getElementById('resThr').textContent = data.threshold;

  const badge = document.getElementById('riskBadge');
  badge.textContent = RISK_LABEL_FR[rc] || rc.toUpperCase();
  badge.className = `result-badge badge-${rc.toLowerCase()}`;
}

document.getElementById('predForm').addEventListener('submit', async e => {
  e.preventDefault();
  const btn = document.getElementById('btnPredict');
  btn.disabled = true;
  btn.innerHTML = '<span class="btn-icon">⏳</span> Calcul en cours…';

  try {
    const features = formToFeatures();
    lastFeatures = features;
    // No threshold query → backend applies DEFAULT_THRESHOLD from .env.
    const result = await api('/predict', 'POST', { features });
    lastPrediction = result;
    showResult(result);
    toast('Prédiction terminée', 'success');
  } catch (err) {
    toast(err.message, 'error');
  } finally {
    btn.disabled = false;
    btn.innerHTML = '<span class="btn-icon">▶</span> Lancer la Prédiction';
  }
});

document.getElementById('btnReset').addEventListener('click', () => {
  document.getElementById('predForm').reset();
  document.getElementById('resultPanel').classList.add('hidden');
  document.getElementById('resultPlaceholder').classList.remove('hidden');
});

document.getElementById('btnGoShap').addEventListener('click', () => goTo('shap'));
document.getElementById('btnGoLLM').addEventListener('click', () => {
  goTo('llm');
  if (lastFeatures) {
    document.getElementById('llmFeaturesInput').value = JSON.stringify(lastFeatures, null, 2);
  }
});

// Info-tip popovers (click or keyboard to open, click outside to close)
document.querySelectorAll('.info-tip-icon').forEach(icon => {
  const wrap = icon.closest('.info-tip');
  const toggle = () => {
    const willOpen = !wrap.classList.contains('open');
    document.querySelectorAll('.info-tip.open').forEach(t => t.classList.remove('open'));
    wrap.classList.toggle('open', willOpen);
  };
  icon.addEventListener('click', e => { e.stopPropagation(); toggle(); });
  icon.addEventListener('keydown', e => {
    if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); e.stopPropagation(); toggle(); }
  });
});
document.addEventListener('click', () => {
  document.querySelectorAll('.info-tip.open').forEach(t => t.classList.remove('open'));
});

// Accordion toggle
document.querySelectorAll('.fgc-header').forEach(h => {
  h.addEventListener('click', () => {
    const bodyId = h.dataset.toggle;
    const body   = document.getElementById(bodyId);
    const open   = body.classList.contains('open');
    body.classList.toggle('open', !open);
    body.classList.toggle('closed', open);
    h.classList.toggle('collapsed', open);
  });
});

// ══════════════════════════════════════════════════════════════════════════
// SHAP PAGE
// ══════════════════════════════════════════════════════════════════════════
const shapTopKInput = document.getElementById('shapTopK');
const shapTopKVal   = document.getElementById('shapTopKVal');
shapTopKInput.addEventListener('input', () => { shapTopKVal.textContent = shapTopKInput.value; });

document.getElementById('btnExplain').addEventListener('click', async () => {
  if (!lastFeatures) { toast('Lancez d\'abord une prédiction pour charger les données du client.', 'error'); return; }

  const btn = document.getElementById('btnExplain');
  btn.disabled = true;
  btn.innerHTML = '<span class="btn-icon">⏳</span> Calcul SHAP en cours…';

  try {
    const topK  = Number(shapTopKInput.value);
    const result = await api(`/explain?top_k=${topK}`, 'POST', { features: lastFeatures });
    renderShap(result);
    toast('Analyse SHAP terminée', 'success');
  } catch (err) {
    toast(err.message, 'error');
  } finally {
    btn.disabled = false;
    btn.innerHTML = '<span class="btn-icon">🔬</span> Expliquer le Dernier Client';
  }
});

// Shared "highest-impact variables" list, fed by SHAP results wherever they're
// computed (SHAP page's Explain button, or the LLM chat's Run SHAP tool call).
// Surfaced on both the SHAP page and the LLM sidebar so analysts know which
// fields to prioritise when framing a what-if scenario.
function renderInfluentialList(containerId, contribs) {
  const list = document.getElementById(containerId);
  if (!list) return;
  if (!contribs || !contribs.length) {
    list.innerHTML = '<li class="influential-empty">Pas encore de données SHAP.</li>';
    return;
  }
  const maxAbs = Math.max(...contribs.map(c => Math.abs(c.shap_value))) || 1;
  list.innerHTML = contribs.map((c, i) => {
    const name = c.feature.replace(/^(plain_num__|winsor_num__|cat__|ord__|nom__)/, '');
    const up = c.shap_value >= 0;
    const pct = Math.round((Math.abs(c.shap_value) / maxAbs) * 100);
    return `<li class="infl-row">
      <span class="infl-rank">${i + 1}</span>
      <span class="infl-name" title="${name}">${name}</span>
      <span class="infl-bar-wrap"><span class="infl-bar ${up ? 'up' : 'down'}" style="width:${pct}%"></span></span>
      <span class="infl-dir ${up ? 'up' : 'down'}">${up ? '▲' : '▼'}</span>
    </li>`;
  }).join('');
}

function renderShap(data) {
  document.getElementById('shapPlaceholder').classList.add('hidden');
  document.getElementById('shapResult').classList.remove('hidden');

  document.getElementById('shapBase').textContent  = data.base_value.toFixed(3);
  const finalEl = document.getElementById('shapFinal');
  finalEl.textContent = (data.prediction * 100).toFixed(1) + '%';
  finalEl.className = `ss-value ${data.prediction >= 0.5 ? 'danger' : ''}`;

  const contribs = data.top_contributions;
  renderInfluentialList('shapInfluentialList', contribs);
  renderInfluentialList('llmInfluentialList', contribs);
  updateStressParamsFromShap(contribs);
  const labels   = contribs.map(c => c.feature.replace(/^(plain_num__|winsor_num__|cat__|ord__|nom__)/, ''));
  const values   = contribs.map(c => c.shap_value);
  const colors   = values.map(v => v >= 0 ? 'rgba(239,68,68,.75)' : 'rgba(16,185,129,.75)');
  const borders  = values.map(v => v >= 0 ? '#EF4444' : '#10B981');

  makeChart('chartShap', {
    type: 'bar',
    data: {
      labels,
      datasets: [{
        data: values,
        backgroundColor: colors,
        borderColor: borders,
        borderWidth: 1.5,
        borderRadius: 6,
        borderSkipped: false
      }]
    },
    options: {
      indexAxis: 'y',
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        x: { grid: { color: '#EFF6FF' }, ticks: { font: { size: 11 } } },
        y: { grid: { display: false }, ticks: { font: { size: 11 } } }
      },
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: ctx => ` SHAP : ${ctx.parsed.x >= 0 ? '+' : ''}${ctx.parsed.x.toFixed(4)}`
          }
        }
      }
    }
  });

  const tbody = document.querySelector('#shapTable tbody');
  tbody.innerHTML = contribs.map((c, i) => {
    const name = c.feature.replace(/^(plain_num__|winsor_num__|cat__|ord__|nom__)/, '');
    const dir  = c.direction === 'increase_risk'
      ? '<span class="dir-up">▲ Augmente le risque</span>'
      : '<span class="dir-down">▼ Diminue le risque</span>';
    const shap = c.shap_value >= 0 ? `+${c.shap_value.toFixed(4)}` : c.shap_value.toFixed(4);
    return `<tr>
      <td>${name}</td>
      <td>${typeof c.value === 'number' ? c.value.toFixed(3) : c.value}</td>
      <td><strong>${shap}</strong></td>
      <td>${dir}</td>
    </tr>`;
  }).join('');
}

// ══════════════════════════════════════════════════════════════════════════
// LLM CHAT PAGE
// ══════════════════════════════════════════════════════════════════════════
const chatMessages = document.getElementById('chatMessages');
let chatHistory = [];

function addMessage(role, text) {
  const isUser = role === 'user';
  const time = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  const div = document.createElement('div');
  div.className = `chat-msg ${role}`;
  div.innerHTML = `<div class="msg-bubble">${text.replace(/\n/g, '<br>')}</div><div class="msg-time">${time}</div>`;
  // Remove welcome screen on first message
  const welcome = chatMessages.querySelector('.chat-welcome');
  if (welcome) welcome.remove();
  chatMessages.appendChild(div);
  chatMessages.scrollTop = chatMessages.scrollHeight;
  return div;
}

function addThinking() {
  const div = document.createElement('div');
  div.className = 'chat-msg assistant';
  div.id = 'thinkingBubble';
  div.innerHTML = `<div class="msg-bubble thinking-dots"><span></span><span></span><span></span></div>`;
  chatMessages.appendChild(div);
  chatMessages.scrollTop = chatMessages.scrollHeight;
  return div;
}

// ── What-if parsing: turn plain language (FR or EN) into real feature
// overrides. Accents are stripped before matching so "région"/"scénario"
// match the same as "region"/"scenario". ─────────────────────────────────
const stripAccents = s => s.normalize('NFD').replace(/[\u0300-\u036f]/g, '');

// Numeric fields: keyword + ("by N%" change, or "to / = / at / à V" absolute set).
const WHATIF_NUM = [
  { kw: ['inflation'],                                            field: 'taux_inflation' },
  { kw: ['gdp', 'pib', 'growth', 'croissance'],                   field: 'croissance_pib' },
  { kw: ['unemployment', 'chomage'],                              field: 'taux_chomage' },
  { kw: ['policy rate', 'central bank', 'directeur'],             field: 'taux_directeur' },
  { kw: ['interest', 'teg', 'interet'],                           field: 'taux_interet_teg' },
  { kw: ['revenue', 'turnover', 'sales', 'chiffre'],              field: 'chiffre_affaires_annuel' },
  { kw: ['loan amount', 'loan', 'montant du pret', 'montant'],    field: 'montant_pret' },
  { kw: ['collateral', 'garantie'],                               field: 'valeur_garanties' },
  { kw: ['short-term debt', 'short term debt', 'dettes court', 'court terme'], field: 'dettes_court_terme' },
  { kw: ['long-term debt', 'long term debt', 'dettes long', 'long terme'],     field: 'dettes_long_terme' },
  { kw: ['equity', 'capitaux propres'],                           field: 'capitaux_propres' },
  { kw: ['cash', 'tresorerie'],                                   field: 'tresorerie_disponible' },
  { kw: ['payment delay', 'delay', 'retard'],                     field: 'retards_paiement_jours_moyen' },
  { kw: ['unpaid', 'impaye'],                                     field: 'montant_impayes' },
  { kw: ['employee', 'employe', 'staff', 'headcount'],            field: 'nombre_employes' },
  { kw: ['company age', 'anciennete'],                            field: 'anciennete_entreprise' },
  { kw: ['duration', 'maturity', 'duree'],                        field: 'duree_mois' },
  { kw: ['sector risk', 'risque sectoriel'],                      field: 'risque_sectoriel' },
  { kw: ['country risk', 'region risk', 'risque pays'],           field: 'risque_pays_region' },
];
// Categorical fields: keyword + an explicit valid value mentioned.
const WHATIF_CAT = [
  { kw: ['region'],                              field: 'region_localisation', values: ['Centre', 'Nord', 'Sud', 'Est', 'Ouest', 'Littoral'] },
  { kw: ['sector', 'secteur'],                   field: 'secteur_activite',    values: ['commerce', 'agriculture', 'btp', 'industrie', 'services', 'tourisme'] },
  { kw: ['zone'],                                field: 'zone_localisation',   values: ['urbaine', 'rurale', 'industrielle'] },
  { kw: ['classification', 'size', 'taille'],    field: 'classification_pme',  values: ['micro', 'petite', 'moyenne'] },
  { kw: ['legal', 'juridique', 'structure'],     field: 'structure_juridique', values: ['SARL', 'SA', 'Entreprise_individuelle'] },
  { kw: ['scenario', 'conjoncture'],             field: 'scenario_economique', values: ['normal', 'degrade', 'severe'] },
  { kw: ['rate type', 'type taux', 'type de taux'], field: 'type_taux',        values: ['fixe', 'variable'] },
  { kw: ['objective', 'objectif', 'financing'],  field: 'objectif_financement', values: ['investissement', 'exploitation', 'expansion'] },
];

function parseWhatIf(message, features) {
  const changes = {};
  const text = stripAccents(` ${message.toLowerCase()} `);

  for (const c of WHATIF_CAT) {
    if (!c.kw.some(k => text.includes(stripAccents(k)))) continue;
    for (const v of c.values) {
      if (new RegExp(`\\b${stripAccents(v.toLowerCase())}\\b`).test(text)) { changes[c.field] = v; break; }
    }
  }

  for (const m of WHATIF_NUM) {
    const kw = m.kw.find(k => text.includes(stripAccents(k)));
    if (!kw) continue;
    const base = features && typeof features[m.field] === 'number' ? features[m.field] : null;
    const win = text.slice(text.indexOf(stripAccents(kw)), text.indexOf(stripAccents(kw)) + 70);

    const pctM = win.match(/(-?\d+(?:\.\d+)?)\s*%/);
    const absM = win.match(/(?:to|=|at|a)\s*([\d.,]+)\s*(k|m|million|millions|mille)?/);

    if (pctM && base != null) {
      const signed = parseFloat(pctM[1]);
      const p = Math.abs(signed) / 100;
      const down = /(drop|decrease|reduce|fall|fell|lower|decline|cut|loses?|shrink|down|baisse|baisser|diminue|diminuer|recule|reduit|chute|effondr)/.test(win);
      const up = /(increase|rise|rises|grow|grew|higher|gain|jump|surge|\bup\b|augmente|augmenter|hausse|monte|grimpe|progresse|accroit)/.test(win);
      const goesDown = signed < 0 || (down && !up);
      changes[m.field] = +(base * (goesDown ? 1 - p : 1 + p)).toFixed(4);
    } else if (absM) {
      let val = parseFloat(absM[1].replace(/,/g, ''));
      const unit = absM[2];
      if (unit === 'k' || unit === 'mille') val *= 1e3;
      if (unit === 'm' || unit === 'million' || unit === 'millions') val *= 1e6;
      if (!isNaN(val)) changes[m.field] = val;
    }
  }
  return changes;
}

function parseManualOverrides(str) {
  const out = {};
  if (!str.trim()) return out;
  str.split(',').forEach(pair => {
    const parts = pair.split(/[:=]/);
    if (parts.length < 2) return;
    const key = parts[0].trim();
    const val = parts.slice(1).join('=').trim();
    if (!key) return;
    const num = Number(val);
    out[key] = val !== '' && !isNaN(num) ? num : val;
  });
  return out;
}

function showDetected(changes) {
  const box = document.getElementById('whatifDetected');
  const keys = Object.keys(changes);
  if (!keys.length) { box.classList.add('hidden'); box.innerHTML = ''; return; }
  box.classList.remove('hidden');
  box.innerHTML = `<div class="wd-title">Sera relancé avec :</div>` +
    keys.map(k => `<span class="wd-chip">${k} = ${changes[k]}</span>`).join('');
}

function addScenarioCard(s) {
  const dir = s.delta_pd > 0.0005 ? 'up' : s.delta_pd < -0.0005 ? 'down' : 'flat';
  const arrow = dir === 'up' ? '▲' : dir === 'down' ? '▼' : '▬';
  const cls = dir === 'up' ? 'sc-up' : dir === 'down' ? 'sc-down' : 'sc-flat';
  const pct = v => `${(v * 100).toFixed(1)}%`;
  const changed = Object.entries(s.changed_features)
    .map(([k, v]) => `<span class="sc-chip">${k} = ${v}</span>`).join('');

  const div = document.createElement('div');
  div.className = 'chat-msg assistant';
  div.innerHTML = `<div class="msg-bubble scenario-card">
    <div class="sc-title">🔮 Modèle relancé avec votre scénario hypothétique</div>
    <div class="sc-changes">${changed}</div>
    <div class="sc-flow">
      <div class="sc-cell"><span class="sc-lbl">PD de Base</span><span class="sc-val">${pct(s.baseline_pd)}</span><span class="sc-rc">${RISK_LABEL_FR[s.baseline_risk_class] || s.baseline_risk_class}</span></div>
      <div class="sc-arrow ${cls}">${arrow}</div>
      <div class="sc-cell"><span class="sc-lbl">Nouvelle PD</span><span class="sc-val">${pct(s.scenario_pd)}</span><span class="sc-rc">${RISK_LABEL_FR[s.scenario_risk_class] || s.scenario_risk_class}</span></div>
    </div>
    <div class="sc-delta ${cls}">Δ ${s.delta_pd >= 0 ? '+' : ''}${(s.delta_pd * 100).toFixed(1)} pts ${dir === 'up' ? '(plus risqué)' : dir === 'down' ? '(plus sûr)' : '(aucun changement)'}</div>
  </div>`;
  const welcome = chatMessages.querySelector('.chat-welcome');
  if (welcome) welcome.remove();
  chatMessages.appendChild(div);
  chatMessages.scrollTop = chatMessages.scrollHeight;
}

async function sendChat(message) {
  if (!message.trim()) return;

  const featText = document.getElementById('llmFeaturesInput').value.trim();
  let features = lastFeatures;
  if (featText) {
    try { features = JSON.parse(featText); } catch { toast('JSON invalide dans les données client', 'error'); return; }
  }
  if (!features) { toast('Aucune donnée client chargée. Remplissez le formulaire de prédiction ou collez du JSON.', 'error'); return; }

  // Build what-if overrides: natural language + explicit box (box wins).
  const parsed = parseWhatIf(message, features);
  const manual = parseManualOverrides(document.getElementById('whatifInput').value);
  const scenarioChanges = { ...parsed, ...manual };
  const hasScenario = Object.keys(scenarioChanges).length > 0;
  showDetected(scenarioChanges);

  const looksWhatIf = /\bwhat\s*if\b|\bif\b.*\b(change|increase|decrease|drop|rise|becomes?)\b|\bet si\b|\bsi\b.*\b(change|augmente|diminue|baisse)\b/.test(message.toLowerCase());
  if (!hasScenario && looksWhatIf) {
    toast('Impossible de détecter automatiquement le changement — indiquez-le dans la zone Scénario Hypothétique, ex. region_localisation=Sud', 'error');
  }

  const btn = document.getElementById('btnSendChat');
  btn.disabled = true;
  document.getElementById('chatPrompt').value = '';

  addMessage('user', message);
  const thinking = addThinking();

  try {
    const result = await api('/chat/analyze', 'POST', {
      message,
      features,
      run_validation:  document.getElementById('llmRunVal').checked,
      run_prediction:  document.getElementById('llmRunPred').checked,
      run_explanation: document.getElementById('llmRunExpl').checked,
      scenario_changes: hasScenario ? scenarioChanges : null,
      threshold: 0.5,
      top_k_shap: 5
    });

    thinking.remove();

    const scenario = result.tool_results?.scenario;
    if (scenario) addScenarioCard(scenario);

    const explanation = result.tool_results?.explanation;
    if (explanation?.top_contributions) {
      renderInfluentialList('llmInfluentialList', explanation.top_contributions);
      renderInfluentialList('shapInfluentialList', explanation.top_contributions);
      updateStressParamsFromShap(explanation.top_contributions);
    }

    // Prefer whatever the backend returned (LLM summary, or a graceful note if the LLM failed).
    let text = result.llm_summary;
    if (!text) {
      const p = result.tool_results?.prediction;
      text = p
        ? `PD calculée : ${(p.probability_default * 100).toFixed(1)}% — classe de risque « ${RISK_LABEL_FR[p.risk_class] || p.risk_class} ».`
        : `Résultat calculé : ${JSON.stringify(result.tool_results, null, 2)}`;
    }
    addMessage('assistant', text);
  } catch (err) {
    thinking.remove();
    addMessage('assistant', `⚠️ Erreur : ${err.message}`);
  } finally {
    btn.disabled = false;
  }
}

document.getElementById('btnSendChat').addEventListener('click', () => {
  sendChat(document.getElementById('chatPrompt').value);
});
document.getElementById('chatPrompt').addEventListener('keydown', e => {
  if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendChat(e.target.value); }
});
document.querySelectorAll('.suggestion-chip').forEach(c =>
  c.addEventListener('click', () => sendChat(c.dataset.msg))
);
document.getElementById('btnLlmLoadLast').addEventListener('click', () => {
  if (lastFeatures) {
    document.getElementById('llmFeaturesInput').value = JSON.stringify(lastFeatures, null, 2);
    toast('Données client chargées', 'success');
  } else {
    toast('Aucune prédiction encore lancée', 'error');
  }
});
document.getElementById('btnClearChat').addEventListener('click', () => {
  chatMessages.innerHTML = `
    <div class="chat-welcome">
      <div class="chat-welcome-icon">🤖</div>
      <div class="chat-welcome-title">Analyste Crédit BFPME</div>
      <div class="chat-welcome-sub">Posez-moi n'importe quelle question sur le profil de risque de crédit d'un client</div>
      <div class="chat-suggestions">
        <button class="suggestion-chip" data-msg="Ce client est-il à haut risque ? Résumez les principaux facteurs de risque.">Ce client est-il à haut risque ?</button>
        <button class="suggestion-chip" data-msg="Quelles actions pourraient améliorer la probabilité de défaut de ce client ?">Comment améliorer le score ?</button>
        <button class="suggestion-chip" data-msg="Expliquez les 3 principaux facteurs qui augmentent le risque pour ce client.">Principaux facteurs de risque ?</button>
      </div>
    </div>`;
  document.querySelectorAll('.suggestion-chip').forEach(c =>
    c.addEventListener('click', () => sendChat(c.dataset.msg))
  );
});

// ══════════════════════════════════════════════════════════════════════════
// MONTE CARLO PAGE  (backend /monte-carlo engine)
// ══════════════════════════════════════════════════════════════════════════

// Fields safe to stress-test: genuine RAW inputs only. Engineered ratios
// (payment_stress_index, garantie_to_loan, cash_to_debt, ...) are excluded
// on purpose — the backend re-derives them from the raw fields on every
// simulated draw (monte_carlo_service.apply_feature_engineering), so
// shocking the ratio directly would just get silently overwritten.
const SHOCKABLE_FIELDS = {
  chiffre_affaires_annuel:       { label: "Chiffre d'Affaires Annuel",        max: 50, pct: 20 },
  dettes_court_terme:            { label: 'Dettes à Court Terme',             max: 60, pct: 25 },
  valeur_garanties:              { label: 'Valeur des Garanties',             max: 50, pct: 15 },
  retards_paiement_jours_moyen:  { label: 'Retards de Paiement',              max: 80, pct: 30 },
  croissance_pib:                { label: 'Croissance du PIB',                max: 80, pct: 40 },
  tresorerie_disponible:         { label: 'Trésorerie Disponible',            max: 60, pct: 25 },
  fonds_roulement_fdr:           { label: 'Fonds de Roulement (FDR)',         max: 60, pct: 25 },
  capitaux_propres:              { label: 'Capitaux Propres',                 max: 50, pct: 20 },
  nombre_employes:               { label: 'Employés',                        max: 40, pct: 15 },
  total_passif:                  { label: 'Total Passif',                    max: 50, pct: 20 },
  total_actif:                   { label: 'Total Actif',                     max: 50, pct: 20 },
  taux_interet_teg:              { label: "Taux d'Intérêt TEG",              max: 40, pct: 15 },
  apport_personnel:              { label: 'Apport Personnel',                 max: 50, pct: 20 },
  montant_total_investissement:  { label: 'Investissement Total',             max: 50, pct: 20 },
  montant_pret:                  { label: 'Montant du Prêt',                  max: 40, pct: 15 },
  montant_impayes:                { label: 'Montant des Impayés',             max: 90, pct: 40 },
  dettes_long_terme:             { label: 'Dettes à Long Terme',              max: 60, pct: 25 },
  besoin_fonds_roulement_bfr:    { label: 'Besoin en Fonds de Roulement (BFR)', max: 60, pct: 25 },
  taux_inflation:                { label: "Taux d'Inflation",                max: 70, pct: 30 },
  taux_directeur:                { label: 'Taux Directeur',                   max: 70, pct: 30 },
  taux_chomage:                  { label: 'Taux de Chômage',                  max: 50, pct: 20 },
  risque_sectoriel:              { label: 'Risque Sectoriel',                 max: 50, pct: 20 },
  risque_pays_region:            { label: 'Risque Pays/Région',               max: 50, pct: 20 },
  anciennete_entreprise:         { label: "Âge de l'Entreprise",             max: 40, pct: 15 },
  capital_social:                { label: 'Capital Social',                   max: 50, pct: 20 },
  duree_mois:                    { label: 'Durée du Prêt',                    max: 40, pct: 15 },
};

const DEFAULT_STRESS_FIELDS = [
  'chiffre_affaires_annuel', 'dettes_court_terme', 'valeur_garanties',
  'retards_paiement_jours_moyen', 'croissance_pib'
];

// Build the stress-parameter sliders for the given raw field names.
function renderStressParams(fieldNames) {
  const container = document.getElementById('stressParamsContainer');
  container.innerHTML = fieldNames.map(field => {
    const cfg = SHOCKABLE_FIELDS[field];
    if (!cfg) return '';
    return `<div class="stress-param">
      <div class="sp-row">
        <span class="sp-label">${cfg.label}</span>
        <span class="sp-pct">±${cfg.pct}%</span>
      </div>
      <input type="range" class="stress-slider" min="0" max="${cfg.max}" value="${cfg.pct}" data-field="${field}" />
    </div>`;
  }).join('');
  container.querySelectorAll('.stress-slider').forEach(sl => {
    const pctLabel = sl.closest('.stress-param').querySelector('.sp-pct');
    sl.addEventListener('input', () => { pctLabel.textContent = `±${sl.value}%`; });
  });
}

// Once a SHAP explanation is available, swap the default stress fields for
// the top SHAP-ranked fields for THIS client — but only the ones that are
// genuine raw inputs (see SHOCKABLE_FIELDS comment above), so the sliders
// stay meaningful for the client actually loaded rather than a fixed list.
function updateStressParamsFromShap(contribs) {
  const matched = [];
  for (const c of contribs) {
    const name = c.feature.replace(/^(plain_num__|winsor_num__|cat__|ord__|nom__)/, '');
    if (SHOCKABLE_FIELDS[name] && !matched.includes(name)) matched.push(name);
    if (matched.length >= 5) break;
  }
  const hint = document.getElementById('stressParamsSource');
  if (matched.length >= 2) {
    renderStressParams(matched);
    hint.textContent = 'Basé sur les variables SHAP les plus influentes pour ce client.';
  } else {
    renderStressParams(DEFAULT_STRESS_FIELDS);
    hint.textContent = 'Variables par défaut — lancez une explication SHAP pour les adapter à ce client.';
  }
}

renderStressParams(DEFAULT_STRESS_FIELDS);
document.getElementById('stressParamsSource').textContent =
  'Variables par défaut — lancez une explication SHAP (onglet SHAP) pour les adapter à ce client.';

// Sim count buttons
let simCount = 2000;
document.querySelectorAll('.sim-count-btn').forEach(b => {
  b.addEventListener('click', () => {
    document.querySelectorAll('.sim-count-btn').forEach(x => x.classList.remove('active'));
    b.classList.add('active');
    simCount = Number(b.dataset.n);
  });
});

// Build the shocks list from the sliders (data-field + value%). Skip 0% bands.
function getShocks() {
  return Array.from(document.querySelectorAll('.stress-slider'))
    .map(sl => ({ field: sl.dataset.field, pct: Number(sl.value) / 100 }))
    .filter(s => s.field && s.pct > 0);
}

document.getElementById('btnRunMC').addEventListener('click', async () => {
  const base = lastFeatures;
  if (!base) { toast('Lancez d\'abord une prédiction pour définir le client de base.', 'error'); return; }

  const shocks = getShocks();
  if (!shocks.length) { toast('Définissez au moins une bande de stress supérieure à 0%.', 'error'); return; }

  const btn = document.getElementById('btnRunMC');
  btn.disabled = true;
  btn.innerHTML = '<span class="btn-icon">⏳</span> En cours…';

  const progress    = document.getElementById('mcProgress');
  const progressBar = document.getElementById('mcProgressBar');
  const progressLbl = document.getElementById('mcProgressLabel');
  progress.classList.remove('hidden');

  // One batched backend call → indeterminate progress: ease to ~90%, then finish.
  let pct = 0;
  progressBar.style.width = '0%'; progressLbl.textContent = '0%';
  const tick = setInterval(() => {
    pct = Math.min(90, pct + 9);
    progressBar.style.width = `${pct}%`; progressLbl.textContent = `${pct}%`;
  }, 60);

  try {
    const result = await api('/monte-carlo', 'POST', {
      features: base,
      shocks,
      n_simulations: simCount,
      distribution: 'uniform',
      n_bins: 10,
      n_extremes: 3
    });
    clearInterval(tick);
    progressBar.style.width = '100%'; progressLbl.textContent = '100%';
    renderMCResults(result);
    progress.classList.add('hidden');
    toast(`${result.n_simulations} simulations terminées`, 'success');
  } catch (err) {
    clearInterval(tick);
    toast(err.message, 'error');
  } finally {
    btn.disabled = false;
    btn.innerHTML = '<span class="btn-icon">🎲</span> Lancer la Simulation';
    progressBar.style.width = '0%';
  }
});

function renderMCResults(r) {
  document.getElementById('mcPlaceholder').classList.add('hidden');
  document.getElementById('mcResults').classList.remove('hidden');

  const fmt = v => `${(v * 100).toFixed(1)}%`;
  const p = r.percentiles;

  document.getElementById('mcP10').textContent   = fmt(p.p10);
  document.getElementById('mcP50').textContent   = fmt(p.p50);
  document.getElementById('mcP90').textContent   = fmt(p.p90);
  document.getElementById('mcMean').textContent  = fmt(r.mean_pd);
  document.getElementById('mcStd').textContent   = `${(r.std_pd * 100).toFixed(1)}%`;
  document.getElementById('mcVar95').textContent = fmt(r.var_95);
  document.getElementById('mcEs95').textContent  = fmt(r.expected_shortfall_95);

  // Plain-language verdict (now includes VaR / ES / threshold-breach rate)
  const verdict = document.getElementById('mcVerdict');
  const mean = r.mean_pd;
  const lvl  = mean >= 0.7 ? 'high' : mean >= 0.4 ? 'medium' : 'low';
  const icon = lvl === 'high' ? '🔴' : lvl === 'medium' ? '🟠' : '🟢';
  const tone = lvl === 'high' ? 'un stress sévère' : lvl === 'medium' ? 'un stress élevé' : 'une bonne résilience';
  verdict.className = `mc-verdict mc-verdict-${lvl}`;
  verdict.innerHTML =
    `${icon} PD de base <strong>${fmt(r.baseline_pd)}</strong>. Sur <strong>${r.n_simulations}</strong> ` +
    `scénarios simulés, le client montre <strong>${tone}</strong> : PD moyenne <strong>${fmt(mean)}</strong> ` +
    `(σ = ${(r.std_pd * 100).toFixed(1)}%). Dans les 5% de cas les plus défavorables, la PD atteint <strong>${fmt(r.var_95)}</strong> ` +
    `(VaR-95) et atteint en moyenne <strong>${fmt(r.expected_shortfall_95)}</strong> (ES-95). ` +
    `<strong>${(r.prob_exceeds_threshold * 100).toFixed(0)}%</strong> des scénarios franchissent le seuil de décision (${r.threshold}).` +
    (r.notes && r.notes.length ? `<div class="mc-note">${r.notes.join(' ')}</div>` : '');

  // Histogram — backend-provided edges/counts
  const counts = r.histogram.counts;
  const edges  = r.histogram.edges;
  const histLabels = counts.map((_, i) => `${(edges[i] * 100).toFixed(0)}–${(edges[i + 1] * 100).toFixed(0)}%`);
  const histColors = counts.map((_, i) => {
    const mid = (edges[i] + edges[i + 1]) / 2;
    return mid >= 0.7 ? 'rgba(239,68,68,.7)' : mid >= 0.4 ? 'rgba(245,158,11,.7)' : 'rgba(16,185,129,.7)';
  });

  makeChart('chartMCHist', {
    type: 'bar',
    data: {
      labels: histLabels,
      datasets: [{ data: counts, backgroundColor: histColors, borderRadius: 5, borderSkipped: false }]
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { display: false }, tooltip: { callbacks: { label: ctx => ` ${ctx.parsed.y} scénarios` } } },
      scales: {
        x: { grid: { display: false }, ticks: { font: { size: 10 } } },
        y: { grid: { color: '#EFF6FF' }, title: { display: true, text: 'Nombre', font: { size: 11 } } }
      }
    }
  });

  // Risk class breakdown
  const rd = r.risk_distribution;
  makeChart('chartMCRisk', {
    type: 'doughnut',
    data: {
      labels: ['Faible', 'Moyen', 'Élevé'],
      datasets: [{
        data: [rd.low, rd.medium, rd.high],
        backgroundColor: ['#10B981', '#F59E0B', '#EF4444'],
        borderWidth: 3, borderColor: '#fff', hoverOffset: 8
      }]
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      cutout: '65%',
      plugins: { legend: { position: 'bottom', labels: { font: { size: 11 }, boxWidth: 10, padding: 10 } } }
    }
  });

  // Scenario extremes (backend returns n best + n worst, with shocked values)
  const tbody = document.querySelector('#mcExtremeTable tbody');
  tbody.innerHTML = r.extremes.map(s => {
    const cls = s.risk_class === 'high' ? 'dir-up' : s.risk_class === 'medium' ? '' : 'dir-down';
    const inputs = Object.entries(s.features)
      .map(([k, v]) => `${k.replace(/_/g, ' ')}: ${Math.abs(v) >= 1000 ? v.toFixed(0) : v.toFixed(2)}`)
      .join(' · ');
    return `<tr>
      <td>#${s.index}</td>
      <td>${inputs || '—'}</td>
      <td><strong>${(s.probability_default * 100).toFixed(1)}%</strong></td>
      <td><span class="${cls}">${RISK_LABEL_FR[s.risk_class] || s.risk_class.toUpperCase()}</span></td>
    </tr>`;
  }).join('');
}

// ══════════════════════════════════════════════════════════════════════════
// INIT
// ══════════════════════════════════════════════════════════════════════════
initHome();
