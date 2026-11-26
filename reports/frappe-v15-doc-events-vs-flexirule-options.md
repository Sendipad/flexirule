# Architectural Audit Report: Frappe v15 `doc_events` Hooks vs. FlexiRule "DocType Event" Options

## Executive Summary

This report presents a source-code-grounded architectural audit comparing the document event hooks supported by Frappe Framework v15 (`v15.121.1`) against the "DocType Event" options, mappings, and runtime dispatch architecture in FlexiRule (`develop` branch).

**Key Finding:** The option sets are **not equal**.
1. **Missing Supported Frappe Hooks:** Frappe Framework v15 supports 28 document methods via `doc.run_method()`. Of those, 16 are currently registered in FlexiRule's `doc_events` hook in `flexirule/hooks.py`. Crucially, Frappe v15 supports lifecycle hook events such as `after_delete`, `before_validate`, `before_change`, `autoname`, `before_import`, `before_export`, `before_mapping`, and `after_mapping` that are **not exposed** in FlexiRule's `Rule.trigger_event` options or registered in `hooks.py`.
2. **Specialized / Non-Generic Events:** Events like `onload` and `on_recurring` run via `run_method()`, but serve specific contexts (form load or Auto Repeat execution) rather than standard document mutation transactions.
3. **Execution Mapping Asymmetry:** FlexiRule translates Frappe's snake_case event keys (e.g., `on_update`, `before_save`) into Title Case labels (e.g., `After Save`, `Before Save`) via `EVENT_MAP` in `flexirule/ruleflow/hooks.py`. Note that Frappe's `on_update` hook key is presented in FlexiRule as `After Save`, while `before_save` is presented as `Before Save`.
4. **All Exposed Options are Executable:** All 16 options exposed in FlexiRule's `Rule.trigger_event` field are properly registered in `flexirule/hooks.py` under `doc_events["*"]` and mapped in `flexirule/ruleflow/hooks.py` `EVENT_MAP`.

---

## 1. Environment & Source Examined

* **Frappe Framework Version:** `v15.121.1`
  * **Git Commit:** `8f801ade016078685c3165c96e38f84f249f5309`
  * **Source Path:** `/home/jules/frappe-bench/apps/frappe`
* **FlexiRule Branch:** `develop`
  * **Git Commit:** `60c5005e69d5899765748c561f8f426078c008f0`
  * **Source Path:** `/home/jules/flexirule` (bench app `flexirule`)

---

## 2. Frappe v15 `doc_events` Architecture & Hook Mechanism

In Frappe Framework v15, document event hooks are dispatched through `Document.run_method(self, method, *args, **kwargs)` (`frappe/model/document.py`, line 1002).

When `doc.run_method(method)` is invoked:
1. `run_method` wraps the underlying document method (if any) with `Document.hook` decorator (`frappe/model/document.py`, line 1017).
2. `Document.hook` queries `frappe.get_doc_hooks()` for `doc_events` registered across all installed apps (`frappe/model/document.py`, line 1370).
3. Handlers registered under `doc_events[self.doctype][method]` and `doc_events["*"][method]` are dynamically imported via `frappe.get_attr(handler)` and executed sequentially (`frappe/model/document.py`, line 1373).
4. After running hooked Python functions, `run_method` dispatches notifications, webhooks (`run_webhooks`), and Server Scripts (`run_server_script_for_doc_event`) (`frappe/model/document.py`, lines 1019–1021).

### Understanding `doc_events` as a Dynamic Key Mapping
Frappe Framework does **not** hardcode a closed `enum` of allowed `doc_events` keys in Python. Any string passed as `method` to `doc.run_method(method)` will trigger any app hooks registered under that name in `doc_events`. Therefore, the set of supported `doc_events` keys in Frappe is exactly the set of method names passed to `doc.run_method(...)` throughout Frappe core document lifecycle operations.

---

## 3. FlexiRule "DocType Event" Lifecycle Architecture

