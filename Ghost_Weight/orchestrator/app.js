/**
 * app.js — Operation Ghost Wait Orchestrator
 *
 * Manages:
 *   - Phase state and transitions
 *   - Phase rail (collapsed/expanded)
 *   - Tab switching (RED / BLUE / GRC)
 *   - Attack explainer overlay
 *   - SIEM log polling (OpenSearch REST API)
 *   - Keyboard controls
 *   - Elapsed timer + clock
 */

'use strict';

// ─── Config ─────────────────────────────────────────────────────────────────
const SIEM_URL = window.SIEM_URL || 'http://localhost:9200';
const SIEM_INDEX = window.SIEM_INDEX || 'qfl-events';
const TOTAL_PHASES = 6;
const POLL_INTERVAL_MS = 3000;
const RAIL_AUTO_COLLAPSE_MS = 4000;
const EXPLAINER_AUTO_DISMISS_MS = 12000;

// ─── State ────────────────────────────────────────────────────────────────
let currentPhase = 1;
let activeTab = 'red';
let phaseData = {};          // loaded phase JSON, keyed by phase number
let startTime = Date.now();
let railCollapseTimer = null;
let explainerDismissTimer = null;
let siemPollTimer = null;
let logFrozen = false;        // true during silent-miss state

// ─── Initialization ───────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  startClock();
  startElapsedTimer();
  loadAllPhases().then(() => {
    renderPhase(currentPhase);
    startSIEMPoll();
  });
  document.addEventListener('keydown', handleKeydown);
  showExplainerAfterLoad();
});

// ─── Phase Loading ────────────────────────────────────────────────────────
async function loadAllPhases() {
  for (let i = 1; i <= TOTAL_PHASES; i++) {
    try {
      const resp = await fetch(`phases/phase_${i}.json`);
      if (resp.ok) {
        phaseData[i] = await resp.json();
      }
    } catch (e) {
      console.warn(`Could not load phase_${i}.json`, e);
      phaseData[i] = getDefaultPhase(i);
    }
  }
}

function getDefaultPhase(n) {
  const phases = [
    { name: 'Recon & Pipeline Enumeration',   atlas: 'AML-T0015', target: 'QL-Assist',        act: 1, act_name: 'THE NEW ATTACK SURFACE' },
    { name: 'Model Behavior Fingerprinting',   atlas: 'AML-T0005', target: 'QL-Assist',        act: 1, act_name: 'THE NEW ATTACK SURFACE' },
    { name: 'Indirect Prompt Injection',        atlas: 'AML-T0051.002', target: 'QL-DocuIntel', act: 2, act_name: "WHY YOUR STACK DOESN'T SEE IT" },
    { name: 'Multi-Agent Trust Exploitation',   atlas: 'AML-T0043', target: 'QL-DocuIntel → QL-FraudSentinel', act: 2, act_name: "WHY YOUR STACK DOESN'T SEE IT" },
    { name: 'Long-Term Memory Poisoning',       atlas: 'AML-T0040', target: 'QL-FraudSentinel', act: 2, act_name: "WHY YOUR STACK DOESN'T SEE IT" },
    { name: 'Objective Hijacking & Impact',     atlas: 'AML-T0048', target: 'QL-FraudSentinel', act: 3, act_name: 'WHAT INSTRUMENTED LOOKS LIKE' },
  ];
  const p = phases[n - 1] || phases[0];
  return {
    phase: n,
    act: p.act,
    act_name: p.act_name,
    name: p.name,
    atlas_technique: p.atlas,
    target_service: p.target,
    default_tab: 'red',
    delivery: 'pre-recorded',
    explainer: {
      badge: 'ATTACK EXPLAINER',
      atlas_id: p.atlas,
      title: p.name,
      body: 'Phase data loading...',
      why_stack_misses: 'Phase data loading...'
    },
    red: {
      attack_context: { name: p.name, atlas_id: p.atlas, target: p.target },
      terminal_mode: 'static',
      terminal_lines: [
        `[*] Phase ${n}: ${p.name}`,
        `[*] Target: ${p.target}`,
        `[*] ATLAS: ${p.atlas}`,
        '',
        '[*] Phase data not yet loaded. Run attack scripts to populate.',
      ]
    },
    blue: {
      detection_status: 'miss',
      gap_analysis: 'Detection coverage analysis loading...',
      control_coverage: []
    },
    grc: {
      risk_score: 20,
      risk_severity: 'LOW',
      control_failures: [],
      regulatory_flags: []
    }
  };
}

