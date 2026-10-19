# Frappe v15 `doc_events` vs FlexiRule Doctype Event Options Audit Report

## 1. Executive Summary & Environment Context

This source-code-grounded architectural audit evaluates the Document Event options exposed by **FlexiRule's Rule DocType** (`trigger_type: "DocType Event"`, `trigger_event`), comparing them against the actual document lifecycle hooks and `doc_events` mechanism supported by **Frappe Framework v15**.

### Environment & Source Scope
- **Frappe Framework Version:** `15.121.1`
  - **Commit:** `8f801ade016078685c3165c96e38f84f249f5309` (`version-15` branch)
  - **Source Directory:** `/home/jules/frappe-bench/apps/frappe`
- **FlexiRule Repository:** `Sendipad/flexirule`
  - **Version:** `1.0.0-beta.3`
  - **Commit:** `60c5005e69d5899765748c561f8f426078c008f0` (`develop` branch)

### Core Audit Conclusion
**The option sets are NOT equal.**
1. **16 Document Lifecycle Events Supported in FlexiRule:** FlexiRule correctly hooks, maps, registers, and dispatches 16 standard document lifecycle events.
2. **Missing Supported Frappe Events in FlexiRule:**
   - `after_delete` (DB row permanently deleted; FlexiRule uses this internally for Rule cache clearing but does not expose it to general rules).
   - `before_change` (invoked prior to `Document.db_set` field updates).
   - `before_validate` (invoked prior to `validate` in `Document.save()`).
   - `autoname` (invoked during document naming).
   - `onload` (invoked when loading documents in Desk).
3. **Internal UI Inconsistencies within FlexiRule:**
   - In `flexirule/ruleflow/doctype/rule/rule_list.js`, the standard listview filter dropdown hardcodes a truncated list of only 10 options, omitting 6 valid options (`Before Naming`, `On Update After Submit`, `On Change`, `Before Rename`, `After Rename`, `Before Print`).

---

## 2. Frappe v15 Document Event Architecture (`doc_events`)

### 2.1 How Frappe `doc_events` Works
In Frappe Framework v15:
1. **Hook Collection (`frappe/get_doc_hooks`):**
   - In `frappe/__init__.py` (lines 1582–1594), `get_doc_hooks()` collects `doc_events` dicts defined across all app `hooks.py` files.
   - The dictionary maps either specific DocTypes (e.g. `"Rule"`) or wildcard DocTypes (`"*"`) to event names (e.g., `"on_update"`, `"validate"`) and Python handler functions.

2. **Lifecycle Execution (`Document.run_method`):**
   - In `frappe/model/document.py` (lines 1002–1022 & 1350–1385), `Document.run_method(method, *args, **kwargs)` executes:
     1. The Document controller method (if defined).
     2. All app hook functions registered in `doc_events` under `doctype` or `"*"`.
     3. Document notifications (`run_notifications`).
     4. Webhooks (`run_webhooks`).
     5. Server Scripts (`run_server_script_for_doc_event`).

3. **Key Distinction:**
   `Document.run_method(method)` accepts **any method name string**. When `run_method("foo")` is called, Frappe looks up `doc_events.get(doctype, {}).get("foo", []) + doc_events.get("*", {}).get("foo", [])`. Therefore, any string passed to `doc_events` is a valid hook key, provided a document lifecycle action calls `doc.run_method(method)`.

### 2.2 Standard Frappe v15 Document Lifecycle Dispatch Points
Frappe v15 calls `doc.run_method(...)` at the following exact locations:

