# FlexiRule Vue 3 Rule Builder - Architectural & Refactoring Assessment

## Executive Summary
The FlexiRule application is a robust visual rule engine with a well-structured state management system using Pinia and Vue Flow. While the core logic is sound, the application suffers from tight coupling between the Frappe legacy layer and the Vue 3 reactivity system, leading to manual synchronization overhead and UI responsiveness challenges on smaller screens.

## Critical Bugs & Edge Cases
1. **Reactivity Sync Gaps**: The bridging between `useRuleStore` and `useGraphStore` often relies on manual array spreading (e.g., `nodes.value = [...graphStore.nodes]`) or `store.touch_node()`. This is prone to sync errors where the UI doesn't reflect the internal store state after complex operations like `pasteNodes` or `insert_node_on_edge`.
2. **Cascade Deletion Logic**: The `delete_node` logic in `useGraphStore.js` is highly complex. While it attempts to handle orphaned subtrees, it may fail in unconventional topologies (e.g., multi-entry loops or sub-rules with multiple return paths), potentially leaving unreachable "ghost" nodes in the data.
3. **Condition Tree ID Collisions**: The custom `uuid()` generator in `ConditionBuilder.vue` and the hydration logic in `ConditionStep.vue` are disconnected. If a user pastes a condition group, there's a risk of ID collisions if the `hydrate` function isn't called immediately on the pasted data, breaking drag-and-drop.
4. **Loop Variable Scope**: The `getAvailableVariables` logic in `useGraphStore.js` is quite heavy (Phase 1 & 2). It assumes a linear execution path, which may produce incorrect variable availability suggestions in complex branching logic where a variable is defined in one branch but not another.

## Frappe/Vue Anti-Patterns
1. **Hybrid State Orchestration**: `rule_builder.js` acts as a jQuery-based orchestrator that subscribes to Pinia stores to update Frappe Page headers. This "dual-source of truth" makes it hard to track where state transitions are initiated.
   - *Recommendation*: Move page-level logic (breadcrumbs, title badges) into a dedicated `usePageStore` or handle them via a Vue-based Header component.
2. **Expensive Dirty Checking**: Using `JSON.stringify(state)` for dirty checking in `useRuleStore` is a performance bottleneck as the graph grows.
   - *Recommendation*: Use a simple `is_dirty` boolean flag in the store that is set to `true` by mutation actions, or leverage a deep watcher with a debounce.
3. **Direct API Calls in Components**: Direct `frappe.call` usage inside components (e.g., `ConditionStep.vue`, `RuleConfigModal.vue`) hinders testability and creates duplication of error handling logic.
   - *Recommendation*: Abstract API calls into Store actions or a dedicated Service layer.

## Logical Duplication & Clean Code
1. **Condition Hydration/Dehydration**: Redundant logic for adding/stripping IDs from condition trees exists in `ConditionStep.vue` and `ConditionBuilder.vue`.
   - *Recommendation*: Centralize this in a `useConditions` composable.
2. **Validation Logic**: Mandatory field validation is split between `useRuleStore.js` (for saving) and `useRuleConfig.js` (for UI feedback).
   - *Recommendation*: Create a unified `validateNode(node)` utility in `contracts.js`.
3. **Type Conversions**: Mapping return types to field types and generating unique action IDs are performed in multiple places.
   - *Recommendation*: Move these to `utils/schema_utils.js` or `core/contracts.js`.
4. **Component Fragmentation**:
   - The distinction between `node_configs/` and `rule_config/types/` is thin. For example, `LoopConfig` simply wraps `LoopNodeConfig`.
   - *Recommendation*: Consolidate these into a unified action-configuration directory.
5. **Schema-Driven UI**: Many action-specific config components (Notify, Wait, Set Value) follow identical form patterns.
   - *Recommendation*: Implement a generic `SchemaForm` component that renders these based on a JSON contract, significantly reducing the number of `.vue` files.
6. **Hidden Feature Flags**: Certain actions like "Switch" are hard-disabled in `contracts.js` via `RELEASE_DISABLED_ACTION_TYPES`.
   - *Recommendation*: Move these flags to a database-driven "RuleFlow Settings" or environment variables to avoid "hidden" code-level locks that confuse developers.

## UI/UX Recommendations
1. **Responsive Tabbed Interface**: On screens smaller than 1200px, the three-panel configuration modal (Input, Config, Output) is unusable.
   - *Action*: Transition to a Tabbed interface on smaller viewports.
2. **Flexible Control Sizing**: Many controls have fixed widths/heights that don't respect the parent container.
   - *Action*: Refactor CSS to use flex-based layouts (`flex-grow`) and ensure LinkControls and Inputs align to the panel width.
3. **Enhanced Field Selection**: The `Query Records` and `Normalization` actions use simple lists for field selection.
   - *Action*: Implement a multi-column check-control that preserves the order of selection (critical for pipeline processing).
4. **Dynamic Icon Mapping**: The icon mapping is currently hardcoded in `RuleConfigModal.vue`.
   - *Action*: Move the icon and color definitions into the `ActionContract` in `contracts.js` for easier extension.

## Step-by-Step Refactoring Plan
1. **Pillar 1: Core Abstraction (High Priority)**
   - Move icon/color metadata and validation rules into `core/contracts.js`.
   - Centralize variable scoping and type mapping utilities.
2. **Pillar 2: Clean Code & Composables**
   - Extract `useConditions` and `useValidation` composables.
   - Refactor `useRuleStore` to eliminate manual "touching" by using Vue 3's reactive deep-watching.
3. **Pillar 3: UI Responsiveness**
   - Implement the Tabbed view in `RuleConfigModal.vue` for smaller screens.
   - Update CSS for all configuration panels to use flexible sizing.
4. **Pillar 4: Enhanced Controls**
   - Develop the `FlexiCheckList` control with multi-column support and selection ordering.
   - Integrate the new control into `QueryRecordsConfig.vue` and `ProcessConfig.vue`.
5. **Pillar 5: Store Decoupling**
   - Move `frappe.call` logic out of components and into Pinia actions.
   - Clean up `rule_builder.js` to reduce jQuery footprint.
