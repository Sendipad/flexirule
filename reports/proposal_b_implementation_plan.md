# PROPOSAL B: PRODUCTION IMPLEMENTATION PLAN
## Direction-Adaptive Responsive Canvas Node Redesign for FlexiRule

---

## 1. EXECUTIVE SUMMARY & TARGET OBJECTIVES

This document translates **Proposal B (Direction-Adaptive Responsive Canvas Node Architecture)** into a concrete, phased engineering roadmap. The goal is to overhaul FlexiRule's Vue Flow node rendering pipeline, replacing rigid 220x140px node cards with **orientation-aware cards that morph geometry and internal multi-column grid layouts depending on flow direction (`LR` vs `TB`)**.

---

## 2. ARCHITECTURAL MILESTONES & PHASES

```
+-------------------------------------------------------------------------+
| PHASE 1: CSS Design Tokens & Container Queries                          |
|   - Define --fxr-* design tokens & container-type: inline-size          |
+-------------------------------------------------------------------------+
                                    |
                                    v
+-------------------------------------------------------------------------+
| PHASE 2: Reusable Base Node Shell (BaseNodeCard.vue)                    |
|   - Extract card frame, status indicators, halos, and direction classes |
+-------------------------------------------------------------------------+
                                    |
                                    v
+-------------------------------------------------------------------------+
| PHASE 3: Direction-Adaptive Dagre Engine (useRuleGraph.js)             |
|   - Dynamic rank geometry: LR (220x160) vs TB (420x110)                 |
+-------------------------------------------------------------------------+
                                    |
                                    v
+-------------------------------------------------------------------------+
| PHASE 4: Semantic Port Handle Docking (PortHandle.vue)                  |
|   - Colored handle pills ([YES], [NO], [For Each]) with directional anchors|
+-------------------------------------------------------------------------+
                                    |
                                    v
+-------------------------------------------------------------------------+
| PHASE 5: Theme Palettes & WCAG Dark Mode Contrast                      |
|   - Vibrant, High Contrast, and Slate palettes with 4.5:1+ WCAG ratios  |
+-------------------------------------------------------------------------+
                                    |
                                    v
+-------------------------------------------------------------------------+
| PHASE 6: E2E Verification & Cypress Testing                            |
|   - Layout toggling regression tests & visual snapshot validation       |
+-------------------------------------------------------------------------+
```

---

## 3. PHASE-BY-PHASE IMPLEMENTATION BREAKDOWN

### PHASE 1: CSS Design Tokens & Container Query Architecture
- **Target File**: `flexirule/public/css/flexirule.css` (or `public/js/flexirule/rule_builder/css/rule_builder.css`)
- **Key Tasks**:
  1. Define CSS variables for direction-adaptive node dimensions:
     ```css
     :root {
       --fxr-node-width-lr: 220px;
       --fxr-node-width-tb: 420px;
       --fxr-node-height-tb: 110px;
       --fxr-grid-gap-sm: 8px;
       --fxr-grid-gap-md: 12px;
     }
     ```
  2. Apply CSS Container Queries to the node wrapper class `.node-card-container`:
     ```css
     .node-card-container {
       container-type: inline-size;
       container-name: node-card;
     }
     ```

---

### PHASE 2: Reusable Base Node Shell (`BaseNodeCard.vue`)
- **Target File**: `flexirule/public/js/flexirule/rule_builder/components/nodes/BaseNodeCard.vue`
- **Key Tasks**:
  1. Extract common node boilerplate (selection borders, execution order badges, `NodeStatusIndicator`, `NodeToolbar`, error halos) into `BaseNodeCard.vue`.
  2. Implement orientation CSS classes based on `useCanvasLayout().isHorizontal`:
     - `.is-orientation-lr`: Sets `width: var(--fxr-node-width-lr)`, `height: auto`.
     - `.is-orientation-tb`: Sets `width: var(--fxr-node-width-tb)`, `height: var(--fxr-node-height-tb)`.

---

### PHASE 3: Direction-Adaptive Dagre Layout Engine Refactoring
- **Target File**: `flexirule/public/js/flexirule/rule_builder/composables/useRuleGraph.js`
- **Key Tasks**:
  1. Update `layoutGraph(direction)` to pass dynamic geometry to `dagreGraph.setNode()`:
     ```javascript
     const isHorizontal = direction === "LR";
     const nodeWidth = isHorizontal ? 220 : 420;
     const nodeHeight = isHorizontal ? 160 : 110;
     const rankSep = isHorizontal ? 120 : 80;
     const nodeSep = isHorizontal ? 50 : 60;

     dagreGraph.setGraph({
       rankdir: direction,
       nodesep: nodeSep,
       ranksep: rankSep,
       marginx: 40,
       marginy: 40,
     });
     ```

---

### PHASE 4: Semantic Port Handle Docking Components
- **Target File**: `flexirule/public/js/flexirule/rule_builder/components/nodes/PortHandle.vue`
- **Key Tasks**:
  1. Create `PortHandle.vue` wrapping Vue Flow's `<Handle>` with custom pill badges (`[YES]`, `[NO]`, `[For Each]`, `[After Last]`).
  2. Dynamically bind `position` prop (`Position.Right`, `Position.Bottom`, `Position.Left`, `Position.Top`) according to `sourcePosition`/`targetPosition` emitted by Vue Flow.

---

### PHASE 5: WCAG Theme Palettes & Dark Mode Contrast
- **Target File**: `flexirule/public/css/flexirule.css`
- **Key Tasks**:
  1. Implement theme token sets (`[data-theme="light"]`, `[data-theme="dark"]`, `[data-theme="high-contrast"]`).
  2. Ensure disabled nodes (`.is-effectively-disabled`) retain background visibility with dashed borders (`border: 2px dashed var(--fxr-border-subtle)`), ensuring contrast ratio >= 4.5:1.

---

### PHASE 6: E2E Verification & Cypress Testing
- **Target File**: `cypress/e2e/rule_builder_layout.cy.js`
- **Key Tasks**:
  1. Write Cypress test verifying layout orientation switch (`LR` -> `TB` -> `LR`).
  2. Assert node width expands from `220px` to `420px` in `TB` mode and internal elements rearrange into multi-column grid layout.