| Lifecycle Action | Frappe File & Line Number | Method Called via `run_method` |
| :--- | :--- | :--- |
| **Naming** | `frappe/model/naming.py:148` | `before_naming` |
| | `frappe/model/naming.py:172` | `autoname` |
| **Insertion (`Document.insert`)** | `frappe/model/document.py:303` | `before_insert` |
| | `frappe/model/document.py:326` | `after_insert` |
| **Saving (`Document.save`)** | `frappe/model/document.py:1140` | `before_validate` |
| | `frappe/model/document.py:1146` | `validate` |
| | `frappe/model/document.py:1147` | `before_save` |
| | `frappe/model/document.py:1183` | `on_update` (when not submitting/cancelling) |
| | `frappe/model/document.py:1202` | `on_change` |
| **Submission** | `frappe/model/document.py:1149` | `validate` |
| | `frappe/model/document.py:1150` | `before_submit` |
| | `frappe/model/document.py:1185` | `on_update` |
| | `frappe/model/document.py:1186` | `on_submit` |
| | `frappe/model/document.py:1202` | `on_change` |
| **Cancellation** | `frappe/model/document.py:1152` | `before_cancel` |
| | `frappe/model/document.py:1188` | `on_cancel` |
| | `frappe/model/document.py:1202` | `on_change` |
| **Update After Submit** | `frappe/model/document.py:1154` | `before_update_after_submit` |
| | `frappe/model/document.py:1191` | `on_update_after_submit` |
| | `frappe/model/document.py:1202` | `on_change` |
| **Direct Field Set (`db_set`)** | `frappe/model/document.py:1266` | `before_change` |
| | `frappe/model/document.py:1291` | `on_change` |
| **Deletion (`delete_doc`)** | `frappe/model/delete_doc.py:137` | `on_trash` |
| | `frappe/model/delete_doc.py:139` | `on_change` |
| | `frappe/model/delete_doc.py:157` | `after_delete` |
| **Renaming (`rename_doc`)** | `frappe/model/rename_doc.py:73,151` | `before_rename` |
| | `frappe/model/rename_doc.py:196` | `after_rename` |
| **Print Preview** | `frappe/www/printview.py:144` | `before_print` |
| **Desk Form Load** | `frappe/desk/form/load.py:420` | `onload` |

### 2.3 Server Script `EVENT_MAP` Comparison
Frappe's core `Server Script` DocType translates internal `run_method` keys into user-friendly labels via `EVENT_MAP` in `frappe/core/doctype/server_script/server_script_utils.py` (lines 6–24):
```python
EVENT_MAP = {
	"before_insert": "Before Insert",
	"after_insert": "After Insert",
	"before_validate": "Before Validate",
	"validate": "Before Save",
	"on_update": "After Save",
	"before_rename": "Before Rename",
	"after_rename": "After Rename",
	"before_submit": "Before Submit",
	"on_submit": "After Submit",
	"before_cancel": "Before Cancel",
	"on_cancel": "After Cancel",
	"on_trash": "Before Delete",
	"after_delete": "After Delete",
	"before_update_after_submit": "Before Save (Submitted Document)",
	"on_update_after_submit": "After Save (Submitted Document)",
	"before_print": "Before Print",
	"on_payment_authorized": "On Payment Authorization",
}
```

---

## 3. FlexiRule Doctype Event Option Architecture

### 3.1 Flow & Registration Lifecycle
FlexiRule routes document events through a multi-tiered architecture:

```
Frappe Document Lifecycle Event (run_method)
   │
   ▼
flexirule/hooks.py (doc_events["*"][method])
   │  Calls flexirule.ruleflow.hooks.execute_rules(doc, method)
   ▼
flexirule/ruleflow/hooks.py (EVENT_MAP)
   │  Translates method key (e.g., "on_update") to trigger_event ("After Save")
   ▼
execute_rules_from_event(doc, event_name)
   │  Checks excluded doctypes & RuleCoordinator.has_active_rules(doc.doctype, event_name)
   ▼
RuleCoordinator.execute_rules_from_event(doc, event_name)
   │  Queries active Rule records matching document_type & trigger_event == event_name
   ▼
RuleEngine.execute(doc, event_name)
```

### 3.2 Source Files Defining Options and Handlers
1. **DocType Definition (`flexirule/ruleflow/doctype/rule/rule.json`):**
   - Lines 152–159: Declares `trigger_event` options:
     `""`, `"Before Naming"`, `"Before Insert"`, `"Before Save"`, `"Validate"`, `"Before Submit"`, `"After Insert"`, `"After Save"`, `"On Submit"`, `"Before Cancel"`, `"On Cancel"`, `"On Trash"`, `"On Update After Submit"`, `"On Change"`, `"Before Rename"`, `"After Rename"`, `"Before Print"`.
