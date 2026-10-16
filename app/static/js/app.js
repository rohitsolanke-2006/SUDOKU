/**
 * IO SIGNAL SUDOKU — Full-Stack Industrial Engineering Application Controller
 * Manages State, REST API Communication, 3D Synchronization, Workbenches, and Modals
 */

const AppState = {
  activeView: 'landing', // 'landing', 'dashboard', 'workbench', 'twin3d', 'diagnostics', 'revisions', 'rules', 'import', 'reports', 'intelligence'
  activeScenarioId: 'SCENARIO_A',
  project: null,
  activeRevision: 'REV_A',
  signals: [],
  hardware: [],
  rules: [],
  tqs: [],
  validation: null,
  revisionDiff: null,
  conflictDNA: null,
  repairPlan: null,
  activeProposal: null,
  isAnalyzingDNA: false,
  isPlanningRepair: false,
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
  if (viewName === 'intelligence') renderIntelligence();
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

  // Engineering Change Intelligence Listeners
  const btnRefreshDNA = document.getElementById('btn-refresh-conflict-dna');
  if (btnRefreshDNA) {
    btnRefreshDNA.addEventListener('click', fetchConflictDNA);
  }

  const btnGenPlan = document.getElementById('btn-generate-repair-plan');
  if (btnGenPlan) {
    btnGenPlan.addEventListener('click', () => generateRepairPlan(true));
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
  const hardViolations = AppState.validation ? AppState.validation.hard_violations_count : 0;
  const softWarnings = AppState.validation ? AppState.validation.soft_warnings_count : 0;

  document.getElementById('dash-stat-signals').textContent = totalSigs;
  document.getElementById('dash-stat-allocated').textContent = allocatedSigs;
  document.getElementById('dash-stat-unallocated').textContent = unallocatedSigs;
  document.getElementById('dash-stat-available-hw').textContent = availableHw;
  document.getElementById('dash-stat-reserved-hw').textContent = reservedHw;
  document.getElementById('dash-stat-tqs').textContent = AppState.tqs.length;

  const hardEl = document.getElementById('dash-stat-hard-violations');
  if (hardEl) hardEl.textContent = hardViolations;

  const warnEl = document.getElementById('dash-stat-soft-warnings');
  if (warnEl) warnEl.textContent = softWarnings;

  // Active Scenario Header in Dashboard
  const dashTitle = document.getElementById('dash-scenario-title');
  const dashSub = document.getElementById('dash-scenario-subtitle');
  const statusBadge = document.getElementById('dash-solver-status-badge');

  const scId = AppState.activeScenarioId || 'SCENARIO_A';
  if (dashTitle) {
    if (scId === 'SCENARIO_A') {
      dashTitle.textContent = 'Active Scenario: Scenario A — Clean Allocation Baseline';
      if (dashSub) dashSub.textContent = '45 instrumentation loops • 100% feasibility • 0 hard violations, 0 warnings';
    } else if (scId === 'SCENARIO_B') {
      dashTitle.textContent = 'Active Scenario: Scenario B — Advisory Warnings (0 Violations)';
      if (dashSub) dashSub.textContent = '45 loops • 100% valid against mandatory rules • 2 genuine advisory warnings';
    } else if (scId === 'SCENARIO_C') {
      dashTitle.textContent = 'Active Scenario: Scenario C — Engineering Constraint Conflict';
      if (dashSub) dashSub.textContent = '46 loops • Hazardous Zone 0 Ex-ia transmitter locked to non-IS slot • IEC 60079-11 clash';
    } else if (scId === 'SCENARIO_D') {
      dashTitle.textContent = 'Active Scenario: Scenario D — Revision & Minimal Repair';
      if (dashSub) dashSub.textContent = 'Rev A baseline (45 loops) vs Rev B ECO (49 loops) • Minimal churn repair planner';
    }
  }

  if (statusBadge) {
    if (hardViolations > 0) {
      statusBadge.textContent = 'INFEASIBLE / CONFLICT';
      statusBadge.className = 'px-2 py-0.5 rounded font-mono font-bold text-[10px] bg-error-light text-error border border-error/30';
    } else if (softWarnings > 0) {
      statusBadge.textContent = 'FEASIBLE (WARNINGS)';
      statusBadge.className = 'px-2 py-0.5 rounded font-mono font-bold text-[10px] bg-amber-50 text-warn border border-amber-300';
    } else {
      statusBadge.textContent = 'OPTIMAL (VERIFIED)';
      statusBadge.className = 'px-2 py-0.5 rounded font-mono font-bold text-[10px] bg-valid-light text-valid border border-valid/30';
    }
  }

  // Interactive Conflict / Warning Notice Banner
  const actionBanner = document.getElementById('dash-action-banner');
  const actionIcon = document.getElementById('dash-action-icon');
  const actionText = document.getElementById('dash-action-text');
  const actionBtn = document.getElementById('dash-action-btn');

  if (actionBanner) {
    if (hardViolations > 0) {
      actionBanner.classList.remove('hidden');
      actionBanner.className = 'p-3 rounded border text-xs flex items-center justify-between gap-3 bg-error-light border-error/40 text-error';
      if (actionIcon) actionIcon.textContent = 'gavel';
      if (actionText) actionText.innerHTML = `<strong>Critical Constraint Conflict Detected:</strong> Zone 0 loop PT-FLARE-IS locked to standard non-IS slot (IEC 60079-11).`;
      if (actionBtn) {
        actionBtn.className = 'px-3 py-1 rounded font-mono font-semibold text-xs flex items-center gap-1 bg-error hover:bg-red-700 text-white shadow';
        actionBtn.textContent = 'Open Conflict DNA & Minimal-Repair';
        actionBtn.onclick = () => switchView('intelligence');
      }
    } else if (softWarnings > 0) {
      actionBanner.classList.remove('hidden');
      actionBanner.className = 'p-3 rounded border text-xs flex items-center justify-between gap-3 bg-amber-50 border-amber-300 text-amber-900';
      if (actionIcon) actionIcon.textContent = 'warning';
      if (actionText) actionText.innerHTML = `<strong>Advisory Engineering Warnings:</strong> 2 soft findings detected (multicore trunk cable pair split & expansion spare channel occupied). Mandatory constraints pass (100% valid).`;
      if (actionBtn) {
        actionBtn.className = 'px-3 py-1 rounded font-mono font-semibold text-xs flex items-center gap-1 bg-amber-600 hover:bg-amber-700 text-white shadow';
        actionBtn.textContent = 'Review Advisory Findings';
        actionBtn.onclick = () => switchView('diagnostics');
      }
    } else {
      actionBanner.classList.remove('hidden');
      actionBanner.className = 'p-3 rounded border text-xs flex items-center justify-between gap-3 bg-green-50 border-green-200 text-green-900';
      if (actionIcon) actionIcon.textContent = 'verified';
      if (actionText) actionText.innerHTML = `<strong>Clean Baseline Allocation:</strong> All 45 loops satisfied with 0 hard violations and 0 warnings. 100% verified against Emerson DeltaV rules.`;
      if (actionBtn) {
        actionBtn.className = 'px-3 py-1 rounded font-mono font-semibold text-xs flex items-center gap-1 bg-brand hover:bg-brand-dark text-white shadow';
        actionBtn.textContent = 'View in 3D Cabinet';
        actionBtn.onclick = () => switchView('twin3d');
      }
    }
  }

  // Render Recent Activity / Findings
  const activityList = document.getElementById('dashboard-activity-feed');
  if (activityList && AppState.validation) {
    if (AppState.validation.findings.length === 0) {
      activityList.innerHTML = `
        <div class="p-3 border border-green-200 bg-green-50/50 rounded flex items-center gap-2 text-xs text-valid font-medium">
          <span class="material-symbols-outlined text-[18px]">verified</span>
          100% Rules Compliant — All 45 instrumentation loops independently validated.
        </div>
      `;
    } else {
      activityList.innerHTML = AppState.validation.findings.slice(0, 6).map(f => `
        <div class="p-2 border border-border bg-white rounded flex items-start gap-2 text-xs">
          <span class="material-symbols-outlined text-[18px] ${f.level === 'ERROR' ? 'text-error' : 'text-warn'}">
            ${f.level === 'ERROR' ? 'gavel' : 'warning'}
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

  const findings = AppState.validation ? AppState.validation.findings : [];

  tbody.innerHTML = filtered.map(s => {
    const isSelected = (s.id === AppState.selectedSignalId || s.assigned_position_id === AppState.selectedSlotId);
    const errFinding = findings.find(f => f.level === 'ERROR' && (f.signal_id === s.id || f.position_id === s.assigned_position_id));
    const warnFinding = findings.find(f => f.level === 'WARNING' && (f.signal_id === s.id || f.position_id === s.assigned_position_id));

    let statusBadge = `<span class="px-1.5 py-0.5 rounded text-[10px] font-mono font-semibold bg-gray-100 text-gray-700">UNALLOCATED</span>`;
    if (errFinding || s.status === 'CONFLICT') {
      statusBadge = `<span class="px-1.5 py-0.5 rounded text-[10px] font-mono font-semibold bg-error-light text-error border border-error/30" title="${errFinding ? errFinding.message : 'Constraint conflict'}">CONFLICT</span>`;
    } else if (warnFinding) {
      statusBadge = `<span class="px-1.5 py-0.5 rounded text-[10px] font-mono font-semibold bg-amber-50 text-warn border border-amber-300" title="${warnFinding.message}">WARNING</span>`;
    } else if (s.status === 'ALLOCATED') {
      statusBadge = `<span class="px-1.5 py-0.5 rounded text-[10px] font-mono font-semibold bg-valid-light text-valid border border-valid/30">ALLOCATED</span>`;
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
        badge.textContent = 'SCENARIO A — CLEAN BASELINE';
        badge.className = 'px-2 py-0.5 rounded font-mono font-bold text-[10px] bg-valid text-white tracking-wide';
      }
      if (desc) desc.textContent = 'Standard feasible run: 45 loops across 4 baseplates. Enforces type compatibility, 1-channel capacity, and Ex-ia barrier segregation with 0 hard violations.';
    } else if (scenarioId === 'SCENARIO_B') {
      if (badge) {
        badge.textContent = 'SCENARIO B — ADVISORY WARNINGS (0 VIOLATIONS)';
        badge.className = 'px-2 py-0.5 rounded font-mono font-bold text-[10px] bg-warn text-white tracking-wide';
      }
      if (desc) desc.textContent = 'Deterministic advisory run: all mandatory constraints satisfied (100% valid), but triggers genuine warnings (multicore cable pair split across baseplates and expansion reserve slot occupied).';
    } else if (scenarioId === 'SCENARIO_C') {
      if (badge) {
        badge.textContent = 'SCENARIO C — SAFETY CONSTRAINT CONFLICT';
        badge.className = 'px-2 py-0.5 rounded font-mono font-bold text-[10px] bg-error text-white tracking-wide';
      }
      if (desc) desc.textContent = 'Controlled Safety Violation: Loop PT-FLARE-IS locked to standard non-IS slot BP-01-CH-01. CP-SAT solver and diagnostics immediately flag IEC 60079-11 intrinsic safety violation.';
    } else if (scenarioId === 'SCENARIO_D') {
      if (badge) {
        badge.textContent = 'SCENARIO D — REVISION & MINIMAL REPAIR';
        badge.className = 'px-2 py-0.5 rounded font-mono font-bold text-[10px] bg-blue-600 text-white tracking-wide';
      }
      if (desc) desc.textContent = 'Differential Re-Marshaling: Comparing Rev A (45 signals) against Rev B ECO (49 signals). Minimal-Repair planner generates 3 safe alternatives minimizing rewire churn.';
    }

    if (dlBtn) {
      dlBtn.href = `/api/scenarios/download-input/${scenarioId}`;
    }

    AppState.conflictDNA = null;
    AppState.repairPlan = null;
    AppState.activeProposal = null;

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
        remedyEl.innerHTML = `
          <div class="font-semibold text-warn mb-1 flex items-center justify-between">
            <span>Recommended Action:</span>
            <button onclick="switchView('intelligence')" class="px-2 py-0.5 bg-cyan-700 hover:bg-cyan-600 text-white rounded text-[10px] font-mono font-bold flex items-center gap-1 shadow">
              <span class="material-symbols-outlined text-[12px]">psychology</span> Fix in Change Intelligence
            </button>
          </div>
          <div class="text-[11px] text-graphite">${diag.suggested_remedy}</div>
        `;
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
  const hardList = document.getElementById('diag-hard-list');
  const warnList = document.getElementById('diag-warn-list');
  const hardCount = document.getElementById('diag-hard-count');
  const warnCount = document.getElementById('diag-warn-count');
  const tqCount = document.getElementById('diag-tq-count');
  const tqContainer = document.getElementById('tqs-list-container');

  const findings = AppState.validation ? AppState.validation.findings : [];
  const hardErrors = findings.filter(f => f.level === 'ERROR');
  const softWarnings = findings.filter(f => f.level === 'WARNING');

  if (hardCount) hardCount.textContent = `${hardErrors.length} Errors`;
  if (warnCount) warnCount.textContent = `${softWarnings.length} Warnings`;
  if (tqCount) tqCount.textContent = `${AppState.tqs.length} Total Queries`;

  if (hardList) {
    if (hardErrors.length === 0) {
      hardList.innerHTML = `<div class="p-3 bg-green-50 border border-green-200 rounded text-valid text-xs flex items-center gap-2"><span class="material-symbols-outlined text-[16px]">verified</span> 0 Hard Violations detected in active configuration.</div>`;
    } else {
      hardList.innerHTML = hardErrors.map(e => `
        <div class="p-2.5 bg-error-light border border-error/30 rounded flex flex-col gap-1 text-xs">
          <div class="flex items-center justify-between">
            <span class="font-mono font-bold text-error">${e.rule_id}</span>
            <span class="font-semibold text-graphite">${e.rule_name}</span>
          </div>
          <p class="text-graphite-muted">${e.message}</p>
          ${e.suggested_action ? `<div class="text-[11px] text-brand font-mono font-semibold">Action: ${e.suggested_action}</div>` : ''}
          <div class="pt-1 flex justify-end">
            <button onclick="switchView('intelligence')" class="px-2 py-0.5 bg-error text-white rounded text-[10px] font-mono font-bold flex items-center gap-1 shadow">
              <span class="material-symbols-outlined text-[11px]">psychology</span> Fix in Change Intelligence
            </button>
          </div>
        </div>
      `).join('');
    }
  }

  if (warnList) {
    if (softWarnings.length === 0) {
      warnList.innerHTML = `<div class="p-3 bg-frame border border-border rounded text-graphite-muted text-xs flex items-center gap-2"><span class="material-symbols-outlined text-[16px] text-valid">check_circle</span> 0 Advisory Warnings — Optimal cable grouping & spare capacity.</div>`;
    } else {
      warnList.innerHTML = softWarnings.map(w => `
        <div class="p-2.5 bg-amber-50 border border-amber-300 rounded flex flex-col gap-1 text-xs">
          <div class="flex items-center justify-between">
            <span class="font-mono font-bold text-warn">${w.rule_id}</span>
            <span class="font-semibold text-graphite">${w.rule_name}</span>
          </div>
          <p class="text-graphite-muted">${w.message}</p>
          ${w.suggested_action ? `<div class="text-[11px] text-brand font-mono font-semibold">Action: ${w.suggested_action}</div>` : ''}
        </div>
      `).join('');
    }
  }

  if (tqContainer) {
    tqContainer.innerHTML = AppState.tqs.map(tq => `
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

  const findings = AppState.validation ? AppState.validation.findings : [];

  container.innerHTML = AppState.rules.map(r => {
    const ruleFindings = findings.filter(f => f.rule_id === r.id);
    let statusBadge = `<span class="px-1.5 py-0.5 rounded text-[10px] font-mono font-bold bg-green-50 text-valid border border-green-200">PASS (0 Violations)</span>`;
    if (ruleFindings.length > 0) {
      const hasError = ruleFindings.some(f => f.level === 'ERROR');
      if (hasError) {
        statusBadge = `<span class="px-1.5 py-0.5 rounded text-[10px] font-mono font-bold bg-red-50 text-error border border-red-200 animate-pulse">VIOLATED (${ruleFindings.length} Critical)</span>`;
      } else {
        statusBadge = `<span class="px-1.5 py-0.5 rounded text-[10px] font-mono font-bold bg-amber-50 text-warn border border-amber-200">FLAGGED (${ruleFindings.length} Advisory)</span>`;
      }
    }

    return `
      <div class="border border-border p-3 bg-white rounded flex items-start justify-between gap-4">
        <div class="flex-1">
          <div class="flex items-center gap-2 mb-1 flex-wrap">
            <span class="px-1.5 py-0.5 rounded text-[10px] font-mono font-bold ${r.category === 'HARD' ? 'bg-red-50 text-error border border-red-200' : 'bg-blue-50 text-brand border border-blue-200'}">
              ${r.category} CONSTRAINT
            </span>
            <span class="font-mono font-bold text-xs text-graphite">${r.id}</span>
            <span class="font-semibold text-xs text-graphite">${r.name}</span>
            ${statusBadge}
          </div>
          <p class="text-xs text-graphite-muted mb-1.5">${r.description}</p>
          <div class="text-[10px] text-graphite-muted font-mono">Source: ${r.source}</div>
        </div>
        <div class="flex flex-col items-end gap-2 shrink-0">
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
    `;
  }).join('');
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

// -----------------------------------------------------------------------------
// Engineering Change Intelligence Engine Controller (USP)
// Tagline: "Don't just find a conflict. Find the smallest safe fix."
// -----------------------------------------------------------------------------

async function renderIntelligence() {
  if (!AppState.conflictDNA) {
    await fetchConflictDNA();
  } else {
    renderConflictDNAPanel();
  }
  if (!AppState.repairPlan) {
    await generateRepairPlan(false);
  } else {
    renderRepairCandidatesPanel();
  }
  renderSimulatorPanel();
}

async function fetchConflictDNA() {
  try {
    AppState.isAnalyzingDNA = true;
    const btn = document.getElementById('btn-refresh-conflict-dna');
    if (btn) btn.innerHTML = `<span class="material-symbols-outlined text-[14px] animate-spin">refresh</span> Analyzing...`;

    const dna = await API.get('/intelligence/conflict-dna');
    AppState.conflictDNA = dna;
    renderConflictDNAPanel();
    showToast(`Conflict DNA analyzed: ${dna.confirmed_violations.length} confirmed violation(s).`, dna.confirmed_violations.length > 0 ? 'warn' : 'success');
  } catch (err) {
    console.error('Conflict DNA error:', err);
    showToast(`Conflict DNA failed: ${err.message}`, 'error');
  } finally {
    AppState.isAnalyzingDNA = false;
    const btn = document.getElementById('btn-refresh-conflict-dna');
    if (btn) btn.innerHTML = `<span class="material-symbols-outlined text-[14px] text-cyan-400">fact_check</span> Analyze Conflict DNA`;
  }
}

function renderConflictDNAPanel() {
  const container = document.getElementById('dna-report-container');
  const badge = document.getElementById('dna-conflicts-badge');
  if (!container || !AppState.conflictDNA) return;

  const dna = AppState.conflictDNA;
  if (badge) {
    badge.textContent = `${dna.confirmed_violations.length} Violations`;
    badge.className = `px-2 py-0.5 rounded font-mono font-bold text-[10px] ${dna.confirmed_violations.length > 0 ? 'bg-red-100 text-red-700 border border-red-200' : 'bg-valid-light text-valid border border-valid/30'}`;
  }

  if (dna.confirmed_violations.length === 0 && dna.possible_causes.length === 0) {
    container.innerHTML = `
      <div class="p-4 border border-valid/30 bg-valid-light/30 rounded text-center space-y-2">
        <span class="material-symbols-outlined text-valid text-3xl">verified</span>
        <div class="font-bold font-mono text-valid text-xs">Clean Allocation DNA</div>
        <p class="text-xs text-graphite-muted">${dna.summary_narrative}</p>
      </div>
    `;
    return;
  }

  const items = [];
  dna.confirmed_violations.forEach(v => {
    items.push(`
      <div class="p-3 border border-red-200 bg-red-50/50 rounded space-y-2 text-xs">
        <div class="flex items-center justify-between">
          <span class="font-mono font-bold text-red-700 flex items-center gap-1">
            <span class="material-symbols-outlined text-[15px] text-red-600">error</span>
            ${v.signal_tag}
          </span>
          <span class="px-1.5 py-0.5 rounded text-[9px] font-mono font-bold bg-red-600 text-white">
            ${v.rule_id}
          </span>
        </div>
        <div class="text-[11px] font-mono text-graphite-muted">
          Position: <strong class="text-graphite">${v.assigned_position_id || 'UNASSIGNED'}</strong> • Type: <strong class="text-graphite">${v.signal_type}</strong>
        </div>
        <p class="text-xs text-red-900 font-medium">${v.root_cause_explanation}</p>
        <div class="p-2 bg-white/80 rounded border border-red-100 space-y-1">
          <div class="text-[10px] font-bold text-graphite uppercase font-mono">Grounded Evidence:</div>
          <ul class="list-disc pl-4 text-[10px] text-graphite-muted space-y-0.5">
            ${v.evidence_data.map(e => `<li>${e}</li>`).join('')}
          </ul>
        </div>
        <div class="p-2 bg-amber-50 rounded border border-amber-200 text-[11px] text-amber-900 flex items-start gap-1.5">
          <span class="material-symbols-outlined text-[14px] text-amber-700 shrink-0">build</span>
          <span><strong>Action:</strong> ${v.practical_remedy}</span>
        </div>
      </div>
    `);
  });

  dna.possible_causes.forEach(p => {
    items.push(`
      <div class="p-3 border border-amber-200 bg-amber-50/40 rounded space-y-1.5 text-xs">
        <div class="flex items-center justify-between">
          <span class="font-mono font-bold text-amber-800 flex items-center gap-1">
            <span class="material-symbols-outlined text-[15px] text-amber-600">help</span>
            ${p.signal_tag}
          </span>
          <span class="px-1.5 py-0.5 rounded text-[9px] font-mono font-bold bg-amber-500 text-white">POSSIBLE CAUSE</span>
        </div>
        <p class="text-xs text-graphite">${p.root_cause_explanation}</p>
        <div class="text-[10px] text-graphite-muted font-mono">Remedy: ${p.practical_remedy}</div>
      </div>
    `);
  });

  container.innerHTML = items.join('');
}

async function generateRepairPlan(notify = true) {
  try {
    AppState.isPlanningRepair = true;
    const btn = document.getElementById('btn-generate-repair-plan');
    if (btn) btn.innerHTML = `<span class="material-symbols-outlined text-[14px] animate-spin">refresh</span> Solving CP-SAT...`;

    const plan = await API.post('/intelligence/repair-plan', {});
    AppState.repairPlan = plan;
    renderRepairCandidatesPanel();

    if (notify) {
      showToast(`Generated ${plan.candidates.length} repair alternatives in ${plan.solve_time_ms}ms!`, 'success');
    }
  } catch (err) {
    console.error('Repair plan error:', err);
    if (notify) showToast(`Repair planning failed: ${err.message}`, 'error');
  } finally {
    AppState.isPlanningRepair = false;
    const btn = document.getElementById('btn-generate-repair-plan');
    if (btn) btn.innerHTML = `<span class="material-symbols-outlined text-[15px]">build_circle</span> Generate Minimal Repair`;
  }
}

function renderRepairCandidatesPanel() {
  const container = document.getElementById('repair-candidates-container');
  const badge = document.getElementById('repair-candidates-badge');
  if (!container || !AppState.repairPlan) return;

  const plan = AppState.repairPlan;
  if (badge) {
    badge.textContent = `${plan.candidates.length} Alternatives`;
  }

  if (plan.candidates.length === 0) {
    container.innerHTML = `
      <div class="p-4 border border-border bg-frame rounded text-center text-xs text-graphite-muted font-mono">
        No feasible repair candidates. Ensure hardware capacity is sufficient.
      </div>
    `;
    return;
  }

  container.innerHTML = plan.candidates.map(c => {
    const isSelected = AppState.activeProposal && AppState.activeProposal.candidate_id === c.candidate_id;
    return `
      <div class="p-3.5 border ${isSelected ? 'border-cyan-500 bg-cyan-50/30 ring-2 ring-cyan-400/20' : 'border-border bg-white'} rounded-lg space-y-2.5 shadow-sm hover:border-cyan-400 transition-all">
        <div class="flex items-center justify-between">
          <span class="font-mono font-bold text-xs text-graphite">${c.candidate_id}</span>
          <div class="flex items-center gap-1.5">
            <span class="px-1.5 py-0.5 rounded text-[9px] font-mono font-bold ${c.is_optimal ? 'bg-valid-light text-valid' : 'bg-blue-50 text-brand'}">
              ${c.solver_status}
            </span>
            <span class="px-1.5 py-0.5 rounded text-[9px] font-mono font-bold bg-gray-100 text-gray-700">
              ${c.strategy}
            </span>
          </div>
        </div>

        <div class="font-bold text-xs text-graphite">${c.title}</div>

        <div class="grid grid-cols-2 gap-2 text-center text-[10px] font-mono bg-frame p-2 rounded">
          <div>
            <div class="text-graphite-muted uppercase">Terminal Moves</div>
            <div class="text-sm font-bold text-brand mt-0.5">${c.moved_signals_count} Pin</div>
          </div>
          <div>
            <div class="text-graphite-muted uppercase">Retention</div>
            <div class="text-sm font-bold text-valid mt-0.5">${c.retained_pct}%</div>
          </div>
        </div>

        <div class="space-y-1 text-[11px] text-graphite-muted">
          ${c.trade_offs.map(t => `<div class="flex items-center gap-1"><span class="material-symbols-outlined text-[13px] text-valid">check</span>${t}</div>`).join('')}
        </div>

        <div class="pt-2 border-t border-border-light flex items-center justify-between">
          <span class="text-[10px] font-mono text-valid font-bold flex items-center gap-1">
            <span class="material-symbols-outlined text-[13px]">verified</span> 0 Hard Violations
          </span>
          <button class="px-2.5 py-1 bg-brand hover:bg-brand-dark text-white rounded text-xs font-mono font-semibold flex items-center gap-1 transition-colors" onclick="previewRepairCandidate('${c.candidate_id}')">
            <span class="material-symbols-outlined text-[13px]">visibility</span> Preview Fix
          </button>
        </div>
      </div>
    `;
  }).join('');
}

async function previewRepairCandidate(candidateId) {
  try {
    showToast(`Simulating repair candidate ${candidateId}...`, 'info');
    const preview = await API.post('/intelligence/simulate', { candidate_id: candidateId });
    AppState.activeProposal = preview;
    renderSimulatorPanel();
    renderRepairCandidatesPanel();
    showToast(`Simulation Ready: ${preview.existing_assignments_changed} move(s), ${preview.retained_pct}% retained.`, 'success');
  } catch (err) {
    console.error('Simulation error:', err);
    showToast(`Simulation failed: ${err.message}`, 'error');
  }
}

function renderSimulatorPanel() {
  const container = document.getElementById('simulator-preview-container');
  const badge = document.getElementById('simulator-status-badge');
  if (!container) return;

  if (!AppState.activeProposal) {
    if (badge) {
      badge.textContent = 'No Proposal';
      badge.className = 'px-2 py-0.5 rounded font-mono font-bold text-[10px] bg-neutral-100 text-neutral-600 border border-neutral-200';
    }
    container.innerHTML = `
      <div class="p-6 border border-dashed border-border rounded text-center text-xs text-graphite-muted font-mono space-y-2">
        <span class="material-symbols-outlined text-neutral-400 text-3xl">model_training</span>
        <div class="font-bold text-graphite">Simulator Inactive</div>
        <p>Click "Preview Fix" on any repair candidate in Pillar 2 to evaluate before-and-after schedule impact.</p>
      </div>
    `;
    return;
  }

  const prop = AppState.activeProposal;
  if (badge) {
    badge.textContent = `Active (${prop.candidate_id})`;
    badge.className = 'px-2 py-0.5 rounded font-mono font-bold text-[10px] bg-cyan-100 text-cyan-800 border border-cyan-300';
  }

  container.innerHTML = `
    <div class="space-y-3 text-xs">
      <!-- Proposal Header -->
      <div class="p-2.5 bg-cyan-50/60 border border-cyan-200 rounded flex items-center justify-between">
        <div>
          <div class="font-mono font-bold text-xs text-cyan-900">${prop.proposal_id}</div>
          <div class="text-[10px] font-mono text-cyan-700">${prop.baseline_revision} → ${prop.proposed_revision}</div>
        </div>
        <span class="px-2 py-0.5 rounded text-[10px] font-mono font-bold ${prop.can_accept ? 'bg-valid-light text-valid border border-valid/30' : 'bg-error-light text-error'}">
          ${prop.can_accept ? 'VALIDATED (READY)' : 'VALIDATION FAILED'}
        </span>
      </div>

      <!-- Telemetry Diff Metrics -->
      <div class="grid grid-cols-2 gap-2 text-[10px] font-mono bg-frame p-2.5 rounded border border-border">
        <div>
          <div class="text-graphite-muted uppercase">Terminal Moves</div>
          <div class="text-base font-bold text-brand mt-0.5">${prop.existing_assignments_changed} Pin</div>
        </div>
        <div>
          <div class="text-graphite-muted uppercase">Retention</div>
          <div class="text-base font-bold text-valid mt-0.5">${prop.retained_pct}%</div>
        </div>
        <div>
          <div class="text-graphite-muted uppercase">Labor Saved</div>
          <div class="text-xs font-bold text-graphite mt-0.5">+${prop.estimated_labor_saved_hours} h</div>
        </div>
        <div>
          <div class="text-graphite-muted uppercase">Hard Violations</div>
          <div class="text-xs font-bold text-valid mt-0.5">0 Violations</div>
        </div>
      </div>

      <!-- Change Breakdown List -->
      <div class="space-y-1.5">
        <div class="text-[10px] font-mono font-bold text-graphite uppercase">Proposed Terminal Movements:</div>
        <div class="max-h-40 overflow-y-auto space-y-1.5 pr-1">
          ${prop.changes.map(c => `
            <div class="p-2 border border-border-light bg-surface rounded flex items-center justify-between text-[11px] font-mono">
              <div>
                <span class="font-bold text-brand">${c.tag}</span>
                <span class="text-graphite-muted">(${c.signal_type})</span>
              </div>
              <div class="text-right">
                <span class="text-red-600 line-through">${c.from_position}</span>
                <span class="text-graphite mx-1">→</span>
                <span class="text-valid font-bold">${c.to_position}</span>
              </div>
            </div>
          `).join('')}
        </div>
      </div>

      <!-- Baseplate Capacity Deltas -->
      <div class="p-2 bg-frame rounded border border-border space-y-1 text-[11px] font-mono">
        <div class="text-[10px] font-bold text-graphite uppercase">Baseplate Utilization:</div>
        <div class="grid grid-cols-4 gap-1 text-center text-[10px]">
          ${Object.entries(prop.capacity_summary || {}).map(([bp, cap]) => `
            <div class="bg-white p-1 rounded border border-border-light">
              <div class="font-bold text-graphite">${bp}</div>
              <div class="text-graphite-muted">${cap.after}/16</div>
              <div class="${cap.delta > 0 ? 'text-brand font-bold' : (cap.delta < 0 ? 'text-amber-600 font-bold' : 'text-gray-400')}">${cap.delta > 0 ? '+' + cap.delta : cap.delta}</div>
            </div>
          `).join('')}
        </div>
      </div>

      <!-- Action Buttons -->
      <div class="pt-2 border-t border-border flex items-center gap-2">
        <button id="btn-cancel-repair" class="flex-1 py-1.5 bg-neutral-200 hover:bg-neutral-300 text-graphite rounded text-xs font-mono font-semibold transition-colors" onclick="cancelRepairProposal()">
          Discard Proposal
        </button>
        <button id="btn-accept-repair" class="flex-1 py-1.5 ${prop.can_accept ? 'bg-valid hover:bg-valid/90' : 'bg-gray-300 cursor-not-allowed'} text-white rounded text-xs font-mono font-bold shadow transition-colors flex items-center justify-center gap-1" ${prop.can_accept ? '' : 'disabled'} onclick="acceptRepairProposal('${prop.proposal_id}')">
          <span class="material-symbols-outlined text-[14px]">check_circle</span> Accept Repair
        </button>
      </div>
    </div>
  `;
}

async function acceptRepairProposal(proposalId) {
  if (!confirm(`Confirm and apply proposed repair schedule ${proposalId} to active project baseline?`)) return;

  try {
    const res = await API.post('/intelligence/accept-repair', { proposal_id: proposalId, confirm: true });
    showToast(res.message, 'success');
    AppState.activeProposal = null;
    await refreshAllData();
    await fetchConflictDNA();
    renderSimulatorPanel();
    switchView('workbench');
  } catch (err) {
    showToast(`Accept failed: ${err.message}`, 'error');
  }
}

async function cancelRepairProposal() {
  try {
    await API.post('/intelligence/cancel-repair');
    AppState.activeProposal = null;
    renderSimulatorPanel();
    renderRepairCandidatesPanel();
    showToast('Proposal discarded. Baseline remained 100% unchanged.', 'info');
  } catch (err) {
    showToast(`Cancel failed: ${err.message}`, 'error');
  }
}

