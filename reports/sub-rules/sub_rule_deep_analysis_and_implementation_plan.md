# Sub-Rule System Deep Analysis & Production-Ready Implementation Plan

## Executive Summary

Sub-Rules in **FlexiRule** serve as modular, encapsulated, and reusable subroutines within the rule execution graph. They allow complex, repeated business logic (such as credit limit checks, tax computations, or discount rules) to be authored once and invoked across multiple rules.

This document presents a deep architectural analysis of FlexiRule's Sub-Rule system, examining:
1. **Backend Sub-Rule Execution Engine**: Cycle detection, depth protection, context isolation via `SubRuleVarsOverlay`, security/permission bypass policies, and parameter mapping.
2. **`Rule` DocType Schema & Interface Contract**: Analysis of sub-rule fields (`trigger_type`, `exposed_as_subrule`, `input_schema`, `output_schema`) and public contract resolution (`sub_rule_contract.py`).
3. **Current Configuration UI & Variable Propagation**: How `SubRuleConfig.vue`, `InputPanel.vue`, `OutputPanel.vue`, and `TransformControl.vue` manage sub-rule mapping and downstream variable discovery.
4. **Production-Ready Implementation Proposal**: A target UI/UX design specification and a phased implementation roadmap for production readiness.

---

## Part 1: Deep Analysis of Backend Implementation

The backend sub-rule engine is driven by `SubRuleHandler` (`flexirule/ruleflow/core/action_handlers/sub_rule.py`) and integrated directly into `RuleEngine`.

### 1. Target Rule Resolution
When an action node with `action_type = "Sub-Rule"` executes, `SubRuleHandler` resolves the target rule:
- **Reference Resolution**: Inspects `action.rule` or `config.sub_rule_name` / `config.rule`.
- **Runtime Registry**: Resolves the active version of logical rule names using `RuleCoordinator.get_runtime_registry()["active_sub_rules"]` or `resolve_rule_reference(sub_rule_name, active_only=True, callable_only=True, exposed_only=True)`.
- **Invocability Guards**: Strictly requires that the target rule satisfies three conditions:
  1. `trigger_type == "Callable Event"`
  2. `exposed_as_subrule == 1`
  3. `is_active == 1`
  If any condition fails, execution raises `MethodExecutionError`.

### 2. Cycle Detection & Recursion Guards
To prevent infinite execution loops and stack overflows:
- **Logical Base Name Stack**: Tracks `execution_stack` in `context["meta"]["execution_stack"]` using base rule names (`base_rule_name` or stripped `_v\d+$` suffixes). If `target_base_name` matches any ancestor in `execution_stack` or the caller itself, `SubRuleHandler` raises `CycleDetectedError`.
- **Depth Limit**: Enforces `MAX_SUB_RULE_DEPTH = 10`. Stack depth is tracked in `context["_sub_rule_depth"]` and `meta["call_depth"]`. Exceeding this limit immediately raises `CycleDetectedError`.

### 3. Execution Context Isolation (`SubRuleVarsOverlay`)
To keep sub-rule executions clean while preserving backward compatibility:
- **Copy-on-Write Overlay**: `SubRuleVarsOverlay` wraps parent variables (`context["vars"]`). Reads search local child mutations first, falling back to parent variables. Writes mutate *only* the child overlay.
- **Result Extraction**: Upon completion, `export_mutations()` extracts only variables assigned or written during the sub-rule's execution, preventing accidental pollution of the caller's global variable scope.

### 4. Input & Output Mapping
- **Input Mapping**: Translates parent variables or context expressions into child parameters using `config.input_mapping` (via `apply_input_mapping`). Mapped variables are injected directly into `sub_context["vars"]`.
- **Output Mapping & Namespacing**:
  - If `config.output_mapping` is specified, maps exported sub-rule result variables back into parent `context["vars"]` using `apply_output_mapping`.
  - If `return_variable` is defined on the action, stores the exported dictionary at `vars[return_variable]`.
  - Otherwise, auto-namespaces results under `vars["subrule_<action_id>"]` to guarantee deterministic storage.

### 5. Permission & Condition Bypass
- **`skip_conditions`**: Defaults to `1` (skip). If set to `0`, the sub-rule's `trigger_condition` is evaluated against an eligibility context containing `_caller_rule`, `_caller_trigger_type`, `_caller_document_type`, etc.
- **`ignore_permissions`**: If enabled on the action, passes through identity authorization (`can_ignore_permissions`). Requires a non-empty `permission_audit_reason` and logs an `AUDIT` entry.

---

## Part 2: Analysis of `Rule` DocType Sub-Rule Fields

The `Rule` DocType contains explicit fields designed specifically for Sub-Rule definition and interface contracts:

| Field Name | Field Type | Section | Purpose |
| :--- | :--- | :--- | :--- |
| `trigger_type` | Select | Trigger Configuration | Must be `"Callable Event"` for the rule to be invocable as a subroutine. |
| `exposed_as_subrule` | Check | Trigger Configuration | Toggles public visibility (`1`/`0`). Only exposed rules appear in sub-rule selection options. |
| `section_break_subrule_interface` | Section Break | Sub-Rule Interface | UI section container, dependent on `trigger_type == 'Callable Event'` and `exposed_as_subrule == 1`. |
| `input_schema` | JSON / Code | Sub-Rule Interface | Declares expected caller input parameters array: `[{ fieldname, label, fieldtype, options, reqd, default, description }]`. |
| `output_schema` | JSON / Code | Sub-Rule Interface | Declares exported output fields array: `[{ fieldname, label, fieldtype, reqd, source, children }]`. |

