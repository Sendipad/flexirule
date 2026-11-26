# FLEXIRULE ACTION TYPE CONFIGURATION UI/UX DEEP ANALYSIS & REMEDIATION PLAN

---

## EXECUTIVE SUMMARY

This report provides a deep-dive technical and usability analysis of all **13 supported action types** in FlexiRule, examining their frontend Vue 3 configuration controls, state bindings, reactivity pipelines, contract validations, and Frappe Framework REST integration points.

---

## DETAILED ACTION TYPE CONFIGURATION ANALYSIS

### 1. ENTRY ACTION (Start Node)
- **UI Controls**: `StartNodeProperties.vue`
- **Key Parameters**: `trigger_type`, `document_type`, `trigger_event`, `trigger_condition`, `skip_for_roles`, `permissions`.
- **UI/UX Bottlenecks & Flaws**:
  - Changing `trigger_type` clears hidden fields via backend contract normalization (`normalize_trigger_type_fields`), but the frontend form does not dynamically wipe local reactive refs until save, causing visual field ghosting.
  - Role selection for `skip_for_roles` uses Frappe MultiSelect controls without auto-suggesting active user roles on tenant sites.

### 2. CONDITION (Branching Condition)
- **UI Controls**: `ConditionBuilder.vue`, `ConditionGroup.vue`, `ConditionRow.vue`
- **Key Parameters**: `config.op` (`and`/`or`), `conditions` tree, `compiled_expression`.
- **UI/UX Bottlenecks & Flaws**:
  - `ConditionBuilder` serializes output to `node.data.config`, but legacy code syncs `condition_json`. If `condition_json` is dirty, `useGraphStore.normalize_graph_nodes` overwrites custom expressions on reload.
  - Deep nested condition groups (depth > 3) exceed drawer width, hiding operator dropdowns off-screen without horizontal scroll support.

### 3. ASSIGNMENT (Batch & Field Assignment)
- **UI Controls**: `InlineTableControl.vue`, `FlexValueControl.vue`, `ControlFactory.vue`
- **Key Parameters**: `target` (`doc.*` or `vars.*`), `operator` (`set`, `increment`, `clear`, etc.), `value` (structured or Jinja template), `when_condition`.
- **UI/UX Bottlenecks & Flaws**:
  - Each assignment row requires clicking into sub-accordions to set value modes (literal, variable, Jinja formula). Setting up 5 field assignments requires over 20 distinct user clicks.
  - Changing target from `doc.status` to `vars.custom_var` does not update the `FlexValueControl` fieldtype schema context dynamically.

### 4. PROCESS (Process Framework Operations)
- **UI Controls**: `ActionFieldProperties.vue`, `ControlFactory.vue`
- **Key Parameters**: `process_name`, `operation`, `config` (schema-driven via `get_operation_config_fields`), `return_variable`, `ignore_permissions`, `permission_audit_reason`.
- **UI/UX Bottlenecks & Flaws**:
  - When `ignore_permissions = 1` is toggled, `permission_audit_reason` is rendered at the bottom of the drawer. If the user clicks Save without seeing it, top-level toast alerts display `act_X: Permission Audit Reason is required` without scrolling or highlighting the field.
  - Operation contracts loaded via `get_operation_config_fields` do not cache schema fields per process, causing redundant REST API roundtrips (`get_process_script`) when reopening process drawers.

### 5. QUERY RECORDS (Fetch Records & Search)
- **UI Controls**: `ResourceMapperControl.vue`, `FlexiGrid.vue`
- **Key Parameters**: `reference_doctype`, `operation` (`Query List`, `Fetch Records`), `config.resource_mapper_ui` (`scalars`, `tables`), `return_variable`.
- **UI/UX Bottlenecks & Flaws**:
  - `ResourceMapperControl` table mappings require setting `target_table` and `source_path`. When mapping child tables, missing sub-fields cause silent Jinja compilation failures on backend `compile_action_mappings`.
  - Field auto-mapping (`copy_same_fields`) overwrites custom scalar mappings without an undo confirmation prompt.

