# Sub-Rule Deep Analysis & Production-Ready Config UI Proposal & Implementation Plan

## Executive Summary

Sub-Rules in **FlexiRule** serve as modular, encapsulated, and reusable workflow units. A Sub-Rule allows complex decision logic, validations, or calculations to be extracted into standalone callable rules that can be invoked from parent rules.

While the backend architecture for Sub-Rules is robust—featuring version resolution, cross-rule cycle detection, call-stack depth limits, context isolation via `SubRuleVarsOverlay`, and schema contract inference—the current authoring and configuration UI has key UX and functionality gaps. Specifically, defining Sub-Rule public contracts (`input_schema` and `output_schema`) relies on raw JSON textareas on the `Rule` DocType, and configuring Sub-Rule action nodes (`SubRuleConfig.vue`) handles input mapping but lacks an integrated, visual output mapping interface and contract validation status.

This document provides:
1. A **deep architectural analysis** of how Sub-Rules function in the FlexiRule backend.
2. A **field-level analysis** of the `Rule` DocType attributes created specifically for Sub-Rules.
3. An **audit of the current frontend implementation** and identification of key usability gaps.
4. A **production-ready proposal** for the Sub-Rule Configuration UI and Sub-Rule Contract Visual Builder.
5. A **step-by-step implementation plan** with concrete component specifications, API interactions, and testing strategies.

---

## Part 1: Deep Analysis of Sub-Rule Backend Architecture

### 1.1 Core Sub-Rule Execution Lifecycle (`SubRuleHandler`)
The backend handler for Sub-Rules resides in `flexirule/ruleflow/core/action_handlers/sub_rule.py`. When an action node of type `Sub-Rule` executes inside the `RuleEngine`:

1. **Target Rule Resolution**:
   - The handler attempts to resolve the target sub-rule reference (`action.rule` or `config.sub_rule_name`).
   - Resolution checks the `RuleCoordinator` runtime registry for the active version of `base_rule_name`, falling back to `resolve_rule_reference()`.
   - The target `Rule` document must satisfy three strict guardrails:
     - `trigger_type == "Callable Event"`
     - `exposed_as_subrule == 1`
     - `is_active == 1`

2. **Cycle & Depth Protection**:
   - **Cross-Rule Cycle Detection**: Prevents infinite loops across rule invocations (e.g. Rule A → Rule B → Rule A). It normalizes names to `base_rule_name` and checks `meta.execution_stack`. If a base rule exists in the execution stack, a `CycleDetectedError` is raised.
   - **Recursion Depth Limits**: Enforces `MAX_SUB_RULE_DEPTH = 10`. If call depth reaches this limit, execution halts safely.

3. **Trigger Filter & Permission Evaluation**:
   - `skip_conditions`: If set to `0`, the handler evaluates the target sub-rule's `trigger_condition` against caller context augmented with caller metadata (`_caller_rule`, `_caller_trigger_type`, etc.).
   - `ignore_permissions`: If set to `1`, permission checks are bypassed during sub-rule execution, generating an `AUDIT` log entry with `frappe.session.user`.

4. **Context Isolation (`SubRuleVarsOverlay`)**:
   - To prevent unintended global variable side-effects, child context receives a `SubRuleVarsOverlay`.
   - Read operations check child mutations first, then fall back to parent variables.
   - Write operations modify child local mutations only, preserving copy-on-write semantics.

5. **Input and Output Mapping**:
   - **Input Mapping**: Evaluates `config.input_mapping` against parent context and injects mapped keys directly into child `vars`.
   - **Output Mapping & Auto-Namespacing**:
     - If `config.output_mapping` is defined, `apply_output_mapping()` transfers specific child variables into parent context `vars`.
     - If `action.return_variable` is defined, the entire child variable payload is assigned to `vars[return_variable]`.
     - If neither is provided, outputs fall back to a deterministic auto-namespace: `vars["subrule_<action_id>"]`.

---

### 1.2 Sub-Rule Contract Engine (`sub_rule_contract.py`)

The contract engine defines the formal public interface for callable Sub-Rules:

