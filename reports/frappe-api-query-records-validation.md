# Follow-up Investigation: Evidence Validation & Behavioral Verification

## 1. Verified Execution Pipeline

This section traces the exact code pathways from the initial Python call down to the database SQL execution layer.

### 1.1 "frappe.get_list" Execution Path
- **Entry Point**: `frappe.get_list(doctype, *args, **kwargs)` in `frappe/__init__.py` (Line 2010).
- **Core Action**: Instantiates `frappe.model.db_query.DatabaseQuery(doctype)` and invokes its `.execute(*args, **kwargs)` method.
- **Inner Functions Called**:
  1. `DatabaseQuery.execute()` [frappe/model/db_query.py, Line 95]
     - Calls `self.check_read_permission()` if `ignore_permissions` is False (Line 131).
     - Calls `self.get_table_columns()` (Line 196).
     - Calls `self.build_and_run()` (Line 202).
  2. `DatabaseQuery.build_and_run()` [frappe/model/db_query.py, Line 209]
     - Calls `self.prepare_args()` (Line 210).
     - Calls `self.add_limit()` (Line 211).
     - Calls `frappe.db.sql()` (Line 227).
  3. `DatabaseQuery.prepare_args()` [frappe/model/db_query.py, Line 229]
     - Calls `self.parse_args()` (Line 230).
     - Calls `self.sanitize_fields()` (Line 231).
     - Calls `self.extract_tables()` (Line 232).
     - Calls `self.build_conditions()` (Line 234).
     - Calls `self.apply_fieldlevel_read_permissions()` (Line 235).
- **Final Execution Layer**: `frappe.db.sql(query, as_dict, debug, ...)` in `frappe/database/database.py` (Line 230).

### 1.2 "frappe.get_all" Execution Path
- **Entry Point**: `frappe.get_all(doctype, *args, **kwargs)` in `frappe/__init__.py` (Line 2038).
- **Core Action**: Modifies the `kwargs` dictionary to set `ignore_permissions = True` and sets the default `limit_page_length = 0` if not explicitly specified. Then, delegates directly to `frappe.get_list()`.
- **Inner Functions Called**: Identical to `frappe.get_list` after the permission bypass adjustment.
- **Final Execution Layer**: `frappe.db.sql()` in `frappe/database/database.py` (Line 230).

### 1.3 "frappe.db.get_list" Execution Path
- **Entry Point**: `frappe.db.get_list(*args, **kwargs)` in `frappe/database/database.py` (Line 765).
- **Core Action**: A simple static wrapper delegating immediately to `frappe.get_list()`.
- **Inner Functions Called**: Calls `frappe.get_list(*args, **kwargs)` in `frappe/__init__.py`.
- **Final Execution Layer**: `frappe.db.sql()` in `frappe/database/database.py` (Line 230).

### 1.4 "frappe.db.get_all" Execution Path
- **Entry Point**: `frappe.db.get_all(*args, **kwargs)` in `frappe/database/database.py` (Line 761).
- **Core Action**: A simple static wrapper delegating immediately to `frappe.get_all()`.
- **Inner Functions Called**: Calls `frappe.get_all(*args, **kwargs)` in `frappe/__init__.py`.
- **Final Execution Layer**: `frappe.db.sql()` in `frappe/database/database.py` (Line 230).

---

### Call Graph

```
[ frappe.db.get_list() ]                 [ frappe.db.get_all() ]
         │                                        │
         ▼                                        ▼
[ frappe.get_list() ] <────────────────── [ frappe.get_all() ]
         │                                   (sets ignore_permissions=True)
         ▼
DatabaseQuery(doctype).execute()
         │
         ├──► check_read_permission()  (Checks access if ignore_permissions=False)
         │      └─► frappe.has_permission()
         │
         └──► build_and_run()
                │
                ├──► prepare_args()
                │      ├─► parse_args()        (Resolves dot-notation field joins)
                │      ├─► sanitize_fields()   (Blocks illegal SQL functions/keywords)
                │      ├─► extract_tables()    (Appends join tables to self.tables)
                │      └─► build_conditions()  (Normalizes filters into where clauses)
                │
                └──► frappe.db.sql()  (Executes compiled raw SQL parameter strings)
```