// ─── Phase Rendering ──────────────────────────────────────────────────────
function renderPhase(n) {
  const data = phaseData[n] || getDefaultPhase(n);
  currentPhase = n;

  // Update phase rail
  updateRailDots(n);

  // Update status bar
  setText('sb-phase', `${n}/${TOTAL_PHASES}`);
  setText('sb-target', data.target_service || '—');
  setText('sb-technique', data.atlas_technique || '—');

  // Update act indicator
  const actNum = data.act || 1;
  const actNames = {
    1: 'THE NEW ATTACK SURFACE',
    2: "WHY YOUR STACK DOESN'T SEE IT",
    3: 'WHAT INSTRUMENTED LOOKS LIKE'
  };
  setText('act-label', `ACT ${toRoman(actNum)}`);
  setText('act-name', data.act_name || actNames[actNum] || '');

  // Render all three panes
  renderRedTab(data);
  renderBlueTab(data);
  renderGRCTab(data);

  // Switch to default tab
  const defaultTab = data.default_tab || 'red';
  switchTab(defaultTab);

  // Show explainer on phase entry
  if (data.explainer) {
    populateExplainer(data.explainer);
    showExplainer();
  }

  // Reset SIEM log stream for new phase
  resetLogStream();
}

// ─── RED TEAM Tab Rendering ──────────────────────────────────────────────
function renderRedTab(data) {
  const red = data.red || {};
  const ctx = red.attack_context || {};

  setText('red-atlas-badge', ctx.atlas_id || data.atlas_technique || '—');
  setText('red-attack-name', ctx.name || data.name || '—');
  setText('red-target-tag', ctx.target || data.target_service || '—');
  setText('red-delivery-tag', (red.terminal_mode || data.delivery || 'STATIC').toUpperCase());

  // Render terminal
  renderTerminal(red);
}

function renderTerminal(red) {
  const mode = red.terminal_mode || 'static';
  const output = document.getElementById('terminal-output');
  output.innerHTML = '';

  if (mode === 'static' && red.terminal_lines) {
    typewriterLines(output, red.terminal_lines);
  } else if (mode === 'recording') {
    output.innerHTML = `<div class="term-line info">[asciinema] Recording: ${red.terminal_recording || '(not set)'}</div>`;
    // asciinema-player integration done in M8
  } else if (mode === 'live') {
    output.innerHTML = `<div class="term-line info">[LIVE] Connecting to attack script...</div>`;
    // WebSocket integration done in M5
  }
}

function typewriterLines(container, lines, idx = 0) {
  if (idx >= lines.length) return;
  const line = lines[idx];
  const div = document.createElement('div');

  // Detect line type from prefix
  if (line.startsWith('[*]') || line.startsWith('$')) {
    div.className = 'term-line prompt';
  } else if (line.startsWith('[!]') || line.toLowerCase().includes('error')) {
    div.className = 'term-line error';
  } else if (line.startsWith('[>]') || line.startsWith('[+]')) {
    div.className = 'term-line info';
  } else {
    div.className = 'term-line output';
  }

  div.textContent = line;
  container.appendChild(div);

  // Auto-scroll
  const tc = document.getElementById('terminal-container');
  tc.scrollTop = tc.scrollHeight;

  const delay = line.trim() === '' ? 50 : 80;
  setTimeout(() => typewriterLines(container, lines, idx + 1), delay);
}

// ─── BLUE TEAM Tab Rendering ─────────────────────────────────────────────
function renderBlueTab(data) {
  const blue = data.blue || {};
  const status = blue.detection_status || 'miss';
  const tabEl = document.getElementById('tab-blue');

  // Apply visual state
  tabEl.classList.remove('silent-miss');
  logFrozen = false;

  if (status === 'miss') {
    tabEl.classList.add('silent-miss');
    logFrozen = true;
    setHTML('detection-badge', '<span class="detection-badge monitoring">MONITORING</span>');
    setText('blue-service-tag', 'ALL SERVICES ACTIVE');
  } else if (status === 'partial') {
    setHTML('detection-badge', '<span class="detection-badge monitoring">PARTIAL VISIBILITY</span>');
  } else if (status === 'detected') {
    setHTML('detection-badge', '<span class="detection-badge alert-active">⚡ ALERT ACTIVE</span>');
  }

  // Gap analysis
  setText('gap-text', blue.gap_analysis || '');

  // Control coverage matrix
  renderControlMatrix(blue.control_coverage || []);
}

