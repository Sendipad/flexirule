# Branch Change Analysis

**Date:** 2026-03-31
**Target Branch:** `develop-1276450611588157079`
**Baseline:** `develop`

---

## 1. Executive Summary

This report delivers a deep, evidence-based architectural analysis and verification of the changes introduced in target branch `develop-1276450611588157079` relative to `develop`.

The core objective of the branch is the **consolidation of the Value Resolver taxonomy**, specifically targetting two major resolver families:
1. **Date & Time Family (`date_time`)**: Consolidates legacy date resolvers (`date_formula` / `date_diff`) into a unified `date_time` family supporting three canonical operations: `calculate`, `diff`, and `format`.
2. **Text Transform Family (`text`)**: Consolidates string manipulation (`string_formula`), normalization (`normalization`), and text formatting (`format`) into a single `text` resolver component (`TextTransformResolver.vue`) supporting four canonical operations: `combine`, `case`, `normalize`, and `format`.

In addition, the branch introduces updates to **Collection / Child Aggregation** resolvers, updates UI controls (`FlexValueControl.vue`, `AssignmentConfig.vue`, `FilterGroup.vue`), and enhances the graph store (`useGraphStore.js`) for dirty state tracking.

**Overall Assessment:** The branch significantly advances FlexiRule's Value Resolver consolidation roadmap, improving UI usability and backward compatibility. However, **critical backend and contract inconsistencies** were discovered during deep code inspection—most notably in `useGraphStore.js` (unreferenced method breakages) and `value_resolver.py` (incomplete operation handling for `fmt_money` in `FormatResolver` and missing compilation paths for legacy `date_formula` / `date_diff` top-level configs).

---

## 2. Comparison Scope

- **Baseline Commit:** `b3c3e43172cf2f65d31725173f2b49bc57308d2f` (`origin/develop`)
- **Target Commit:** `c4d677286baa15b4397a201cacf78e7fb49d3ce2` (`origin/develop-1276450611588157079`)
- **Merge Base:** `b3c3e43172cf2f65d31725173f2b49bc57308d2f`
- **Total Unique Commits:** 1 (`c4d6772 refactor(resolver): consolidate Date & Time family into date_time`)
- **Total Changed Files:** 20 files (+1282 lines, -1107 lines)

---

## 3. Commit Summary

| Commit SHA | Author | Message | Logical Scope |
| :--- | :--- | :--- | :--- |
| `c4d6772` | FlexiRule Team | `refactor(resolver): consolidate Date & Time family into date_time` | Consolidated `date_time` and `text` resolver families, added operations subcomponents, updated backend compiler, and expanded regression tests. |

---

## 4. Changed Files Summary