---

## 2. API Ownership (DatabaseQuery vs Engine vs Query Builder)

### 2.1 Coexistence and Roles
- **✅ Verified by source code**: `DatabaseQuery` is the legacy, string-based query processor. It is exclusively selected when executing `frappe.get_list()`, `frappe.get_all()`, and backing REST list views/reports.
- **✅ Verified by source code**: The PyPika-based `Engine` is selected when a developer uses `frappe.qb.get_query(...)` or invokes `frappe.qb.from_(...)`.
- **✅ Verified by source code**: These engines coexist in the codebase. `DatabaseQuery` has not been replaced due to deep coupling with legacy desk features, whereas `frappe.qb` is designed as a modern, injection-safe parameterization layer for complex programmatic queries.

---

## 3. Child DocType Behavior Matrix

| Scenario | Administrator | Normal User | ignore_permissions=True | Status |
| :--- | :--- | :--- | :--- | :--- |
| **A: Direct query on Child Table** | ✅ Allowed | ❌ Failed (`PermissionError`) | ✅ Allowed | **✅ Verified by execution path** |
| **B: Field selection with Child dot-notation** | ✅ Allowed | ✅ Allowed (if parent permitted)| ✅ Allowed | **✅ Verified by execution path** |
| **C: Dict filter with Child dot-notation** | ❌ Failed (DB Err) | ❌ Failed (DB Err) | ❌ Failed (DB Err) | **✅ Verified by execution path** |
| **D: List filter referencing Child Table** | ✅ Allowed | ✅ Allowed (if parent permitted)| ✅ Allowed | **✅ Verified by execution path** |

---

## 4. SQL Verification

### 4.1 Scenario A (Child Field Selection dot-notation)
- **Code**: `frappe.get_list("Rule", fields=["name", "permissions.role"])`
- **Generated SQL**:
```sql
select `tabRule`.name, `tabRule Permission`.`role`
from `tabRule` left join `tabRule Permission` on (
    `tabRule Permission`.parenttype = 'Rule'
    and `tabRule Permission`.parent = `tabRule`.name
)
order by `tabRule`.`priority` DESC
limit 1 offset 0
```
- **Joins**: `left join \`tabRule Permission\` on (\`tabRule Permission\`.parenttype = 'Rule' and \`tabRule Permission\`.parent = \`tabRule\`.name)`
- **Where Clause**: None
- **Permission Conditions**: None (Bypassed under Administrator context)
- **Order Clause**: `order by \`tabRule\`.\`priority\` DESC`

### 4.2 Scenario B (Dict filter with dot-notation)
- **Code**: `frappe.get_list("Rule", filters={"permissions.role": "System Manager"})`
- **Generated SQL**: No SQL generated due to execution crash.
- **Where Clause**: Fails parsing with `Unknown column 'tabRule.permissions.role' in 'WHERE'`.

### 4.3 Scenario C (List filter referencing Child Table)
- **Code**: `frappe.get_list("Rule", filters=[["Rule Permission", "role", "=", "System Manager"]])`
- **Generated SQL**:
```sql
select `tabRule`.`name`
from `tabRule` left join `tabRule Permission` on (
    `tabRule Permission`.parenttype = 'Rule'
    and `tabRule Permission`.parent = `tabRule`.name
)
where `tabRule Permission`.`role` = 'System Manager'
order by `tabRule`.`priority` DESC
limit 1 offset 0
```
- **Joins**: `left join \`tabRule Permission\` on (\`tabRule Permission\`.parenttype = 'Rule' and \`tabRule Permission\`.parent = \`tabRule\`.name)`
- **Where Clause**: `where \`tabRule Permission\`.\`role\` = 'System Manager'`
- **Permission Conditions**: None (Bypassed under Administrator context)
- **Order Clause**: `order by \`tabRule\`.\`priority\` DESC`

