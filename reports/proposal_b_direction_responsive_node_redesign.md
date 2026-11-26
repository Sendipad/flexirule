# PROPOSAL B: DIRECTION-ADAPTIVE RESPONSIVE CANVAS NODE ARCHITECTURE FOR FLEXIRULE

---

## EXECUTIVE SUMMARY

Proposal B presents a responsive, direction-aware canvas node redesign for FlexiRule. Recognizing that workflow graphs flow along orthogonal axes depending on user orientation preferences (**Left-to-Right `LR`** vs **Top-to-Bottom `TB`**), Proposal B dynamically aligns node expansion, aspect ratios, and internal column layouts to the active canvas flow direction.

---

## 1. WAR ROOM DESIGN DEBATE & SYNTHESIS

### Panel Discussion:
- **Lead Engineer**: "Fixed 220x140px node cards waste vertical space in Top-to-Bottom layouts and squeeze text in Left-to-Right layouts. We need orientation-aware card geometry!"
- **Devil’s Advocate**: "If node width expands to 480px in Top-to-Bottom mode, Dagre rank separation (`ranksep`) must adjust dynamically. Otherwise, wide nodes in adjacent ranks will collide!"
- **The Lazy End-User**: "When I switch layout from LR to TB, I want my Condition logic and field mappings to spread out side-by-side in columns so I don't have to scroll down inside a tiny card box!"
- **Domain Specialist**: "By pairing direction-adaptive aspect ratios with container queries and accessibility-tested color palettes, Proposal B optimizes screen real estate across all desktop and mobile viewport sizes."

---

## 2. ORIENTATION-ADAPTIVE NODE GEOMETRY & EXPANSION PHYSICS

```
                       DIRECTION: LEFT-TO-RIGHT (LR)
+------------------------+
| [icon] PROCESS         |  <-- Fixed Rank Width (220px)
| Set Customer Status    |  <-- Vertical Expansion (height: auto)
+------------------------+
| Operation: Update      |
| doc.status = "Active"  |  <-- Stacked 1-Column or 2-Column Vertical Flow
| Return: vars.result    |
+------------------------+
|  [o] IN         OUT [o]|
+------------------------+

                       DIRECTION: TOP-TO-BOTTOM (TB)
+-----------------------------------------------------------------------+
| [icon] PROCESS | Operation: Update Field     | Return Schema:         |
| Set Status     | doc.status = "Active"       | vars.result (Data)     |
+-----------------------------------------------------------------------+
| [o] IN (Top)                                               OUT (Bottom) [o] |
+-----------------------------------------------------------------------+
  ^ Column 1 (Metadata)    ^ Column 2 (Parameters)      ^ Column 3 (Outputs)
  <------------------ Expanded Rank Width (380px - 480px) ----------------->
```

### 1. Left-to-Right (`LR`) Layout Expansion:
- **Rank Direction**: Horizontal.
- **Node Geometry**: Fixed rank column width (`220px`), **Vertical Height Expansion** (`height: auto`).
- **Internal Content Layout**: Information is stacked vertically in 1 or 2 narrow compact rows to keep rank width slim and avoid pushing downstream ranks off-screen.

### 2. Top-to-Bottom (`TB`) Layout Expansion:
- **Rank Direction**: Vertical.
- **Node Geometry**: Fixed rank row height (`110px`), **Horizontal Width Expansion** (`380px` to `480px`).
- **Internal Content Layout**: Information is distributed horizontally across **3 Responsive CSS Grid Columns**:
  - **Column 1 (Identity)**: Icon, Action Category Badge, Action Label, Execution Order.
  - **Column 2 (Configuration)**: Active Operation, Field Assignments, Condition Expression preview.
  - **Column 3 (Outputs & Diagnostics)**: Return Variable Name, Resolved Schema Badge, Node Status Indicator.

---

## 3. RESPONSIVE CONTAINER QUERY ENGINE & DENSITY BREAKPOINTS

Nodes utilize CSS Container Queries (`container-type: inline-size`) to automatically adjust internal font sizes, icon visibility, and padding based on available card width:

```css
.node-card-container {
  container-type: inline-size;
  container-name: node-card;
}

/* Compact Container (< 200px) */
@container node-card (max-width: 200px) {
  .node-body-grid {
    grid-template-columns: 1fr;
    gap: 4px;
  }
  .type-label { display: none; }
}

/* Standard Rank Container (201px - 350px) */
@container node-card (min-width: 201px) and (max-width: 350px) {
  .node-body-grid {
    grid-template-columns: 1fr 1fr;
    gap: 8px;
  }
}

/* Wide TB Grid Container (> 351px) */
@container node-card (min-width: 351px) {
  .node-body-grid {
    grid-template-columns: 120px 1fr 120px;
    gap: 12px;
  }
}
```

---

## 4. DYNAMIC ACTION CATEGORY THEME PALETTES

Proposal B includes 3 user-selectable color themes optimized for WCAG AA/AAA contrast standards in Light and Dark modes:

### Palette Option 1: Modern Vibrant (Default)
- **Process**: Cyan (`#0891b2`)
- **Condition**: Amber (`#d97706`)
- **Loop**: Indigo (`#4f46e5`)
- **Sub-Rule**: Purple (`#9333ea`)
- **Query Records**: Emerald (`#059669`)
- **System / Stop**: Rose (`#e11d48`)

### Palette Option 2: High Contrast (Accessibility First)
- High WCAG 7:1 contrast ratios with thick 2px solid category borders and high-visibility text badges for low-vision authors.

### Palette Option 3: Enterprise Slate (Minimalist)
- Subdued neutral zinc/slate tones with subtle colored status indicator dots for dark-mode environments.

---

## 5. DAGRE LAYOUT ENGINE REFACTORING BLUEPRINT

When layout direction switches between `LR` and `TB`, `useRuleGraph.js` adjusts Dagre node dimensions and rank separations:

```javascript
const isHorizontal = direction === "LR";

// Direction-adaptive Dagre geometry
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