| File | Change | Area | Risk | Notes |
| :--- | :--- | :--- | :--- | :--- |
| `flexirule/public/js/flexirule/core/formula_registry.js` | Modified | Frontend Core | Low | Updated formula registry definitions for new operations |
| `flexirule/public/js/flexirule/rule_builder/components/rule_config/FilterGroup.vue` | Modified | Frontend UI | Low | Filter control formatting adjustment |
| `flexirule/public/js/flexirule/rule_builder/components/rule_config/types/AssignmentConfig.vue` | Modified | Frontend Action | Medium | Updated resolver props and initialization handling |
| `flexirule/public/js/flexirule/rule_builder/controls/FlexValueControl.vue` | Modified | Frontend Control | Medium | Added `date_time` & `text` family support to value picker |
| `flexirule/public/js/flexirule/rule_builder/controls/value_resolver/components/CollectionResolver.vue` | Modified | Frontend Resolver | Low | UI label and prop synchronization |
| `flexirule/public/js/flexirule/rule_builder/controls/value_resolver/components/DateTimeResolver.vue` | Added | Frontend Resolver | High | Primary Date & Time UI component |
| `flexirule/public/js/flexirule/rule_builder/controls/value_resolver/components/FormatResolver.vue` | Deleted | Frontend Resolver | Medium | Replaced by `TextTransformResolver.vue` |
| `flexirule/public/js/flexirule/rule_builder/controls/value_resolver/components/NormalizationResolver.vue` | Deleted | Frontend Resolver | Medium | Replaced by `TextTransformResolver.vue` |
| `flexirule/public/js/flexirule/rule_builder/controls/value_resolver/components/StringFormulaResolver.vue` | Deleted | Frontend Resolver | Medium | Replaced by `TextTransformResolver.vue` |
| `flexirule/public/js/flexirule/rule_builder/controls/value_resolver/components/TextTransformResolver.vue` | Added | Frontend Resolver | High | Consolidated Text Transform UI component |
| `.../operations/DateTimeCalculateConfig.vue` | Renamed | Frontend Operation | Medium | Renamed from `DateFormulaResolver.vue` |
| `.../operations/DateTimeDiffConfig.vue` | Renamed | Frontend Operation | Medium | Renamed from `DateDiffResolver.vue` |
| `.../operations/DateTimeFormatConfig.vue` | Added | Frontend Operation | Low | New operation component for date formatting |
| `flexirule/public/js/flexirule/rule_builder/controls/value_resolver/index.js` | Modified | Frontend Registry | High | Re-registered strategies for `date_time` and `text` |
| `flexirule/public/js/flexirule/rule_builder/controls/value_resolver/strategies.js` | Modified | Frontend Registry | Medium | Added strategy filtering (`hidden`, `child_aggregation`) |
| `flexirule/public/js/flexirule/rule_builder/controls/value_resolver/useValueResolver.js` | Modified | Frontend Composable | High | Normalization logic for canonical family structure |
| `flexirule/public/js/flexirule/rule_builder/stores/useGraphStore.js` | Modified | Frontend Store | High | Graph dirty state tracking refactor |
| `flexirule/ruleflow/core/value_resolver.py` | Modified | Backend Engine | High | Compiler dispatch for canonical `family` and backward compatibility |
| `flexirule/ruleflow/tests/test_collection_resolver.py` | Modified | Backend Tests | Low | Added sum, avg, and legacy payload tests |
| `flexirule/ruleflow/tests/test_value_resolvers_complex.py` | Modified | Backend Tests | Low | Added tests for `date_time` and `text` families |

---

## 5. Architectural Changes

### 1. Value Resolver Taxonomy Consolidation
- **Date & Time Family (`date_time`)**: Replaces top-level `date_formula` and `date_diff` strategies.
  - Canonical Structure: `{ family: "date_time", operation: "calculate" | "diff" | "format", config: { ... } }`.
  - Strategy Key in JS: `date_time`.
- **Text Transform Family (`text`)**: Replaces `string_formula`, `normalization`, and `format` top-level strategies.
  - Canonical Structure: `{ family: "text", operation: "combine" | "case" | "normalize" | "format", config: { ... } }`.
  - Strategy Key in JS: `text`.

### 2. UI Component Hierarchy
- Operations for `date_time` are split into modular Vue components inside `controls/value_resolver/components/operations/`:
  - `DateTimeCalculateConfig.vue` (for `calculate` operation)
  - `DateTimeDiffConfig.vue` (for `diff` operation)
  - `DateTimeFormatConfig.vue` (for `format` operation)

---

## 6. Backend Changes

### 1. `ValueResolver.compile_resolver_config` Updates (`value_resolver.py`)
- Added checks for `family == "collection"` or `kind == "collection"` and `family == "child_aggregation"` / `kind == "child_aggregation"`.
- Added checks for `family == "text"` or `kind == "text"`:
  - `op == "combine"` -> returns `StringFormulaResolver` (`str_op="concat"`)
  - `op == "case"` -> returns `StringFormulaResolver` (for `uppercase`/`lowercase`) or `NormalizationResolver` (for `titlecase` / custom)
  - `op == "normalize"` -> returns `NormalizationResolver`
  - `op == "format"` -> returns `FormatResolver` (`fmt_op="format"`)
- Added checks for `family == "date_time"` or `kind == "date_time"`:
  - `op == "calculate"` -> returns `DateFormulaResolver`
  - `op == "diff"` -> returns `DateDiffResolver`
  - `op == "format"` -> returns `FormatResolver` (`fmt_op="format_date"`)

