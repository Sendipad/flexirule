# PROPOSAL A: NEXT-GENERATION CANVAS NODE ARCHITECTURE FOR FLEXIRULE

---

## EXECUTIVE SUMMARY

Proposal A introduces a radical, ergonomic redesign of FlexiRule's visual canvas node representation. Aimed at eliminating visual clutter, reducing click depth, improving layout adaptability, and enhancing dark-mode accessibility, Proposal A shifts FlexiRule from static, fixed-size node boxes to **Adaptive Morphing Canvas Cards with Semantic Port Docking and Inline Canvas Quick-Editing**.

---

## 1. WAR ROOM DESIGN DEBATE & SYNTHESIS

### Panel Consensus & Vision:
- **Lead Engineer**: "We need nodes that dynamically adapt their dimensions based on canvas zoom level and configuration complexity without breaking Dagre layout anchors."
- **Devil’s Advocate**: "Handle ambiguity is killing our authors. When a Condition node has True and False handles next to each other, users connect to the wrong branch. Output ports MUST be visually distinct and explicitly labeled!"
- **The Lazy End-User**: "Stop making me open 15 side-drawers just to change `doc.status` from 'Draft' to 'Approved'! Let me edit simple field values directly on the node card!"
- **Domain Specialist**: "By introducing Morphing Node Cards and Inline Canvas Pills, FlexiRule reaches feature parity with modern workflow design systems like N8N, ComfyUI, and Retool Workflows."

---

## 2. CORE ARCHITECTURAL PILLARS OF PROPOSAL A

### Pillar 1: Adaptive Morphing Card Layout (Compact vs Expanded)
Nodes automatically transition between two visual states based on canvas zoom and interaction context:

1. **Compact Mode (Zoom < 0.75 or Unselected)**:
   - Width: `140px`, Height: `44px`.
   - Displays action type icon, action label, and a single status dot.
   - Reduces canvas clutter on large 50+ node graphs.

2. **Expanded Mode (Zoom >= 0.75 or Selected / Hovered)**:
   - Width: `260px`, Height: `auto` (min `120px`).
   - Displays full action category badge, operation subtitle, inline variable pills, and explicit output handle ports.

```
+-------------------------------------------------------+
|  [icon] PROCESS  ::  Set Order Status       (v) [dot]  |
+-------------------------------------------------------+
|  OPERATION: Update Document Field                     |
|  +-------------------------------------------------+  |
|  |  doc.status  <--  "Approved"        [edit]     |  |
|  +-------------------------------------------------+  |
|  RETURN: vars.order_result                            |
+-------------------------------------------------------+
|  [o] IN (top/left)               OUT (bottom/right) [o]|
+-------------------------------------------------------+
```

---

### Pillar 2: Semantic Visual Port Docking System
Replace raw Vue Flow handle dots with **Semantic Port Docking Badges**:

- **Condition Node**:
  - `True Port`: Green pill (`bg-emerald-500`), anchored bottom-right, labeled `YES / True`.
  - `False Port`: Amber pill (`bg-amber-500`), anchored bottom-left, labeled `NO / False`.
- **Loop Node**:
  - `For Each Port`: Blue pill (`bg-sky-500`), anchored right, labeled `For Each Item`.
  - `After Last Port`: Slate pill (`bg-slate-500`), anchored bottom, labeled `After Last`.
  - `Loop Return Port`: Curved green port on top-left for loop body return edges.

---

### Pillar 3: Inline Canvas Smart Quick-Editing
Eliminate side-drawer roundtrips for simple action edits:
- **Assignment & Set Value**: Double-clicking an inline value pill on the canvas converts the text into an active input control.
- **Process Operations**: Dropdown selectors embedded directly in the card header allow switching operations without unselecting the node.

---

### Pillar 4: Real-time Validation & Error Halo System
- **Error Halo**: When contract validation fails (e.g., missing required fields or unconfigured sub-rules), the node card renders a glowing red halo (`box-shadow: 0 0 0 3px rgba(239, 68, 68, 0.4)`).
- **Click-to-Fix Badge**: A floating warning badge displays the exact error count (`! 2 errors`). Clicking the badge auto-scrolls the sidebar directly to the invalid input control.

---

### Pillar 5: Token-Driven Adaptive CSS Engine

Unified CSS design tokens for seamless Light and Dark mode rendering:

```css
:root {
  --fxr-node-bg: #ffffff;
  --fxr-node-border: #e2e8f0;
  --fxr-node-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
  --fxr-port-true: #10b981;
  --fxr-port-false: #f59e0b;
  --fxr-port-loop: #0284c7;
}

[data-theme="dark"] {
  --fxr-node-bg: #1e293b;
  --fxr-node-border: #334155;
  --fxr-node-shadow: 0 4px 12px rgba(0, 0, 0, 0.5);
  --fxr-port-true: #059669;
  --fxr-port-false: #d97706;
  --fxr-port-loop: #0369a1;
}
```

---

## 3. IMPLEMENTATION ROADMAP & COMPONENT REFACTORING

1. **Phase 1: Custom Node Shell (`BaseNodeCard.vue`)**:
   - Extract common card layout, handles, toolbars, and halo effects into a reusable wrapper component.
2. **Phase 2: Semantic Handle Port Components (`PortHandle.vue`)**:
   - Build custom handle wrapper supporting dynamic labels, tooltips, and directional routing.
3. **Phase 3: Inline Canvas Editor Integration (`InlineFieldPill.vue`)**:
   - Embed lightweight inputs directly on canvas cards for Assignment and Set Value actions.