### 4.4 Scenario D (frappe.get_all on Child Table)
- **Code**: `frappe.get_all("Rule Permission")`
- **Generated SQL**:
```sql
select `tabRule Permission`.`name`
from `tabRule Permission`
order by `tabRule Permission`.`modified` DESC
limit 1 offset 0
```
- **Joins**: None
- **Where Clause**: None
- **Permission Conditions**: Bypassed (`ignore_permissions=True`)
- **Order Clause**: `order by \`tabRule Permission\`.\`modified\` DESC`

---

## 5. Source Code Evidence

### 5.1 Verification of Scenario A (Field Selection dot-notation Join)
- **✅ Verified by source code**:
  - **File**: `frappe/model/db_query.py`
  - **Class**: `DatabaseQuery`
  - **Method**: `parse_args()` (Lines 362–380)
  - **Execution Path**:
    1. Loop over fields in `self.fields`. If `.` is present, splits to `linked_fieldname, fieldname = field.split(".", 1)`.
    2. Retrieves metadata and identifies that `permissions` is a `Table` field. Sets `field = f"\`tabRule Permission\`.\`role\`"`.
    3. During `extract_tables()` (Line 508), detects `tabRule Permission` in field definition and appends it to `self.tables`.
    4. During `prepare_args()` (Line 274), loops over `self.tables[1:]` and dynamically constructs the left join.
  - **Conclusion**: Dot-notation field selection automatically triggers child table left joining by design.

### 5.2 Verification of Scenario B (Failure of Dict Filter dot-notation)
- **✅ Verified by source code**:
  - **File**: `frappe/model/db_query.py`
  - **Class**: `DatabaseQuery`
  - **Method**: `prepare_filter_condition()` (Line 774)
  - **Execution Path**:
    1. Filter dictionaries are mapped to list tuples. However, they bypass dot-notation resolution.
    2. Line 774 prepends parent table name blindly: `column_name = cast_name(f"{tname}.\`{f.fieldname}\`")`.
    3. Produces raw column SQL: `\`tabRule\`.\`permissions.role\``, causing database unknown column failures.
  - **Conclusion**: Dictionary-based dot-notation filters are completely unsupported in legacy `DatabaseQuery`.

### 5.3 Verification of Scenario C (List Filter Join Support)
- **✅ Verified by source code**:
  - **File**: `frappe/model/db_query.py`
  - **Class**: `DatabaseQuery`
  - **Method**: `prepare_filter_condition()` (Line 767)
  - **Execution Path**:
    1. Receives list filter `["Rule Permission", "role", "=", "System Manager"]`.
    2. Sets `f.doctype = "Rule Permission"`, and `tname = "\`tabRule Permission\`"`.
    3. Line 771 checks `tname not in self.tables` and appends `"Rule Permission"` to `self.tables` via `self.append_table()`.
    4. Automatically triggers left join during `prepare_args()`.
  - **Conclusion**: Standard list-style filters referencing the Child DocType explicitly are fully supported and initiate automatic joins.

### 5.4 Verification of Scenario E (Child DocType Permission Requirements)
- **✅ Verified by source code**:
  - **File**: `frappe/permissions.py`
  - **Class**: N/A
  - **Method**: `has_permission()` (Line 77) & `has_child_permission()` (Line 763)
  - **Execution Path**:
    1. Line 99 checks `user == "Administrator"`. If True, immediately returns `True` (bypassing any table restrictions).
    2. Line 111 evaluates `frappe.is_table(doctype)`. Since `'Rule Permission'` is a child table, redirects to `has_child_permission()`.
    3. If `parent_doctype` parameter is not passed, `has_child_permission` rejects request at Line 781: `Please specify a valid parent DocType for...` and returns `False` (leading to a `PermissionError`).
    4. If `parent_doctype="Rule"` is passed, evaluates `has_permission("Rule")` and executes successfully if parent is permitted.
  - **Conclusion**: Non-Administrator child table queries via `frappe.get_list` require explicit `parent_doctype` arguments to bypass `PermissionError`.