function renderControlMatrix(coverage) {
  const container = document.getElementById('control-matrix');
  container.innerHTML = '';
  coverage.forEach(item => {
    const div = document.createElement('div');
    div.className = `control-item ${item.status || 'gap'}`;
    div.innerHTML = `<div class="dot"></div>${item.control || item}`;
    container.appendChild(div);
  });
}

// ─── GRC Tab Rendering ───────────────────────────────────────────────────
function renderGRCTab(data) {
  const grc = data.grc || {};
  const score = grc.risk_score || 0;

  // Risk meter
  setText('grc-score', score);
  const fill = document.getElementById('grc-risk-fill');
  fill.style.width = `${score}%`;
  fill.className = 'risk-bar-fill ' + getRiskClass(score);

  const severityEl = document.getElementById('grc-severity-label');
  const severity = grc.risk_severity || getRiskSeverityLabel(score);
  severityEl.textContent = severity;
  severityEl.className = 'risk-severity-label ' + getRiskColorClass(score);

  // Control failures
  const cfContainer = document.getElementById('control-failures');
  cfContainer.innerHTML = '';
  (grc.control_failures || []).forEach(item => {
    const div = document.createElement('div');
    const statusType = item.status || 'fail';
    div.className = `control-failure-row ${statusType}`;
    const icon = statusType === 'fail' ? '✕' : statusType === 'warn' ? '△' : '✓';
    div.innerHTML = `
      <span class="cf-icon">${icon}</span>
      <span class="cf-text">${item.description || item}</span>
      <span class="cf-framework">${item.framework || ''}</span>
    `;
    cfContainer.appendChild(div);
  });

  // Regulatory flags
  const tbody = document.getElementById('reg-table-body');
  tbody.innerHTML = '';
  (grc.regulatory_flags || getDefaultRegFlags(score)).forEach(item => {
    const tr = document.createElement('tr');
    const statusClass = (item.status_class || item.status || 'compliant').toLowerCase().replace(/[^a-z]/g, '-');
    tr.innerHTML = `
      <td>${item.regulation || item}</td>
      <td><span class="status-badge ${statusClass}">${item.status || 'COMPLIANT'}</span></td>
    `;
    tbody.appendChild(tr);
  });
}

function getDefaultRegFlags(score) {
  return [
    { regulation: 'NIST AI RMF', status: score > 60 ? 'TRIGGERED' : 'COMPLIANT', status_class: score > 60 ? 'triggered' : 'compliant' },
    { regulation: 'FFIEC AI Guidance', status: score > 70 ? 'TRIGGERED' : 'COMPLIANT', status_class: score > 70 ? 'triggered' : 'compliant' },
    { regulation: 'GLBA', status: score > 75 ? 'UNDER REVIEW' : 'COMPLIANT', status_class: score > 75 ? 'under-review' : 'compliant' },
    { regulation: 'SOX', status: score > 80 ? 'TRIGGERED' : 'GAP IDENTIFIED', status_class: score > 80 ? 'triggered' : 'gap' },
    { regulation: 'SR 11-7', status: 'GAP IDENTIFIED', status_class: 'gap' },
  ];
}

function getRiskClass(s) {
  if (s <= 20) return 'low';
  if (s <= 50) return 'medium';
  if (s <= 80) return 'high';
  return 'critical';
}

function getRiskSeverityLabel(s) {
  if (s <= 20) return 'LOW RISK';
  if (s <= 50) return 'MEDIUM RISK';
  if (s <= 80) return 'HIGH RISK';
  return 'CRITICAL';
}

function getRiskColorClass(s) {
  if (s <= 20) return 'text-green';
  if (s <= 50) return 'text-silver';
  if (s <= 80) return 'text-orange';
  return 'text-orange';
}