### 2. Class Definitions Preserved
- `DateFormulaResolver`, `DateDiffResolver`, `StringFormulaResolver`, `NormalizationResolver`, `FormatResolver`, and `CollectionResolver` are all retained in Python to execute resolved logic.

---

## 7. Frontend Changes

### 1. `useValueResolver.js`
- Normalizes incoming payloads upon initialization in `setupState()`:
  - Converts legacy `child_aggregation` or `collection` payloads to standard structure.
  - Converts `text` and `date_time` payloads to normalized structures with `operation` and `config`.
- Emits serialized state in canonical 2-level payload format:
  ```json
  {
    "family": "date_time",
    "operation": "calculate",
    "config": { ... },
    "kind": "date_time"
  }
  ```

### 2. Strategy Registry (`index.js` & `strategies.js`)
- Unregistered legacy top-level strategies (`date_formula`, `date_diff`, `string_formula`, `normalization`, `format`).
- Registered `date_time` and `text` strategies.
- Updated `getAllStrategies()` in `strategies.js` to filter out hidden strategies and `child_aggregation`.

---

## 8. Value Resolver Changes

The table below summarizes the transition between baseline and target branch resolver taxonomy:

| Baseline Kind / Family | Target Canonical Family | Target Operation | UI Component | Backend Resolver Class |
| :--- | :--- | :--- | :--- | :--- |
| `date_formula` | `date_time` | `calculate` | `DateTimeCalculateConfig.vue` | `DateFormulaResolver` |
| `date_diff` | `date_time` | `diff` | `DateTimeDiffConfig.vue` | `DateDiffResolver` |
| (New Operation) | `date_time` | `format` | `DateTimeFormatConfig.vue` | `FormatResolver` (`fmt_op="format_date"`) |
| `string_formula` | `text` | `combine` | `TextTransformResolver.vue` | `StringFormulaResolver` |
| `string_formula` (case) | `text` | `case` | `TextTransformResolver.vue` | `StringFormulaResolver` / `NormalizationResolver` |
| `normalization` | `text` | `normalize` | `TextTransformResolver.vue` | `NormalizationResolver` |
| `format` | `text` | `format` | `TextTransformResolver.vue` | `FormatResolver` |
| `child_aggregation` | `collection` | `sum` / `avg` / etc. | `CollectionResolver.vue` | `CollectionResolver` |

---

## 9. Rule Engine / Runtime Changes

- When evaluating rules containing `family: "date_time"` or `family: "text"` configurations, `ValueResolver.compile_resolver_config` maps them directly to compiled resolver instances (`DateFormulaResolver`, `DateDiffResolver`, `FormatResolver`, etc.).
- Expression compiling (`ValueResolver.compile`) supports inner `resolverToken`s wrapped in canonical `family` payloads.

---

## 10. Configuration & Data Contract Changes

- **Saved Rule Payload Changes**: Newly configured resolvers in the Rule Builder canvas will save in the new `family` + `operation` + `config` format.
- **Backward Compatibility**:
  - Frontend `useValueResolver.js` normalizes legacy `child_aggregation`, `collection`, `text`, and `date_time` payloads on read.
  - Backend `ValueResolver.compile_resolver_config` handles legacy `kind` payloads if `kind == "math_formula"`, `kind == "string_formula"`, `kind == "normalization"`, `kind == "format"`, `kind == "system_context"`.

---

## 11. Test Changes

### 1. `test_collection_resolver.py`
- Added `test_sum_operation`: Verifies unfiltered and filtered sum over collection items.
- Added `test_avg_operation`: Verifies unfiltered and filtered average calculation.
- Added `test_child_aggregation_backward_compatibility`: Verifies legacy `child_aggregation` payload parsing.
- Added `test_canonical_two_level_contract`: Verifies compilation of `{ family: "collection", operation: "sum", ... }`.

### 2. `test_value_resolvers_complex.py`
- Added `test_date_time_family_resolver`: Verifies `calculate`, `diff`, and `format` operations via canonical `family: "date_time"`.
- Added `test_text_transform_resolver`: Verifies `combine`, `case`, `normalize`, and `format` operations via canonical `family: "text"`.
- Updated `test_value_resolver_compile_expression_resolver_token` to use the new `family: "text"` format.