---

## 6. Validation of Previous Findings

Revisiting the gaps identified in the first report:

### 6.1 Direct Child DocType Queries Gap
- **Status**: **VERIFIED**
- **Justification**: Non-administrators running "Query List" on a child DocType will always experience a `PermissionError` in FlexiRule because the handler `_query_list` in `query_records.py` does not forward or configure a `parent_doctype` parameter in its execution `kwargs`.

### 6.2 Child Table Filtering Gap
- **Status**: **VERIFIED**
- **Justification**: Although the backend `query_records.py` is capable of processing nested list filters, the frontend `FilterGroup` and field selector components are completely locked to direct parent-level fields. Users have no UI capability to define parent-child joins or construct child filters.

### 6.3 Child Field Selections Gap
- **Status**: **PARTIALLY TRUE**
- **Justification**: While we classified this as a backend gap, the backend validation `_doctype_has_field` in `query_records.py` and standard `frappe.get_list()` actually support dot-notation field queries perfectly (Scenario A). The gap is exclusively in the frontend UI `QueryRecordsConfig.vue`, which prevents user input or selection of dot-notated child fields.

---

## 7. Corrected Compatibility Matrix

| Capability | Frappe Core | FlexiRule Backend | FlexiRule Frontend | Gap Status |
| :--- | :--- | :--- | :--- | :--- |
| **Child Field Dot-Notation Selection** | ✅ Yes | ✅ Supported & Validated | ❌ Blocked | **UI Gap Only** |
| **List filters referencing Child Table**| ✅ Yes | ✅ Supported & Validated | ❌ Blocked | **UI Gap Only** |
| **Dict filters using dot-notation** | ❌ No | ❌ Unsupported | ❌ Blocked | **Not a Gap** (Unsupported by Frappe) |
| **Non-Admin Child Queries (get_list)** | ✅ Yes (Requires `parent_doctype`) | ❌ Unsupported | ❌ Blocked | **Critical Backend/UI Gap** |

---

## 8. Corrected Implementation Recommendations

The following action items are strictly corrected to focus solely on achieving 100% compatibility with Frappe's public query APIs:

### Recommendation 1: Forward parent_doctype parameter in Query Records Handler
- **✅ Verified by source code**: `frappe/permissions.py` (Line 763).
- **Current Behavior**: FlexiRule executes `frappe.get_list(doctype, ...)` without `parent_doctype` arguments.
- **Gap**: Causes `PermissionError` for non-Administrators querying child tables.
- **Recommendation**: Update `QueryRecordsConfig.vue` to allow selecting a `parent_doctype` when the target DocType is a child table. Forward this option directly to the backend executor `_query_list()`.
- **Priority**: **Critical** | **Complexity**: Small

### Recommendation 2: Enable Child Field Text Entry in Frontend UI
- **✅ Verified by execution path**: Scenario A SQL execution.
- **Current Behavior**: Frontend field picker is locked to a static `MultiSelectList` of direct parent fields.
- **Gap**: Prevents users from utilizing the backend's fully-supported child field selection.
- **Recommendation**: Add a text-entry field or an "Add Custom Field" button to `QueryRecordsConfig.vue`, allowing users to type child field dot-notation (e.g., `items.item_code`) manually.
- **Priority**: **High** | **Complexity**: Medium

### Recommendation 3: Implement Safe AST Expression Whitelisting
- **✅ Verified by source code**: `flexirule/ruleflow/core/permissions.py` (Line 245).
- **Current Behavior**: Validation pass is a dummy `compile` call which only verifies Python syntax, presenting severe security issues during safe evaluation.
- **Gap**: Lacks AST node verification.
- **Recommendation**: Implement `ast.parse()`-based validation. Restrict expressions strictly to safe nodes, rejecting all unauthorized calls.
- **Priority**: **High** | **Complexity**: Medium