### Public Interface Resolution (`sub_rule_contract.py`)
- **Dual Mode (Declared vs. Inferred)**:
  - **Declared Mode**: When `input_schema` or `output_schema` is populated, the backend parses and validates the JSON array, checking fieldname patterns and mandatory flags.
  - **Inferred Compatibility Mode**: If schemas are empty, `get_sub_rule_contract(rule_doc)` infers inputs (via variable discovery in `validation_service.py`) and outputs (via action return variables, process variable writes, and assignment targets).
- **Contract API**: `flexirule.ruleflow.api.get_sub_rule_contract(rule_name)` provides a unified RPC endpoint returning contract versioning, schema definitions, declaration source (`declared` vs `inferred`), and validation errors.

---

## Part 3: Current Config UI Analysis & Variable Catalog Propagation

The frontend configuration UI for a Sub-Rule action node is managed in `SubRuleConfig.vue`, `InputPanel.vue`, `OutputPanel.vue`, and `TransformControl.vue`.

### Current Workflow & Capabilities:
1. **Rule Selector**:
   - Uses `ComboBoxControl` bound to `node.data.rule`. Fetches available callable rules from `useRuleStore.fetch_available_rules()`.
2. **Contract Resolution**:
   - Calls `flexirule.ruleflow.api.get_sub_rule_contract` upon rule selection.
   - Populates `inputTargetOptions` from `contract.input_schema`.
   - Propagates `contract.output_schema` directly to `node.data.resolved_output_schema`.
3. **Input Parameter Mapping**:
   - Supports **Table Mode** (`List`) and **Visual Mapper Mode** (`TransformControl.vue`).
   - Maps parent available variables (`store.variables`) to sub-rule target parameters.
4. **Variable Catalog Propagation**:
   - `resolved_output_schema` on the action node is read by `useMetaStore` / `getAvailableVariables(nodeId)`.
   - Downstream action nodes (Assignments, Conditions, Process calls) can browse and auto-complete output fields produced by the sub-rule, including nested child structures (`vars.sub_result.items.rate`).

---

## Part 4: Production-Ready Configuration UI Proposal & Implementation Roadmap

### 1. UX Design & Feature Specification

```
┌──────────────────────────────────────────────────────────────────────────┐
│  Sub-Rule Action Node: Call Customer Credit Check                         │
├──────────────────────────────────────────────────────────────────────────┤
│  Target Sub-Rule: [ Customer Credit Check (Active v2)                  ▼]│
│  Interface Contract: [✓ Declared] [2 Inputs, 3 Outputs]                  │
├──────────────────────────────────────────────────────────────────────────┤
│  Input Parameter Mapping                                                  │
│  [ List View | Visual Mapper ]                              [+ Add Row] │
│  ┌──────────────────────────┬───┬──────────────────────────────────────┐ │
│  │ Parent Context Variable  │   │ Sub-Rule Parameter                   │ │
│  ├──────────────────────────┼───┼──────────────────────────────────────┤ │
│  │ vars.customer_code       │ → │ party (Customer) [Reqd]              │ │
│  │ vars.posting_date        │ → │ as_of_date (Date)                    │ │
│  └──────────────────────────┴───┴──────────────────────────────────────┘ │
├──────────────────────────────────────────────────────────────────────────┤
│  Execution & Security Settings                                           │
│  [✓] Skip Trigger Conditions                                             │
│  [ ] Bypass Permissions (Requires Audit Reason)                          │
└──────────────────────────────────────────────────────────────────────────┘
```

### Key UI/UX Enhancements:
1. **Contract Health & Status Header**:
   - Contract badge displaying whether the target sub-rule uses an **Explicit Declared Contract** or **Inferred Legacy Contract**.
   - Direct link/button to open the target Sub-Rule in a new tab for inspection or editing.
   - Real-time display of target contract validation warnings (e.g. unmapped required inputs).
2. **Enhanced Parameter Mapping**:
   - **Auto-Align Button**: Single-click auto-mapping matching parent variable names to sub-rule parameter names.
   - Clear visual indicator for required target parameters (`reqd: 1`).
   - Full autocomplete support for parent context variables using `useNavigableFields`.
3. **Output & Result Integration**:
   - Unified display of output result variable name (`return_variable`) and automatic schema preview.

---

### 2. Actionable Implementation Roadmap

#### Phase 1: Sub-Rule Interface Contract Hardening & Backend Validation (1-2 Days)
- Enhance `validation_service.py` to perform strict cross-rule contract validation during parent rule save:
  - Check that all required sub-rule inputs (`reqd: 1`) are supplied in `input_mapping`.
  - Verify that mapped target parameter names exist in target's declared input schema.
- Add backend test coverage for edge-case contract mismatches in `test_sub_rule_contract.py`.

#### Phase 2: Enhanced Configuration UI Component (`SubRuleConfig.vue`) (2-3 Days)
- Refactor `SubRuleConfig.vue`:
  - Add **Auto-Align** action button to match parent variables with sub-rule parameters.
  - Implement contract status header badge and active version indicator.
  - Integrate `useNavigableFields` for rich parent variable autocomplete in mapping rows.
  - Highlight missing mandatory inputs in red during validation.

#### Phase 3: Visual Data Flow & Variable Discovery Verification (1-2 Days)
- Verify `resolved_output_schema` propagation in `useMetaStore`.
- Ensure nested child fields from sub-rule outputs are correctly displayed in downstream `ComboBoxControl` and `ValueResolverControl`.

#### Phase 4: End-to-End Testing & Pre-Commit Audit (1 Day)
- Execute frontend Node tests and Cypress E2E smoke tests for Sub-Rule authoring and canvas execution.
- Run Python backend test suite (`test_sub_rule_contract.py`, `test_subrule_activation.py`, `test_engine_comprehensive.py`).
- Run linter checks (`pre-commit run --all`).
