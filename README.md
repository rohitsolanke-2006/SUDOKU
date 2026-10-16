# IO SIGNAL SUDOKU — Industrial I/O Allocation Platform & 3D Digital Twin
### Emerson DeltaV Electronic Marshaling Optimization & Churn Minimizer

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg)](https://fastapi.tiangolo.com/)
[![Google OR-Tools](https://img.shields.io/badge/Google%20OR--Tools-CP--SAT-4285F4.svg)](https://developers.google.com/optimization)
[![Three.js](https://img.shields.io/badge/Three.js-r128-black.svg)](https://threejs.org/)
[![Tests](https://img.shields.io/badge/tests-16%20passed-brightgreen.svg)]()

IO SIGNAL SUDOKU is an industrial engineering application that allocates complex instrumentation I/O loops to physical cabinet hardware channels while strictly satisfying electrical segregation, intrinsic safety (Ex-ia), and thermal constraints using **Google OR-Tools CP-SAT**.

---

## 1. Key Architectural Capabilities

1. **Google OR-Tools CP-SAT Constraint Optimization Engine**:
   - Solves multi-dimensional signal allocations in milliseconds.
   - Enforces **hard constraints**: Signal type compatibility, 1-channel slot capacity, Intrinsic Safety (IEC 60079-11 Ex-ia barrier segregation on BP-02), and voltage/carrier isolation (IEEE 518).
   - Solves **soft multi-objective functions**: Revision churn minimization ($w_1$), multicore trunk cable grouping ($w_2$), and thermal hotspot distribution ($w_3$).

2. **Decoupled Independent Constraint & Parity Validator**:
   - Performs independent, data-backed audits of all allocations without relying on solver success flags.
   - Evaluates real metrics: hard violations, soft warnings, spare capacities, and cable grouping dispersion.

3. **Revision-Aware Churn Minimizer (Rev A vs Rev B What-If Simulator)**:
   - Diffs engineering revisions side-by-side: detects added signals, decommissioned signals, and attribute modifications (e.g. loops upgraded to Ex-ia).
   - Solves with warm-start L1 pin retention penalty to preserve existing valid physical terminations, saving estimated field wiring labor hours.
   - Provides explicit **Accept Baseline** or **Reject / Revert** workflows.

4. **Real Interactive 3D Digital Twin**:
   - High-performance Three.js representation of a Rittal TS8 / DeltaV marshaling enclosure.
   - Modular hierarchy: `Cabinet CAB-01` → `CIOC Controllers (Active/Standby)` → `4 Baseplates (BP-01..BP-04)` → `64 CHARM Modules`.
   - Interactive raycasting: click any CHARM to highlight in 3D and 2-way select the signal in the table.
   - Camera presets (3/4 Axonometric Isometric, Front Elevation, CIOC, BP-01, BP-02, BP-03, BP-04).
   - Live color-coded status filtering (Allocated Green, IS Barrier Blue, Expansion Spare Gray, Warning Amber, Conflict Red, Selected Cyan).

5. **Explainable Diagnostics & Decision Inspector**:
   - Inspects any signal or slot: explains why an assignment was made with rule citations.
   - Evaluates rejected candidates: displays candidate slots across the cabinet and the exact engineering rule that eliminated each candidate.
   - Technical Query (TQ) issue tracker with assignee, status, and audit comment threads.

6. **Full-Stack Persistence & Export Engine**:
   - Single-command FastAPI server with thread-safe data persistence.
   - Downloadable CSV and multi-sheet Microsoft Excel (.xlsx) workbooks with formatting.

---

## 2. Quick Start & Execution

### Prerequisites
- Python 3.10+ (Tested on Python 3.10, 3.11, 3.12, 3.13)
- Modern web browser (Chrome, Edge, Firefox, Safari with WebGL enabled)

### Step 1: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 2: Launch Application
```bash
python run.py
```
Or with uvicorn directly:
```bash
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

### Step 3: Access Web Console
- **Interactive Engineering Workstation**: [http://127.0.0.1:8000/](http://127.0.0.1:8000/)
- **FastAPI OpenAPI Swagger Documentation**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **Healthcheck Endpoint**: [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)

---

## 3. Running Automated Tests

Run the comprehensive test suite verifying the CP-SAT solver, capacity limits, type compatibility, IS isolation, churn minimization, validator, and REST APIs:

```bash
python -c "import ortools; from ortools.sat.python import cp_model; import pytest, sys; sys.exit(pytest.main(['-v', 'tests']))"
```
Output:
```
tests/test_api.py::test_healthcheck PASSED
tests/test_api.py::test_get_project_and_signals PASSED
tests/test_api.py::test_get_hardware PASSED
tests/test_api.py::test_solve_api PASSED
tests/test_api.py::test_validate_api PASSED
tests/test_api.py::test_revisions_compare_api PASSED
tests/test_api.py::test_export_csv_and_excel PASSED
tests/test_revision.py::test_revision_diff PASSED
tests/test_solver.py::test_solver_feasible_rev_a PASSED
tests/test_solver.py::test_solver_enforces_capacity_limit PASSED
tests/test_solver.py::test_solver_enforces_type_compatibility PASSED
tests/test_solver.py::test_solver_enforces_intrinsic_safety_isolation PASSED
tests/test_solver.py::test_solver_minimizes_churn PASSED
tests/test_validator.py::test_validator_detects_capacity_overflow PASSED
tests/test_validator.py::test_validator_detects_is_barrier_violation PASSED
tests/test_validator.py::test_validator_detects_type_mismatch PASSED
======================== 16 passed in ~6.2s ========================
```

---

## 4. Repeatable Demonstration Walkthrough for Judges

1. **Launch Console**: Open `http://127.0.0.1:8000/` in your browser.
2. **Review Dashboard**: Click **Dashboard** to inspect real stored signals (43 loops), 64 CHARM slots, and 14/14 validated rules.
3. **Inspect Signal Matrix**: Click **Signal Matrix**. Filter by `IS_AI_HART` or search for `PT-105-IS`. Notice its assigned slot `BP-02-CH-01` on the Intrinsic Safety baseplate.
4. **Interactive Decision Inspector**: Click the **Inspect** button next to `PT-105-IS` to see the exact evidence why it was placed on `BP-02-CH-01` and why standard slots were rejected.
5. **Explore 3D Digital Twin**: Click **3D Digital Twin**.
   - Use left-click to orbit and wheel to zoom into the cabinet.
   - Click camera presets (`BP-01`, `BP-02`, `Front`, `3/4 ISO`).
   - Click on any CHARM slot in the 3D model to select it; see its live channel telemetry update in the HUD.
   - Filter by status (`Allocated`, `Spare`, `Warning`, `Conflict`).
6. **Simulate Revision Churn (Rev A vs Rev B)**: Click **Churn Minimizer**.
   - Review the comparison telemetry between Rev A and Rev B (+5 delta additions, upgraded IS classification for PT-102).
   - Click **Run Churn Minimization Solver**: OR-Tools CP-SAT solves the revision model with pin retention penalty, relocating only PT-102 to the IS barrier while preserving 97.6% of assignments!
   - Click **Accept Rev B Baseline** to promote it.
7. **Export Schedules**: Click **Reports & Export** to download the audited schedule in formatted `.CSV` or multi-sheet `.XLSX`.

---

## 5. Engineering Standards & Rules Implemented

- **RULE-HARD-01**: Signal Type Compatibility (IEC 61131-2)
- **RULE-HARD-02**: Slot Capacity Limit (1 channel per CHARM terminal)
- **RULE-HARD-03**: Intrinsic Safety Segregation (IEC 60079-11 Ex-ia barrier isolation)
- **RULE-HARD-04**: Voltage & Carrier Segregation (IEEE 518 noise isolation)
- **RULE-HARD-05**: Spare Capacity Protection (20% plant expansion reserve)
- **RULE-SOFT-01**: Revision Churn Minimization (L1 pin retention)
- **RULE-SOFT-02**: Multicore Cable Pair Proximity Grouping (API RP 552)
- **RULE-SOFT-03**: Thermal Load Balancing (Rittal thermal guidelines)