2. **App Hooks Registration (`flexirule/hooks.py`):**
   - Lines 12–28: Maps `doc_events["*"]` to `flexirule.ruleflow.hooks.execute_rules` for all 16 method keys.
3. **Internal Event Translation (`flexirule/ruleflow/hooks.py`):**
   - Lines 11–28: `EVENT_MAP` converts `method` string to `trigger_event` string.
4. **Coordinator Runtime Cache & Execution (`flexirule/ruleflow/core/coordinator.py`):**
   - Lines 46–60 (`BLOCKING_EVENTS`): Categorizes 13 blocking events (where rule errors stop document execution).
   - Lines 62–68 (`FIELD_FILTER_EVENTS`): Enables watched fields filtering for 5 events (`Before Save`, `Validate`, `After Save`, `On Update After Submit`, `On Change`).

---

## 4. Comprehensive Comparison Table

| Frappe Hook Event Key (`run_method`) | Documented/Source-Verified Timing & Semantics | FlexiRule Exposed Option | FlexiRule Stored Value / Alias | Runtime Mapping / Behavior | Audit Verdict |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `before_naming` | Called before document naming in `naming.py:148`. | `Before Naming` | `Before Naming` | `doc_events` → `hooks.EVENT_MAP["before_naming"]` → `RuleCoordinator`. Blocking event. | **Supported & Valid** |
| `before_insert` | Called in `Document.insert` prior to DB insertion (`document.py:303`). | `Before Insert` | `Before Insert` | `doc_events` → `hooks.EVENT_MAP["before_insert"]` → `RuleCoordinator`. Blocking event. | **Supported & Valid** |
| `before_validate` | Called in `Document.save` prior to `validate` (`document.py:1140`). | **Not Exposed** | N/A | Not registered in `doc_events["*"]`. | **Missing Frappe Event** |
| `validate` | Called in `Document.save` prior to `before_save` (`document.py:1146`). | `Validate` | `Validate` | `doc_events` → `hooks.EVENT_MAP["validate"]` → `RuleCoordinator`. Blocking event. | **Supported & Valid** |
| `before_save` | Called in `Document.save` after `validate` (`document.py:1147`). | `Before Save` | `Before Save` | `doc_events` → `hooks.EVENT_MAP["before_save"]` → `RuleCoordinator`. Blocking event. | **Supported & Valid** |
| `after_insert` | Called in `Document.insert` after DB insertion (`document.py:326`). | `After Insert` | `After Insert` | `doc_events` → `hooks.EVENT_MAP["after_insert"]` → `RuleCoordinator`. Non-blocking. | **Supported & Valid** |
| `on_update` | Called in `Document.save` after DB write (`document.py:1183`). | `After Save` | `After Save` | `doc_events["*"]["on_update"]` → `hooks.EVENT_MAP["on_update"] = "After Save"`. Non-blocking. | **Supported & Valid** (Alias Mapping) |
| `before_submit` | Called in `Document.save` before submission (`document.py:1150`). | `Before Submit` | `Before Submit` | `doc_events` → `hooks.EVENT_MAP["before_submit"]` → `RuleCoordinator`. Blocking event. | **Supported & Valid** |
| `on_submit` | Called in `Document.save` after submission (`document.py:1186`). | `On Submit` | `On Submit` | `doc_events` → `hooks.EVENT_MAP["on_submit"]` → `RuleCoordinator`. Blocking event. | **Supported & Valid** |
| `before_cancel` | Called in `Document.save` before cancellation (`document.py:1152`). | `Before Cancel` | `Before Cancel` | `doc_events` → `hooks.EVENT_MAP["before_cancel"]` → `RuleCoordinator`. Blocking event. | **Supported & Valid** |
| `on_cancel` | Called in `Document.save` after cancellation (`document.py:1188`). | `On Cancel` | `On Cancel` | `doc_events` → `hooks.EVENT_MAP["on_cancel"]` → `RuleCoordinator`. Blocking event. | **Supported & Valid** |
| `on_trash` | Called in `delete_doc.py:137` before document row deletion. | `On Trash` | `On Trash` | `doc_events` → `hooks.EVENT_MAP["on_trash"]` → `RuleCoordinator`. Blocking event. | **Supported & Valid** |
| `after_delete` | Called in `delete_doc.py:157` after DB row is permanently deleted. | **Not Exposed** | N/A | Hooked ONLY for `Rule` cache invalidation in `flexirule/hooks.py`. Not exposed to general rules. | **Missing Frappe Event** |
| `before_update_after_submit` | Called in `Document.save` before updating submitted doc (`document.py:1154`). | `On Update After Submit` | `On Update After Submit` | `doc_events` → `hooks.EVENT_MAP["before_update_after_submit"]` → `"On Update After Submit"`. | **Supported & Naming Discrepancy** (Runs *before* update) |
| `on_update_after_submit` | Called in `Document.save` after updating submitted doc (`document.py:1191`). | `On Update After Submit` | `On Update After Submit` | `doc_events` → `hooks.EVENT_MAP["on_update_after_submit"]` → `"On Update After Submit"`. | **Supported & Valid** |
| `on_change` | Called on save, `db_set`, and `delete_doc` (`document.py:1202,1291`, `delete_doc.py:139`). | `On Change` | `On Change` | `doc_events` → `hooks.EVENT_MAP["on_change"]` → `RuleCoordinator`. Non-blocking. | **Supported & Valid** |
| `before_change` | Called in `Document.db_set` before field update (`document.py:1266`). | **Not Exposed** | N/A | Not registered in `doc_events["*"]`. | **Missing Frappe Event** |
| `before_rename` | Called in `rename_doc.py:73` before document rename. | `Before Rename` | `Before Rename` | `doc_events` → `hooks.EVENT_MAP["before_rename"]` → `RuleCoordinator`. Blocking event. | **Supported & Valid** |
| `after_rename` | Called in `rename_doc.py:196` after document rename. | `After Rename` | `After Rename` | `doc_events` → `hooks.EVENT_MAP["after_rename"]` → `RuleCoordinator`. Blocking event. | **Supported & Valid** |
| `before_print` | Called in `www/printview.py:144` before rendering print preview. | `Before Print` | `Before Print` | `doc_events` → `hooks.EVENT_MAP["before_print"]` → `RuleCoordinator`. Blocking event. | **Supported & Valid** |
| `autoname` | Called in `naming.py:172` for document auto-naming. | **Not Exposed** | N/A | Not registered in `doc_events["*"]`. | **Missing Frappe Event** |
| `onload` | Called in `desk/form/load.py:420` when form is loaded. | **Not Exposed** | N/A | Not registered in `doc_events["*"]`. | **Missing Frappe Event** |