// ─── Phase Rail ───────────────────────────────────────────────────────────
function expandRail() {
  document.getElementById('phase-rail').classList.add('expanded');
  clearTimeout(railCollapseTimer);
  railCollapseTimer = setTimeout(collapseRail, RAIL_AUTO_COLLAPSE_MS);
}

function collapseRail() {
  document.getElementById('phase-rail').classList.remove('expanded');
}

function updateRailDots(active) {
  document.querySelectorAll('.rail-dot').forEach(el => {
    const n = parseInt(el.dataset.phase);
    el.className = 'rail-dot ' + (n < active ? 'done' : n === active ? 'active' : 'upcoming');
  });
  document.querySelectorAll('.rail-phase-item').forEach(el => {
    const n = parseInt(el.dataset.phase);
    el.className = 'rail-phase-item ' + (n < active ? 'done' : n === active ? 'active' : '');
  });
}

// Clicking expanded rail items
document.querySelectorAll('.rail-phase-item').forEach(el => {
  el.addEventListener('click', () => {
    const n = parseInt(el.dataset.phase);
    if (!isNaN(n)) goToPhase(n);
  });
});

// ─── Tab Switching ────────────────────────────────────────────────────────
function switchTab(tab) {
  activeTab = tab;
  document.querySelectorAll('.persona-tab').forEach(el => {
    el.classList.toggle('active', el.dataset.tab === tab);
  });
  document.querySelectorAll('.tab-pane').forEach(el => {
    const paneTab = el.id.replace('tab-', '');
    el.classList.toggle('active', paneTab === tab);
  });
}

// ─── Navigation ──────────────────────────────────────────────────────────
function nextPhase() {
  if (currentPhase < TOTAL_PHASES) {
    goToPhase(currentPhase + 1);
  }
}

function prevPhase() {
  if (currentPhase > 1) {
    goToPhase(currentPhase - 1);
  }
}

function goToPhase(n) {
  expandRail();
  renderPhase(n);
}

// ─── Attack Explainer ─────────────────────────────────────────────────────
function populateExplainer(explainer) {
  setText('explainer-atlas-id', explainer.atlas_id || '');
  setText('explainer-title', explainer.title || '');
  setText('explainer-body', explainer.body || '');
  setText('explainer-why', explainer.why_stack_misses || '');
}

function showExplainer() {
  const overlay = document.getElementById('explainer-overlay');
  overlay.classList.add('visible');
  clearTimeout(explainerDismissTimer);
  explainerDismissTimer = setTimeout(hideExplainer, EXPLAINER_AUTO_DISMISS_MS);
}

function hideExplainer() {
  document.getElementById('explainer-overlay').classList.remove('visible');
  clearTimeout(explainerDismissTimer);
}

function toggleExplainer() {
  const overlay = document.getElementById('explainer-overlay');
  if (overlay.classList.contains('visible')) {
    hideExplainer();
  } else {
    const data = phaseData[currentPhase];
    if (data && data.explainer) {
      populateExplainer(data.explainer);
    }
    showExplainer();
  }
}

function showExplainerAfterLoad() {
  // Show explainer on initial load after phases are ready
  // (handled in DOMContentLoaded → loadAllPhases → renderPhase)
}

// ─── SIEM Log Polling ─────────────────────────────────────────────────────
function startSIEMPoll() {
  siemPollTimer = setInterval(pollSIEM, POLL_INTERVAL_MS);
  pollSIEM(); // immediate first poll
}

async function pollSIEM() {
  if (logFrozen) return;  // silent-miss: stop polling

  const today = new Date().toISOString().split('T')[0].replace(/-/g, '.');
  const indexName = `${SIEM_INDEX}-${today}`;
  const url = `${SIEM_URL}/${indexName}/_search`;
  const query = {
    query: {
      term: { atlas_phase: currentPhase }
    },
    sort: [{ '@timestamp': { order: 'desc' } }],
    size: 50
  };

  try {
    const resp = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(query)
    });

    if (!resp.ok) {
      setSIEMPollStatus('SIEM UNAVAILABLE');
      return;
    }

    const data = await resp.json();
    const hits = data.hits?.hits || [];
    setSIEMPollStatus(`SIEM · ${hits.length} EVENTS`);
    renderLogEvents(hits);
  } catch (e) {
    setSIEMPollStatus('SIEM UNREACHABLE');
  }
}