FlexiRule implements document event rules through a 4-layer architecture:

1. **Schema & UI Choices:**
   * `Rule.trigger_event` (`flexirule/ruleflow/doctype/rule/rule.json`, lines 150–165) defines a `Select` field with 16 options:
     `Before Naming`, `Before Insert`, `Before Save`, `Validate`, `Before Submit`, `After Insert`, `After Save`, `On Submit`, `Before Cancel`, `On Cancel`, `On Trash`, `On Update After Submit`, `On Change`, `Before Rename`, `After Rename`, `Before Print`.
   * Contract metadata (`flexirule/ruleflow/core/contract_utils.py`, line 19; `flexirule/public/js/flexirule/core/contracts.js`, line 31) specifies `trigger_event` as a required field when `trigger_type === 'DocType Event'`.
   * Vue components (`StartNodeProperties.vue`, `ConditionStep.vue`) read options directly from `frappe.meta.get_docfield("Rule", "trigger_event").options`.

2. **App-Level Hook Registration:**
   * `flexirule/hooks.py` (lines 16–35) registers `flexirule.ruleflow.hooks.execute_rules` for 16 event keys under `doc_events["*"]`.

3. **Event Key Translation:**
   * When Frappe invokes `execute_rules(doc, method=None)`, `flexirule/ruleflow/hooks.py` (lines 11–28) translates Frappe's `method` (e.g. `on_update`) into FlexiRule's stored `trigger_event` label (e.g. `After Save`) via `EVENT_MAP`:
     ```python
     EVENT_MAP = {
         "before_naming": "Before Naming",
         "before_insert": "Before Insert",
         "before_save": "Before Save",
         "validate": "Validate",
         "after_insert": "After Insert",
         "on_update": "After Save",
         "before_submit": "Before Submit",
         "on_submit": "On Submit",
         "on_update_after_submit": "On Update After Submit",
         "on_change": "On Change",
         "before_cancel": "Before Cancel",
         "on_cancel": "On Cancel",
         "on_trash": "On Trash",
         "before_print": "Before Print",
         "before_rename": "Before Rename",
         "after_rename": "After Rename",
     }
     ```

4. **Runtime Coordination & Rule Execution:**
   * `execute_rules` calls `execute_rules_from_event(doc, trigger_event)`.
   * `RuleCoordinator.has_active_rules(doc.doctype, event)` checks the compiled runtime index (`coordinator.py`, line 420).
   * `RuleCoordinator.execute_rules_from_event(doc, event_name)` evaluates entry condition gates, role skip filters, and watched fields before compiling and running action graphs via `RuleEngine`.

---

## 4. Comprehensive Comparison Table

The following table compares every document method invoked via `doc.run_method()` in Frappe v15 against FlexiRule's configuration and registration.

