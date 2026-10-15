---
name: Signal Matrix Industrial Workstation
colors:
  surface: '#f5fbf7'
  surface-dim: '#d5dbd8'
  surface-bright: '#f5fbf7'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#eff5f1'
  surface-container: '#e9efec'
  surface-container-high: '#e4e9e6'
  surface-container-highest: '#dee4e0'
  on-surface: '#171d1b'
  on-surface-variant: '#3e4946'
  inverse-surface: '#2c3230'
  inverse-on-surface: '#ecf2ef'
  outline: '#6e7976'
  outline-variant: '#bec9c5'
  surface-tint: '#026b5f'
  primary: '#006258'
  on-primary: '#ffffff'
  primary-container: '#247c70'
  on-primary-container: '#c8fff4'
  inverse-primary: '#84d5c7'
  secondary: '#206b46'
  on-secondary: '#ffffff'
  secondary-container: '#a8f3c4'
  on-secondary-container: '#28714c'
  tertiary: '#784e00'
  on-tertiary: '#ffffff'
  tertiary-container: '#996500'
  on-tertiary-container: '#fff2e5'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#a0f2e3'
  primary-fixed-dim: '#84d5c7'
  on-primary-fixed: '#00201c'
  on-primary-fixed-variant: '#005047'
  secondary-fixed: '#a8f3c4'
  secondary-fixed-dim: '#8dd6a9'
  on-secondary-fixed: '#002111'
  on-secondary-fixed-variant: '#005231'
  tertiary-fixed: '#ffddb3'
  tertiary-fixed-dim: '#fdba57'
  on-tertiary-fixed: '#291800'
  on-tertiary-fixed-variant: '#624000'
  background: '#f5fbf7'
  on-background: '#171d1b'
  surface-variant: '#dee4e0'
typography:
  headline-lg:
    fontFamily: Inter
    fontSize: 1.25rem
    fontWeight: '600'
    lineHeight: 1.5rem
    letterSpacing: -0.01em
  headline-md:
    fontFamily: Inter
    fontSize: 1rem
    fontWeight: '600'
    lineHeight: 1.25rem
    letterSpacing: -0.005em
  headline-sm:
    fontFamily: Inter
    fontSize: 0.875rem
    fontWeight: '600'
    lineHeight: 1.125rem
    letterSpacing: '0'
  body-md:
    fontFamily: Inter
    fontSize: 0.8125rem
    fontWeight: '400'
    lineHeight: 1.125rem
    letterSpacing: '0'
  body-sm:
    fontFamily: Inter
    fontSize: 0.75rem
    fontWeight: '400'
    lineHeight: 1rem
    letterSpacing: '0'
  label-code-lg:
    fontFamily: JetBrains Mono
    fontSize: 0.875rem
    fontWeight: '500'
    lineHeight: 1.125rem
    letterSpacing: 0.02em
  label-code-md:
    fontFamily: JetBrains Mono
    fontSize: 0.75rem
    fontWeight: '500'
    lineHeight: 1rem
    letterSpacing: 0.01em
  label-code-sm:
    fontFamily: JetBrains Mono
    fontSize: 0.6875rem
    fontWeight: '400'
    lineHeight: 0.875rem
    letterSpacing: 0.03em
  caption:
    fontFamily: Inter
    fontSize: 0.6875rem
    fontWeight: '500'
    lineHeight: 0.875rem
    letterSpacing: 0.04em
rounded:
  sm: 0.125rem
  DEFAULT: 0.25rem
  md: 0.375rem
  lg: 0.5rem
  xl: 0.75rem
  full: 9999px
spacing:
  gutter: 0.5rem
  margin: 0.5rem
  space-xs: 0.125rem
  space-sm: 0.25rem
  space-md: 0.5rem
  space-lg: 0.75rem
  space-xl: 1rem
---

## Brand & Style

This design system draws direct inspiration from industrial control systems, process automation suites (such as Emerson DeltaV and Yokogawa CENTUM), and CAD/CAM engineering environments. It prioritizes operational certitude, deterministic feedback, and ergonomic density for long-duration technical work.

### Aesthetic Axioms
- **Utilitarian Constructivism:** Every line, fill, and dividing boundary represents an explicit functional state or architectural boundary. Decorative ornament, diffuse drop-shadows, and floating cards are entirely prohibited.
- **Docked Panel Topography:** All panels are docked, flush, or nested within strict tabular gutters. The environment behaves as a rigid console workstation with anchored horizontal and vertical splitters.
- **Instrument Precision:** Information is displayed with zero ambiguity. Engineering tags, rack-slot coordinates, and discrete register values are treated as first-class citizens alongside standard interactive components.
- **Controlled Chromatic Discipline:** Color is deployed strictly as semantic status instrumentation. The primary canvas maintains a neutral industrial baseline to eliminate ocular fatigue during continuous monitoring.

