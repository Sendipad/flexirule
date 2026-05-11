# Frontend (Rule Builder) Architecture

## Vue 3 + Pinia Architecture
- Entry: `rule_builder.js` → `frappe.ui.RuleBuilder` class
- Vue app in `App.vue` with VueFlow canvas
- State: 5 modular Pinia stores (`/stores/`)
  1. `useRuleStore` — Rule doc lifecycle, save/load, status transitions, process metadata
  2. `useGraphStore` — Nodes/edges array, topology, normalization (node_id/name handling), Dagre layout triggers
  3. `useUIStore` — Sidebar open/closed, selected node(s), modal state, test visualization overlay
  4. `useMetaStore` — DocType metadata cache (fields, child tables, system fields)
  5. `useHistoryStore` — Snapshot-based undo/redo (JSON deep clone, max 50)

## Composables (`/composables/`)
- `useRuleGraph` — Dagre-based auto-layout, layer assignment, edge routing
- `useRuleConfig` — Draft node management (temp state before save)
- `useClipboard` — Copy/paste across tabs, fallback to localStorage → sessionStorage
- `useNodeExecutionState` — **NEW** real-time execution visualization during test runs (highlight active node, show result badges)
- `useActionTypeMapper` — Normalize action_type strings for frontend-handler alignment

## Node Components (`/components/nodes/`)
- `StartNode.vue` — Entry Action entry point
- `ProcessNode.vue` — Generic action node (most common)
- `ConditionNode.vue` — Condition with true/false handles
- `LoopNode.vue` — Loop with body entry and exit connections
- `StopNode.vue` — Terminal node (Success/Error styling)
- `ActionSelectorNode.vue` — Prompt to choose action type

## Configuration Modal
- `RuleConfigModal.vue` — Full-screen dialog (configurable per-action)
- Two modes:
  - **Sidebar mode** (`settings.action_config_mode = "sidebar"`): Inline panel on right side
  - **Modal mode**: Full-screen centered dialog
- `SchemaRenderer.vue` + `ControlFactory.vue` — Dynamically render fields from schema
- Control components (~15): `DataControl`, `LinkControl`, `SelectControl`, `CheckControl`, `TextControl`, `CodeControl`, `TextGeneratorControl`, `ResourceMapperControl`, `FlexiGrid` (table mapping), `AutocompleteControl`, `FieldPickerControl`, `MultiFieldPickerControl`, `InlineTableControl`, `MultiSelectControl`, `PercentSliderControl`

## Condition Builder
- `ConditionBuilder.vue` — Visual multi-condition builder (nested AND/OR groups)
- `ConditionNodeDisplay.vue` — Compact read-only view inside node
- Condition AST stored in `condition_json`; compiled on save to `compiled_expression`

## API Integration
All backend calls via `frappe.call()`:
- Rule lifecycle: `frappe.client.get/save`, `transition_rule`, `validate_rule_document`
- Execution: `test_rule`, `simulate_rule`, `execute_rule`, `get_execution_preview`
- Metadata: `get_contract_dto`, `get_node_config_schema`, `get_action_context_schema`
- Process: `get_process_list`, `get_process_js_paths`
- Cache: `clear_cache`

## Undo/Redo
- Snapshot-based (deep clone of `{nodes, edges}` from GraphStore)
- History stack holds up to 50 snapshots
- Deduplication: consecutive identical states collapsed

## Test Execution Visualization
- `useNodeExecutionState` tracks live execution progress
- Overlays node badges (✅/❌/⏳) and step highlight on canvas
- Sidebar panel shows step-by-step log + duration
- Payload parsed from engine's `last_execution_payload`