1. **Explicit Schemas vs. Inferred Compatibility Mode**:
   - **Explicit Contract**: Defined via `input_schema` and `output_schema` JSON arrays on the target `Rule`.
   - **Inferred Contract**: For legacy rules without declared schemas, `get_sub_rule_contract()` infers:
     - *Inputs*: Required variables detected across all condition expressions and actions in the rule.
     - *Outputs*: Roots created by action return variables, Process `writes_vars`, and `Assignment` actions to `vars.*`.

2. **Contract Structure**:
   - **Input Schema Item**: `{ fieldname, label, fieldtype, options, reqd, default, description }`
   - **Output Schema Item**: `{ fieldname, label, fieldtype, reqd, source, children }` (where `children` supports nested sub-fields for complex objects/tables).

3. **Validation Rules**:
   - `validate_sub_rule_contract()` checks that:
     - Declared input schemas include all required variables referenced within the Sub-Rule.
     - Declared output schemas do not promise fields that the Sub-Rule's actions never write.
     - Simple field identifiers and duplicate fieldname checks are satisfied.

---

## Part 2: Analysis of `Rule` DocType Sub-Rule Fields

The `Rule` DocType (`flexirule/ruleflow/doctype/rule/rule.json`) includes dedicated fields specifically created for Sub-Rule definition and lifecycle management:

| Fieldname | Fieldtype | Visibility / Dependency | Description |
| :--- | :--- | :--- | :--- |
| `trigger_type` | Select | Always visible | Set to `"Callable Event"` for Sub-Rules. |
| `exposed_as_subrule` | Check | `eval:doc.trigger_type==="Callable Event"` | Checkbox granting permission for this rule to be invoked as a Sub-Rule. |
| `section_break_subrule_interface` | Section Break | `eval:doc.trigger_type==="Callable Event" && doc.exposed_as_subrule` | Collapsible section containing contract definition tools. |
| `input_schema` | Code (JSON) | `eval:doc.trigger_type==="Callable Event" && doc.exposed_as_subrule` | Raw JSON array storing the public input parameters contract. |
| `output_schema` | Code (JSON) | `eval:doc.trigger_type==="Callable Event" && doc.exposed_as_subrule` | Raw JSON array storing the public output contract and nested child fields. |
| `base_rule_name` | Data | Read-only | Logical identifier used across versions for target resolution and cycle detection. |
| `version` | Int | Read-only | Auto-incrementing version counter ensuring contract compatibility across iterations. |

### Key Issues Identified in Field Usage:
1. **Raw JSON Input/Output Textareas**: Storing `input_schema` and `output_schema` as raw JSON code fields makes contract creation error-prone and unintuitive for business analysts and rule designers.
2. **Lack of Live Contract Validation in Form View**: Designers editing raw JSON receive no instantaneous feedback on missing required inputs or invalid JSON formatting until document save.

---

## Part 3: Analysis of Current Frontend Sub-Rule Config UI

The current frontend UI components involved in Sub-Rule configuration are:
1. `flexirule/public/js/flexirule/rule_builder/components/rule_config/types/SubRuleConfig.vue`: Configures Sub-Rule action nodes inside the visual Rule Builder graph.
2. `InputPanel.vue` and `OutputPanel.vue`: Sidebar panels supplying variable catalogues and contract metadata.
3. `TransformControl.vue`: Provides a visual drag-and-drop / node mapper for field mappings.

### Identified UX Gaps & Limitations:
1. **Missing Output Mapping Interface in `SubRuleConfig.vue`**:
   - `SubRuleConfig.vue` currently only renders an **Input Mapping** section.
   - To configure output extraction, users must rely on `return_variable` or auto-namespacing. There is no visual table/mapper for mapping specific Sub-Rule outputs back to custom parent variables (`vars.*`).
2. **Missing Interface Contract Status & Diagnostic Card**:
   - While `SubRuleConfig.vue` calls `flexirule.ruleflow.api.get_sub_rule_contract`, it only displays simple error messages if loading fails.
   - It lacks a summary badge showing:
     - Target Sub-Rule status (Active vs. Draft vs. Missing).
     - Declared vs. Inferred contract status.
     - List of required inputs with visual indicator (asterisk/badge).