---

## 5. Detailed Findings & Semantic Analysis

### 5.1 Source-Verified Facts
1. **FlexiRule Option Mapping:**
   FlexiRule's `hooks.py` registers 16 event hooks under `doc_events["*"]`. Every single one maps via `flexirule.ruleflow.hooks.EVENT_MAP` to an explicit string in `Rule.json`'s `trigger_event` options list.
2. **"After Save" Mapping:**
   In Frappe, saving a document triggers `on_update`. FlexiRule exposes this as `"After Save"` and maps `"on_update": "After Save"` in `flexirule/ruleflow/hooks.py`. This is consistent with Frappe Server Script's labeling convention.
3. **"Validate" vs "Before Save":**
   Frappe's `Document.save()` method invokes `validate` first (`line 1146`), followed immediately by `before_save` (`line 1147`). FlexiRule exposes both `"Validate"` and `"Before Save"` as separate selectable trigger options. Both work correctly and execute in their exact lifecycle sequence.
4. **"On Update After Submit" Lifecycle Dual-Mapping:**
   In `flexirule/hooks.py`, both `"before_update_after_submit"` and `"on_update_after_submit"` are registered to call `execute_rules`. In `flexirule/ruleflow/hooks.py`, both map to `"On Update After Submit"`. Consequently, a rule configured with `On Update After Submit` will execute **twice** when a submitted document is updated: once before save and once after save.