### 6. LOOP (Iteration & Body Execution)
- **UI Controls**: `LoopNodeConfig.vue`, `ComboBoxControl.vue`
- **Key Parameters**: `config.iterator` (`doc.items` or `vars.query_result`), `return_variable` (item alias, e.g. `item`).
- **UI/UX Bottlenecks & Flaws**:
  - `LoopNodeConfig` migrates legacy `config.alias` to `return_variable` on mount, but if `return_variable` is updated, `config.alias` remains in `node.data.config`, causing schema hash mismatches in dirty state comparisons (`checkDirty()`).
  - Iterating over non-array variables fails gracefully on backend but displays no visual warning badge in the builder UI.

### 7. SUB-RULE (Callable Sub-Rule Execution)
- **UI Controls**: `SubRuleNodeConfig.vue`
- **Key Parameters**: `rule` (target callable rule name), `input_mapping`, `output_mapping`.
- **UI/UX Bottlenecks & Flaws**:
  - `SubRuleNodeConfig` filters available rules by `document_type`, but selecting a global sub-rule (no `document_type`) shows an ambiguous "Target rule has conditions" notice even when no conditions exist.
  - Sub-rule cycle checks occur on backend save rather than client-side selection, forcing users to attempt a save before discovering circular sub-rule dependencies.

### 8. WAIT (Duration & Timestamp Delay)
- **UI Controls**: `WaitNodeConfig.vue`, `SelectControl.vue`, `DataControl.vue`
- **Key Parameters**: `config.wait_type` (`Duration`, `Timestamp`), `config.value`, `config.unit` (`Minutes`, `Hours`, `Days`).
- **UI/UX Bottlenecks & Flaws**:
  - Selecting `Timestamp` wait type requires entering a Jinja expression or datetime string, but no datetime picker control is embedded in `WaitNodeConfig.vue`.

### 9. SWITCH (Multi-Branch Routing)
- **UI Controls**: `SwitchNodeConfig.vue`, `GenericGrid.vue`
- **Key Parameters**: `config.variable`, `config.cases` (`value`, `target_handle`).
- **UI/UX Bottlenecks & Flaws**:
  - Adding new switch case rows does not dynamically scaffold matching output handles on the Vue Flow canvas node until full canvas re-layout or reload.

### 10. STOP (Terminal Execution)
- **UI Controls**: `ActionFieldProperties.vue`
- **Key Parameters**: `operation` (`Success`, `Error`), `value_template`.
- **UI/UX Bottlenecks & Flaws**:
  - `Stop` node in `Error` mode allows entering error templates, but `value_template` input lacks Jinja variable autocomplete hints available in `TextGeneratorControl`.

### 11. RAISE ERROR (Validation Exception)
- **UI Controls**: `ActionFieldProperties.vue`
- **Key Parameters**: `config.error_type` (`Validation Error`, `Permission Error`), `value_template`.
- **UI/UX Bottlenecks & Flaws**:
  - Migration code transforms `Raise Error` with `operation == 'Error'` into `config.error_type = 'Validation Error'`, but legacy rules retain `operation: 'Error'` in serialized `doc.actions`, causing contract validation warnings.

### 12. NOTIFY (System Email & Communication)
- **UI Controls**: `TextGeneratorControl.vue`, `ControlFactory.vue`
- **Key Parameters**: `config.recipients`, `value_template` (Message body).
- **UI/UX Bottlenecks & Flaws**:
  - Recipient field accepts comma-separated email addresses or context variables, but fails to validate syntax until runtime execution.

### 13. DOCUMENT ACTION (DocType Workflow State Changes)
- **UI Controls**: `ActionFieldProperties.vue`
- **Key Parameters**: `operation` (`Submit`, `Cancel`, `Trash`, `Amend`), `reference_doctype`.
- **UI/UX Bottlenecks & Flaws**:
  - Attempting to submit a non-submittable DocType is blocked by backend `validate_rule_definition`, but the node configuration UI does not disable submittable-only operations when `reference_doctype` is selected.

---

## ACTIONABLE REMEDIATION ROADMAP

1. **Unify Validation & Canvas Highlighting**:
   - Update `useUIStore.js` to anchor validation error arrays to `node.id`, applying `border-red-500` and error tooltips directly to Vue Flow nodes.
2. **Streamline Click Depth**:
   - Replace modal-heavy assignment editing with inline Quick-Edit bars on node canvas cards.
3. **Proactive Contract Pre-Validation**:
   - Run local contract validation inside node configuration drawers during input `@update:modelValue` events to catch errors before global save.