function resetLogStream() {
  document.getElementById('log-stream').innerHTML = '';
  logFrozen = false;
  // Re-check current phase state
  const data = phaseData[currentPhase];
  if (data?.blue?.detection_status === 'miss') {
    logFrozen = true;
  }
}

function renderLogEvents(hits) {
  const stream = document.getElementById('log-stream');
  const existing = new Set(
    [...stream.querySelectorAll('.log-row')].map(el => el.dataset.id)
  );

  // Add new events (prepend for newest-on-bottom after reverse)
  const reversed = [...hits].reverse();
  reversed.forEach(hit => {
    if (existing.has(hit._id)) return;
    const src = hit._source || {};
    const row = document.createElement('div');
    row.className = 'log-row';
    row.dataset.id = hit._id;

    const ts = src['@timestamp'] ? src['@timestamp'].substring(11, 19) : '??:??:??';
    const sev = src.severity || 'INFO';
    const svc = src.service || '?';
    const msg = src.message || JSON.stringify(src).substring(0, 80);

    row.innerHTML = `
      <span class="log-ts">${ts}</span>
      <span class="log-sev ${sev}">${sev}</span>
      <span class="log-svc">${svc}</span>
      <span class="log-msg">${escapeHtml(msg)}</span>
    `;
    stream.appendChild(row);
  });

  // Trim to 50 visible rows
  const rows = stream.querySelectorAll('.log-row');
  if (rows.length > 50) {
    for (let i = 0; i < rows.length - 50; i++) {
      rows[i].remove();
    }
  }

  // Auto-scroll to bottom
  stream.scrollTop = stream.scrollHeight;
}

function setSIEMPollStatus(msg) {
  const el = document.getElementById('siem-poll-status');
  if (el) el.textContent = msg;
}

// ─── Clock & Timer ────────────────────────────────────────────────────────
function startClock() {
  function tick() {
    const now = new Date();
    const t = now.toTimeString().split(' ')[0];
    const el = document.getElementById('live-clock');
    if (el) el.textContent = t;
  }
  tick();
  setInterval(tick, 1000);
}

function startElapsedTimer() {
  function tick() {
    const elapsed = Math.floor((Date.now() - startTime) / 1000);
    const h = String(Math.floor(elapsed / 3600)).padStart(2, '0');
    const m = String(Math.floor((elapsed % 3600) / 60)).padStart(2, '0');
    const s = String(elapsed % 60).padStart(2, '0');
    const el = document.getElementById('elapsed-timer');
    if (el) el.textContent = `${h}:${m}:${s}`;
  }
  tick();
  setInterval(tick, 1000);
}

// ─── Keyboard Controls ────────────────────────────────────────────────────
function handleKeydown(e) {
  // Don't intercept if typing in an input
  if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;

  switch (e.code) {
    case 'Space':
    case 'ArrowRight':
      e.preventDefault();
      nextPhase();
      break;
    case 'ArrowLeft':
      e.preventDefault();
      prevPhase();
      break;
    case 'Digit1':
      switchTab('red');
      break;
    case 'Digit2':
      switchTab('blue');
      break;
    case 'Digit3':
      switchTab('grc');
      break;
    case 'KeyE':
      toggleExplainer();
      break;
    case 'KeyR':
      renderPhase(currentPhase);
      break;
    case 'KeyF':
      toggleFullscreen();
      break;
    case 'KeyP':
      // Pause/resume — asciinema player integration (M8)
      break;
    case 'Escape':
      hideExplainer();
      break;
  }
}

function toggleFullscreen() {
  if (!document.fullscreenElement) {
    document.documentElement.requestFullscreen?.();
  } else {
    document.exitFullscreen?.();
  }
}

// ─── Utilities ────────────────────────────────────────────────────────────
function setText(id, text) {
  const el = document.getElementById(id);
  if (el) el.textContent = text;
}

function setHTML(id, html) {
  const el = document.getElementById(id);
  if (el) el.innerHTML = html;
}

function escapeHtml(str) {
  return str.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

function toRoman(n) {
  return ['I','II','III','IV','V','VI'][n - 1] || n;
}
