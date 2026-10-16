/**
 * IO SIGNAL SUDOKU — Full-Stack Industrial Engineering Application Controller
 * Manages State, REST API Communication, 3D Synchronization, Workbenches, and Modals
 */

const AppState = {
  activeView: 'landing', // 'landing', 'dashboard', 'workbench', 'twin3d', 'diagnostics', 'revisions', 'rules', 'import', 'reports'
  activeScenarioId: 'SCENARIO_A',
  project: null,
  activeRevision: 'REV_A',
  signals: [],
  hardware: [],
  rules: [],
  tqs: [],
  validation: null,
  revisionDiff: null,
  selectedSignalId: null,
  selectedSlotId: null,
  selectedDiagnostic: null,
  filterSignalType: 'ALL',
  filterStatus: 'ALL',
  searchQuery: '',
  isSolving: false,
  viewer3D: null
};

// API Client
const API = {
  async get(endpoint) {
    const res = await fetch(`/api${endpoint}`);
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },
  async post(endpoint, data = {}) {
    const res = await fetch(`/api${endpoint}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },
  async patch(endpoint, data = {}) {
    const res = await fetch(`/api${endpoint}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },
  async upload(endpoint, formData) {
    const res = await fetch(`/api${endpoint}`, {
      method: 'POST',
      body: formData
    });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  }
};

// Application Initialization
document.addEventListener('DOMContentLoaded', async () => {
  setupNavigation();
  setup3DViewer();
  setupEventListeners();
  await refreshAllData();
});

function setupNavigation() {
  document.querySelectorAll('[data-view-nav]').forEach(btn => {
    btn.addEventListener('click', (e) => {
      e.preventDefault();
      const targetView = btn.getAttribute('data-view-nav');
      switchView(targetView);
    });
  });
}

function switchView(viewName) {
  AppState.activeView = viewName;
  document.querySelectorAll('.view-section').forEach(sec => {
    sec.classList.add('hidden');
  });

  const activeSec = document.getElementById(`view-${viewName}`);
  if (activeSec) {
    activeSec.classList.remove('hidden');
  }

  // Update nav link active highlights
  document.querySelectorAll('[data-view-nav]').forEach(btn => {
    if (btn.getAttribute('data-view-nav') === viewName) {
      btn.classList.add('bg-brand', 'text-white', 'border-brand-dark');
      btn.classList.remove('text-graphite-muted', 'hover:bg-frame');
    } else {
      btn.classList.remove('bg-brand', 'text-white', 'border-brand-dark');
      btn.classList.add('text-graphite-muted', 'hover:bg-frame');
    }
  });

  // Re-render view-specific UI
  if (viewName === 'dashboard') renderDashboard();
  if (viewName === 'workbench') renderWorkbench();
  if (viewName === 'twin3d') {
    if (AppState.viewer3D) {
      setTimeout(() => AppState.viewer3D.onResize(), 50);
    }
  }
  if (viewName === 'diagnostics') renderDiagnostics();
  if (viewName === 'revisions') renderRevisions();
  if (viewName === 'rules') renderRules();
  if (viewName === 'reports') renderReports();
}

function setup3DViewer() {
  const container = document.getElementById('threejs-cad-viewport');
  if (!container) return;

  AppState.viewer3D = new Cabinet3DViewer('threejs-cad-viewport', {
    onSelect: (slotId, slotData) => {
      onSelectSlotFrom3D(slotId, slotData);
    }
  });

  // Wire 3D Preset Camera Buttons
  document.querySelectorAll('[data-cam-preset]').forEach(btn => {
    btn.addEventListener('click', () => {
      const preset = btn.getAttribute('data-cam-preset');
      if (AppState.viewer3D) AppState.viewer3D.setCameraPreset(preset);
      document.querySelectorAll('[data-cam-preset]').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
    });
  });

  // Wire 3D Status Filter Buttons
  document.querySelectorAll('[data-3d-filter]').forEach(btn => {
    btn.addEventListener('click', () => {
      const f = btn.getAttribute('data-3d-filter');
      if (AppState.viewer3D) AppState.viewer3D.applyStatusFilter(f);
      document.querySelectorAll('[data-3d-filter]').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
    });
  });
}

function setupEventListeners() {
  // Solve Buttons
  document.querySelectorAll('.btn-trigger-solve').forEach(b => {
    b.addEventListener('click', triggerSolve);
  });

  // Revision Switcher
  const revSelect = document.getElementById('revision-selector');
  if (revSelect) {
    revSelect.addEventListener('change', async (e) => {
      const newRev = e.target.value;
      await API.post('/project/active-revision', { revision: newRev });
      AppState.activeRevision = newRev;
      await refreshAllData();
      showToast(`Switched active revision to ${newRev}`, 'info');
    });
  }

  // Reset Demo Project
  const btnReset = document.getElementById('btn-reset-demo');
  if (btnReset) {
    btnReset.addEventListener('click', async () => {
      if (confirm('Reset project back to original Emerson DeltaV marshaling baseline?')) {
        await API.post('/project/reset');
        await refreshAllData();
        showToast('Reset back to factory demo datasets.', 'success');
      }
    });
  }

  // Signals Search & Filters
  const searchInput = document.getElementById('signals-search-input');
  if (searchInput) {
    searchInput.addEventListener('input', (e) => {
      AppState.searchQuery = e.target.value;
      renderWorkbench();
    });
  }

  const typeFilter = document.getElementById('signals-type-filter');
  if (typeFilter) {
    typeFilter.addEventListener('change', (e) => {
      AppState.filterSignalType = e.target.value;
      renderWorkbench();
    });
  }

  const statusFilter = document.getElementById('signals-status-filter');
  if (statusFilter) {
    statusFilter.addEventListener('change', (e) => {
      AppState.filterStatus = e.target.value;
      renderWorkbench();
    });
  }

  // File Import Dropzone
  const fileInput = document.getElementById('signals-file-input');
  if (fileInput) {
    fileInput.addEventListener('change', handleFileUpload);
  }

  // Persistent Demo Lab Scenario Selectors
  document.querySelectorAll('[data-load-scenario]').forEach(btn => {
    btn.addEventListener('click', async () => {
      const scenarioId = btn.getAttribute('data-load-scenario');
      await loadScenario(scenarioId);
    });
  });

  // CAD 3D Connection Card Action Buttons
  const btnCardMatrix = document.getElementById('btn-card-view-matrix');
  if (btnCardMatrix) {
    btnCardMatrix.addEventListener('click', () => {
      switchView('workbench');
      if (AppState.selectedSignalId) {
        setTimeout(() => {
          const row = document.querySelector(`tr[onclick*="${AppState.selectedSignalId}"]`);
          if (row) row.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }, 100);
      }
    });
  }

  const btnCardInspect = document.getElementById('btn-card-inspect-rejections');
  if (btnCardInspect) {
    btnCardInspect.addEventListener('click', () => {
      if (AppState.selectedSignalId) {
        inspectSignalDecision(AppState.selectedSignalId);
        switchView('workbench');
      } else {
        switchView('diagnostics');
      }
    });
  }

  // Preset Demo Loaders
  document.querySelectorAll('[data-load-demo]').forEach(btn => {
    btn.addEventListener('click', async () => {
      const demoKey = btn.getAttribute('data-load-demo');
      if (demoKey === 'REV_A') {
        await API.post('/project/active-revision', { revision: 'REV_A' });
      } else if (demoKey === 'REV_B') {
        await API.post('/project/active-revision', { revision: 'REV_B' });
      }
      await refreshAllData();
      showToast(`Loaded ${demoKey} demonstration dataset.`, 'success');
      switchView('workbench');
    });
  });

  // What-If Simulation Runner
  const btnRunWhatIf = document.getElementById('btn-run-what-if');
  if (btnRunWhatIf) {
    btnRunWhatIf.addEventListener('click', triggerWhatIfSimulation);
  }

  // Accept Baseline Button
  const btnAcceptBaseline = document.getElementById('btn-accept-baseline');
  if (btnAcceptBaseline) {
    btnAcceptBaseline.addEventListener('click', async () => {
      if (confirm('Accept Revision B as the new active engineering baseline?')) {
        await API.post('/revisions/accept-baseline');
        await refreshAllData();
        showToast('Revision B accepted as active baseline.', 'success');
        switchView('dashboard');
      }
    });
  }
}

// Data Refresh
async function refreshAllData() {
  try {
    const [proj, sigs, hw, rules, tqs, val, diff] = await Promise.all([
      API.get('/project'),
      API.get('/signals'),
      API.get('/hardware'),
      API.get('/rules'),
      API.get('/tqs'),
      API.get('/validate'),
      API.get('/revisions/compare')
    ]);

    AppState.project = proj;
    AppState.activeRevision = proj.active_revision;
    AppState.signals = sigs;
    AppState.hardware = hw;
    AppState.rules = rules;
    AppState.tqs = tqs;
    AppState.validation = val;
    AppState.revisionDiff = diff;

    // Update Revision Dropdown
    const revSelect = document.getElementById('revision-selector');
    if (revSelect) revSelect.value = proj.active_revision;

    // Update Top Telemetry Badges
    updateTopTelemetry();

    // Update 3D Hardware Model with signals mapping
    if (AppState.viewer3D) {
      AppState.viewer3D.updateHardwareState(hw, {}, sigs);
    }

    // Render active view
    switchView(AppState.activeView);
  } catch (err) {
    console.error('Data refresh error:', err);
    showToast(`Failed to load project telemetry: ${err.message}`, 'error');
  }
}

function updateTopTelemetry() {
  const allocatedCount = AppState.signals.filter(s => s.status === 'ALLOCATED').length;
  const totalSignals = AppState.signals.length;

  document.querySelectorAll('.kpi-allocated-signals').forEach(el => el.textContent = `${allocatedCount} / ${totalSignals}`);
  document.querySelectorAll('.kpi-hardware-capacity').forEach(el => el.textContent = `64 CHARMs`);

  const parityEl = document.getElementById('badge-rules-validated');
  if (parityEl && AppState.validation) {
    if (AppState.validation.is_valid) {
      parityEl.innerHTML = `<span class="material-symbols-outlined text-[15px] text-valid">verified</span><span class="font-semibold text-valid font-mono">14/14 Rules Validated</span>`;
    } else {
      parityEl.innerHTML = `<span class="material-symbols-outlined text-[15px] text-error">gavel</span><span class="font-semibold text-error font-mono">${AppState.validation.hard_violations_count} Rule Violations</span>`;
    }
  }
}

// -----------------------------------------------------------------------------
// View Renderers
// -----------------------------------------------------------------------------

function renderDashboard() {
  const container = document.getElementById('dashboard-metrics-grid');
  if (!container) return;

  const totalSigs = AppState.signals.length;
  const allocatedSigs = AppState.signals.filter(s => s.status === 'ALLOCATED').length;
  const unallocatedSigs = totalSigs - allocatedSigs;
  const reservedHw = AppState.hardware.filter(h => h.is_reserved).length;
  const availableHw = AppState.hardware.filter(h => h.status === 'AVAILABLE').length;

  document.getElementById('dash-stat-signals').textContent = totalSigs;
  document.getElementById('dash-stat-allocated').textContent = allocatedSigs;
  document.getElementById('dash-stat-unallocated').textContent = unallocatedSigs;
  document.getElementById('dash-stat-available-hw').textContent = availableHw;
  document.getElementById('dash-stat-reserved-hw').textContent = reservedHw;
  document.getElementById('dash-stat-tqs').textContent = AppState.tqs.length;

  // Render Recent Activity / Findings
  const activityList = document.getElementById('dashboard-activity-feed');
  if (activityList && AppState.validation) {
    activityList.innerHTML = AppState.validation.findings.slice(0, 5).map(f => `
      <div class="p-2 border border-border bg-white rounded flex items-start gap-2 text-xs">
        <span class="material-symbols-outlined text-[18px] ${f.level === 'ERROR' ? 'text-error' : 'text-warn'}">
          ${f.level === 'ERROR' ? 'error' : 'warning'}
        </span>
        <div class="flex-1">
          <div class="font-semibold text-graphite">${f.rule_name} (${f.rule_id})</div>
          <div class="text-graphite-muted">${f.message}</div>
          ${f.suggested_action ? `<div class="text-[11px] text-brand font-mono mt-0.5">Action: ${f.suggested_action}</div>` : ''}
        </div>
      </div>
    `).join('');
  }
}

function renderWorkbench() {
  const tbody = document.getElementById('signals-table-body');
  if (!tbody) return;

  let filtered = AppState.signals;
  if (AppState.filterSignalType !== 'ALL') {
    filtered = filtered.filter(s => s.signal_type === AppState.filterSignalType);
  }
  if (AppState.filterStatus !== 'ALL') {
    filtered = filtered.filter(s => s.status === AppState.filterStatus);
  }
  if (AppState.searchQuery) {
    const q = AppState.searchQuery.toLowerCase();
    filtered = filtered.filter(s => s.tag.toLowerCase().includes(q) || s.description.toLowerCase().includes(q) || (s.multicore_cable_id || '').toLowerCase().includes(q));
  }

  tbody.innerHTML = filtered.map(s => {
    const isSelected = (s.id === AppState.selectedSignalId || s.assigned_position_id === AppState.selectedSlotId);
    let statusBadge = `<span class="px-1.5 py-0.5 rounded text-[10px] font-mono font-semibold bg-gray-100 text-gray-700">UNALLOCATED</span>`;
    if (s.status === 'ALLOCATED') {
      statusBadge = `<span class="px-1.5 py-0.5 rounded text-[10px] font-mono font-semibold bg-valid-light text-valid border border-valid/30">ALLOCATED</span>`;
    } else if (s.status === 'CONFLICT') {
      statusBadge = `<span class="px-1.5 py-0.5 rounded text-[10px] font-mono font-semibold bg-error-light text-error border border-error/30">CONFLICT</span>`;
    }

    return `
      <tr class="border-b border-border-light hover:bg-surface-tint/10 cursor-pointer ${isSelected ? 'bg-brand/10 font-medium' : ''}" onclick="selectSignalRow('${s.id}')">
        <td class="p-2 font-mono font-semibold text-graphite flex items-center gap-1.5">
          ${s.locked ? `<span class="material-symbols-outlined text-[14px] text-brand" title="Locked by Engineer">lock</span>` : ''}
          ${s.tag}
        </td>
        <td class="p-2 text-graphite-muted max-w-xs truncate" title="${s.description}">${s.description || '—'}</td>
        <td class="p-2">
          <span class="px-1 py-0.5 rounded font-mono text-[10px] border ${s.is_intrinsic_safety ? 'bg-blue-50 text-blue-700 border-blue-200' : 'bg-frame text-graphite border-border'}">
            ${s.signal_type}
          </span>
        </td>
        <td class="p-2 font-mono text-[11px] text-graphite-muted">${s.voltage || '24VDC'}</td>
        <td class="p-2 font-mono text-[11px] text-graphite-muted">${s.multicore_cable_id ? `${s.multicore_cable_id} (P${s.cable_pair_index || 1})` : '—'}</td>
        <td class="p-2 font-mono font-bold ${s.assigned_position_id ? 'text-brand' : 'text-gray-400'}">
          ${s.assigned_position_id || '[UNASSIGNED]'}
        </td>
        <td class="p-2">${statusBadge}</td>
        <td class="p-2 text-center">
          ${s.assigned_position_id ? `
            <button class="px-2 py-0.5 border border-brand/30 bg-brand/5 hover:bg-brand hover:text-white rounded text-[11px] text-brand font-mono font-semibold transition-colors flex items-center gap-1 mx-auto" onclick="event.stopPropagation(); jumpTo3DSignal('${s.id}')" title="Trace physical wiring route in 3D cabinet twin">
              <span class="material-symbols-outlined text-[13px]">view_in_ar</span> 3D
            </button>
          ` : `<span class="text-gray-400 font-mono text-[10px]">—</span>`}
        </td>
        <td class="p-2 text-right">
          <button class="px-2 py-0.5 border border-border hover:bg-frame rounded text-[11px] text-brand font-mono font-semibold" onclick="event.stopPropagation(); inspectSignalDecision('${s.id}')">
            Inspect
          </button>
        </td>
      </tr>
    `;
  }).join('');
}

function selectSignalRow(signalId) {
  AppState.selectedSignalId = signalId;
  const sig = AppState.signals.find(s => s.id === signalId);
  if (sig && sig.assigned_position_id) {
    AppState.selectedSlotId = sig.assigned_position_id;
    if (AppState.viewer3D) {
      AppState.viewer3D.selectSlot(sig.assigned_position_id, false);
    }
  }
  updateCADConnectionCard(sig, sig ? sig.assigned_position_id : null);
  renderWorkbench();
  inspectSignalDecision(signalId);
}

function onSelectSlotFrom3D(slotId, slotData) {
  AppState.selectedSlotId = slotId;
  const sig = AppState.signals.find(s => s.assigned_position_id === slotId);
  if (sig) {
    AppState.selectedSignalId = sig.id;
    updateCADConnectionCard(sig, slotId);
    inspectSignalDecision(sig.id);
  } else {
    // Show vacant slot info
    const hw = AppState.hardware.find(h => h.id === slotId);
    updateCADConnectionCard(null, slotId);
    showSlotDetails(hw || { id: slotId });
  }
  renderWorkbench();
}

function jumpTo3DSignal(signalId) {
  selectSignalRow(signalId);
  switchView('twin3d');
  const sig = AppState.signals.find(s => s.id === signalId);
  if (sig && sig.assigned_position_id && AppState.viewer3D) {
    setTimeout(() => {
      AppState.viewer3D.selectSlot(sig.assigned_position_id, true);
    }, 120);
  }
}

function updateCADConnectionCard(sig, slotId) {
  const card = document.getElementById('cad-3d-connection-card');
  if (!card) return;

  if (sig) {
    const tagEl = document.getElementById('cad-card-tag');
    if (tagEl) tagEl.textContent = sig.tag;
    const descEl = document.getElementById('cad-card-desc');
    if (descEl) descEl.textContent = sig.description || 'DeltaV Marshaled Field Loop';
    const posEl = document.getElementById('cad-card-pos');
    if (posEl) posEl.textContent = sig.assigned_position_id || slotId || 'UNASSIGNED';
    const typeEl = document.getElementById('cad-card-type');
    if (typeEl) typeEl.textContent = sig.signal_type;

    const pos = sig.assigned_position_id || slotId || '';
    const bpCode = pos.split('-')[0] || 'BP01';
    let bpName = 'AI 4-20mA Carrier';
    if (bpCode === 'BP02') bpName = 'HART / IS Barrier [Ex-ia]';
    else if (bpCode === 'BP03') bpName = 'RTD / TC Temp [mV]';
    else if (bpCode === 'BP04') bpName = 'DI / DO 24VDC Discrete';
    const bpEl = document.getElementById('cad-card-bp');
    if (bpEl) bpEl.textContent = `${bpCode} (${bpName})`;

    const tbEl = document.getElementById('cad-card-tb');
    if (tbEl) tbEl.textContent = `TB-${bpCode} (Ch ${pos.replace(/.*-C0?/, '') || '1'})`;

    const statusBox = document.getElementById('cad-card-status');
    const statusText = document.getElementById('cad-card-status-text');
    if (statusBox && statusText) {
      const statusIcon = statusBox.querySelector('.material-symbols-outlined');
      if (sig.status === 'ALLOCATED') {
        statusBox.className = 'p-2 rounded text-[11px] font-mono flex items-start gap-1.5 bg-valid/20 border border-valid/40 text-valid-light';
        if (statusIcon) {
          statusIcon.textContent = 'verified';
          statusIcon.className = 'material-symbols-outlined text-[15px] text-valid shrink-0';
        }
        statusText.textContent = sig.is_intrinsic_safety ? 'Fully Validated (IEC 60079-11 Ex-ia Certified)' : 'Fully Validated (Emerson DeltaV Certified)';
      } else if (sig.status === 'CONFLICT') {
        statusBox.className = 'p-2 rounded text-[11px] font-mono flex items-start gap-1.5 bg-error/20 border border-error/40 text-red-200';
        if (statusIcon) {
          statusIcon.textContent = 'error';
          statusIcon.className = 'material-symbols-outlined text-[15px] text-error shrink-0';
        }
        statusText.textContent = 'Hazardous Area Safety Conflict (Zone 0 Non-IS Barrier Clash)';
      } else {
        statusBox.className = 'p-2 rounded text-[11px] font-mono flex items-start gap-1.5 bg-neutral-800 border border-neutral-700 text-neutral-300';
        if (statusIcon) {
          statusIcon.textContent = 'help_outline';
          statusIcon.className = 'material-symbols-outlined text-[15px] text-neutral-400 shrink-0';
        }
        statusText.textContent = 'Pending Constraint Solver Assignment';
      }
    }

    const cableBox = document.getElementById('cad-card-cable');
    if (cableBox) {
      if (sig.multicore_cable_id) {
        cableBox.classList.remove('hidden');
        const cid = document.getElementById('cad-card-cable-id');
        if (cid) cid.textContent = sig.multicore_cable_id;
        const cpr = document.getElementById('cad-card-pair');
        if (cpr) cpr.textContent = sig.cable_pair_index || '1';
      } else {
        cableBox.classList.add('hidden');
      }
    }

    card.classList.remove('hidden');
  } else if (slotId) {
    const tagEl = document.getElementById('cad-card-tag');
    if (tagEl) tagEl.textContent = `[VACANT] Slot ${slotId}`;
    const descEl = document.getElementById('cad-card-desc');
    if (descEl) descEl.textContent = '20% Expansion Reserve Spare Channel';
    const posEl = document.getElementById('cad-card-pos');
    if (posEl) posEl.textContent = slotId;
    const typeEl = document.getElementById('cad-card-type');
    if (typeEl) typeEl.textContent = 'SPARE';
    const bpEl = document.getElementById('cad-card-bp');
    if (bpEl) bpEl.textContent = 'DeltaV CHARM Carrier';
    const tbEl = document.getElementById('cad-card-tb');
    if (tbEl) tbEl.textContent = `TB-${slotId}`;

    const statusBox = document.getElementById('cad-card-status');
    const statusText = document.getElementById('cad-card-status-text');
    if (statusBox && statusText) {
      statusBox.className = 'p-2 rounded text-[11px] font-mono flex items-start gap-1.5 bg-neutral-800 border border-neutral-700 text-neutral-300';
      const statusIcon = statusBox.querySelector('.material-symbols-outlined');
      if (statusIcon) {
        statusIcon.textContent = 'radio_button_unchecked';
        statusIcon.className = 'material-symbols-outlined text-[15px] text-neutral-400 shrink-0';
      }
      statusText.textContent = 'Available for future loop marshaling';
    }

    const cableBox = document.getElementById('cad-card-cable');
    if (cableBox) cableBox.classList.add('hidden');
    card.classList.remove('hidden');
  }
}

async function loadScenario(scenarioId) {
  try {
    showToast(`Loading ${scenarioId}...`, 'info');
    const res = await API.post('/scenarios/load', { scenario_id: scenarioId });
    AppState.activeScenarioId = scenarioId;

    // Update Scenario Buttons
    document.querySelectorAll('[data-load-scenario]').forEach(b => {
      if (b.getAttribute('data-load-scenario') === scenarioId) {
        b.className = 'scenario-btn active px-2 py-0.5 rounded text-[10px] font-mono font-semibold transition-colors bg-brand text-white';
      } else {
        b.className = 'scenario-btn px-2 py-0.5 rounded text-[10px] font-mono font-semibold transition-colors bg-neutral-800 text-neutral-300 hover:bg-neutral-700';
      }
    });

    // Update Scenario Mission Banner
    const badge = document.getElementById('scenario-badge');
    const desc = document.getElementById('scenario-desc');
    const dlBtn = document.getElementById('btn-download-scenario-input');

    if (scenarioId === 'SCENARIO_A') {
      if (badge) {
        badge.textContent = 'SCENARIO A — CLEAN ALLOCATION';
        badge.className = 'px-2 py-0.5 rounded font-mono font-bold text-[10px] bg-valid text-white tracking-wide';
      }
      if (desc) desc.textContent = 'Standard feasible run: 45 loops across 4 baseplates. Enforces type compatibility, 1-channel capacity, and Ex-ia barrier segregation with 0 hard violations.';
    } else if (scenarioId === 'SCENARIO_B') {
      if (badge) {
        badge.textContent = 'SCENARIO B — CONSTRAINT CONFLICT AUDIT';
        badge.className = 'px-2 py-0.5 rounded font-mono font-bold text-[10px] bg-error text-white tracking-wide';
      }
      if (desc) desc.textContent = 'Controlled Safety Violation: Loop PT-FLARE-IS locked to standard 24V slot BP01-C05. CP-SAT solver and diagnostics immediately flag IEC 60079-11 intrinsic safety violation.';
    } else if (scenarioId === 'SCENARIO_C') {
      if (badge) {
        badge.textContent = 'SCENARIO C — REVISION CHURN MINIMIZER';
        badge.className = 'px-2 py-0.5 rounded font-mono font-bold text-[10px] bg-blue-600 text-white tracking-wide';
      }
      if (desc) desc.textContent = 'Differential Re-Marshaling: Comparing Rev A (45 signals) against Rev B (49 signals). CP-SAT minimizes rewire churn to retain 97.7% of existing field terminations.';
    }

    if (dlBtn) {
      dlBtn.href = `/api/scenarios/download-input/${scenarioId}`;
    }

    await refreshAllData();
    showToast(`Loaded ${res.scenario_name}: ${res.signals_count} signals (${res.status})`, 'success');
  } catch (err) {
    console.error('Scenario load error:', err);
    showToast(`Failed to load scenario: ${err.message}`, 'error');
  }
}

// -----------------------------------------------------------------------------
// Decision Inspector & Diagnostics Modal
// -----------------------------------------------------------------------------

async function inspectSignalDecision(signalId) {
  try {
    const diag = await API.get(`/diagnostics/${signalId}`);
    AppState.selectedDiagnostic = diag;

    const panel = document.getElementById('inspector-panel');
    if (!panel) return;

    panel.classList.remove('hidden');
    document.getElementById('inspect-signal-tag').textContent = diag.signal_tag;
    document.getElementById('inspect-outcome').textContent = diag.outcome;
    document.getElementById('inspect-outcome').className = `px-2 py-0.5 rounded font-mono font-bold text-xs ${diag.outcome === 'SUCCESS' ? 'bg-valid-light text-valid' : 'bg-error-light text-error'}`;
    document.getElementById('inspect-assigned-pos').textContent = diag.assigned_position_id || 'UNALLOCATED';

    const evidenceList = document.getElementById('inspect-evidence-list');
    evidenceList.innerHTML = diag.rule_evidence.map(e => `
      <li class="flex items-center gap-1.5 text-xs text-graphite">
        <span class="material-symbols-outlined text-[15px] text-valid">check_circle</span>
        ${e}
      </li>
    `).join('');

    const rejectTable = document.getElementById('inspect-rejections-table');
    if (rejectTable) {
      rejectTable.innerHTML = diag.candidate_rejections.slice(0, 10).map(r => `
        <tr class="border-b border-border-light text-[11px]">
          <td class="p-1 font-mono font-semibold">${r.position_id}</td>
          <td class="p-1 font-mono text-error font-semibold">${r.reason_code}</td>
          <td class="p-1 text-graphite-muted">${r.reason_details}</td>
        </tr>
      `).join('');
    }

    const remedyEl = document.getElementById('inspect-remedy-box');
    if (remedyEl) {
      if (diag.suggested_remedy) {
        remedyEl.classList.remove('hidden');
        document.getElementById('inspect-remedy-text').textContent = diag.suggested_remedy;
      } else {
        remedyEl.classList.add('hidden');
      }
    }
  } catch (err) {
    console.error('Inspector error:', err);
  }
}

function showSlotDetails(hw) {
  const panel = document.getElementById('inspector-panel');
  if (!panel) return;
  panel.classList.remove('hidden');
  document.getElementById('inspect-signal-tag').textContent = `Slot ${hw.id}`;
  document.getElementById('inspect-outcome').textContent = hw.status || 'AVAILABLE';
  document.getElementById('inspect-outcome').className = `px-2 py-0.5 rounded font-mono font-bold text-xs bg-frame text-graphite`;
  document.getElementById('inspect-assigned-pos').textContent = hw.terminal_block || hw.id;

  document.getElementById('inspect-evidence-list').innerHTML = `
    <li class="text-xs text-graphite">Baseplate: ${hw.baseplate_type || 'DeltaV Carrier'}</li>
    <li class="text-xs text-graphite">Supported Types: ${(hw.supported_signal_types || []).join(', ')}</li>
    <li class="text-xs text-graphite">Intrinsic Safety: ${hw.is_is_rated ? 'Ex-ia Certified' : 'Non-IS'}</li>
    <li class="text-xs text-graphite">Spare Status: ${hw.is_reserved ? 'Expansion Reserve' : 'Available for allocation'}</li>
  `;
}

// -----------------------------------------------------------------------------
// Constraint Solver Invocation
// -----------------------------------------------------------------------------

async function triggerSolve() {
  if (AppState.isSolving) return;
  AppState.isSolving = true;

  document.querySelectorAll('.btn-trigger-solve').forEach(b => {
    b.disabled = true;
    b.innerHTML = `<span class="material-symbols-outlined text-[14px] animate-spin">refresh</span> Solving CP-SAT...`;
  });

  try {
    const payload = {
      project_id: AppState.project ? AppState.project.id : 'proj_deltav_01',
      revision: AppState.activeRevision,
      preserve_locked: true,
      soft_churn_weight: 15.0,
      cable_grouping_weight: 4.0,
      thermal_balance_weight: 2.0,
      time_limit_seconds: 6.0
    };

    const res = await API.post('/solve', payload);
    showToast(`Solver Finished: ${res.status} in ${res.solve_time_ms}ms (${res.allocated_signals} allocated)`, res.status === 'OPTIMAL' ? 'success' : 'warn');
    await refreshAllData();
  } catch (err) {
    console.error('Solve error:', err);
    showToast(`Solver Error: ${err.message}`, 'error');
  } finally {
    AppState.isSolving = false;
    document.querySelectorAll('.btn-trigger-solve').forEach(b => {
      b.disabled = false;
      b.innerHTML = `<span class="material-symbols-outlined text-[14px]">play_circle</span> Auto-Solve Allocation`;
    });
  }
}

// -----------------------------------------------------------------------------
// Revision Comparison & What-If Simulator
// -----------------------------------------------------------------------------

function renderRevisions() {
  const diff = AppState.revisionDiff;
  if (!diff) return;

  document.getElementById('diff-churn-index').textContent = diff.churn_index;
  document.getElementById('diff-retained-pct').textContent = `${diff.static_retained_pct}%`;
  document.getElementById('diff-rewires-count').textContent = `${diff.rewires_count} Pins`;
  document.getElementById('diff-additions-count').textContent = `+${diff.added_signals.length} ch`;
  document.getElementById('diff-labor-saved').textContent = `+${diff.estimated_labor_hours_saved} h`;

  // Render Added / Modified Table
  const table = document.getElementById('revisions-diff-table');
  if (!table) return;

  const rows = [];
  diff.added_signals.forEach(sId => {
    rows.push(`
      <tr class="border-b border-border-light text-xs bg-green-50/40">
        <td class="p-2 font-mono font-bold text-valid">[ADDED]</td>
        <td class="p-2 font-mono font-semibold">${sId}</td>
        <td class="p-2 text-graphite-muted">Newly introduced signal in Rev B</td>
        <td class="p-2 font-mono text-valid">New Slot Assigned</td>
      </tr>
    `);
  });

  diff.modified_signals.forEach(m => {
    rows.push(`
      <tr class="border-b border-border-light text-xs bg-amber-50/40">
        <td class="p-2 font-mono font-bold text-warn">[MODIFIED]</td>
        <td class="p-2 font-mono font-semibold">${m.tag}</td>
        <td class="p-2 text-graphite-muted">${JSON.stringify(m.changes)}</td>
        <td class="p-2 font-mono text-warn">Reallocated for IS isolation</td>
      </tr>
    `);
  });

  diff.reassigned_signals.forEach(r => {
    rows.push(`
      <tr class="border-b border-border-light text-xs bg-blue-50/40">
        <td class="p-2 font-mono font-bold text-brand">[REASSIGNED]</td>
        <td class="p-2 font-mono font-semibold">${r.tag}</td>
        <td class="p-2 text-graphite-muted">${r.reason}</td>
        <td class="p-2 font-mono text-brand">${r.rev_a_position} → ${r.rev_b_position}</td>
      </tr>
    `);
  });

  table.innerHTML = rows.join('') || `<tr><td colspan="4" class="p-4 text-center text-graphite-muted">No differential churn detected between revisions.</td></tr>`;
}

async function triggerWhatIfSimulation() {
  try {
    showToast('Running CP-SAT What-if Churn Simulation...', 'info');
    const res = await API.post('/revisions/simulate-what-if', { soft_churn_weight: 25.0 });
    AppState.revisionDiff = res.revision_diff;
    renderRevisions();
    showToast(`Simulation Complete: Churn Index ${res.revision_diff.churn_index} (${res.revision_diff.static_retained_pct}% retained)`, 'success');
  } catch (err) {
    showToast(`Simulation Failed: ${err.message}`, 'error');
  }
}

// -----------------------------------------------------------------------------
// Diagnostics & TQs
// -----------------------------------------------------------------------------

function renderDiagnostics() {
  const container = document.getElementById('tqs-list-container');
  if (!container) return;

  container.innerHTML = AppState.tqs.map(tq => `
    <div class="border border-border p-3 bg-white rounded shadow-sm flex flex-col gap-2">
      <div class="flex items-center justify-between">
        <div class="flex items-center gap-2">
          <span class="font-mono font-bold text-xs text-brand">${tq.id}</span>
          <span class="font-semibold text-graphite text-xs">${tq.title}</span>
        </div>
        <span class="px-2 py-0.5 rounded text-[10px] font-mono font-bold ${tq.status === 'RESOLVED' ? 'bg-valid-light text-valid' : 'bg-warn-light text-warn'}">
          ${tq.status}
        </span>
      </div>
      <p class="text-xs text-graphite-muted">${tq.description}</p>
      ${tq.suggested_resolution ? `
        <div class="text-[11px] bg-frame p-2 rounded border border-border">
          <span class="font-semibold text-graphite">Proposed Resolution:</span> ${tq.suggested_resolution}
        </div>
      ` : ''}
      <div class="flex items-center justify-between text-[11px] text-graphite-muted pt-1 border-t border-border-light">
        <span>Assignee: <strong>${tq.assignee}</strong></span>
        ${tq.status !== 'RESOLVED' ? `
          <button class="px-2 py-0.5 bg-valid text-white rounded text-[11px] font-semibold hover:bg-valid/90" onclick="resolveTQ('${tq.id}')">
            Mark Resolved
          </button>
        ` : `<span class="text-valid font-mono font-semibold">Verified</span>`}
      </div>
    </div>
  `).join('');
}

async function resolveTQ(tqId) {
  try {
    await API.patch(`/tqs/${tqId}`, { status: 'RESOLVED' });
    await refreshAllData();
    showToast(`Technical Query ${tqId} resolved.`, 'success');
  } catch (err) {
    showToast(`Failed to update TQ: ${err.message}`, 'error');
  }
}

// -----------------------------------------------------------------------------
// Rules Configuration View
// -----------------------------------------------------------------------------

function renderRules() {
  const container = document.getElementById('rules-list-container');
  if (!container) return;

  container.innerHTML = AppState.rules.map(r => `
    <div class="border border-border p-3 bg-white rounded flex items-start justify-between gap-4">
      <div class="flex-1">
        <div class="flex items-center gap-2 mb-1">
          <span class="px-1.5 py-0.5 rounded text-[10px] font-mono font-bold ${r.category === 'HARD' ? 'bg-red-50 text-error border border-red-200' : 'bg-blue-50 text-brand border border-blue-200'}">
            ${r.category} CONSTRAINT
          </span>
          <span class="font-mono font-bold text-xs text-graphite">${r.id}</span>
          <span class="font-semibold text-xs text-graphite">${r.name}</span>
        </div>
        <p class="text-xs text-graphite-muted mb-1.5">${r.description}</p>
        <div class="text-[10px] text-graphite-muted font-mono">Source: ${r.source}</div>
      </div>
      <div class="flex flex-col items-end gap-2">
        <label class="flex items-center gap-1.5 cursor-pointer text-xs">
          <input type="checkbox" ${r.enabled ? 'checked' : ''} onchange="toggleRuleEnabled('${r.id}', this.checked)" class="rounded text-brand focus:ring-brand">
          <span class="font-semibold">${r.enabled ? 'Enabled' : 'Bypassed'}</span>
        </label>
        ${r.category === 'SOFT' ? `
          <div class="flex items-center gap-1 text-[11px] font-mono">
            <span>Penalty Weight:</span>
            <input type="number" value="${r.weight}" min="1" max="100" class="w-14 p-0.5 text-center border border-border rounded text-xs" onchange="updateRuleWeight('${r.id}', this.value)">
          </div>
        ` : ''}
      </div>
    </div>
  `).join('');
}

async function toggleRuleEnabled(ruleId, enabled) {
  try {
    await API.patch(`/rules/${ruleId}`, { enabled: enabled });
    showToast(`Rule ${ruleId} ${enabled ? 'enabled' : 'bypassed'}.`, 'info');
  } catch (err) {
    showToast(`Rule update failed: ${err.message}`, 'error');
  }
}

async function updateRuleWeight(ruleId, weight) {
  try {
    await API.patch(`/rules/${ruleId}`, { weight: parseFloat(weight) });
    showToast(`Rule ${ruleId} penalty weight updated to ${weight}.`, 'info');
  } catch (err) {
    showToast(`Rule update failed: ${err.message}`, 'error');
  }
}

// -----------------------------------------------------------------------------
// Import & Data Validation
// -----------------------------------------------------------------------------

async function handleFileUpload(e) {
  const file = e.target.files[0];
  if (!file) return;

  const formData = new FormData();
  formData.append('file', file);

  try {
    showToast(`Parsing and validating ${file.name}...`, 'info');
    const res = await API.upload('/signals/import', formData);
    if (res.errors && res.errors.length > 0) {
      showToast(`Imported with ${res.errors.length} validation errors. Review report.`, 'warn');
      const errBox = document.getElementById('import-errors-display');
      if (errBox) {
        errBox.classList.remove('hidden');
        errBox.innerHTML = res.errors.map(er => `
          <div class="text-xs text-error font-mono">Row ${er.row}: [${er.field}] ${er.error}</div>
        `).join('');
      }
    } else {
      showToast(`Successfully imported ${res.imported_count} signals!`, 'success');
      await refreshAllData();
      switchView('workbench');
    }
  } catch (err) {
    showToast(`Import Failed: ${err.message}`, 'error');
  }
}

// -----------------------------------------------------------------------------
// Reports & Exports
// -----------------------------------------------------------------------------

function renderReports() {
  document.getElementById('report-proj-name').textContent = AppState.project ? AppState.project.name : 'Plant Expansion Unit A';
  document.getElementById('report-active-rev').textContent = AppState.activeRevision;
  document.getElementById('report-timestamp').textContent = new Date().toISOString();
  document.getElementById('report-total-signals').textContent = AppState.signals.length;
  document.getElementById('report-allocated-signals').textContent = AppState.signals.filter(s => s.status === 'ALLOCATED').length;
  document.getElementById('report-violations-count').textContent = AppState.validation ? AppState.validation.hard_violations_count : 0;
  document.getElementById('report-warnings-count').textContent = AppState.validation ? AppState.validation.soft_warnings_count : 0;
}

// Toast Notifications
function showToast(msg, type = 'info') {
  const toast = document.createElement('div');
  toast.className = `fixed bottom-4 right-4 z-50 px-3 py-2 rounded text-xs font-mono font-semibold text-white shadow-lg flex items-center gap-2 transition-all duration-300 transform translate-y-2 opacity-0`;

  if (type === 'success') toast.classList.add('bg-valid');
  else if (type === 'warn') toast.classList.add('bg-warn');
  else if (type === 'error') toast.classList.add('bg-error');
  else toast.classList.add('bg-graphite');

  toast.innerHTML = `<span class="material-symbols-outlined text-[16px]">info</span> ${msg}`;
  document.body.appendChild(toast);

  setTimeout(() => {
    toast.classList.remove('translate-y-2', 'opacity-0');
  }, 10);

  setTimeout(() => {
    toast.classList.add('translate-y-2', 'opacity-0');
    setTimeout(() => toast.remove(), 300);
  }, 4000);
}