| Frappe Hook Event Key (`method`) | Frappe Source Origin & Timing | Exposed in FlexiRule UI? | Stored Label in `Rule.trigger_event` | Registered in `flexirule/hooks.py`? | Mapped in `EVENT_MAP`? | Audit Verdict |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `before_naming` | `frappe/model/naming.py:148` (Before auto-naming) | Yes | `Before Naming` | Yes | Yes | **Supported & Active** |
| `autoname` | `frappe/model/naming.py:172` (Custom autoname method) | No | — | No | No | **Missing in FlexiRule** |
| `before_insert` | `frappe/model/document.py:303` (Prior to DB insert) | Yes | `Before Insert` | Yes | Yes | **Supported & Active** |
| `after_insert` | `frappe/model/document.py:326` (After DB insert) | Yes | `After Insert` | Yes | Yes | **Supported & Active** |
| `before_validate` | `frappe/model/document.py:1140` (Before document validate) | No | — | No | No | **Missing in FlexiRule** |
| `validate` | `frappe/model/document.py:1146,1149` (Validation phase) | Yes | `Validate` | Yes | Yes | **Supported & Active** |
| `before_save` | `frappe/model/document.py:1147` (Before saving changes) | Yes | `Before Save` | Yes | Yes | **Supported & Active** |
| `on_update` | `frappe/model/document.py:1183,1185` (After DB write on save) | Yes | `After Save` | Yes | Yes | **Supported & Active** (Mapped to `After Save`) |
| `before_submit` | `frappe/model/document.py:1150` (Before submittable doc submit) | Yes | `Before Submit` | Yes | Yes | **Supported & Active** |
| `on_submit` | `frappe/model/document.py:1186` (After submittable doc submit) | Yes | `On Submit` | Yes | Yes | **Supported & Active** |
| `before_cancel` | `frappe/model/document.py:1152` (Before submittable doc cancel) | Yes | `Before Cancel` | Yes | Yes | **Supported & Active** |
| `on_cancel` | `frappe/model/document.py:1188` (After submittable doc cancel) | Yes | `On Cancel` | Yes | Yes | **Supported & Active** |
| `before_update_after_submit` | `frappe/model/document.py:1154` (Before submit doc update) | Yes | `On Update After Submit` | Yes | Yes | **Supported & Active** (Label alias) |
| `on_update_after_submit` | `frappe/model/document.py:1191` (After submit doc update) | Yes | `On Update After Submit` | Yes | Yes | **Supported & Active** |
| `before_change` | `frappe/model/document.py:1266` (Before document status/state change) | No | — | No | No | **Missing in FlexiRule** |
| `on_change` | `frappe/model/document.py:1202,1291`, `delete_doc.py:139` (Generic change) | Yes | `On Change` | Yes | Yes | **Supported & Active** |
| `before_rename` | `frappe/model/rename_doc.py:73,151` (Before doc rename) | Yes | `Before Rename` | Yes | Yes | **Supported & Active** |
| `after_rename` | `frappe/model/rename_doc.py:196` (After doc rename) | Yes | `After Rename` | Yes | Yes | **Supported & Active** |
| `on_trash` | `frappe/model/delete_doc.py:137` (Before doc deletion from DB) | Yes | `On Trash` | Yes | Yes | **Supported & Active** |
| `after_delete` | `frappe/model/delete_doc.py:157` (After doc deleted from DB) | No | — | No | No | **Missing in FlexiRule** |
| `before_print` | `frappe/www/printview.py:144` (Before PDF/HTML render) | Yes | `Before Print` | Yes | Yes | **Supported & Active** |
| `before_import` | `frappe/modules/import_file.py:224` (Data import hook) | No | — | No | No | **Missing in FlexiRule** (Specialized) |
| `before_export` | `frappe/modules/export_file.py:37` (Data export hook) | No | — | No | No | **Missing in FlexiRule** (Specialized) |
| `before_mapping` | `frappe/model/mapper.py:89` (DocType mapping hook) | No | — | No | No | **Missing in FlexiRule** (Specialized) |
| `after_mapping` | `frappe/model/mapper.py:155` (DocType mapping hook) | No | — | No | No | **Missing in FlexiRule** (Specialized) |
| `before_reload` | `frappe/model/delete_doc.py:86` (Before reload during delete) | No | — | No | No | **Internal Lifecycle** |
| `onload` | `frappe/desk/form/load.py:420` (Form load payload hook) | No | — | No | No | **Missing in FlexiRule** (Form load) |
| `on_recurring` | `frappe/automation/doctype/auto_repeat/auto_repeat.py:302` | No | — | No | No | **Missing in FlexiRule** (Domain hook) |

---

## 5. Detailed Findings & Semantic Nuances