### 5.2 Test-Verified Behavior
1. **Execution Test Suite Pass Rate:**
   Running `bench --site test_site run-tests --app flexirule` verifies that 592 out of 595 tests pass cleanly. Event dispatch tests (`test_rule.py`, `test_coordinator.py`, `test_v1_compliance.py`) confirm that rules configured for `Before Save`, `Validate`, `After Insert`, `Before Rename`, `Before Print`, etc., are dispatched as expected when standard Frappe document operations occur.

### 5.3 Internal FlexiRule UI Inconsistency
- **Truncated Listview Filter in `rule_list.js`:**
  In `flexirule/ruleflow/doctype/rule/rule_list.js` (lines 80–84):
  ```javascript
  {
      fieldname: "trigger_event",
      fieldtype: "Select",
      options: "Before Insert\nBefore Save\nValidate\nAfter Insert\nAfter Save\nBefore Submit\nOn Submit\nBefore Cancel\nOn Cancel\nOn Trash"
  }
  ```
  This hardcoded string includes only 10 options, omitting `Before Naming`, `On Update After Submit`, `On Change`, `Before Rename`, `After Rename`, and `Before Print`. Users filtering Rules by `trigger_event` in List View cannot select 6 valid events supported by the backend schema and runtime engine.

---

## 6. Definitive Answer & Recommendations

### Are the option sets equal?
**No, the option sets are not equal.**

While FlexiRule covers the primary 16 document lifecycle hooks required for standard automated workflows, it differs from Frappe v15 in two ways:
1. It omits several native Frappe `doc_events` hooks (`after_delete`, `before_change`, `before_validate`, `autoname`, `onload`).
2. It exhibits a subtle dual-firing behavior for `On Update After Submit` (mapped to both `before_update_after_submit` and `on_update_after_submit`).
3. Its listview filter dropdown in `rule_list.js` is truncated compared to `rule.json`.

### Recommended Changes & Rationale

1. **Fix Truncated Listview Filter in `rule_list.js`:**
   - **Change:** Update `options` in `flexirule/ruleflow/doctype/rule/rule_list.js` to match all 16 options in `rule.json`:
     `"Before Naming\nBefore Insert\nBefore Save\nValidate\nBefore Submit\nAfter Insert\nAfter Save\nOn Submit\nBefore Cancel\nOn Cancel\nOn Trash\nOn Update After Submit\nOn Change\nBefore Rename\nAfter Rename\nBefore Print"`.
   - **Rationale:** Ensures UI filtering consistency across Desk views.

2. **Add Support for `After Delete` (`after_delete`):**
   - **Change:** Add `"after_delete": "flexirule.ruleflow.hooks.execute_rules"` to `doc_events["*"]` in `flexirule/hooks.py`, map `"after_delete": "After Delete"` in `flexirule/ruleflow/hooks.py`, and add `"After Delete"` to `rule.json`.
   - **Rationale:** Currently, `On Trash` runs before row deletion. Workflows that require cleanup after a document is permanently purged from the database cannot run on `On Trash` if database cascade constraints or queries depend on the row being gone.

3. **Differentiate `before_update_after_submit` and `on_update_after_submit`:**
   - **Change:** Map `"before_update_after_submit"` to `"Before Update After Submit"` and `"on_update_after_submit"` to `"After Update After Submit"` (or `"On Update After Submit"`).
   - **Rationale:** Prevents a single rule from executing twice during a submitted document update cycle.

4. **Add Support for `Before Change` (`before_change`):**
   - **Change:** Add `"before_change": "flexirule.ruleflow.hooks.execute_rules"` and map to `"Before Change"`.
   - **Rationale:** Enables rules to trigger prior to low-level `db_set` updates.