## Colors

The system uses a strictly calibrated, non-saturated instrument palette engineered for extreme legibility under high cognitive load.

### Structural Surfaces
- **Workstation Canvas (`#E9EBE8`):** Base desktop foundation and docking well background.
- **Docked Surface / Panel Face (`#F5F6F3`):** Raised working panels, table rows, tab headers, and inspector toolbars.
- **CAD Viewport / Embedded Canvas (`#252C2D`):** High-contrast inspection canvas dedicated to matrix boards, 3D channel schematics, and slot tracing.
- **Surface Hover / Active Trough (`#DEE2DF`):** Interactive cell depress state and unassigned slot background.
- **Border Structural (`#C9CECA`):** 1px structural dividing lines across panels, tables, and channel headers.
- **Border Recessed / Secondary (`#DCE0DD`):** Internal subdivisions, matrix subdivision sub-ticks, and disabled boundaries.

### Semantic Instrumentation
- **Muted Teal (`#247C70`):** Active selection, active rack node, focused channel cursor, and targeted register.
- **Teal Subdued Fill (`#E4F0EE`):** Selection wash for highlighted rows and multiselect matrices.
- **Valid Green (`#39815A`):** Confirmed valid allocation, verified IO parity, and online signal status.
- **Green Subdued Fill (`#E8F2EC`):** Validated cell background or locked input background.
- **Warning Amber (`#C58A2B`):** Channel contention, uncommitted draft assignments, and soft parity cautions.
- **Violation Red (`#B94A48`):** Parity conflict, short circuit, duplicate slot assignment, and rule violation.
- **Violation Red Fill (`#F8ECEC`):** Error cell background and critical warning callout troughs.

### Typography & Content
- **Text Primary (`#252B29`):** Dark graphite for primary data, register indices, and labels.
- **Text Secondary (`#565E5A`):** Channel descriptions, inactive metadata, and engineering units.
- **Text Inverted (`#F5F6F3`):** Canvas tags and selection indicators within dark graphite CAD viewports.

## Typography

The typographic hierarchy prioritizes tabular alignment, dense vertical metrics, and distinct separation between operational labels and alphanumeric telemetry.

### Font Role Allocation
- **Inter:** Applied to UI chrome, structural headers, dropdown menus, property sheets, modal titles, and status bar descriptors. Rendered at standard weights (400, 600) with compact line-heights to support high information density.
- **JetBrains Mono:** Applied to all coordinate vectors (e.g., `R04:C09`), IO addresses (e.g., `%IX102.4`), discrete signal tags, hexadecimal payloads, and Sudoku grid matrix cells. Monospaced alignment guarantees zero optical jitter when values update in real-time.

### Typographic Rules
- All monospaced tags, slot identifiers, and channel statuses are uppercase by default.
- Labels for table headers and engineering attributes must use `caption` styling with uppercase transform and `0.04em` tracking.
- Do not use font sizes larger than 20px (`headline-lg`) inside panelized operational views; display hierarchy is achieved via weight, casing, and 1px frame isolation rather than scale inflation.

## Layout & Spacing

The layout is governed by a strict 4px/8px industrial mechanical grid. The viewport is treated as a continuous physical console: panels are docked edge-to-edge, separated only by 1px rules or standardized 8px utility gutters.

### Layout Philosophy
- **Tiled Viewport Architecture:** The main screen spans 100vw/100vh with zero viewport scrolling outside designated panel troughs. Sub-panels resize via draggable sash splitters.
- **Three-Tier Zoning:**
  1. *Top Utility Strip (28px height):* File IO, project schema, global execution state, parity monitor.
  2. *Central Working Bay:* Multi-pane division consisting of Left Node Tree / Channel Palette (240px–320px), Central Matrix CAD Viewport (fluid flex container), and Right Telemetry Inspector (280px–360px).
  3. *Bottom Diagnostic Ledger (32px collapsed, 160px expanded):* Chronological signal logs, validation errors, and parity trace outputs.

### Spacing Rules
- **Component Padding:** Standard input and cell internal padding is locked to `space-xs` (2px) vertically and `space-md` (8px) horizontally.
- **Dense Grouping:** Related properties inside inspector rows must adhere to `space-sm` (4px) gaps to preserve visual affinity.

## Elevation & Depth

This system intentionally rejects skeuomorphic drop-shadows, blurred glass, and floating Z-axis planes. Depth is established through tectonic layering and low-contrast perimeter rules.