3. **Absence of Visual Contract Builder for Sub-Rule Authors**:
   - When editing a rule with `trigger_type = "Callable Event"`, the user has no visual UI in Frappe Form view or Rule Builder header settings to define `input_schema` and `output_schema` visually.
4. **Variable Catalogue Schema Propagation**:
   - Downstream action nodes after a Sub-Rule call do not automatically receive nested child schema autocompletion unless `resolved_output_schema` is explicitly saved on the node data.

---

## Part 4: Production-Ready UI/UX Proposal & Component Architecture

To resolve these limitations, we propose a comprehensive, production-ready Sub-Rule Configuration UI overhaul.

```
+-----------------------------------------------------------------------------------+
|                            Sub-Rule Action Configuration                          |
+-----------------------------------------------------------------------------------+
| Target Sub-Rule: [ Select Callable Sub-Rule v ] (Active | Version 2 | Contract Valid) |
+-----------------------------------------------------------------------------------+
| [ TAB 1: Input Mapping ]   [ TAB 2: Output Mapping ]   [ TAB 3: Execution Rules ] |
+-----------------------------------------------------------------------------------+
| TAB 1: INPUT MAPPING                                                              |
| Mode: [ Visual Mapper | Key-Value List ]                                         |
| Parent Variable / Expression       -->   Sub-Rule Parameter                        |
| [ vars.customer_id             v ] -->   [ party (Customer) *         ]          |
| [ doc.posting_date             v ] -->   [ transaction_date (Date)    ]          |
| [+ Auto-Map Matching Fields]                                                      |
+-----------------------------------------------------------------------------------+
| TAB 2: OUTPUT MAPPING                                                             |
| Target Variable in Parent Scope   <--   Sub-Rule Output Field                     |
| [ vars.credit_score            v ] <--   [ score (Int)                ]          |
| [ vars.approval_status         v ] <--   [ status (Data)              ]          |
| Root Return Variable: [ vars.subrule_result ] (Stores complete response object)  |
+-----------------------------------------------------------------------------------+
| TAB 3: EXECUTION RULES                                                            |
| [x] Skip Sub-Rule Trigger Filters                                                 |
| [ ] Bypass Permission Checks (ignore_permissions)                                 |
|     Reason: [ Must provide audit reason when checked                     ]        |
+-----------------------------------------------------------------------------------+
```

### Key UI Features:

1. **Sub-Rule Contract Visual Builder (`SubRuleContractBuilder.vue`)**:
   - Embedded directly in Frappe Form view (`rule.js`) and Rule Builder settings.
   - Provides a dynamic table editor for inputs and outputs with column controls:
     - `FieldName` (slugified identifier)
     - `Label` (display text)
     - `Fieldtype` (Select: Data, Link, Currency, Table, Check, Int, Float, Select, etc.)
     - `Options / DocType` (conditional on fieldtype)
     - `Required` (Check)
     - `Source / Description`
     - Child Fields Editor for `Table` / `JSON` object outputs.
   - Includes a **"Auto-Infer Schemas from Rule Logic"** button that populates the contract based on static analysis of the sub-rule's internal steps.

2. **Unified Sub-Rule Action Config (`SubRuleConfig.vue`)**:
   - **Header Header Card**:
     - Shows Target Rule Status badge (Active/Inactive), Version Tag, and Contract Validity state.
     - Direct "Edit Sub-Rule in New Tab" link for quick authoring navigation.
   - **Tab 1: Input Mapping**:
     - Displays Sub-Rule input schema with clear indications for required (`*`) vs optional parameters.
     - "Auto-Map Fields" button: automatically matches parent variables with sub-rule parameters based on name similarity.
     - Dual-mode support: Visual Mapper (`TransformControl.vue`) and Table List.
   - **Tab 2: Output Mapping**:
     - Allows explicit mapping of sub-rule output fields to parent scope `vars.<name>`.
     - Displays `return_variable` option for capturing the complete output payload dictionary.
     - Automatically updates `resolved_output_schema` on the action node so downstream nodes gain full autocomplete support.
   - **Tab 3: Execution Controls**:
     - Toggle for `skip_conditions` (default checked).
     - Toggle for `ignore_permissions` with mandatory audit reason input box.