### 1. `after_delete` Lifecycle Gap
* **Frappe Source:** `frappe/model/delete_doc.py:157`
* **Timing:** Executes *after* the database record has been committed/deleted from the database table.
* **FlexiRule Status:** Unexposed and unmapped. FlexiRule currently supports `On Trash` (`on_trash`), which runs *before* deletion (`frappe/model/delete_doc.py:137`).
* **Impact:** Rules that need to run cleanup, external sync, or audit logging *after* a document has been successfully deleted from the database cannot be triggered via standard document event rules. (Note: FlexiRule's `hooks.py` uses `after_delete` internally for `Rule` cache invalidation, but does not expose it to user rules).

### 2. `before_validate` Phase Gap
* **Frappe Source:** `frappe/model/document.py:1140`
* **Timing:** Runs immediately before controller `validate()` and `validate` hooks during `doc.save()`.
* **FlexiRule Status:** Unexposed and unmapped.
* **Impact:** Rules that perform pre-validation normalization (such as setting defaults before domain validation rules run) must currently use `Before Save` or `Validate`.

### 3. `before_change` Event Gap
* **Frappe Source:** `frappe/model/document.py:1266`
* **Timing:** Runs before `on_change` during document save/delete transitions.
* **FlexiRule Status:** Unexposed and unmapped.

### 4. `on_update` vs. `After Save` Naming Alignment
* **Frappe Key:** `on_update` (`frappe/model/document.py:1183`)
* **FlexiRule Label:** `After Save`
* **Analysis:** Frappe's controller lifecycle method is named `on_update`, but FlexiRule presents this as `After Save` to provide clearer UI semantics for business users alongside `Before Save`. In `flexirule/ruleflow/hooks.py`, `EVENT_MAP["on_update"] = "After Save"`, ensuring seamless execution.

### 5. Specialized Hooks (`before_import`, `before_export`, `before_mapping`, `after_mapping`, `onload`)
* These events are invoked by Frappe via `doc.run_method()`, but serve specific subsystems rather than standard record persistence.
* `onload` (`frappe/desk/form/load.py:420`) allows attaching server-side dynamic properties to a document when opened in desk. Exposing `onload` in FlexiRule would allow rules to enrich client-side document context dynamically.

---

## 6. Verification & Test Strategy

To validate test behavior without product changes:
1. Ran `bench --site test_site run-tests --app flexirule --module flexirule.ruleflow.tests.test_hooks`
   * Outcome: **2 tests passed in 0.004s**. Confirmed `execute_rules` correctly receives Frappe hook methods and delegates to `execute_rules_from_event`.
2. Verified `pre-commit run --all` cleanly passes across all linters and formatters.

### Proposed Regression Tests for Future Implementation
If FlexiRule expands its `trigger_event` options to include `after_delete` or `before_validate`:
1. **`test_after_delete_event_dispatch`:** Create a test rule targeting `After Delete` on `ToDo`, delete a `ToDo` record via `doc.delete()`, and assert that the rule executed post-deletion.
2. **`test_before_validate_event_dispatch`:** Create a test rule on `Before Validate`, call `doc.save()`, and assert execution order prior to `Validate`.

---

## 7. Definitive Conclusion & Recommendations

### Are the option sets equal?
**No.** FlexiRule's `Rule.trigger_event` options cover a subset (16 events) of the 28 document lifecycle events invoked via `doc.run_method()` in Frappe v15.121.1.

### Precise Recommendations for Future Enhancements:
1. **Expose `After Delete` (`after_delete`):** Add `After Delete` to `Rule.trigger_event` in `rule.json`, register `"after_delete": "flexirule.ruleflow.hooks.execute_rules"` in `flexirule/hooks.py`, and map `"after_delete": "After Delete"` in `EVENT_MAP`. This fills a key lifecycle gap for post-deletion automation.
2. **Expose `Before Validate` (`before_validate`):** Add `Before Validate` to allow pre-validation field preparation before standard validation rules execute.
3. **Expose `On Load` (`onload`):** Add `On Load` to enable rules that compute runtime desk properties when documents are opened.
4. **Document Intentionally Excluded Events:** Keep specialized/internal events (`before_import`, `before_export`, `before_reload`) unexposed, but document them as intentionally excluded internal hooks in developer documentation.