### Depth Mechanisms
1. **Recessed Wells (`#E9EBE8`):** Workstation baseplate that recedes visually underneath primary tool panels.
2. **Flush Working Faces (`#F5F6F3`):** Active interactive surfaces sitting level with the tool plane, bounded strictly by 1px solid borders (`#C9CECA`).
3. **Engraved Fields:** Input elements, search boxes, and unallocated grid slots utilize an inset appearance created via a 1px solid border (`#C9CECA`) paired with a slightly darker surface fill (`#E9EBE8` or `#FFFFFF`).
4. **Dark Inspection Cutouts (`#252C2D`):** Dedicated CAD viewports act as recessed terminal windows set into the light chassis, framed by a continuous 1px structural boundary (`#252B29`).
5. **No Ambient Shadows:** Modals and contextual popovers use sharp 1px borders (`#252B29`) and a dark 2px hard keyline drop rather than diffuse multi-stop shadows.

## Shapes

The design language embodies structural rigidity and precision tooling. Radii are kept minimal to maximize usable screen real estate and preserve crisp alignment against 1px borders.

### Corner Rules
- **Base Geometry:** Standard interactive elements (buttons, inputs, status badges, and tabs) use a strict 2px to 4px radius (`roundedness: 1`).
- **Data Matrix Cells:** Sudoku grid cells, register tables, and panel docking borders use an absolute square radius (`0px`) to prevent visual gap artifacts when cells are packed in continuous 9x9 grids.
- **Status Indicators:** Channel LED indicators and binary allocation flags use 0px squares or strictly circular geometry (50%) when representing hardware status diodes.

## Components

### Buttons & Tool Controls
- **Standard Tool Button:** Height 24px or 28px. Background `#F5F6F3`, border 1px solid `#C9CECA`, border-radius 2px, font `Inter` 12px weight 500, color `#252B29`. Hover: background `#E9EBE8`. Active: background `#DEE2DF`, border-color `#247C70`.
- **Primary Action (Commit / Allocate):** Background `#247C70`, border 1px solid `#1A5A52`, border-radius 2px, font `Inter` 12px weight 600, color `#F5F6F3`. Hover: background `#1D665C`.
- **Icon Toolbar Buttons:** 24x24px square, 0px radius, flat borderless in resting state. On hover: 1px solid `#C9CECA` with `#E9EBE8` background.

### Inputs & Engineering Spec Fields
- **Data Field:** Height 24px. Background `#FFFFFF`, 1px solid border `#C9CECA`, 2px radius. Font `JetBrains Mono` 12px. Padding 2px 6px. Focused state: 1px solid `#247C70` outline without glow rings.
- **Read-Only / Derived Field:** Background `#E9EBE8`, border 1px solid `#DCE0DD`, text `#565E5A`. Monospace.

### 9x9 Signal Matrix Grid (Sudoku Viewport)
- **Cell Structure:** Fixed 36x36px to 48x48px squares, 0px radius. 1px solid `#C9CECA` cell boundaries.
- **3x3 Subgrid Divider:** 2px solid `#252B29` bounding stroke separating 3x3 operational regions.
- **Cell Resting State:** Background `#FFFFFF`, text `JetBrains Mono` 16px weight 600, center aligned.
- **Cell Active / Focus:** Background `#E4F0EE`, outline 2px inset `#247C70`.
- **Cell Valid Allocation:** Background `#E8F2EC`, text `#39815A`.
- **Cell Parity Violation:** Background `#F8ECEC`, text `#B94A48`, subtle 1px dashed corner warning tag.
- **Cell Fixed (Pre-assigned Hardware IO):** Background `#E9EBE8`, text `#252B29`, weight 700.

### Channel Chips & Status Flags
- **Signal Tag Badge:** Height 18px. Monospaced 11px font. Background `#E9EBE8`, 1px solid `#C9CECA`, 2px radius, padding 0 4px.
- **Diagnostic Pill:** Height 16px. Valid: `#39815A` text on `#E8F2EC` background. Contention/Warning: `#C58A2B` text on `#FAF3E7` background. Error: `#B94A48` text on `#F8ECEC` background.

### Docked Panels & Tree Inspectors
- **Panel Header:** Height 24px. Background `#E9EBE8`, border-bottom 1px solid `#C9CECA`. Typography `Inter` 11px uppercase weight 600, tracking 0.04em, text `#565E5A`. Includes inline dock/collapse icon controls.
- **Tree View Item:** Height 20px. Monospace tags indented by 12px per level with `#C9CECA` 1px guide lines. Selection triggers `#E4F0EE` background with 2px left border `#247C70`.