3. **Downstream Variable Catalogue Integration**:
   - Enhances `useRuleStore.js` and `useGraphStore.js` to inspect `Sub-Rule` nodes and automatically append their `resolved_output_schema` to the available variable catalogue.

---

## Part 5: Step-by-Step Production Implementation Roadmap

### Phase 1: Sub-Rule Contract Visual Builder Component
- **Files to create/modify**:
  - `flexirule/public/js/flexirule/rule_builder/components/contract/SubRuleContractBuilder.vue`
  - `flexirule/ruleflow/doctype/rule/rule.js`
- **Tasks**:
  1. Build `SubRuleContractBuilder.vue` supporting visual row addition, fieldtype pickers, required toggles, options inputs, and child field schema editors for outputs.
  2. Integrate `SubRuleContractBuilder` into Frappe `Rule` form view to replace raw JSON textareas for `input_schema` and `output_schema`.
  3. Add "Infer Contract from Logic" button calling backend API `flexirule.ruleflow.api.get_sub_rule_contract` with `infer_only=True`.

### Phase 2: Refactor `SubRuleConfig.vue`
- **Files to modify**:
  - `flexirule/public/js/flexirule/rule_builder/components/rule_config/types/SubRuleConfig.vue`
- **Tasks**:
  1. Reorganize `SubRuleConfig.vue` into 3 structured tabs/sections: Input Mapping, Output Mapping, Execution Rules.
  2. Implement Output Mapping table editor (`config.output_mapping`).
  3. Add "Auto-Map Matching Inputs" and "Auto-Map Matching Outputs" quick action buttons.
  4. Add Sub-Rule Target Header Status Card with live contract validation status.

### Phase 3: Downstream Schema Propagation & Store Integration
- **Files to modify**:
  - `flexirule/public/js/flexirule/rule_builder/stores/useRuleStore.js`
  - `flexirule/public/js/flexirule/rule_builder/composables/useRuleConfig.js`
- **Tasks**:
  1. Ensure `resolved_output_schema` is saved into node data when Sub-Rule contract loads or output mapping changes.
  2. Update variable catalog computed property in `useRuleStore` to recursively parse `resolved_output_schema` from preceding `Sub-Rule` nodes.

### Phase 4: Backend API Enhancements & Guardrails
- **Files to modify**:
  - `flexirule/ruleflow/api.py`
  - `flexirule/ruleflow/core/sub_rule_contract.py`
- **Tasks**:
  1. Ensure `get_sub_rule_contract` API returns comprehensive status flags (`is_active`, `version`, `base_rule_name`, `errors`, `input_schema_declared`, `output_schema_declared`).
  2. Enforce validation check on Rule submit/activate when `trigger_type == "Callable Event"` and `exposed_as_subrule == 1`.

### Phase 5: Verification & End-to-End Testing
- **Files to create/modify**:
  - `flexirule/ruleflow/tests/test_sub_rule_config_ui.py`
  - `cypress/integration/sub_rule_builder.cy.js`
- **Tasks**:
  1. Write backend unit tests for contract inference and API endpoints.
  2. Write Cypress E2E test covering:
     - Sub-Rule creation with visual contract builder.
     - Sub-Rule invocation from parent rule with Input & Output mapping.
     - Verification of context isolation and output variable availability in downstream nodes.

---

## Part 6: Pre-Commit & Verification Strategy

Before submitting implementation changes, the following checks must be executed:
1. **Frontend Unit Tests**: Run `yarn test:frontend` to verify standalone JS/Vue unit tests.
2. **Backend Unit Tests**: Run `bench --site test_site run-tests --module flexirule.ruleflow.tests.test_sub_rule_contract` and `test_rule`.
3. **Pre-Commit Framework**: Run `pre-commit run --all` from the virtual environment (`/home/jules/frappe-bench/env/bin/pre-commit`).
