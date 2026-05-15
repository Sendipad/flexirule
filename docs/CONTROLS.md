# Reusable Vue Controls & Widgets

This document details the smart and innovative Vue components used throughout the FlexiRule UI. These controls are designed for high reusability, particularly within action node configuration panels, and provide sophisticated data manipulation and visual orchestration capabilities.

---

## 1. ValueResolverControl
**File:** `flexirule/public/js/flexirule/rule_builder/controls/ValueResolverControl.vue`

The `ValueResolverControl` is a "magic" input widget that allows users to define dynamic values using a variety of formula types without writing raw code.

### ✨ Key Features & Innovation
- **Multi-Modal Formula Support:** A single token-based UI that can switch between:
  - **Date Formula:** Add/subtract days, weeks, months, or years from "Today" or a Document Field with sign-aware offsets.
  - **Math Formula:** Perform arithmetic operations between fields or constants with configurable decimal precision.
  - **Date Difference:** Calculate the span between two dates in days, months, or years (with intelligent month-to-year conversion).
  - **Child Table Aggregation:** Perform `SUM`, `AVG`, or `COUNT` operations on child table rows with zero-length safety (e.g., using `max(len(rows), 1)` for averages).
  - **String Manipulation:** Advanced concatenation, currency formatting, and case transformations (Upper/Lower).
  - **System Context:** Access session user data or perform role-based authorization checks directly within a value.
- **Dynamic Expression Preview:** As the user configures the formula via the popover UI, a live Jinja-compatible expression snippet is generated and displayed at the bottom of the popover.
- **Context-Aware Field Pickers:** Automatically filters and displays relevant document fields based on the selected formula type (e.g., only showing numeric fields for Math Formulas).
- **Tokenized UI:** Displays a compact, icon-rich "token" in the form that summarizes the configured logic (e.g., "Today + 5 Days").
- **Intelligent Viewport Positioning:** The control automatically calculates available screen space. If there isn't enough room below the input, the configuration popover intelligently "flips" to appear above the token, ensuring the UI is never cut off by the browser window.
- **Granular Category Filtering:** Developers can use the `allowedKinds` prop to restrict which formula categories are available. This is useful for specific fields where only "Date" or "Math" logic might be appropriate.
- **Seamless Backwards Compatibility:** Includes a robust hydration layer that automatically migrates older rule schemas (like legacy `function_name` or `offset_days` fields) into the modern multi-mode format without user intervention.
- **Deep Frappe Utility Integration:** The generated snippets leverage high-level Frappe Python utilities (e.g., `frappe.utils.add_to_date`, `frappe.utils.fmt_money`), ensuring the resulting logic is both powerful and standard-compliant.

---

## 2. ResourceMapperControl
**File:** `flexirule/public/js/flexirule/rule_builder/controls/ResourceMapperControl.vue`

The `ResourceMapperControl` is a high-density mapping interface used to define how data flows between different objects or DocTypes.

### ✨ Key Features & Innovation
- **Intelligent Auto-Mapping:** A "Magic" button that performs fuzzy matching between source and target field names, suggesting mappings and allowing users to review/delete them before applying.
- **Recursive Mapping Support:** Handles both scalar (top-level) fields and complex child table mappings within a single unified interface.
- **Source Context Versatility:** Allows mapping from various sources including `doc`, `old_doc`, `vars` (upstream node outputs), and loop iterators.
- **Mixed-Mode Source Types:** Each field mapping can be defined as:
  - **Path:** A direct reference to a field in the source object.
  - **Expr:** A dynamic Jinja expression.
  - **Static:** A hardcoded literal value.
- **Batch Operations:** Supports multi-select and bulk deletion of mappings to speed up configuration.
- **Read-Only / No-Copy Detection:** Visually highlights fields that are read-only or marked as "No Copy" in the DocType metadata.

---

## 3. TextGeneratorControl
**File:** `flexirule/public/js/flexirule/rule_builder/controls/TextGeneratorControl.vue`

A sophisticated rich-text editor based on Tiptap that seamlessly blends static text with dynamic logic and variables.

### ✨ Key Features & Innovation
- **Visual Logic Blocks:** Instead of writing complex Jinja tags (`{% if ... %}`), users insert visual "Badges" for conditions and loops.
- **Nested Recursive Editing:** Double-clicking a logic badge opens a "Bottom Panel" containing another instance of `TextGeneratorControl`, allowing users to define content for "IF TRUE", "ELSE", or "LOOP BODY" in a structured, hierarchical way.
- **Slash Commands & Mentions:**
  - Typing `@` opens a variable picker.
  - Typing `/` opens a logic block picker.
- **Live Jinja Synchronization:** Seamlessly toggles between a "Visual" mode and a "Raw Jinja" mode, ensuring compatibility for power users while maintaining simplicity for others.
- **Context-Aware Iterators:** Inside a loop block, the variable picker automatically includes properties of the current loop item (e.g., `item.qty`).

---

## 4. TransformControl
**File:** `flexirule/public/js/flexirule/rule_builder/controls/TransformControl.vue`

A visual "Spider-Web" style mapper for connecting two data schemas.

### ✨ Key Features & Innovation
- **Visual Connectivity:** Uses SVG-based cubic bezier curves to draw connections between source (left) and target (right) tree nodes.
- **Tree-Based Schema Explorer:** Handles deeply nested JSON schemas or DocType hierarchies with expandable/collapsible nodes.
- **Drag-to-Connect:** Users can initiate a connection by clicking an anchor on a source field and "dropping" it onto a target field.
- **Fuzzy Search & Filtering:** Both source and target columns have independent search bars to quickly locate fields in large schemas.
- **Auto-Syncing Lines:** The mapping lines automatically recalculate and redraw as the user scrolls, expands nodes, or resizes the window.

---

## 5. ConditionBuilder
**File:** `flexirule/public/js/flexirule/rule_builder/components/condition_builder/ConditionBuilder.vue`

A powerful, recursive interface for building complex boolean logic.

### ✨ Key Features & Innovation
- **Nested Logic Groups:** Supports infinite nesting of AND/OR groups to create sophisticated logical branches.
- **Drag-and-Drop Reordering:** Allows users to move conditions or entire groups between different levels of the hierarchy using a smooth drag-and-drop UX.
- **Collection Queries:** Specialized "Collection" nodes allow checking conditions against child tables (e.g., "Check if ANY item in the table has a price > 100").
- **Smart Operator Loading:** Dynamically fetches valid operators from the backend based on field types (e.g., `contains` for strings, `>` for numbers).
- **Context-Aware Scoping:** Automatically manages variable aliases (like `doc` or `item`) depending on where the condition is being evaluated.

---

## 6. ComboBoxControl
**File:** `flexirule/public/js/flexirule/rule_builder/controls/ComboBoxControl.vue`

A highly optimized replacement for the standard HTML select/autocomplete, tailored for the Frappe ecosystem.

### ✨ Key Features & Innovation
- **Floating UI Portal:** Uses `Teleport` and `useFloatingDropdown` to ensure the dropdown menu is never clipped by parent containers or scroll areas.
- **Multi-Source Loading:** Seamlessly handles local arrays, remote Frappe Link queries, and custom async data providers.
- **Rich Option Rendering:** Supports icons, descriptions, and "Type Badges" for each option, making it easier to distinguish between different types of variables or fields.
- **Button vs. Input Modes:** Can function as a standard autocomplete input or a compact "Button" trigger that opens a searchable popover.
- **Keyboard Navigation:** Full support for arrow keys, Enter to select, and Escape to close, including type-ahead matching in button mode.