---

## 12. Documentation Changes

No documentation files (`docs/`, `*.md`) were updated in this commit.

---

## 13. Build & Validation Results

| Command | Result | Notes |
| :--- | :--- | :--- |
| `python3 -c "import ast; ast.parse(...)"` | **PASS** | Validated AST syntax for all modified backend Python files (`value_resolver.py`, test files). |
| `bench build --app flexirule` | **BLOCKED** | Environment limitation: `bench` command not executed inside a Frappe bench context. |
| `bench --site test_site run-tests --app flexirule` | **BLOCKED** | Environment limitation: Frappe bench context unavailable in standard sandbox session. |
| `yarn lint` | **FAIL / BLOCKED** | Dependency/Configuration issue: ESLint v10 installed in sandbox environment requires flat config format (`eslint.config.js`), failing on legacy `.eslintrc`. |
| `pytest flexirule/ruleflow/tests/` | **BLOCKED** | Missing dependency: `pytest` executed outside Frappe bench environment where `frappe` module is not installed in global python path. |

---

## 14. Findings

### Finding 1: Broken Method Reference in `useGraphStore.js` (CRITICAL)
- **ID:** `FINDING-001`
- **Severity:** Critical
- **Area:** Frontend Store (`useGraphStore.js`)
- **Finding:** In `useGraphStore.js`, the diff introduces references to `this.mark_dirty()` and `this.clear_dirty()`. However, `useGraphStore.js` defines `markDirty()` and `clearDirty()` (camelCase), NOT snake_case.
- **Evidence:** `useGraphStore.js` lines 14-16:
  ```javascript
  // Line 14:
  if (this.is_performing_layout) return;
  this.mark_dirty(); // TypeError: this.mark_dirty is not a function
  ```
- **Impact:** Any graph node change (addition, movement, deletion) in the Visual Builder canvas will throw a runtime JS TypeError exception (`this.mark_dirty is not a function`), crashing canvas interaction.

### Finding 2: Unhandled Legacy `date_formula` and `date_diff` Top-Level Configs in Backend Compiler (HIGH)
- **ID:** `FINDING-002`
- **Severity:** High
- **Area:** Backend Value Resolver (`value_resolver.py`)
- **Finding:** In `value_resolver.py`, the legacy compilation blocks for `kind == "date_formula"` and `kind == "date_diff"` were completely removed from `compile_resolver_config()`. If an existing saved rule stored in the database uses `{ "kind": "date_formula", ... }` without a `family` key, `ValueResolver.compile_resolver_config()` now skips all checks and falls through to `return NoneResolver()`.
- **Evidence:** `value_resolver.py` diff removing lines 609-618 & 626-634:
  ```python
  # Removed code in target branch:
  # if kind == "date_formula":
  #     return DateFormulaResolver(...)
  # if kind == "date_diff":
  #     return DateDiffResolver(...)
  ```
- **Impact:** Existing production rules saved prior to this migration using legacy `date_formula` or `date_diff` payloads will silently evaluate to `NoneResolver()` (returning `None` at runtime), causing severe functional regressions for existing rules.

### Finding 3: Missing `fmt_money` Support in `FormatResolver` for Text Family Format (MEDIUM)
- **ID:** `FINDING-003`
- **Severity:** Medium
- **Area:** Backend Value Resolver (`value_resolver.py` / `FormatResolver`)
- **Finding:** In `value_resolver.py`, when `family == "text"` and `op == "format"`, it returns `FormatResolver(fmt_op="format", fmt_field=..., fmt_config=...)`. However, if a user wants money formatting (`fmt_money`), `TextTransformResolver.vue` does not expose `fmt_money` option under `format` operation, and backend `FormatResolver` hardcodes `fmt_op="format"`.
- **Evidence:** `value_resolver.py` lines 686-691:
  ```python
  if op == "format":
      return FormatResolver(
          fmt_op="format",
          fmt_field=inner_dict.get("fmt_field") or config.get("fmt_field"),
          fmt_config=inner_dict.get("fmt_config") or config.get("fmt_config", ""),
      )
  ```
- **Impact:** Formatting currencies via the new Text Transform family requires raw Jinja/Python string formatting rather than Frappe's native `fmt_money` helper.

### Finding 4: Dead Strategy Registration Code in `strategies.js` (LOW)
- **ID:** `FINDING-004`
- **Severity:** Low
- **Area:** Frontend Registry (`strategies.js`)
- **Finding:** `getAllStrategies()` in `strategies.js` filters out `!s.hidden` and `kind !== "child_aggregation"`. However, legacy strategies `date_formula` and `date_diff` are no longer registered in `index.js`, making explicit filtering checks for un-registered strategies redundant.
- **Evidence:** `strategies.js` line 30:
  ```javascript
  return Object.entries(RESOLVER_STRATEGIES)
      .filter(([kind, s]) => !s.hidden && kind !== "child_aggregation")
  ```
- **Impact:** Code cleanliness / minor maintenance debt.

---

## 15. Compatibility / Regression Analysis

### Saved Rules Compatibility
- **Text Resolvers**: Saved rules with `{ "kind": "string_formula" }`, `{ "kind": "normalization" }`, or `{ "kind": "format" }` are **backward compatible** because `compile_resolver_config()` retains fallback `if kind == "string_formula"` / `normalization` / `format` branches.
- **Child Aggregation**: Saved rules with `{ "kind": "child_aggregation" }` are **backward compatible** because `compile_resolver_config()` handles `kind == "child_aggregation"`.
- **Date Resolvers**: Saved rules with `{ "kind": "date_formula" }` or `{ "kind": "date_diff" }` without `family: "date_time"` are **NOT backward compatible** (see `FINDING-002`).

### Frontend UI Compatibility
- Opening a legacy rule with `date_formula` or `date_diff` in the UI is handled by `useValueResolver.js` (which defaults `kind` to `date_time` and sets `activeKind.value = "date_time"`), but saving it migrates it to the new `family: "date_time"` format.

---

## 16. Missing Test Coverage

1. **Legacy Payload Regression Tests**:
   - `test_value_resolvers_complex.py` contains tests for the new `family: "date_time"` structure, but lacks a test verifying that raw legacy dicts `{ "kind": "date_formula", "base_type": "today", ... }` still compile and execute correctly without `family: "date_time"`.
2. **`TextTransformResolver.vue` UI Integration Tests**:
   - No Cypress / UI tests verify changing operations inside `TextTransformResolver.vue` (e.g., switching from `combine` to `case` or `normalize`).
3. **Graph Store Dirty State Unit Tests**:
   - No frontend store unit test covers `useGraphStore` dirty state marking on node changes, which allowed `FINDING-001` (`mark_dirty()` vs `markDirty()`) to slip through unnoticed.

---

## 17. Recommended Follow-up

Before merging target branch `develop-1276450611588157079` into `develop`:

1. **Fix `useGraphStore.js` (CRITICAL)**:
   - Change `this.mark_dirty()` to `this.markDirty()` and `this.clear_dirty()` to `this.clearDirty()` in `useGraphStore.js`.
2. **Restore Legacy Date Resolver Backend Fallbacks (HIGH)**:
   - In `flexirule/ruleflow/core/value_resolver.py`, restore the fallback checks for top-level `kind == "date_formula"` and `kind == "date_diff"` when `family` is absent.
3. **Add Backend Unit Tests for Legacy Date Payloads (MEDIUM)**:
   - Add unit tests in `test_value_resolvers_complex.py` explicitly compiling raw legacy `{ "kind": "date_formula" }` and `{ "kind": "date_diff" }` payloads to guarantee zero regressions for existing production databases.

---

## 18. Final Assessment

The target branch `develop-1276450611588157079` successfully implements the architectural vision of consolidating Value Resolvers into clean, canonical families (`date_time`, `text`, `collection`). The modular UI structure and expanded test suite are significant improvements.

However, due to **FINDING-001** (runtime crash on canvas node edits) and **FINDING-002** (backward-compatibility regression for legacy date formulas), **the branch is not yet ready for production merge without follow-up remediation**.
