# Fetch Records and Query Records — Consolidated Reports

**Repository:** `Sendipad/flexirule`  
**Branch:** `feat/fetch-records-mode`  
**Related PR:** [#379](https://github.com/Sendipad/flexirule/pull/379)  
**Purpose:** Consolidate the existing Fetch Records, Frappe Query Builder capability, operator parity, filter-tree architecture, child-table aggregation, and test-coverage reports into one navigable document.

## Editorial note

This is a documentation-only consolidation. The source reports are included verbatim under separate headings to avoid silently changing conclusions or discarding technical evidence. Where findings overlap or reflect different points in the branch's evolution, consult the original report section and its stated environment/commit context rather than assuming all observations were verified against the same PR head.

## Included reports

1. [reports/query-records/child-table-aggregation-capability-audit.md](#consolidated-source-1-reports-query-records-child-table-aggregation-capability-audit-md)
2. [reports/query-records/fetch-records-operator-parity-v15-v16.md](#consolidated-source-2-reports-query-records-fetch-records-operator-parity-v15-v16-md)
3. [reports/query-records/filter-tree-adapter-implementation-plan.md](#consolidated-source-3-reports-query-records-filter-tree-adapter-implementation-plan-md)
4. [reports/query-records/frappe-qb-capabilities-and-limits-report.md](#consolidated-source-4-reports-query-records-frappe-qb-capabilities-and-limits-report-md)
5. [reports/query-records/frappe-qb-v15-capability-audit.md](#consolidated-source-5-reports-query-records-frappe-qb-v15-capability-audit-md)
6. [reports/query-records/tree_builder_and_fetch_records_audit.md](#consolidated-source-6-reports-query-records-tree-builder-and-fetch-records-audit-md)
7. [reports/query_records_fetch_records_backend_implementation_report.md](#consolidated-source-7-reports-query-records-fetch-records-backend-implementation-report-md)
8. [reports/test-coverage-audit.md](#consolidated-source-8-reports-test-coverage-audit-md)
9. [reports/tree-builder-query-records-architecture-audit.md](#consolidated-source-9-reports-tree-builder-query-records-architecture-audit-md)

\n\n---\n\n# Consolidated source 1: reports/query-records/child-table-aggregation-capability-audit.md\n\n> Original report content follows. Preserved without rewriting so findings, evidence, caveats, and historical context remain attributable to their source.\n\n# Child-Table Aggregation Capability Audit in Fetch Records

**Target Repository:** `Sendipad/flexirule`
**Related UI PR:** [#389 — Compact Syntax-Aware Output Fields Editor](https://github.com/Sendipad/flexirule/pull/389)
**Framework:** Frappe v15 (MariaDB 10.6+ / MySQL 8.0+)
**Branch under Audit:** `feat/fetch-records-mode`
**Audit Scope:** Analysis-only capability audit backed by executable Frappe v15 bench tests.

---

## 1. Executive Verdict

| Audit Question                                                                    | Verdict | Summary                                                                                                                                                                                                                                                                                            |
| :-------------------------------------------------------------------------------- | :-----: | :------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **1. Is child-table aggregation possible in Frappe v15?**                         | **YES** | Native PyPika query terms with explicit `LEFT JOIN` clauses on child DocTypes execute cleanly and accurately in Frappe v15.                                                                                                                                                                        |
| **2. Is it supported by raw dotted field strings in `frappe.qb.get_query`?**      | **NO**  | `frappe.qb.get_query` string field parser fails to detect child tables wrapped inside function calls (e.g. `sum(items.qty)`), omitting the required `LEFT JOIN` and raising MariaDB `OperationalError 1054`.                                                                                       |
| **3. Is it supported by the current FlexiRule Fetch Records implementation?**     | **NO**  | `QueryRecordsHandler._fetch_records` passes raw field string expressions directly to `frappe.qb.get_query`, causing runtime database errors whenever a child-table field is passed inside an aggregate function.                                                                                   |
| **4. Can it be supported safely with a bounded extension to the query compiler?** | **YES** | A structured query compiler can build explicit PyPika child joins, apply strict `parent`, `parenttype`, and `parentfield` join constraints, auto-manage `GROUP BY` clauses, enforce a single-child-table rule (preventing Cartesian product inflation), and preserve Frappe's permission contract. |

---

## 2. Empirical Evidence & Executable Test Results

All test cases were executed against the live MariaDB-backed test site (`test_site`) in the installed Frappe v15 bench environment (`/home/jules/frappe-bench`).

### 2.1 Test Environment & Fixture Setup

- **Test Doctypes:** `QB Test Parent` (Parent) and `QB Test Child` (Child Table field `items`).
- **Fixture Records:**
    - **P1 (`l87s1atjte`):** Enabled = 1, Status = "Open", 3 child rows (`ITEM-001` qty=2 rate=10, `ITEM-001` qty=3 rate=10, `ITEM-002` qty=5 rate=20). Total Qty = 10.0.
    - **P2 (`l875vqoa6g`):** Enabled = 1, Status = "Pending", 1 child row (`ITEM-001` qty=1 rate=10). Total Qty = 1.0.
    - **P3 (`l87o5sin6t`):** Enabled = 0, Status = "Closed", 0 child rows (empty collection).

### 2.2 Raw Dotted String Aggregation in `frappe.qb.get_query`

Passing raw aggregate string expressions containing child-table dots (`items.qty`, `items.rate`, `items.name`) to `frappe.qb.get_query` produces the following results:

| Expression Configured      | Generated SQL                                                             | Observed Execution Result                                                                     |
| :------------------------- | :------------------------------------------------------------------------ | :-------------------------------------------------------------------------------------------- |
| `sum(items.qty) as res`    | `SELECT name, SUM(items.qty) res FROM tabQB Test Parent GROUP BY name`    | **FAILED:** `pymysql.err.OperationalError: (1054, "Unknown column 'items.qty' in 'SELECT'")`  |
| `count(items.name) as res` | `SELECT name, COUNT(items.name) res FROM tabQB Test Parent GROUP BY name` | **FAILED:** `pymysql.err.OperationalError: (1054, "Unknown column 'items.name' in 'SELECT'")` |
| `avg(items.rate) as res`   | `SELECT name, AVG(items.rate) res FROM tabQB Test Parent GROUP BY name`   | **FAILED:** `pymysql.err.OperationalError: (1054, "Unknown column 'items.rate' in 'SELECT'")` |
| `min(items.rate) as res`   | `SELECT name, MIN(items.rate) res FROM tabQB Test Parent GROUP BY name`   | **FAILED:** `pymysql.err.OperationalError: (1054, "Unknown column 'items.rate' in 'SELECT'")` |
| `max(items.rate) as res`   | `SELECT name, MAX(items.rate) res FROM tabQB Test Parent GROUP BY name`   | **FAILED:** `pymysql.err.OperationalError: (1054, "Unknown column 'items.rate' in 'SELECT'")` |

### 2.3 Fetch Records Handler Execution Trace

Executing `QueryRecordsHandler._fetch_records` with action configuration:

```json
{
	"operation": "Fetch Records",
	"reference_doctype": "QB Test Parent",
	"config": {
		"fields": ["name", "sum(items.qty) as total_qty"],
		"group_by": "name"
	}
}
```

**Output Exception Trace:**

```text
pymysql.err.OperationalError: (1054, "Unknown column 'items.qty' in 'SELECT'")
```

_Confirmation:_ `QueryRecordsHandler._fetch_records` does not transform or compile aggregate function strings before delegating to `frappe.qb.get_query`.

---

## 3. Detailed Aggregation Semantics Audit (Use Cases A–E)

### Use Case A: Aggregate Child Rows Per Parent

**Objective:** Calculate aggregate values (`SUM`, `COUNT`, `AVG`, `MIN`, `MAX`) for each parent record.

**PyPika Implementation:**

```python
parent_tbl = frappe.qb.DocType("QB Test Parent")
child_tbl = frappe.qb.DocType("QB Test Child")

query = (
    frappe.qb.from_(parent_tbl)
    .left_join(child_tbl)
    .on(
        (child_tbl.parent == parent_tbl.name)
        & (child_tbl.parenttype == "QB Test Parent")
        & (child_tbl.parentfield == "items")
    )
    .select(
        parent_tbl.name,
        Sum(child_tbl.qty).as_("total_qty"),
        Count(child_tbl.name).as_("item_count"),
        Avg(child_tbl.rate).as_("avg_rate"),
        Min(child_tbl.rate).as_("min_rate"),
        Max(child_tbl.rate).as_("max_rate"),
    )
    .groupby(parent_tbl.name)
)
```

**Compiled SQL:**

```sql
SELECT
  `tabQB Test Parent`.`name`,
  SUM(`tabQB Test Child`.`qty`) `total_qty`,
  COUNT(`tabQB Test Child`.`name`) `item_count`,
  AVG(`tabQB Test Child`.`rate`) `avg_rate`,
  MIN(`tabQB Test Child`.`rate`) `min_rate`,
  MAX(`tabQB Test Child`.`rate`) `max_rate`
FROM `tabQB Test Parent`
LEFT JOIN `tabQB Test Child`
  ON `tabQB Test Child`.`parent` = `tabQB Test Parent`.`name`
 AND `tabQB Test Child`.`parenttype` = 'QB Test Parent'
 AND `tabQB Test Child`.`parentfield` = 'items'
GROUP BY `tabQB Test Parent`.`name`
```

**Verified Results:**

- **P1 (`l87s1atjte`):** `total_qty=10.0`, `item_count=3`, `avg_rate=13.3333`, `min_rate=10.0`, `max_rate=20.0`.
- **P2 (`l875vqoa6g`):** `total_qty=1.0`, `item_count=1`, `avg_rate=10.0`, `min_rate=10.0`, `max_rate=10.0`.
- **P3 (`l87o5sin6t`):** `total_qty=None`, `item_count=0`, `avg_rate=None`, `min_rate=None`, `max_rate=None`.

_Key Takeaway:_ Left joins correctly return `0` for `COUNT` and `None` (`NULL`) for `SUM`/`AVG`/`MIN`/`MAX` when child collections are empty.

---

### Use Case B: Aggregate Across All Matching Child Rows (Global Aggregation)

**Objective:** Compute a single summary row across all matching child rows without grouping by parent.

**PyPika Implementation:**

```python
query = (
    frappe.qb.from_(parent_tbl)
    .left_join(child_tbl)
    .on(
        (child_tbl.parent == parent_tbl.name)
        & (child_tbl.parenttype == "QB Test Parent")
        & (child_tbl.parentfield == "items")
    )
    .where(parent_tbl.enabled == 1)
    .select(
        Sum(child_tbl.qty).as_("global_qty"),
        Count(child_tbl.name).as_("global_count"),
        Avg(child_tbl.rate).as_("global_avg"),
    )
)
```

**Compiled SQL:**

```sql
SELECT
  SUM(`tabQB Test Child`.`qty`) `global_qty`,
  COUNT(`tabQB Test Child`.`name`) `global_count`,
  AVG(`tabQB Test Child`.`rate`) `global_avg`
FROM `tabQB Test Parent`
LEFT JOIN `tabQB Test Child`
  ON `tabQB Test Child`.`parent` = `tabQB Test Parent`.`name`
 AND `tabQB Test Child`.`parenttype` = 'QB Test Parent'
 AND `tabQB Test Child`.`parentfield` = 'items'
WHERE `tabQB Test Parent`.`enabled` = 1
```

**Verified Results:** `[{'global_qty': 11.0, 'global_count': 4, 'global_avg': 12.5}]` (Exactly 1 global summary row returned).

---

### Use Case C: Mixed Parent Fields and Child Aggregates (`ONLY_FULL_GROUP_BY`)

**Objective:** Verify SQL compliance when non-aggregated parent fields (`status`, `parent_title`) are selected alongside child aggregates.

**Tested Grouping Options:**

1. **Group by Primary Key (`parent.name`):**

    ```sql
    SELECT `tabQB Test Parent`.`name`, `tabQB Test Parent`.`status`, `tabQB Test Parent`.`parent_title`, SUM(`tabQB Test Child`.`qty`) `total_qty`
    FROM `tabQB Test Parent`
    LEFT JOIN `tabQB Test Child` ON `tabQB Test Child`.`parent` = `tabQB Test Parent`.`name` ...
    GROUP BY `tabQB Test Parent`.`name`
    ```

    _Execution Result:_ **SUCCESS.** Under MariaDB / MySQL `ONLY_FULL_GROUP_BY`, grouping by the primary key `name` guarantees functional dependency of all other parent columns (`status`, `parent_title`), so MariaDB executes this query without error.

2. **Group by All Non-Aggregated Selected Columns:**
    ```sql
    GROUP BY `tabQB Test Parent`.`name`, `tabQB Test Parent`.`status`, `tabQB Test Parent`.`parent_title`
    ```
    _Execution Result:_ **SUCCESS.** Guarantees strict SQL-92/99 compatibility across all SQL engines.

---

### Use Case D: Multiple Child Tables & Cartesian Join Inflation

**Objective:** Test join semantics and numeric correctness when a parent DocType joins multiple child tables simultaneously.

**Experimental Setup:**
Parent P1 has **3 rows** in `QB Test Child` (qty: 2, 3, 5 -> true sum = 10.0) and **2 rows** in `QB Test Child 2` (scores: 10, 20 -> true sum = 30.0).

**Compiled Multi-Child Query:**

```sql
SELECT
  `tabQB Test Parent`.`name`,
  SUM(`tabQB Test Child`.`qty`) `total_qty`,
  COUNT(`tabQB Test Child`.`name`) `item_count`,
  SUM(`tabQB Test Child 2`.`score`) `total_score`,
  COUNT(`tabQB Test Child 2`.`name`) `comment_count`
FROM `tabQB Test Parent`
LEFT JOIN `tabQB Test Child`
  ON `tabQB Test Child`.`parent` = `tabQB Test Parent`.`name` AND `tabQB Test Child`.`parenttype` = 'QB Test Parent' AND `tabQB Test Child`.`parentfield` = 'items'
LEFT JOIN `tabQB Test Child 2`
  ON `tabQB Test Child 2`.`parent` = `tabQB Test Parent`.`name` AND `tabQB Test Child 2`.`parenttype` = 'QB Test Parent' AND `tabQB Test Child 2`.`parentfield` = 'comments'
WHERE `tabQB Test Parent`.`name` = 'l87s1atjte'
GROUP BY `tabQB Test Parent`.`name`
```

**Observed Results Comparison:**

| Metric          | Single Child Join Expected | Multi-Child Join Actual |        Multiplication Factor         |
| :-------------- | :------------------------: | :---------------------: | :----------------------------------: |
| `total_qty`     |          **10.0**          |        **20.0**         | **2x** (multiplied by 2 child2 rows) |
| `item_count`    |           **3**            |          **6**          |                **2x**                |
| `total_score`   |           **30**           |         **90**          | **3x** (multiplied by 3 child1 rows) |
| `comment_count` |           **2**            |          **6**          |                **3x**                |

**Critical Architectural Finding:** Joining multiple child tables in a single flat SQL query creates a Cartesian product ($3 \times 2 = 6$ intermediate joined rows). Aggregate functions (`SUM`, `COUNT`, `AVG`) compute over these duplicate rows and produce **corrupted, inflated aggregate values**!

_Design Mandate:_ FlexiRule must explicitly **reject queries that attempt to aggregate over multiple child tables in a single query**, or compile child aggregations into separate CTEs / subqueries before joining.

---

### Use Case E: Permissions & Security Contract

**Objective:** Ensure query execution preserves Frappe's security contract and row-level permissions.

**Execution Audit:**

- `execute_query(doctype, kwargs, ignore_permissions=False)` checks session permissions via Frappe's `Permission.check_permissions(query, user)`.
- When executed under a restricted user context (e.g. `Guest`), `execute_query` correctly enforces permission checks and raises `PermissionError`.
- Any bounded query compiler extension must pass its constructed PyPika query through `Permission.check_permissions(query, user)` or attach `DatabaseQuery(doctype).build_match_conditions()`.

---

## 4. Capability Matrix

| Aggregate Function                  | Input Syntax Mode                     | Grouping Mode                  | Frappe v15 Engine Support | Current Fetch Records Support | Root Cause of Failure / Status                                                              |
| :---------------------------------- | :------------------------------------ | :----------------------------- | :-----------------------: | :---------------------------: | :------------------------------------------------------------------------------------------ |
| `SUM`, `COUNT`, `AVG`, `MIN`, `MAX` | Dotted String (e.g. `sum(items.qty)`) | Per-Parent / Global            |          **NO**           |        **UNSUPPORTED**        | Engine string parser fails to detect child table inside function call; missing `LEFT JOIN`. |
| `SUM`, `COUNT`, `AVG`, `MIN`, `MAX` | PyPika Term + Explicit Join           | Per-Parent (`GROUP BY parent`) |          **YES**          |        **UNSUPPORTED**        | `frappe.qb.get_query` interface does not accept PyPika join objects via `kwargs`.           |
| `SUM`, `COUNT`, `AVG`, `MIN`, `MAX` | PyPika Term + Explicit Join           | Global (No `GROUP BY`)         |          **YES**          |        **UNSUPPORTED**        | Requires custom PyPika builder.                                                             |
| `SUM`, `COUNT`, `AVG`, `MIN`, `MAX` | Multi-Child Table Join                | Any                            |       **DANGEROUS**       |        **UNSUPPORTED**        | Causes Cartesian product row inflation ($N \times M$), producing invalid aggregate numbers. |

---

## 5. Failure Analysis

### Exact Failure Location & Root Cause

1. **Location:** `frappe/database/query.py` -> `Engine._parse_field` / `Engine._get_fields_from_string`.
2. **Mechanism:**
    - When a plain field string like `"items.qty"` is passed, `Engine._parse_field` splits on `.` and registers a child table `LEFT JOIN` on `tabQB Test Child`.
    - When a function-wrapped string like `"sum(items.qty) as total_qty"` is passed, `Engine._parse_field` matches the function regex (e.g. `sum(...)`), wraps the inner string directly into a PyPika `CustomFunction` or `Sum` term, but **skips table field path inspection** for the inner argument.
    - The compiled SQL contains `SUM(\`items.qty\`)`or`SUM(\`items\`.\`qty\`)`, but **no `LEFT JOIN`clause** is added to the`FROM` block.
3. **Database Error:**
    - MariaDB receives `SELECT name, SUM(items.qty) res FROM tabQB Test Parent GROUP BY name`.
    - MariaDB throws: `pymysql.err.OperationalError: (1054, "Unknown column 'items.qty' in 'SELECT'")`.

---

## 6. Recommended Design Options & Architecture

### Option Comparison

| Option                                                    | Engineering Effort | Maintenance Cost | Risk | Recommendation                                                                                                                                                                                                                                                      |
| :-------------------------------------------------------- | :----------------: | :--------------: | :--: | :------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **Option 1: Retain String Expressions Only**              |        Zero        |       Zero       | None | Keep current behavior (reject child aggregates in UI).                                                                                                                                                                                                              |
| **Option 2: Structured Child-Table Aggregation Compiler** |       Medium       |       Low        | Low  | **RECOMMENDED FOR FUTURE ENHANCEMENT.** Build a dedicated compiler helper that detects aggregate functions over child fields, constructs explicit PyPika `LEFT JOIN`s, enforces single-child-table boundaries, auto-generates `GROUP BY`, and enforces permissions. |
| **Option 3: Fallback to `frappe.get_list`**               |        High        |       High       | High | Not recommended; `frappe.get_list` lacks Query Builder term flexibility and pagination controls.                                                                                                                                                                    |

### Proposed Bounded Compiler Architecture (Option 2)

If FlexiRule chooses to implement child-table aggregation in a future release, the architecture must follow these strict rules:

```text
Configured Fields ["name", "sum(items.qty) as total_qty"]
                   │
                   ▼
     ┌───────────────────────────┐
     │  FlexiRule Query Compiler │
     └─────────────┬─────────────┘
                   │
    ┌──────────────┴──────────────┐
    │ 1. Validate Single Child Table
    │ 2. Build PyPika Parent DocType Term
    │ 3. Build PyPika Child DocType Term
    │ 4. Add ON (child.parent==parent.name AND parenttype AND parentfield)
    │ 5. Wrap Field in PyPika Sum/Count/Avg/Min/Max
    │ 6. Auto-add non-aggregated fields to GROUP BY
    │ 7. Apply Permission.check_permissions(query, user)
    └──────────────┬──────────────┘
                   │
                   ▼
         Native PyPika Query Execution
```

**Mandatory Guardrails for the Compiler:**

1. **Single Child Table Rule:** Reject any query configuration that attempts to aggregate fields from more than one child table in the same query to prevent Cartesian multiplication.
2. **Strict Join Condition:** Always include `child.parent == parent.name`, `child.parenttype == parent_doctype`, and `child.parentfield == child_fieldname`.
3. **`GROUP BY` Auto-Completion:** Automatically add all selected non-aggregate parent fields to the `GROUP BY` clause to comply with `ONLY_FULL_GROUP_BY`.
4. **Permissions:** Execute `Permission.check_permissions(query, user)` prior to `query.run()`.

---

## 7. Test Plan for Future Feature Implementation

Before enabling child-table aggregation in Fetch Records, the following test suite must be implemented and passing:

1. **Single Child Table Aggregation Tests (`test_fetch_records_child_aggregation.py`):**
    - Test `SUM`, `COUNT`, `AVG`, `MIN`, `MAX` per parent on a child table.
    - Verify empty child collection handling (returns `0` for count, `None`/`NULL` for sums/averages).
2. **Global Aggregation Tests:**
    - Test global summary queries across all matching child rows without `GROUP BY`.
3. **Multi-Child Table Prevention Test:**
    - Assert that configuring fields from two distinct child tables in an aggregate query raises a validation error: `"Child-table aggregation supports only one child table per query to prevent data duplication."`
4. **`GROUP BY` Compliance Test:**
    - Test queries selecting `parent.name`, `parent.status`, and `SUM(items.qty)` to verify proper `GROUP BY` compilation.
5. **Security & Permission Tests:**
    - Execute child aggregate queries as a non-System Manager user and verify that permission restrictions on parent documents are strictly enforced.
6. **Regression Suite:**
    - Execute full existing `test_fetch_records.py` and `test_frappe_qb_capabilities.py` suites to ensure zero regressions for non-aggregate queries.

---

## 8. UI Recommendation for PR #389

Based on the empirical evidence gathered during this audit:

1. **Retain Current Restriction in `output_fields_model.js`:**
   PR #389 currently includes the following validation in `validateOutputFields`:

    ```javascript
    if (field.includes(".")) {
	errors.push(
		prefix +
			"aggregate functions currently support root DocType fields only; child/link aggregates need backend support."
	);
    }
    ```

    **Verdict:** This validation rule is **100% CORRECT and NECESSARY**. It accurately reflects the capabilities of the current backend. Removing this restriction without backend compiler changes would allow users to save configurations that crash at runtime with MariaDB `OperationalError 1054`.

2. **Conditions for Lifting the UI Restriction:**
   The UI validation restriction in `output_fields_model.js` should remain in place until:
    - A structured child-table query compiler is implemented in `flexirule/ruleflow/core/action_handlers/query_records.py`.
    - The backend integration test suite specified in Section 7 is fully implemented and passing in CI.

---

## 9. Final Capability Verdict & Summary

- **Child-Table Aggregation via Raw Dotted Strings:** **UNSUPPORTED** (Fails at DB execution with MariaDB Error 1054).
- **Child-Table Aggregation via PyPika Explicit Joins:** **POSSIBLE & VERIFIED** (Supported natively by Frappe v15 / PyPika).
- **Current Fetch Records Mode:** **UNSUPPORTED** (Delegates directly to raw string parser).
- **Recommended Action for PR #389:** **RETAIN CURRENT UI RESTRICTION** (Block aggregate source fields containing dots).
\n\n---\n\n# Consolidated source 2: reports/query-records/fetch-records-operator-parity-v15-v16.md\n\n> Original report content follows. Preserved without rewriting so findings, evidence, caveats, and historical context remain attributable to their source.\n\n# Fetch Records Operator Parity Audit: Frappe 15 vs Frappe 16

**Audit date:** 2026-10-12  
**Scope:** Operators used by `frappe.qb.get_query`, which is the execution API for FlexiRule Fetch Records. This report deliberately separates Query Builder from `frappe.get_list` / `frappe.model.db_query.DatabaseQuery`; the two APIs have overlapping but non-identical parser and execution contracts.

## Executive finding

Fetch Records was not fully aligned before this audit:

1. Its backend allowlist included `<>`, but neither Frappe 15 nor Frappe 16 `OPERATOR_MAP` registers `<>`. The normal portable spelling is `!=`; Fetch Records now rejects `<>`.
2. The UI and backend must **not** expose `regex` just because the operator map contains it. Both release branches map `regex` to PyPika's `Term.regex`, which emits the SQL token `REGEX`. The inspected Frappe 15 and 16 `frappe/query_builder/utils.py` versions do not install the dialect patch that makes this executable. Frappe's `develop` source explicitly documents that `REGEX` is supported by neither backend and includes a patch mapping MariaDB/MySQL to `REGEXP` and PostgreSQL to `~*`. Since that patch was absent from both release-branch snapshots, Fetch Records now fails closed and does not advertise `regex`.
3. Frappe has five nested-set operators in both versions. The previous adapter had duplicated the list in its source; it now derives it from Frappe's `NestedSetHierarchy` constant. Backend validation now checks that a tree operator targets either the name field of a Tree DocType or a Link to a Tree DocType, rather than merely accepting the operator name.
4. The portable Fetch Records contract consists of the shared, executable filter operators, FlexiRule aliases normalized to those operators, and the five Frappe nested-set operators. Frappe 16-only or dialect-specific operators are intentionally not exposed as portable Fetch Records operators.

## Source snapshots inspected

The code below was read from both release branches, not inferred from docs or the other major version.

| Source | Frappe 15 blob SHA | Frappe 16 blob SHA | Why it matters |
|---|---|---|---|
| [`frappe/database/operator_map.py`](https://github.com/frappe/frappe/blob/version-15/frappe/database/operator_map.py) | `837d86282c4483aeec6421153123c024418f6707` | `218983a318fd8005626dffa183ea6ef54df0f120` | The Query Builder operator functions and version differences. |
| [`frappe/database/query.py`](https://github.com/frappe/frappe/blob/version-15/frappe/database/query.py) | `30318e2d79dd875b3ed9adea9d710c3c36167775` | `1377710fe5acfb1683a08eb8218e8cdae582778d` | Actual Query Builder filter parsing, operator dispatch, tree expansion and boolean filter behavior. |
| [`frappe/database/utils.py`](https://github.com/frappe/frappe/blob/version-15/frappe/database/utils.py) | `e031e8379510cf7e0121c08d1c28bbe482037297` | `9e2343538595bd822a379a24a73b1d0d865fd27d` | The canonical `NestedSetHierarchy` operator tuple. |
| [`frappe/query_builder/utils.py`](https://github.com/frappe/frappe/blob/version-15/frappe/query_builder/utils.py) | `7074321fb71d23179e2ceb7b2b147f8450a07104` | `d151133d9fb041d5b9465eca2cc8a634678149f7` | Query Builder runtime monkey patches; the checked release snapshots do not include `patch_regex_operator`. |
| [`frappe/model/db_query.py`](https://github.com/frappe/frappe/blob/version-15/frappe/model/db_query.py) | `2ddb8ee71b0526f3a4bda58574725d720b6e1cf7` | `dc0c9827703bb43260a66be0fec0dcd1aa6c8ad9` | Cross-check only. This is the ORM query path, not the Fetch Records execution path. |
| [Frappe standard filter UI `filter.js`](https://github.com/frappe/frappe/blob/version-15/frappe/public/js/frappe/ui/filters/filter.js) | `59324ff3aee40beb70c699829fd2e4c06ad26869` | `bba692739d2134a347efa6a805b3c12827f9e9f9` | Per-field operator restrictions; Frappe 16 is stricter for Select/Color comparisons and has more explicit text/numeric field rules. |

The Fetch Records UI sources inspected were [`FilterLeaf.vue`](https://github.com/Sendipad/flexirule/blob/fix/fetch-records-review-findings/flexirule/public/js/flexirule/rule_builder/components/rule_config/query_filters/FilterLeaf.vue) and backend handler [`query_records.py`](https://github.com/Sendipad/flexirule/blob/fix/fetch-records-review-findings/flexirule/ruleflow/core/action_handlers/query_records.py), plus the compatibility adapter [`frappe_query_compat.py`](https://github.com/Sendipad/flexirule/blob/fix/fetch-records-review-findings/flexirule/ruleflow/utils/frappe_query_compat.py).

## Native Query Builder operator contract

### Operators shared by the Frappe 15 and Frappe 16 release branches

The portable executable set represented by Fetch Records is:

- Comparisons: `=`, `!=`, `<`, `<=`, `>`, `>=`.
- Pattern and membership filters: `like`, `not like`, `in`, `not in`.
- Value operators: `between`, `is`, `timespan`.
- Tree operators from `NestedSetHierarchy`: `ancestors of`, `descendants of`, `not ancestors of`, `not descendants of`, and `descendants of (inclusive)`.

Frappe's `OPERATOR_MAP` also contains `=<` and `=>`, which are aliases for `<=` and `>=`. Fetch Records uses the canonical spellings and does not offer duplicate aliases. The map also contains `+`, `-`, `/`, and `*` for expression/arithmetic operations; these are not offered as ordinary filter operators. On Frappe 15, the string `nested_set` is a registry key whose value is the tree-operator tuple, not a leaf operator; Frappe 16 imports `NESTED_SET_OPERATORS` separately. The adapter now uses the source-level `NestedSetHierarchy` constant rather than maintaining a duplicate tree list.

### Differences and important traps

| Operator or family | Frappe 15 Query Builder | Frappe 16 Query Builder | Fetch Records decision |
|---|---|---|---|
| `ilike` | Not in `OPERATOR_MAP` | In `OPERATOR_MAP`; direct SQL spelling is dialect-dependent | Not exposed in the portable contract. Frappe 16 can select ILIKE for PostgreSQL's `like` handling; MariaDB does not use the PostgreSQL ILIKE syntax. |
| `previous`, `next` | Not handled by the v15 Query Builder's simple-filter dispatch | Special-cased in `_build_criterion_for_simple_filter` and converted to date ranges | Not exposed directly because these are v16-only. The portable UI offers FlexiRule's `Timespan` abstraction, which the backend converts to `between`. |
| `regex` | Present in `OPERATOR_MAP`, but its mapped PyPika rendering is not executable on the inspected release branch | Same issue in the inspected release branch | Not exposed or allowlisted. The Frappe `develop` implementation documents the problem and adds a dialect-aware patch: [`patch_regex_operator`](https://github.com/frappe/frappe/blob/develop/frappe/query_builder/utils.py#L334-L364). PyPika's unpatched `Term.regex` emits `REGEX`, not MariaDB/MySQL's `REGEXP` or PostgreSQL's `~*` ([PyPika terms](https://github.com/kayak/pypika/blob/master/pypika/terms.py#L178-L185), [matching enum](https://github.com/kayak/pypika/blob/master/pypika/enums.py#L32-L40)). |
| `<>` | Not in `OPERATOR_MAP` | Not in `OPERATOR_MAP` | Removed from Fetch Records validation; use `!=`. |
| Custom operators from filter hooks | Not supported by this release Query Builder path | The v16 Query Builder parser consults `get_additional_filters_from_hooks()` | Not accepted in Fetch Records' fixed portable allowlist. Hook-specific operators need an explicit FlexiRule contract and frontend value/editor before they can safely be exposed. |

Do not confuse this table with `frappe.model.db_query.DatabaseQuery` or `frappe.get_list`. Those paths have their own filter conversion, including `previous`/`next` handling in Frappe 15. Fetch Records calls `frappe.qb.get_query`, so that ORM behavior does not prove that the Query Builder supports the same syntax.

## FlexiRule operator mapping after the changes

| FlexiRule UI option | Backend payload/execution | Status |
|---|---|---|
| Equals / Not Equals / relational comparisons | Native `=`, `!=`, `<`, `<=`, `>`, `>=` | Aligned on v15/v16 |
| Like / Not Like | Native `like` / `not like` | Aligned on v15/v16 |
| In / Not In | Native `in` / `not in`; the value editor provides lists/strings | Aligned on v15/v16 |
| Between | Normalized to `between` | Aligned on v15/v16 |
| Timespan | Resolved to date bounds and sent as `between` | FlexiRule abstraction, portable on v15/v16 |
| Starts With / Ends With | Normalized to `like` with a trailing/leading `%` | FlexiRule aliases; they do not pretend to be native Frappe operators |
| Is | Native `is`, with value `set` or `not set` | The backend now validates the native value contract |
| Five nested-set operators | Derived on the backend from Frappe's `NestedSetHierarchy`; adapter preserves tree behavior in standalone and boolean-group filters | Aligned on v15/v16; backend validates Tree DocType applicability |
| `<>` | Rejected | Previously accepted by the backend despite lacking a native operator mapping; corrected |
| `regex` | Rejected | Map entry is not sufficient proof of executable SQL on the inspected release branches |
| `ilike`, `previous`, `next` | Rejected by the portable allowlist | Intentionally excluded due to version/dialect differences |

The UI applies additional field-type restrictions from the Frappe standard filter UI. FlexiRule uses the **intersection of the Frappe 15 and 16 restrictions** so an operator is not offered only on one supported major version: for example, Check fields expose equality only, Select fields do not expose range comparisons (Frappe 16 adds that restriction), Color does not expose range comparisons (also stricter in v16), text-like field types follow the union of the Frappe 15/16 exclusions, and integer/numeric fields inherit the v16 numeric restrictions. `Starts With` and `Ends With` inherit the `like` restriction because they normalize to `like` in the backend.

The UI offers nested-set operators for a Link to a Tree DocType, and also for the `name` field when querying a Tree DocType. The backend validates the tree-target requirement for canonical and legacy filter shapes, so manually edited or stale configurations cannot rely solely on the UI to prevent invalid tree filters. After dynamic values resolve, the backend also checks the operator allowlist and value contracts for both canonical filter trees and older Frappe-style filter rows.

## Regression coverage added

The dedicated database-backed test module, [`test_fetch_records_tree_operators.py`](https://github.com/Sendipad/flexirule/blob/fix/fetch-records-review-findings/flexirule/ruleflow/tests/test_fetch_records_tree_operators.py), runs against a real persisted Tree DocType. It covers all five nested-set operators as single filters and composed with both AND and OR, plus the allowed operator set, rejected aliases/version-specific entries, `is` value validation, and Tree DocType target validation.

CI is configured with the existing full Frappe 15 backend suite and a separate Frappe 16 job that runs this integration module. CI results should be read from the current PR checks; a previous passing run does not certify this revision.

## Final assessment

Fetch Records now exposes a deliberate cross-version portable subset, not every key present in Frappe's multi-purpose `OPERATOR_MAP`. That distinction is necessary because the map includes arithmetic helpers, registry entries, version-specific filters and an operator (`regex`) that the inspected release runtime renders as invalid SQL. Operators presented in the UI now map to supported backend behavior or to an explicitly documented FlexiRule alias, and nested-set operators are checked against their target DocType rather than accepted by name alone.
\n\n---\n\n# Consolidated source 3: reports/query-records/filter-tree-adapter-implementation-plan.md\n\n> Original report content follows. Preserved without rewriting so findings, evidence, caveats, and historical context remain attributable to their source.\n\n# Query Records Filter Tree — Production Implementation Plan

**Repository:** `Sendipad/flexirule`  
**Source branch reviewed:** `refactor/query-records`  
**Report path:** `reports/query-records/filter-tree-adapter-implementation-plan.md`  
**Scope:** Filter TreeBuilder / FilterLeaf data flow and the boundary between UI filter state and the Fetch Records backend query contract.

## 1. Executive decision

Do **not** make `TreeBuilder` or `FilterLeaf` directly own the backend filter representation.

Use a dedicated, explicit **Filter Tree Adapter / Serializer** between the interactive UI tree and the canonical Fetch Records backend filter structure.

Recommended architecture:

```
Interactive UI tree
  TreeBuilder
  TreeBuilderNode
  FilterLeaf / FilterGroup
          |
          v
  Filter Tree Adapter
  - normalize
  - validate
  - serialize
  - deserialize
          |
          v
Canonical Fetch Records filters
          |
          v
Backend Query Records
          |
          v
frappe.qb.get_query()
```

The UI model should remain optimized for editing. The backend representation should remain optimized for query execution and Frappe compatibility.

This avoids coupling the Vue tree to the exact representation accepted by the installed Frappe version and makes the Frappe compatibility layer the backend concern rather than a responsibility of the UI.

---

## 2. Source-code findings from `refactor/query-records`

### 2.1 TreeBuilder is already a generic UI tree editor

Current `TreeBuilder.vue`:

- owns a root group;
- supports `and` / `or`;
- creates leaf nodes through a supplied `leafFactory`;
- creates nested groups;
- supports removal and drag/drop;
- maintains stable UI node IDs;
- emits a cloned tree through `update:modelValue`;
- intentionally knows nothing about Fetch Records or Frappe query syntax.

This is the correct separation and should be preserved.

### 2.2 TreeBuilderNode is also correctly UI-oriented

`TreeBuilderNode.vue` recursively renders groups and leaves.

It needs:

- node identity;
- parent/child relationships;
- group operator;
- drag/drop state;
- add/remove actions.

It should **not** be changed to understand backend filter arrays.

### 2.3 QueryFilterTree currently combines two responsibilities

Current `QueryFilterTree.vue` contains both:

1. the UI tree state;
2. conversion between that tree and the external filter payload.

The current internal model is approximately:

```js
{
  id,
  type: "group",
  operator: "and" | "or",
  children: [
    {
      id,
      type: "leaf",
      doctype,
      field,
      operator,
      value
    }
  ]
}
```

The current serializer produces leaf arrays of the form:

```js
[doctype, field, operator, value]
```

and combines multiple children using logical operator strings:

```js
[
  [doctype, field, "=", value],
  "or",
  [doctype, field, "=", value]
]
```

This is already evidence that an adapter boundary exists conceptually. The production improvement should be to make that boundary explicit and reusable rather than redesigning TreeBuilder around backend arrays.

### 2.4 FilterGroup requires a complete editable leaf model

Current `FilterGroup.vue` expects a row with:

- `doctype`
- `field`
- `operator`
- `value`

It also owns Frappe/FlexiRule-specific UI behavior such as:

- field navigation;
- operator selection;
- field-type-specific operators;
- nested-set operators;
- Between;
- Timespan;
- FlexValueControl;
- variable/resolver values;
- field validation.

Therefore the UI leaf must remain richer than a raw backend list item.

### 2.5 Backend compatibility already establishes an important constraint

Current `flexirule/ruleflow/utils/frappe_query_compat.py` detects whether the installed Frappe version supports:

- `ignore_permissions`;
- logical filter groups.

When logical filter groups are not supported natively, the compatibility layer converts nested logical filters into Frappe/PyPika `Criterion` objects.

This confirms that **logical filter representation belongs at the backend boundary**, not inside the Vue TreeBuilder.

The compatibility layer also explicitly handles simple filter leaves and rejects unsupported dotted fields for its legacy logical-filter fallback.

---

## 3. Production architecture

Introduce a dedicated module conceptually named:

```
filter_tree_adapter.js
```

or, preferably if the project already has a suitable query/filter utility location:

```
query_filter_adapter.js
```

The exact file location should be chosen after checking the existing frontend utility/composable organization.

It should expose four primary operations:

```js
normalizeFilterTree(value, context)
serializeFilterTree(tree, context)
deserializeFilterPayload(payload, context)
validateFilterTree(tree, context)
```

Optional helpers:

```js
createFilterLeaf(context)
createFilterGroup(operator)
isFilterLeaf(node)
isFilterGroup(node)
```

The adapter should contain **no Vue template logic**.

It may use plain JavaScript objects and functions and should be independently testable.

---

## 4. Canonical UI model

The editor model should remain tree-shaped.

Recommended conceptual schema:

```js
{
  id: "stable-ui-id",
  type: "group",
  operator: "and",
  children: [
    {
      id: "stable-ui-id",
      type: "leaf",
      doctype: "Sales Order",
      field: "customer",
      operator: "=",
      value: {
        mode: "static",
        value: "CUST-0001"
      }
    }
  ]
}
```

### UI-only properties

The following must never be required by the backend:

- `id`
- `type`
- expansion state;
- selection state;
- drag state;
- temporary editor state;
- UI validation state.

These are editor concerns.

### Query semantics

The following are semantic query properties:

- DocType;
- field/path;
- operator;
- value;
- logical operator;
- nested grouping.

The adapter is responsible for converting these semantic properties into the canonical backend structure.

---

## 5. Canonical backend representation

The backend representation should be selected from the structures actually supported by the Fetch Records implementation and installed Frappe Query Builder.

Do **not** invent a third query language.

The preferred simple leaf representation remains list-based where supported:

```js
["fieldname", "=", value]
```

or the existing four-part representation where the DocType must travel with the leaf:

```js
["DocType", "fieldname", "=", value]
```

The exact canonical choice must be the one already accepted by the current Fetch Records backend. The adapter should normalize all UI leaves to that one representation before emitting configuration.

For logical groups, preserve the backend-supported nested representation rather than flattening expressions in the UI.

The important invariant is:

> TreeBuilder never needs to know which representation Frappe accepts.

---

## 6. Serialization rules

### 6.1 Leaf

A valid leaf:

```
doctype + field + operator + value
```

is serialized into the canonical backend leaf representation.

No UI-only properties may survive serialization.

### 6.2 Group

A group with no children:

- is invalid for execution;
- may exist temporarily while the user is editing;
- must be reported by validation rather than silently becoming a query.

A group with one child may serialize directly to that child if this is semantically equivalent in the backend contract.

A group with multiple children must preserve its logical operator.

### 6.3 Nested groups

Nested groups must retain their grouping semantics.

For example:

```
AND
├── status = Open
└── OR
    ├── priority = High
    └── priority = Medium
```

must never be flattened into:

```
status = Open
AND priority = High
OR priority = Medium
```

because that changes the meaning.

The adapter must preserve the tree's grouping boundaries.

### 6.4 Empty/incomplete leaves

A newly created leaf may temporarily contain:

```
field: ""
```

while the user is editing.

That is acceptable in the UI model.

It must not be emitted as an executable backend filter.

Validation should identify:

```
"A filter field is required."
```

rather than generating malformed backend criteria.

This is particularly important because the current blank-leaf bug originated from the distinction between a valid UI node and a complete query criterion.

---

## 7. Deserialization rules

The reverse adapter is equally important.

When existing configuration enters the editor:

```
backend filters
      |
      v
deserializeFilterPayload()
      |
      v
UI tree
```

Requirements:

1. Generate stable UI IDs.
2. Never use backend values as UI IDs.
3. Preserve AND/OR grouping.
4. Preserve DocType information.
5. Preserve FlexValue structures.
6. Preserve nested filter groups.
7. Preserve values without coercing their semantic type.
8. Normalize legacy accepted forms only at this boundary.

The editor should receive one predictable tree shape regardless of which accepted backend filter form was stored.

---

## 8. Legacy/accepted input compatibility

The adapter may accept more than one input representation when reading existing configuration.

For example:

```js
["status", "=", "Open"]
```

and:

```js
["Sales Order", "status", "=", "Open"]
```

may both be recognized if they are currently valid inputs.

However:

- only one canonical representation should be emitted;
- compatibility parsing must be isolated;
- new UI code must not branch on legacy representations.

This prevents legacy support from spreading into TreeBuilder and FilterGroup.

---

## 9. FlexValue integration

The adapter must treat filter values as opaque semantic values.

For example:

```js
{
  mode: "static",
  value: "Open"
}
```

or a variable/resolver/expression value must remain intact.

Do not convert FlexValue into a plain string merely because the backend ultimately resolves it.

The pipeline should be:

```
UI FlexValue
   ↓
serialized filter
   ↓
backend resolver/context handling
   ↓
query value
```

The adapter is responsible for structural serialization, not value resolution.

This keeps Value Resolver semantics outside the filter tree serializer.

---

## 10. Operators

The adapter should not maintain a second independent list of query operators.

Operator availability belongs to the existing field/operator capability logic.

The adapter should:

- preserve the selected operator;
- validate that an operator exists;
- preserve case/representation required by the backend contract;
- reject unsupported values during validation.

The UI can continue to derive field-specific operator options from the existing FilterGroup logic.

Future operator additions should therefore not require changes to the adapter unless serialization semantics change.

---

## 11. Fields and dotted references

Field references must remain strings at the semantic query layer.

Examples:

```
customer
customer.customer_name
items.item_code
items.qty
```

The adapter must not split these into unrelated frontend concepts merely because they contain dots.

The field navigator may provide the user-friendly navigation experience, but the selected backend field/path should remain the exact reference expected by the query backend.

This gives:

```
Display label
      ≠
Backend field reference
```

The UI may show:

```
Customer → Customer Name
```

while storing:

```
customer.customer_name
```

---

## 12. Validation boundary

Validation should exist at two levels.

### UI validation

Performed while editing:

- field selected;
- operator selected;
- required value supplied;
- valid field for selected DocType;
- valid field path;
- valid nested group;
- valid Between values;
- valid value control.

### Serialization validation

Performed before emitting executable configuration:

- no malformed leaf;
- no empty executable group;
- valid logical operator;
- valid leaf shape;
- valid backend field representation;
- valid operator;
- value structure remains serializable.

The adapter should return structured validation information where practical:

```js
{
  valid: false,
  errors: [
    {
      path: ["children", 0, "field"],
      code: "required",
      message: "A filter field is required."
    }
  ]
}
```

The existing user-facing validation messages can remain localized in the UI layer.

---

## 13. Emission strategy

Avoid a situation where both TreeBuilder and FetchRecordsConfig independently transform filters.

Recommended flow:

```
TreeBuilder
   ↓
UI tree
   ↓
QueryFilterTree
   ↓
adapter.serializeFilterTree()
   ↓
Fetch Records config.filters
```

The adapter should be the only code responsible for turning the tree into backend filter syntax.

Similarly:

```
config.filters
   ↓
adapter.deserializeFilterPayload()
   ↓
QueryFilterTree
   ↓
TreeBuilder
```

---

## 14. FetchRecordsConfig responsibility

`FetchRecordsConfig.vue` should remain responsible for:

- assembling the complete Fetch Records configuration;
- passing `filters` into QueryFilterTree;
- receiving serialized filters;
- emitting the complete action configuration;
- handling Fields;
- Order By;
- Group By;
- Limit;
- Offset;
- Distinct.

It should **not** understand individual tree nodes.

This is especially important as Fetch Records grows to support more query-builder features.

---

## 15. QueryFilterTree responsibility after refactor

`QueryFilterTree.vue` should become a thin integration layer:

1. receive `modelValue`;
2. deserialize it into a UI tree;
3. render TreeBuilder;
4. receive tree mutations;
5. validate;
6. serialize through the adapter;
7. emit the canonical filter payload.

It should not contain a growing collection of backend-format conditionals.

---

## 16. TreeBuilder responsibility

No Fetch Records-specific logic should be introduced into generic TreeBuilder.

TreeBuilder should continue to know only:

- group;
- leaf;
- children;
- logical group operator;
- node identity;
- add/remove/move.

This preserves TreeBuilder as a reusable component for:

- Conditions;
- Filters;
- future rule trees;
- other nested expression builders.

---

## 17. Backend responsibility

The backend remains authoritative for actual query execution.

The pipeline should be:

```
Fetch Records config
       ↓
backend handler
       ↓
frappe.qb.get_query()
       ↓
Frappe Query Builder
```

The existing compatibility layer remains responsible for Frappe-version differences, particularly logical filters and permission-related API differences.

Do not move backend compatibility logic into JavaScript.

---

## 18. Important distinction: adapter vs compatibility layer

These are two different layers.

### Frontend adapter

Solves:

> How does the interactive Vue tree become the Fetch Records filter payload?

### Backend compatibility layer

Solves:

> How does the Fetch Records filter payload execute correctly on the installed Frappe version?

Architecture:

```
Vue tree
   ↓
Frontend adapter
   ↓
FlexiRule canonical filter payload
   ↓
Fetch Records backend
   ↓
Frappe compatibility layer
   ↓
frappe.qb.get_query()
```

Neither layer should absorb the other's responsibilities.

---

## 19. Testing strategy

The adapter should have focused unit tests before changing TreeBuilder behavior.

### Required serialization tests

1. Empty root group.
2. One leaf.
3. Multiple AND leaves.
4. Multiple OR leaves.
5. Nested AND/OR.
6. Deep nested groups.
7. Four-part leaf with DocType.
8. Three-part leaf without DocType.
9. Static FlexValue.
10. Variable FlexValue.
11. Resolver/expression FlexValue.
12. Dotted Link field.
13. Dotted child field.
14. Empty field.
15. Empty group.
16. Unsupported logical operator.
17. Malformed leaf.

### Required deserialization tests

For every supported backend representation:

```
backend → UI tree → backend
```

must preserve query semantics.

The strongest test is semantic round-trip equality rather than object identity.

UI-generated IDs must not affect round-trip comparison.

### Component tests

Verify:

- Add Filter creates a complete editable leaf;
- field/operator/value controls render immediately;
- nested groups retain their operator;
- changing AND to OR changes serialized output;
- deleting a leaf updates serialized filters;
- moving a node does not corrupt grouping;
- invalid filters fail validation.

### Regression tests

Verify existing Fetch Records behavior for:

- Fields;
- Order By;
- Group By;
- Limit;
- Offset;
- Distinct;
- Refresh Schema;
- Link fields;
- child fields.

---

## 20. Performance requirements

Do not serialize the entire tree on every keystroke if this becomes expensive for large trees.

The first implementation may continue using Vue's deep watcher because current trees are expected to be small.

However, the adapter should be pure and cheap enough to call repeatedly.

Avoid:

- API calls during serialization;
- schema fetches during serialization;
- field metadata traversal unrelated to the changed node;
- repeated deep cloning of the entire rule document;
- generating new IDs during every serialization;
- asynchronous serialization.

Schema metadata should be resolved outside the adapter.

---

## 21. Reactivity requirements

The adapter must never mutate the source tree during:

- serialization;
- deserialization;
- validation.

Use immutable/clone semantics where necessary.

This is particularly important because TreeBuilder uses a reactive root and emits deep-cloned values.

The adapter should therefore behave as a pure boundary:

```
input → output
```

with no hidden Vue mutations.

---

## 22. Error handling

Malformed persisted configuration must not crash the rule-builder UI.

The adapter should:

1. attempt to parse;
2. normalize recognized forms;
3. preserve as much valid structure as possible;
4. report invalid nodes;
5. allow the editor to display and repair them.

Do not silently turn malformed filters into an unrestricted query.

An invalid filter configuration must never result in:

```
filters = []
```

and accidentally mean "return all records".

This is a critical production safety invariant.

---

## 23. Security boundary

The frontend adapter must never be treated as a security boundary.

It can validate structure for UX, but:

- permissions;
- field permissions;
- DocType permissions;
- `ignore_permissions`;
- query safety;
- Frappe capability compatibility

remain backend responsibilities.

The backend must validate and enforce them regardless of what the Vue UI sends.

---

## 24. Migration strategy

Because FlexiRule is pre-RC and backward compatibility is not a major constraint, do not introduce a complicated migration framework.

Recommended approach:

### Phase 1

Keep current accepted payloads.

### Phase 2

Introduce the adapter and normalize input.

### Phase 3

Make the adapter the sole serializer.

### Phase 4

Remove duplicate serialization code from QueryFilterTree.

### Phase 5

Add focused tests.

If a legacy representation is no longer needed before RC, it may be removed rather than permanently supported.

---

## 25. Implementation phases

### Phase A — Contract inventory

Before changing code:

- inventory every current filter payload shape;
- inspect Fetch Records backend parsing;
- inspect `frappe.qb.get_query` invocation;
- inventory tests;
- document supported logical nesting;
- document 3-part vs 4-part leaf forms;
- document FlexValue handling.

**Deliverable:** one canonical serialization contract.

### Phase B — Adapter

Create the pure adapter.

Implement:

- normalize;
- create leaf/group;
- deserialize;
- serialize;
- validate.

No UI redesign.

### Phase C — QueryFilterTree integration

Replace local parsing/serialization logic with adapter calls.

Keep TreeBuilder unchanged.

### Phase D — Validation integration

Ensure incomplete UI nodes are allowed during editing but cannot become executable filters.

### Phase E — Regression tests

Add adapter tests and QueryFilterTree-focused tests.

### Phase F — Full Fetch Records validation

Verify complete configuration behavior:

```
Filters
Fields
Order By
Group By
Limit
Offset
Distinct
```

including combinations.

### Phase G — CI

Run:

- frontend lint;
- frontend build;
- relevant unit tests;
- existing backend Fetch Records tests;
- full application test suite if CI capacity permits.

---

## 26. Definition of done

The implementation is production-ready when all of the following are true:

- TreeBuilder remains backend-agnostic.
- FilterLeaf remains optimized for interactive editing.
- One adapter owns filter serialization/deserialization.
- No duplicate filter serialization exists in FetchRecordsConfig.
- Nested AND/OR semantics are preserved.
- UI-only IDs never reach the backend.
- FlexValue structures are preserved.
- Link and child-table field paths remain exact backend references.
- Invalid filters cannot silently become an unrestricted query.
- Backend permission enforcement remains backend-only.
- Frappe compatibility remains backend-only.
- Adapter unit tests cover every supported filter shape.
- Existing Fetch Records tests remain green.
- Frontend lint/build pass.
- No backend query behavior is changed as part of the frontend adapter refactor unless a separate backend requirement is explicitly identified.

---

## 27. Recommended final ownership model

| Responsibility | Component / Layer |
|---|---|
| Interactive tree | TreeBuilder |
| Recursive node rendering | TreeBuilderNode |
| Filter field/operator/value editor | FilterGroup / FilterLeaf UI |
| Filter UI state | QueryFilterTree |
| Tree ↔ backend conversion | Filter Tree Adapter |
| Complete action configuration | FetchRecordsConfig |
| Query execution | Fetch Records backend |
| Frappe API/version compatibility | `frappe_query_compat.py` |
| Permissions/security | Backend / Frappe |

The key design rule is:

> **The TreeBuilder should model the user's intent as a tree. The adapter should model how that intent is serialized for the backend. Neither side should be forced to become the other.**

---

### 27. Recommended final ownership model

The ownership model should explicitly reflect the FilterLeaf extraction and stable navigation state:

| Responsibility | Component / Layer |
|---|---|
| Interactive tree | TreeBuilder |
| Recursive node rendering | TreeBuilderNode |
| One filter leaf editor | FilterLeaf |
| Field navigation for one leaf | FilterLeaf → useNavigableFields |
| Field picker UI | ComboBoxControl |
| Legacy flat filter collection | FilterGroup, only where still required |
| Filter UI tree integration | QueryFilterTree |
| Tree ↔ backend conversion | Filter Tree Adapter |
| Complete action configuration | FetchRecordsConfig |
| Query execution | Fetch Records backend |
| Frappe API/version compatibility | `frappe_query_compat.py` |
| Permissions/security | Backend / Frappe |

`FilterGroup.vue` must not become a second navigation implementation. The long-term Query Filter Tree path should use `FilterLeaf.vue` for individual filter editing and stable navigation state.

### 27.1 Migration sequence for FilterGroup → FilterLeaf

Do not rewrite all filter behavior at once. Extract incrementally:

1. Preserve the existing row data shape and operator/value behavior.
2. Move one complete filter row into `FilterLeaf.vue`.
3. Move the field picker and its navigation behavior with the row.
4. Replace index-based navigation state with one `useNavigableFields()` instance per leaf.
5. Verify Link and child-table navigation.
6. Switch QueryFilterTree to render `FilterLeaf.vue` through the existing tree structure.
7. Keep `FilterGroup.vue` available for legacy consumers until repository-wide usage confirms it is no longer required.
8. Remove duplicated field-discovery/navigation code only after all consumers have migrated.

This staged approach prevents the UI extraction from becoming a simultaneous query-contract refactor.

### 28. Explicit non-goals

## 28. Explicit non-goals

This implementation must not:

- rewrite TreeBuilder around backend arrays;
- make FilterLeaf know about `frappe.qb`;
- duplicate Frappe's query parser in JavaScript;
- introduce a second query language;
- move permission logic to the frontend;
- resolve variables/resolvers in the frontend adapter;
- redesign Fields/Order By/Group By as part of the filter adapter;
- change the backend compatibility layer merely to accommodate the UI.

This plan is specifically a **filter-tree representation and boundary refactor**.
\n\n---\n\n# Consolidated source 4: reports/query-records/frappe-qb-capabilities-and-limits-report.md\n\n> Original report content follows. Preserved without rewriting so findings, evidence, caveats, and historical context remain attributable to their source.\n\n# Frappe Query Builder (`frappe.qb.get_query`) Evidence-Based Audit & Capabilities Report

## Executive Summary
This report records source-level and empirical observations about Frappe v15's native Query Builder (`frappe.qb.get_query` / `Engine.get_query`) and FlexiRule's **Fetch Records** integration (`QueryRecordsHandler._fetch_records`). The capability probes and FlexiRule integration tests are separate evidence categories: a native QB capability passing does not prove the FlexiRule adapter preserves the input or produces correct results.

The seven dedicated modules below define 39 test methods. The latest CI runs for the reviewed head completed successfully. This confirms the repository's CI workflow passed for that commit; it does not by itself prove every listed edge case is covered. See the verification status below. Test modules:
1. `test_qb_field_path_capabilities.py` (5 tests) - Reuses installed `Rule`, `Rule Action`, `Process` DocTypes
2. `test_qb_operator_capabilities.py` (6 tests) - Reuses installed `Rule` DocType
3. `test_qb_tree_capabilities.py` (5 tests) - Retains dedicated `QB Tree Node <RUN_ID>` DocType (Tree DocType required)
4. `test_qb_fieldtype_value_matrix.py` (3 tests) - Reuses installed `Rule`, `Data Review Task` DocTypes & retains `QB Matrix Temp <RUN_ID>` fixture for `Date`/`Currency`
5. `test_fetch_records_normalization.py` (4 tests) - Direct unit tests for `QueryRecordsHandler`
6. `test_fetch_records_filter_tree_integration.py` (3 tests) - Reuses installed `Rule` DocType
7. `test_fetch_records.py` (13 tests) - Reuses installed `Rule` & `Rule Action` DocTypes

---

## 1. Environment & Execution Context
- **Frappe Version**: Frappe v15.121.1 (`apps/frappe`)
- **Database Backend**: MariaDB / MySQL (InnoDB engine on `test_site`)
- **Test Site**: `test_site` (`/home/jules/frappe-bench`)
- **Test Command**: `bench --site test_site run-tests --app flexirule --module flexirule.ruleflow.tests.<module_name>`
- **Dedicated module inventory**: 39 test methods across the seven listed modules. **Latest verified CI status for this report revision**: Server CI and Linters completed successfully. The earlier failed run below is historical and was superseded by the successful runs for the updated head.

### CI verification history — 2026-10-09

- **Latest Linters run:** [GitHub Actions run 37973964439](https://github.com/Sendipad/flexirule/actions/runs/37973964439) — completed successfully; Frappe Linter and Vulnerable Dependency Check both passed.
- **Latest CI run:** [GitHub Actions run 37973964507](https://github.com/Sendipad/flexirule/actions/runs/37973964507) — completed successfully; Server and changes jobs passed. Frontend was skipped by the workflow's path filtering.
- **Superseded failed run:** [run 37971338723](https://github.com/Sendipad/flexirule/actions/runs/37971338723) failed with 10 failures, 1 error, and 2 skipped. Do not describe that older result as the current CI status.
- **Interpretation:** the updated head has green CI. CI success is evidence that the configured workflow passed, but it does not automatically prove coverage of edge cases not exercised by assertions.
- **Scope caution:** at the reviewed source snapshot, `query_records.py` recursively resolves the whole filter payload and falls back to `_normalize_filters_for_backend()` for non-canonical lists/dicts. Compare this implementation with the intended canonical-tree-only contract for Fetch Records; preserve legacy normalization for established Query Records modes without routing the new mode through a legacy fallback.

---

## 2. Test Safety, Fixture Isolation & Zero Deletion-on-Collision Architecture
To guarantee that running tests never delete pre-existing site data, DocTypes, or shared records:
- **Reuse Installed FlexiRule DocTypes**:
  - `Rule`, `Rule Action`, `Process`, and `Data Review Task` are reused across operator capability, filter tree integration, field path capability, and value matrix tests.
  - Reused fields include `rule_name`, `is_active`, `execution_mode`, `priority`, `max_execution_time`, `description`, `resolved_on`, `actions.action_id`, and `process_name.description`.
- **Justified Dedicated Fixtures**:
  - `QB Tree Node <RUN_ID>`: Retained as a uniquely named per-run test DocType because no installed FlexiRule DocType has `is_tree: 1` required to test tree hierarchy operators (`descendants of`, `ancestors of`, etc.).
  - `QB Matrix Temp <RUN_ID>`: Retained as a uniquely named per-run test DocType strictly to cover `Date` and `Currency` fieldtypes not present on installed FlexiRule DocTypes.
- **Zero Deletion-on-Collision & Explicit Ownership Tracking**:
  - Setup-time deletions (`frappe.delete_doc` / `frappe.db.delete` on pre-existing records) have been completely eliminated.
  - Each test run generates a unique hex suffix (`_run_id = uuid.uuid4().hex[:8].upper()`) for its test documents and dedicated DocTypes.
  - If a document or DocType with the generated test name unexpectedly already exists, the test fails fast (`RuntimeError`) rather than silently deleting or reusing pre-existing site data.
  - Queries match test data using explicit created document name lists (`["rule_name", "in", [name1, name2, ...]]`) rather than fuzzy SQL `LIKE` wildcards with `_`.
  - `tearDownClass` deletes ONLY test-owned records and test-created DocTypes in reverse creation order, preserving pre-existing site records and shared metadata.

---

## 3. Comprehensive Capability & Operator Audit

### A. Comparison Operators (`=`, `!=`, `>`, `>=`, `<`, `<=`)
- **Native Frappe Status**: **Supported (Source-confirmed & Empirically verified)**.
- **Tested Field Types**: Data, Int, Float, Currency, Date, Datetime, Check / Boolean.
- **Operand Representations**:
  - Native Python values (`10`, `3.14159`, `datetime.date(2026, 3, 1)`, `datetime.datetime(...)`, `True`, `False`).
  - Numeric strings (`"42"`, `"50.00"`), ISO date strings (`"2026-03-01"`), and ISO datetime strings (`"2026-03-15 00:00:00"`).
  - Boundary values: Negative integers (`-10`), negative floats (`-0.5`), zero (`0`), and fractional seconds (`2026-03-31 23:59:59.999999`).

### B. Pattern Matching Operators (`like`, `not like`, `starts with`, `ends with`)
- **Wildcard Supply Contract & Double-Wildcarding**:
  1. **Native `like`**: Expects the **caller** to supply wildcards (`%` or `_`). Plain strings without wildcards execute an exact SQL match.
  2. **Native `not like`**: Expects caller-supplied wildcards. Records with `SQL NULL` values in the field are omitted from results due to SQL tri-state logic.
  3. **FlexiRule `starts with` & Characterization Note**:
     - `QueryRecordsHandler._normalize_single_filter_operator` automatically appends `%` to the operand string (`val` -> `val%`).
     - **Observed Behavior**: If an input string is already wildcarded (e.g. `"Test%"`), `starts with` currently produces `"Test%%"`. This observed implementation behavior is documented in characterization test `test_01_ui_operator_normalization` in `test_fetch_records_normalization.py`. Production code remains unchanged in this test refactoring task. If wildcard sanitization/trimming is desired, it should be addressed in a separate focused change.
  4. **FlexiRule `ends with`**: Automatically prepends `%` to the operand string (`val` -> `%val`).

### C. Set Membership (`in` and `not in`)
- **Native Frappe Status**: **Supported (Source-confirmed & Empirically verified)**.
- **List / Sequence Handling**:
  - Lists of native values (`[10, 20]`) and strings.
  - Comma-separated strings (`"CODE_A,CODE_B"`): Natively split by `frappe.database.operator_map.func_in` into `['CODE_A', 'CODE_B']`.
  - Empty lists (`[]`): Natively converted by `Engine._apply_filter` to `("",)`, returning 0 records safely without raising SQL syntax errors.

### D. Range Operators (`between` and `not between`)
- **Native Frappe Status**: **Supported (Source-confirmed & Empirically verified)**.
- **Boundary Inclusivity**: Natively inclusive on both lower and upper bounds (`start <= field <= end`).
- **Date & Datetime Range Semantics**:
  - Tested with ISO Date strings (`["2026-03-01", "2026-03-31"]`) and Datetime strings with microsecond precision (`["2026-03-01 00:00:00", "2026-03-31 23:59:59.999999"]`).
  - FlexiRule `_coerce_between_value` accepts 2-element lists, tuples, comma-separated strings `"start, end"`, and falls back to `(val, val)` for single strings (treating it as a single-day range).

### E. Check / Boolean Coercion
- **Native Frappe Status**: **Supported (Source-confirmed & Empirically verified)**.
- **Boolean Handling**:
  - Python `True` / `False` are converted by `Engine._apply_filter` to integer `1` / `0`.
  - Numeric integers `1` / `0` and numeric strings `'1'` / `'0'` match stored database integer values.
- **FlexiRule Value Coercion (`_extract_filter_value_payload`)**:
  - When wrapped in structured UI dicts with `value_type: "boolean"`, inputs `True`, `1`, `"1"`, `"Yes"`, `"yes"`, `"true"`, `"True"` resolve to `1`.
  - Inputs `False`, `0`, `"0"`, `"No"`, `"no"`, `"false"`, `"False"` resolve to `0`.
  - Plain un-wrapped string variants (e.g. `"true"`) pass through uncoerced to the database.

---

## 4. Complete Coverage Matrix

| Path / Operator | Native Frappe | FlexiRule Normalization | Failure Stage / Notes |
| :--- | :--- | :--- | :--- |
| `field` | **Supported** | Direct | Selected on root table |
| `process_name.description` | **Supported** | Direct | Dynamic `LEFT JOIN` on Level 1 table (`Rule Action` -> `Process`) |
| `link1.link2.field` | **Unsupported** | None | `ValueError: too many values to unpack (expected 2)` in `DynamicTableField.parse` |
| `actions.action_id` | **Supported** | Direct | Dynamic `LEFT JOIN` on child table (`Rule` -> `Rule Action`) |
| `actions.process_name.description` | **Unsupported** | None | `ValueError: too many values to unpack (expected 2)` in `DynamicTableField.parse` |
| `=`, `!=`, `>`, `>=`, `<`, `<=` | **Supported** | Direct | Executed via PyPika comparison |
| `like`, `not like` | **Supported** | Direct | Executed with `%` and `_` wildcards; SQL NULLs excluded under `not like` |
| `in`, `not in` | **Supported** | Direct | Comma-strings split; empty lists converted to `("",)` |
| `is set`, `is not set` | **Supported** | Direct | Matches NULL and empty string `""` |
| `descendants of` | **Supported** | Direct | Evaluates Tree DocType `lft` and `rgt` on `QB Tree Node <RUN_ID>` |
| `ancestors of` | **Supported** | Direct | Evaluates Tree DocType `lft` and `rgt` on `QB Tree Node <RUN_ID>` |
| `starts with` / `ends with` | Unsupported | Normalized | Converted to `like "val%"` / `like "%val"` (see double-wildcarding note) |
| `Between` / `Timespan` | Unsupported | Normalized | Coerced to `between [start, end]` |

---

## 5. Summary & Release Recommendations
1. **Fixture isolation**: the inspected dedicated fixtures use run-specific names and track created records. This is a source review of cleanup behavior, not a claim that the latest CI run passed; keep test-owned-resource cleanup paired with fail-fast collision checks.
2. **Dotted Path UI Depth**: UI ComboBox controls for Fetch Records should constrain dotted field navigation to 1 link level or direct child table level, as >1 level dotted chains trigger `ValueError: too many values to unpack` in `frappe.qb.get_query`.
3. **Double Wildcarding**: Users configuring `starts with` in FlexiRule who manually enter a `%` suffix will produce `%%`. A separate focused change may be considered if wildcard sanitization is desired.
4. **Child Table Link Fields**: Traversing link fields within child tables (e.g. `actions.process_name.description`) is natively unsupported by `frappe.qb.get_query`. Direct child queries or multi-action sub-queries should be recommended for child link references.
\n\n---\n\n# Consolidated source 5: reports/query-records/frappe-qb-v15-capability-audit.md\n\n> Original report content follows. Preserved without rewriting so findings, evidence, caveats, and historical context remain attributable to their source.\n\n# Frappe v15 `frappe.qb.get_query` Architectural Capability Audit Report

## Executive Summary

This report separates three evidence categories that must not be conflated:

1. **Native Frappe Query Builder characterization** — observations about the installed Frappe v15 `frappe.qb.get_query()` API and its SQL/runtime behavior. These characterize Frappe, not the correctness of FlexiRule's adapter.
2. **Fetch Records integration evidence** — on commit 693971455c0752f45879cee82e91c635a2e07a27, both configured PR workflows (CI run 38182490923 and Linters run 38182491032) completed successfully. That CI workflow temporarily pinned esbuild for its two standalone frontend tests; .github/workflows/ci.yml was then restored in commit 47e4b5713c9b2e7dcf99a0d89cffc7478a9d8906, so the restored workflow's rerun is the evidence for the current head. CI success applies only to the exact commit and workflow definition that ran.
3. **Existing-mode legacy regression tests** — `test_query_records_filters.py` also covers legacy tuple/list/dict normalization and established Query Records modes. Keep those compatibility guarantees separate from Fetch Records' new persisted contract.

**Contract discrepancy at the reviewed head:** the intended Fetch Records contract is canonical `group`/`leaf` tree only, but `query_records.py` currently recursively calls `resolve_payload()` on the entire filter object and then invokes `_normalize_filters_for_backend()` for non-canonical list/dict filters. In addition, `test_03_legacy_tuple_and_list_filter_shapes` in `test_fetch_records_filter_tree_integration.py` explicitly expects Fetch Records to accept legacy filters. Both the implementation and that test conflict with the intended strict contract. Legacy normalization should remain available to established modes such as Query List/Get List; Fetch Records should validate and convert only canonical trees.

****CI evidence:** [CI run 38182490923](https://github.com/Sendipad/flexirule/actions/runs/38182490923) and [Linters run 38182491032](https://github.com/Sendipad/flexirule/actions/runs/38182491032) passed on commit 693971455c0752f45879cee82e91c635a2e07a27. Because .github/workflows/ci.yml was subsequently restored, verify the new head's runs before treating the restored workflow as green.

---

## 1. Installed Environment Specifications

* **Frappe Version:** `15.121.1`
* **Frappe Repository Commit:** `8f801ade016078685c3165c96e38f84f249f5309` (branch: `version-15`)
* **Python Version:** `3.12.13`
* **Database Engine:** `MariaDB`
* **Database Version:** `10.11.14-MariaDB-0ubuntu0.24.04.1`
* **Query Builder Implementation Files:**
  * `frappe/query_builder/utils.py` (Defines `get_query()` entry point, `PseudoColumnMapper`, and patches `run()` / `walk()`)
  * `frappe/database/query.py` (Defines `Engine`, `Permission`, `ChildQuery`, `DynamicTableField`, `parse_fields`, `apply_filters`)
  * `frappe/database/operator_map.py` (Defines operator mappings including `NestedSetHierarchy`, `is`, `between`, `timespan`)
  * `frappe/utils/nestedset.py` (Implements `get_ancestors_of`, `get_descendants_of`, `rebuild_tree` for tree hierarchy evaluation)
  * `frappe/query_builder/builder.py` (Database-specific builder overrides for MariaDB & Postgres)

---

## 2. Detailed Capability Audit Findings by Category

### 2.1 Basic Query & Fields Selection
* **`frappe.qb.get_query("DocType")`**: Generates `SELECT name FROM tabDocType`. Omitting fields defaults selection to `name`.
* **Explicit Fields (`fields=["name", "status"]`)**: Generates `SELECT name, status FROM tabDocType`. Returns list of dictionaries with matching keys.
* **Comma-Separated Fields (`fields="name, status"`)**: Supported. `Engine.parse_fields` splits comma-separated string paths.
* **Wildcard (`fields="*"`)**: Generates `SELECT * FROM tabDocType` selecting all table columns.
* **Aliases (`fields=["name as doc_id"]`)**: Generates `SELECT name doc_id FROM tabDocType`. Returned dictionary keys match the alias name (`doc_id`).

### 2.2 Execution Modes & Iterator Support
* **`query.run(as_dict=True)`**: Returns list of dictionaries.
* **`query.run(as_list=True)`**: Returns tuple/list of row tuples.
* **`query.run(pluck=True)`**: Returns a flat list of scalar values for a single selected column.
* **Iterator Execution (`query.run(as_iterator=True)`)**: **SUPPORTED.** Returns a Python generator object (`<class 'generator'>`).
  * `query.run(as_dict=True, as_iterator=True)` yields row dictionaries item-by-item during iteration.
  * `query.run(as_list=True, as_iterator=True)` yields row lists item-by-item during iteration.
  * Completely consumed during test execution with exact row count and dictionary key validation (`{P1, P2, P3}`).

### 2.3 Filter Syntax, Null/Set Operators & Complex Logical OR/AND
* **Dict Equality (`filters={"status": "Open"}`)**: Generates `WHERE status = 'Open'`.
* **Dict Operator (`filters={"qty": [">", 0]}`)**: Generates `WHERE qty > 0`.
* **List Form (`filters=[["status", "=", "Open"]]`)**: Generates `WHERE status = 'Open'`.
* **Null / Set Operators (`is set` / `is not set`)**:
  * Tested on `nullable_text` field (`P1 = "A"`, `P2 = None`, `P3 = "C"`).
  * `filters=[["nullable_text", "is", "set"]]` generates `WHERE nullable_text != ''` and returns exactly `{P1, P3}`.
  * `filters=[["nullable_text", "is", "not set"]]` generates `WHERE nullable_text IS NULL OR nullable_text = ''` and returns exactly `{P2}`.
* **Infix String `"or"` in List Filters (`filters=[["status", "=", "Open"], "or", ["status", "=", "Pending"]]`)**: **UNSUPPORTED / BROKEN.** `Engine.apply_filters` loops through list elements and converts string `"or"` into `{"name": "or"}`, producing `WHERE name = 'or'`, which yields 0 records.
* **Nested Logical Structures via Pypika `Criterion`**: **SUPPORTED.**
  * `((t.status == "Open") & (t.enabled == 1)) | ((t.status == "Pending") & (t.enabled == 1))` generates `WHERE (status='Open' AND enabled=1) OR (status='Pending' AND enabled=1)` and returns `{P1, P2}`.
  * `(t.status == "Open") & ((t.enabled == 1) | (t.status == "Pending"))` generates `WHERE status='Open' AND (enabled=1 OR status='Pending')` and returns `{P1}`.

### 2.4 Filter Operators & Tree Operators
* **Standard Comparison Operators (`=`, `!=`, `>`, `<`, `>=`, `<=`, `like`, `not like`, `in`, `not in`)**: Fully supported and verified against exact record sets.
* **Tree / Nested Set Operators (`descendants of`, `ancestors of`, `not descendants of`, `not ancestors of`)**: **SUPPORTED on `is_tree=1` DocTypes.**
  * `Engine._apply_filter` checks `_operator.casefold() in OPERATOR_MAP["nested_set"]` (`NestedSetHierarchy`), calling `get_nested_set_hierarchy_result(ref_doctype, docname, hierarchy)`.
  * `filters=[["name", "descendants of", root_name]]` on `QB Test Tree` generates `WHERE name IN ('Child A', 'Grandchild A', 'Child B')` and returns all descendant nodes.
  * `filters=[["name", "ancestors of", grandchild_name]]` generates `WHERE name IN ('Child A', 'Root')` and returns ancestor nodes.
  * Applying tree operators to a non-tree DocType or non-existent document node raises a `KeyError` or returns empty node tuples.

### 2.5 Link-Field Traversal & Ordering
* **Selecting Dotted Linked Fields (`fields=["name", "target_link.territory", "category_link.group_code"]`)**: Fully supported. Automatically generates multiple `LEFT JOIN` clauses (`tabQB Test Target`, `tabQB Test Category`).
* **Filtering Dotted Linked Fields (`filters={"target_link.territory": "North"}`)**: Fully supported.
* **Dotted Path `order_by="target_link.territory asc"`**: **UNSUPPORTED in string parser.** `Engine.apply_order_by` splits string by comma and prepends table name without resolving join alias, generating `ORDER BY tabQB Test Parent.target_link.territory ASC`, which raises `pymysql.err.OperationalError: Unknown column`.
* **Pypika Join & Ordering**: **SUPPORTED.** Explicitly joining tables and ordering via `orderby(target_table.territory)` generates `ORDER BY tabQB Test Target.territory` and executes successfully.

### 2.6 Child Table Traversal vs. Structured Child Fetching
* **Flat Child Traversal (`fields=["name", "items.item_code"]`)**: Generates `LEFT JOIN tabQB Test Child ON ...`. Duplicates parent rows in the result set for every matching child record (3 rows for parent `P1` with 3 items).
* **Structured Child Fetching (`fields=["name", {"items": ["item_code", "qty"]}]`)**: **SUPPORTED.** Returns distinct parent row dictionaries (`len = 3`). `Engine` instantiates a `ChildQuery` object for `items`, executes a secondary query against `tabQB Test Child`, and embeds child dict lists directly into each parent dictionary (`row["items"] = [...]`).
* **Distinct Parent Deduplication (`distinct=True`)**:
  * For flat query selecting only parent fields (`fields=["name"]`, `filters={"items.item_code": "ITEM-001"}`), `distinct=True` generates `SELECT DISTINCT name FROM ...` and deduplicates parent rows (`{P1, P2}`).
  * If child fields are in SELECT (`fields=["name", "items.item_code"]`), `distinct=True` cannot deduplicate parent rows because distinct applies to the entire row tuple `(name, item_code)`.

### 2.7 Child DocType as Root Query & `parent_doctype`
* **Direct Child Query (`frappe.qb.get_query("QB Test Child")`)**: Fully supported. Generates `SELECT name, item_code, parent, parenttype, parentfield FROM tabQB Test Child`.
* **Filtering Child DocType by Parent Context**: Fully supported using `filters=[["parent", "=", parent_name], ["parenttype", "=", "QB Test Parent"]]`.
* **`parent_doctype` Argument (`frappe.qb.get_query("QB Test Child", parent_doctype="QB Test Parent")`)**: **UNSUPPORTED on `get_query()`.** Raises `TypeError: Engine.get_query() got an unexpected keyword argument 'parent_doctype'`.
* **Permission Enforcement for Child DocTypes**: `parent_doctype` is an argument for permission checks (`Permission.check_permissions(query, parent_doctype="...")` or `frappe.has_permission("QB Test Child", parent_doctype="...")`), not a query builder parameter.

### 2.8 Aggregation & Scalar Functions
* **Documented Dict Aggregation / Scalar Syntax (`fields=[{"COUNT": "name"}]` / `fields=[{"IFNULL": ...}]`)**: **UNSUPPORTED.** `Engine.parse_fields` interprets dictionary objects in `fields` as child table queries (`ChildQuery`). It looks up table field `"COUNT"`, raising `AttributeError: 'NoneType' object has no attribute 'fieldtype'`.
* **Raw String Functions (`fields=["count(name) as total_count"]`)**: Supported for standard SQL functions.
* **Child Dotted Aggregation String (`fields=["sum(items.qty)"]`)**: **UNSUPPORTED.** `Engine.parse_fields` does not trigger automatic child table JOINs when dotted paths are inside raw function strings, raising `OperationalError: Unknown column 'items.qty'`.
* **Pypika Aggregation & Scalar Objects (`Count()`, `Sum()`, `Avg()`, `Min()`, `Max()`, `Now()`, `Coalesce()`, `Concat()`, `Abs()`, `Extract()`)**:
  * Pypika function objects in `fields` generate valid SQL expressions.
  * Pypika explicit child join (`frappe.qb.from_(parent).left_join(child)...`) calculates child `Sum(child.qty)` accurately (`total_qty = 10.0` for `P1`).
  * `Coalesce(PseudoColumnMapper('\`tabQB Test Parent\`.\`target_link\`'), "'None'")` evaluates NULL values properly. Un-table-qualified string column names in function objects cause `PseudoColumnMapper` to treat them as string literals `'target_link'` due to column name resolution rules.

### 2.9 Record Locking
* **`for_update=True`, `skip_locked=True`, `wait=False`**: **SUPPORTED in transaction.**
  * `for_update=True, skip_locked=True` generates `FOR UPDATE SKIP LOCKED`.
  * `for_update=True, wait=False` generates `FOR UPDATE NOWAIT`.
  * Executed inside active transaction (`frappe.db.begin() ... frappe.db.rollback()`).

### 2.10 Permissions & User Context
* **`ignore_permissions=True` / `user="..."` as `get_query()` kwargs**: **UNSUPPORTED.** Raises `TypeError: Engine.get_query() got an unexpected keyword argument`.
* **Permission Checking**: `frappe.qb.get_query()` is strictly a SQL builder. Permission checking is performed via `frappe.database.query.Permission.check_permissions(query, user=user)`.

---

## 3. Evidence-Hardened Capability Matrix

| Capability | Input / API Form | SQL Generation | Execution | Semantic Verification | Status | Root Cause / Exact Limitation |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Basic Query** | `get_query("DocType")` | `SELECT name FROM tab` | Success | Returns default `name` | **SUPPORTED** | None |
| **Explicit Fields** | `fields=["a", "b"]` | `SELECT a, b FROM tab` | Success | Returns dicts with `a`, `b` | **SUPPORTED** | None |
| **Comma Fields** | `fields="a, b"` | `SELECT a, b FROM tab` | Success | Splits string into fields | **SUPPORTED** | None |
| **Wildcard Fields**| `fields="*"` | `SELECT * FROM tab` | Success | Returns all schema columns | **SUPPORTED** | None |
| **Field Aliases** | `fields=["a as foo"]` | `SELECT a foo FROM tab` | Success | Returned dict has key `foo` | **SUPPORTED** | None |
| **`as_dict=True`** | `query.run(as_dict=True)` | Native SQL | Success | Returns list of dicts | **SUPPORTED** | None |
| **`as_list=True`** | `query.run(as_list=True)` | Native SQL | Success | Returns list of tuples | **SUPPORTED** | None |
| **`pluck=True`** | `query.run(pluck=True)` | Native SQL | Success | Returns flat value list | **SUPPORTED** | Requires single field |
| **`as_iterator=True`**| `query.run(as_iterator=True)`| Unbuffered SQL | Success | Returns generator yields | **SUPPORTED** | Python generator object |
| **Dict Filters** | `filters={"a": "b"}` | `WHERE a = 'b'` | Success | Exact record set | **SUPPORTED** | None |
| **Dict Op Filters**| `filters={"a": [">", 0]}`| `WHERE a > 0` | Success | Exact record set | **SUPPORTED** | None |
| **List Filters** | `filters=[["a", "=", "b"]]`| `WHERE a = 'b'` | Success | Exact record set | **SUPPORTED** | None |
| **`is set` / `is not set`**| `filters=[["col", "is", "set"]]`| `WHERE col != ''` / `IS NULL`| Success | `{P1, P3}` / `{P2}` | **SUPPORTED** | Semantic null check verified |
| **Infix String OR** | `filters=[..., "or", ...]`| `WHERE name = 'or'` | Success | Returns 0 records | **BROKEN** | `Engine.apply_filters` converts string `"or"` to `{"name": "or"}` |
| **Pypika OR** | `filters=(t.a==1)\|(t.b==2)`| `WHERE (a=1) OR (b=2)`| Success | Exact record set | **SUPPORTED** | Pypika Criterion |
| **Tree Operators** | `filters=[["a", "descendants of", root]]` | `WHERE name IN (...)` | Success | Descendants/Ancestors | **SUPPORTED** | Requires `is_tree=1` DocType |
| **Link Field Select**| `fields=["link.col"]` | `LEFT JOIN tabTarget` | Success | Joined column value | **SUPPORTED** | Auto LEFT JOIN |
| **Link Field Filter**| `filters={"link.col": "v"}`| `WHERE tabTarget.col = v`| Success | Filtered on joined table | **SUPPORTED** | Auto LEFT JOIN |
| **Link String Order**| `order_by="link.col asc"`| `ORDER BY tabParent.link.col`| OperationalError | Unknown column error | **UNSUPPORTED** | `Engine.apply_order_by` string parser unmapped alias |
| **Pypika Link Order**| `.left_join().orderby()`| `ORDER BY tabTarget.col`| Success | Ordered by joined field | **SUPPORTED** | Pypika explicit join |
| **Child Dotted Select**| `fields=["items.col"]` | `LEFT JOIN tabChild` | Success | Duplicates parent rows | **SUPPORTED** | Relational 1:N join |
| **Child Dotted Filter**| `filters={"items.col": "v"}`| `WHERE tabChild.col = v`| Success | Filters on child field | **SUPPORTED** | Relational 1:N join |
| **Structured Child** | `fields=[{"items": ["a"]}]`| `SELECT parent` (Sub-query) | Success | `row["items"] = [...]` dicts | **SUPPORTED** | `ChildQuery` sub-query per parent |
| **Distinct Parent** | `distinct=True` | `SELECT DISTINCT name` | Success | Deduplicates parent rows | **SUPPORTED** | Only when parent fields selected |
| **Child Root Query** | `get_query("Child DocType")`| `FROM tabChild` | Success | Returns child records | **SUPPORTED** | Includes parent, parenttype, parentfield |
| **`parent_doctype`**| `get_query(..., parent_doctype="...")`| N/A | TypeError | Kwarg rejected | **UNSUPPORTED** | Not in `Engine.get_query` signature |
| **Dict Aggregation**| `fields=[{"COUNT": "a"}]`| N/A | AttributeError | Interp. as child query | **UNSUPPORTED** | Dict in fields reserved for `ChildQuery` |
| **String Function** | `fields=["count(a) as x"]`| `SELECT COUNT(a) x` | Success | Calculated aggregate | **SUPPORTED** | Standard SQL string expression |
| **Pypika Functions**| `fields=[Count(t.a)]` | `SELECT COUNT(a)` | Success | Calculated aggregate | **SUPPORTED** | Pypika function object |
| **Dotted Child Sum** | `fields=["sum(items.qty)"]`| N/A | OperationalError | Unknown column error | **UNSUPPORTED** | `Engine` string parser fails child join for functions |
| **Pypika Child Sum**| `.left_join().select(Sum())`| `SELECT SUM(tabChild.qty)`| Success | Exact child sum | **SUPPORTED** | Pypika explicit join |
| **Pypika Now()** | `fields=[Now()]` | `SELECT NOW()` | Success | `datetime.datetime` | **SUPPORTED** | Pypika function object |
| **Pypika Coalesce** | `fields=[Coalesce(col, v)]`| `SELECT COALESCE(col, v)`| Success | Safe fallback value | **SUPPORTED** | Requires `PseudoColumnMapper` column term |
| **Order By / Group By**| `order_by="..."`, `group_by="..."`| `ORDER BY ... GROUP BY ...`| Success | Ordered & grouped | **SUPPORTED** | Standard fields |
| **Pagination** | `limit=10, offset=10` | `LIMIT 10 OFFSET 10` | Success | Page slice | **SUPPORTED** | None |
| **Record Locking** | `for_update=True, skip_locked=True`| `FOR UPDATE SKIP LOCKED`| Success | Lock acquired | **SUPPORTED** | Requires active transaction |
| **`ignore_permissions`**| `get_query(..., ignore_permissions=True)`| N/A | TypeError | Kwarg rejected | **UNSUPPORTED** | Not in `Engine.get_query` signature |
| **`user` Context** | `get_query(..., user="...")`| N/A | TypeError | Kwarg rejected | **UNSUPPORTED** | Not in `Engine.get_query` signature |
| **Permission Check**| `Permission.check_permissions()`| N/A | Success | Asserts read/select | **SUPPORTED** | Separate permission checker class |

---

## 4. Documentation Mismatches Identified

1. **Dict-Based Aggregation & Scalar Function Syntax Mismatch:**
   * *Documentation hypothesis:* `fields=[{"COUNT": "name", "as": "total"}]` or `fields=[{"IFNULL": ["field", "'val'"]}]`
   * *Installed Frappe v15 reality:* **REJECTED with `AttributeError`.** `Engine.parse_fields` interprets any `dict` element in `fields` as a child table query (`ChildQuery`). Since `"COUNT"` is not a child table field, `field.fieldtype` raises `AttributeError: 'NoneType' object has no attribute 'fieldtype'`.
   * *Correct Working Approach:* Use string function expressions (e.g. `fields=["count(name) as total"]`) or Pypika function objects (`Count()`, `Sum()`, `Now()`).

2. **Infix String `"or"` in List Filters:**
   * *Documentation hypothesis:* `filters=[["status", "=", "Open"], "or", ["status", "=", "Pending"]]`
   * *Installed Frappe v15 reality:* **BROKEN.** `Engine.apply_filters` iterates through list elements and parses string `"or"` as `{"name": "or"}`, resulting in `WHERE name = 'or'`, returning 0 records.
   * *Correct Working Approach:* Compile OR filter conditions into Pypika `Criterion` objects before passing to `get_query(filters=...)`.

3. **`ignore_permissions` & `user` Kwargs on `get_query()`:**
   * *Documentation hypothesis:* `frappe.qb.get_query("DocType", ignore_permissions=True, user="...")`
   * *Installed Frappe v15 reality:* **REJECTED with `TypeError`.** `Engine.get_query()` signature does not accept `ignore_permissions` or `user` kwargs.
   * *Correct Working Approach:* Call `frappe.database.query.Permission.check_permissions(query, user=...)` explicitly.

4. **String-Path `order_by` on Dotted Link Fields:**
   * *Documentation hypothesis:* `order_by="target_link.territory asc"`
   * *Installed Frappe v15 reality:* **REJECTED with `OperationalError`.** `Engine.apply_order_by` splits comma strings and prepends table name without resolving join table aliases.
   * *Correct Working Approach:* Construct explicit Pypika joins (`frappe.qb.from_(parent).left_join(target)...`) and pass `.orderby(target_table.territory)`.

5. **Dotted Child Field Sum in String Expressions:**
   * *Documentation hypothesis:* `fields=["sum(items.qty) as total_qty"]`
   * *Installed Frappe v15 reality:* **REJECTED with `OperationalError`.** `Engine.parse_fields` does not trigger child table joins when dotted paths appear inside function strings.
   * *Correct Working Approach:* Use explicit Pypika child joins with `Sum(child_table.qty)`.

---

## 5. Frappe Capability Findings (Fact-Only)

1. `frappe.qb.get_query()` is a lightweight wrapper that instantiates `frappe.database.query.Engine()` and constructs Pypika query builder objects.
2. `Engine` provides automatic `LEFT JOIN` generation for single-level dotted Link field selections/filters (`target_link.territory`) and dotted Child table selections/filters (`items.item_code`).
3. Dotted string field paths in `order_by` do not resolve join aliases in `Engine.apply_order_by`, raising database `OperationalError`. Explicit Pypika joins resolve this completely.
4. Structured child table retrieval (`fields=["name", {"items": ["item_code", "qty"]}]`) executes separate sub-queries via `ChildQuery` and constructs nested dictionary arrays in parent records without row multiplication.
5. Infix string `"or"` in list filters is broken in `Engine.apply_filters`. Complex AND/OR filter trees must be compiled into Pypika `Criterion` objects.
6. Tree operators (`descendants of`, `ancestors of`) are fully supported by `Engine._apply_filter` via `NestedSetHierarchy` on DocTypes configured with `is_tree=1`.
7. `frappe.qb.get_query()` does not take `ignore_permissions`, `user`, or `parent_doctype` kwargs. Permission enforcement is executed separately via `Permission.check_permissions(query, user=user)`.
8. Iterator execution (`as_iterator=True`) returns a Python generator yielding rows item-by-item for `as_dict=True` and `as_list=True`.

---

## 6. FlexiRule Query Records Architectural Implications

The factual audit findings establish clear contracts for the upcoming FlexiRule Query Records refactor:

1. **Query Field Paths:** Simple parent fields (`status`) and dotted link fields (`customer.customer_group`) can be passed directly as string field paths.
2. **Link Traversal:** Read/select and filter operations on linked DocTypes are natively supported by `frappe.qb.get_query()`.
3. **Child-Table Traversal:** Dotted child fields (`items.item_code`) generate relational 1:N joins in flat queries.
4. **Child DocType as Root Query:** Child DocTypes (`tabSales Order Item`) can be queried directly as root DocTypes. However, linking them to parent context requires filtering on `parent`, `parenttype`, and `parentfield`.
5. **`parent_doctype` Handling:** Do not pass `parent_doctype` as a kwarg to `frappe.qb.get_query()`. Pass `parent_doctype` directly to `Permission.check_permissions` or `frappe.has_permission`.
6. **Filtering:** Standard comparison and pattern operators can be passed as simple list tuples `[field, op, val]`.
7. **Nested AND/OR Compilation:** The FlexiRule Condition/Filter Builder must compile UI filter trees (AND/OR, nested brackets) into native Pypika `Criterion` objects before passing to `get_query(filters=...)`.
8. **Distinct Parent Deduplication:** Query Records actions filtering parent documents via child tables must pass `distinct=True` when selecting parent fields to prevent duplicate parent execution.
9. **Ordering:** Order-by on standard fields can be passed as string paths. Dotted linked field order-by must be compiled into explicit Pypika joins.
10. **Grouping:** Standard `group_by` strings are fully supported.
11. **Aggregation:** Serialize aggregate functions using SQL string expressions (`count(name) as total`) or Pypika function objects (`Count()`, `Sum()`). Do not use dict aggregation syntax.
12. **Structured Child Retrieval:** When Query Records needs to return nested document structures for rule execution context, pass structured dict field specifications (`fields=["name", {"items": ["item_code", "qty"]}]`).
13. **Retrieval Modes:** Support `as_dict=True` for record dicts, `pluck=True` for single-column value lists, and `as_iterator=True` for large batch processing.
14. **Permissions:** Perform permission checks explicitly via `Permission.check_permissions(query, user=rule_user)` in the backend handler.
15. **Pypika Compilation Boundary:** Maintain the explicit architectural boundary:
    `FlexiRule UI Config -> Normalized JSON Specification -> FlexiRule Backend Compiler -> Pypika Criterion / Query -> frappe.qb.get_query() -> MariaDB`.


## 16. Current Review-Fix Test Failure and Remediation (2026-10-11)

The server CI log for the review-fix branch shows:

- Command: bench --site test_site run-tests --app flexirule
- Result: 543 tests run, one error, zero assertion failures, two skipped.
- Error: test_fetch_records_delegates_native_qb_payload_and_permissions raised KeyError: 0 in Frappe's is_virtual_doctype lookup after the test reached frappe.get_list.

Root cause: this test intends to assert the native frappe.qb.get_query payload, but it relied on environment-derived capability detection. On the Frappe v15 CI environment, native ignore_permissions support is absent, so the compatibility layer correctly chose the permission-aware frappe.get_list fallback. The test had mocked QB only, not the fallback path, and therefore unintentionally touched database metadata.

Remediation pushed: the test now stubs QUERY_CAPABILITIES to represent the native-capability scenario and asserts the ignore_permissions=False argument explicitly. Separate compatibility tests continue to cover the v15 fallback. This is intended to make the test deterministic across Frappe versions without weakening production permission handling. Do not mark this item complete until the updated CI rerun passes.


## 17. Latest CI Rerun: Normalized Filter Payload Assertion (2026-10-11)

The server failure was a stale test expectation, not a runtime defect: root-DocType filter leaves are normalized before delegation, so the native frappe.qb.get_query payload uses three-item leaves such as ["enabled", "=", 1] and ["email", "like", "%@example.com"], connected by "or". The test was corrected to assert this payload. Both configured workflows passed on commit 693971455c0752f45879cee82e91c635a2e07a27; the CI workflow was subsequently restored in 47e4b5713c9b2e7dcf99a0d89cffc7478a9d8906, and that restored head still needs its own CI verification.

### Recommendation: keep root-relative QB filters at the adapter boundary

Do not globally remove the root DocType from FlexiRule's persisted filter representation just to mirror Frappe's native QB payload. Keep one stable, explicit Fetch Records filter-tree contract in the UI/configuration layer; validate each leaf against the selected root DocType and any supported link/child path; then normalize root-field leaves to [field, operator, value] only in the Frappe QB adapter. Preserve qualified paths where they carry meaning, and reject ambiguous or unsupported paths rather than silently stripping a prefix. This isolates Frappe-version-specific syntax from saved rules and avoids breaking existing Query Records modes that use legacy filter formats. Add contract tests for persisted tree -> validated internal representation -> QB payload, including root fields, linked/child paths, and literal values equal to "or".


## 18. Independent source review and current acceptance status (2026-10-12)

This section records an independent check of the framework API contracts and the current PR head. It intentionally separates source-level facts from integration behavior that still requires runtime tests.

### Verified framework API facts

- Frappe v15 source: `frappe/database/query.py`, `Engine.get_query` accepts `validate_filters`, `skip_locked`, and `wait` as keyword-only arguments; it does **not** declare `ignore_permissions`. Its `Engine.get_query` builds a Query Builder query and does not itself provide the Frappe 16 permission-aware contract.
- Frappe v16 source: `frappe/database/query.py`, `Engine.get_query` declares `ignore_permissions: bool = True`, `ignore_user_permissions: bool = False`, `user`, `parent_doctype`, `reference_doctype`, and `or_filters`. It sets `self.apply_permissions = not ignore_permissions`. This confirms the permission flag's presence and the direction of its default, but not by itself every field/row permission behavior.
- Frappe v15 boot information populates `bootinfo.versions` from installed app versions, including the `frappe` version. The Fetch Records editor's v15 warning uses this server-provided value and is conditional on both Fetch Records mode and the explicit bypass checkbox.

### Findings matrix

| Requirement | Current assessment | Evidence / remaining proof |
|---|---|---|
| v15 + bypass disabled | Implemented in adapter: uses `frappe.get_list`, with a fail-closed translation for supported filter structures | Source inspection confirms v15 QB lacks the flag. Full integration tests are still needed for row/field permission parity. |
| v15 + bypass enabled | Implemented in adapter: uses QB without passing the unsupported keyword | Requires integration tests proving the action's existing server-side authorization/audit gate and unrestricted results. |
| v16 + bypass disabled | Implemented by native QB delegation with `ignore_permissions=False` when detected | Framework source confirms API support; live Frappe 16 runtime integration remains required. |
| v16 + bypass enabled | Implemented by native QB delegation with `ignore_permissions=True` when detected | Framework source confirms API support; live Frappe 16 runtime integration remains required. |
| Missing/invalid bypass configuration | Existing `can_ignore_permissions` gate returns false for a missing/false flag and requires role authorization plus an audit reason for explicit bypass | Add adversarial handler-level tests for malformed values and verify every execution identity. |
| v15 filter tree | Adapter preserves AND-only trees and one OR group expressible by `filters` + `or_filters`; unsupported OR shapes are rejected | Unit tests cover selected cases. Runtime coverage of operators, linked paths, date values, and empty/null groups is incomplete. |
| Aggregation and field permissions | Root-field aggregates can flow through the permission-aware list path; child/link aggregate expressions are rejected by Fetch Records validation | Do not claim parity for filter/order/group field-level restrictions or all aggregate shapes until tested against both framework versions. |
| UI warning | Added to the Query Records configuration UI; requires Fetch Records mode, Frappe 15 boot version, and enabled bypass | CI/linter run for the warning commit is pending at time of writing. No dedicated component-level behavior test has yet been demonstrated. |

### Upstream Frappe 15 API proposal

The smallest upstream-compatible improvement is to add an explicit, backwards-compatible permission-aware contract to Frappe 15's `frappe.qb.get_query` / `Engine.get_query`:

1. Add keyword-only `ignore_permissions: bool = True` (preserving current unrestricted behavior for existing callers) and, if required for parity, an explicit effective `user` parameter.
2. When `ignore_permissions=False`, apply the framework's existing native permission pipeline to the query before execution: DocType permission, row-level/user permission conditions, ownership and sharing restrictions, permission-query hooks, and permitted-field enforcement for selected fields and fields used by filters, ordering, grouping, and aggregates.
3. Ensure permission constraints are applied **before** aggregation, grouping, distinct selection, limits, and offsets. Do not fetch unrestricted rows and post-filter them.
4. Reuse the established framework permission machinery rather than introduce a second authorization implementation. Keep default behavior backwards-compatible, document which permission dimensions are guaranteed, and add tests for denied DocTypes, hidden rows, User Permissions, shares/ownership, query hooks, restricted fields, aggregates, and explicit user context.
5. Define how native filters and `or_filters` compose, and reject query shapes for which the API cannot preserve semantics.

This is a proposal only; no vendored Frappe source is changed by this PR.

### Verification caveat

The previous head's configured CI and linter workflows passed on `d61e679ada447cdca3cd08db6ad372aa9defd23b`. The warning change was committed afterward, so those earlier green runs do not verify the current head. The full Frappe/MariaDB authorization matrix and both-version integration suite must remain marked pending until the new head's CI and the required runtime tests establish those outcomes.

## 19. Revised release decision — native Query Builder only (2026-10-12)

This section supersedes the earlier recommendation in this report to use `frappe.get_list` as a Frappe 15 permission-aware fallback. After product review, compatibility between Fetch Records' native Query Builder filter tree and Frappe 15 permission enforcement is deferred until after the first production release and discussion with the Frappe team.

### Execution contract for the first production release

- **Fetch Records always executes through `frappe.qb.get_query`.** It does not switch to `frappe.get_list` or `frappe.get_all` based on permission mode. This avoids silently changing field parsing, joins, aggregate behavior, nested boolean semantics, and result shape between framework versions.
- **Frappe 16+ (when the installed `Engine.get_query` signature exposes `ignore_permissions`):** pass the explicit permission flag to the native API. Permission behavior is owned by the installed framework implementation; validate it with integration tests for the exact supported versions.
- **Frappe 15 (no native `ignore_permissions` API parameter):** Fetch Records cannot claim native per-record permission enforcement. The editor enables Skip Permissions by default and locks that setting for Fetch Records on Frappe 15. The backend rejects permission-sensitive Fetch Records calls rather than falling back to a different query API. The existing FlexiRule authorization policy and mandatory audit-reason check remain in force when the bypass is used.
- **Permission-filtered reads on Frappe 15:** use the existing Query List mode (which uses `frappe.get_list`) until the upstream API question is resolved. This is an explicit product boundary, not a compatibility fallback hidden inside Fetch Records.
- **Frappe 15 nested logical filters:** the adapter compiles supported root-DocType leaf groups to native Pypika `Criterion` objects and then calls `frappe.qb.get_query`. It rejects linked/child-field leaves inside those compiled groups rather than altering query meaning. Better parity is deferred, not inferred from this partial compiler.

### API selection and initialization

`detect_query_capabilities()` now inspects only the installed `Engine.get_query` method signature for the explicit `ignore_permissions` parameter, once when the adapter module is imported. Source-text inspection of `Engine.apply_filters` has been removed. A positive match enables passing the native keyword; an uninspectable signature fails closed by treating the permission parameter as unavailable. Fetch Records does not choose `frappe.get_list` as an alternative execution path.

This is a small, local feature-detection boundary based on the public method signature, not a vendored copy of Frappe code and not a general promise of v15/v16 semantic parity.

### Result limits

- The backend no longer injects a default limit or caps a configured limit/offset.
- Explicit dynamic or static limits are still resolved and validated as non-negative integers before query execution.
- An omitted limit is omitted from the Query Builder payload; the rule author controls whether to limit results. The UI may provide a suggested default in the future, but it is not an execution policy.
- An explicitly configured limit of zero returns no rows. This preserves the rule author's intent because some legacy Query Builder implementations treat a falsey limit as if no limit were supplied. This semantic correction is not an implicit positive limit or a backend result cap.

### Acceptance and remaining verification

This change intentionally removes the previous Frappe 15 `get_list` fallback and its promise of permission parity. It must not be described as enforcing normal record-level permissions on Frappe 15. The existing role and audit-reason governance for explicit permission bypass remains mandatory.

CI and the Frappe/MariaDB integration suite must be rerun on the updated PR head. In particular, test: native permission flag forwarding where supported; v15 failure when bypass is not configured; v15 audited bypass dispatch; nested root-field groups and fail-closed linked/child groups; large dynamic limit/offset pass-through; omitted-limit pass-through; and regression behavior for all other Query Records modes.
\n\n---\n\n# Consolidated source 6: reports/query-records/tree_builder_and_fetch_records_audit.md\n\n> Original report content follows. Preserved without rewriting so findings, evidence, caveats, and historical context remain attributable to their source.\n\n# Tree Builder & Fetch Records Config Audit & Fix Report

## Overview
This report details the deep analysis, code audit, linter/formatting fixes, and test verification performed on the new Tree Builder component and Fetch Records configuration system in FlexiRule.

---

## 1. Scope & System Components Audited
- **Tree Builder Infrastructure (`TreeBuilder.vue`, `TreeBuilderNode.vue`, `useTreeBuilder.js`, `tree_builder_utils.js`)**: Generic nested group/leaf tree editor supporting drag-and-drop, AND/OR logic gates, and structural constraints.
- **Query Filters & Serializer (`QueryFilterTree.vue`, `FilterLeaf.vue`, `query_filter_serializer.js`, `filter_operators.mjs`)**: Domain-specific query filter tree serialization, deserialization, validation, and metadata navigation.
- **Fetch Records Configuration (`FetchRecordsConfig.vue`, `OutputFieldsEditor.vue`, `output_fields_model.js`)**: UI controls for result shapes, output field projections, sort criteria, limits, offsets, and group-by clauses.
- **Backend Query Records Handler (`query_records.py`, `frappe_query_compat.py`)**: Backend filter tree validation, operator normalization, dynamic expression resolution, and query builder execution (`frappe.qb.get_query`).

---

## 2. Issues Identified & Resolved

### A. Linter & Environment Configuration
- **ESLint Config Compatibility**:
  - *Issue*: `package.json` was executing `eslint --ext .js,.vue .`, which failed under modern ESLint v9/v10 due to removed CLI flags (`--ext`) and missing `eslint.config.mjs` flat configuration file.
  - *Fix*: Created `eslint.config.mjs` using `@eslint/eslintrc` `FlatCompat` to preserve rules and globals, and updated `package.json` script to `"lint": "eslint ."`.
  - *Verification*: `yarn lint` passes cleanly with zero errors.

### B. Frontend Filter Validation & Dynamic Expressions
- **Dynamic Expression Support in `Is` Operator (`FilterLeaf.vue`)**:
  - *Issue*: `FilterLeaf.vue`'s `isValidIsValue` validation assumed static string values `"set"` or `"not set"` for the `is` operator, marking valid dynamic string expressions (e.g., `{doc.status_filter}`) as invalid.
  - *Fix*: Updated `isValidIsValue` to validate dynamic expressions starting with `{` or `@` as valid value configurations for the `is` operator.
  - *Verification*: Frontend unit test suite (`node filter_operators.test.mjs`, `node query_filter_serializer.test.js`) and UI validation pass cleanly.

### C. Backend Query Records Field Reference & Validation
- **Group-By Expression Token Splitting (`query_records.py`)**:
  - *Issue*: `_validate_doctype_field_references` checked `_is_plain_field_reference` on raw `group_by` field expressions without extracting field tokens first when direction modifiers or spaces were present.
  - *Fix*: Updated token extraction in `group_by` validation (`field_token = field_expr.split()[0].strip()`) prior to checking field existence against target DocType metadata.
- **Backend `Is` Operator Validation (`query_records.py`)**:
  - *Issue*: Backend validation in `_validate_canonical_fetch_filter_tree` and `_validate_resolved_fetch_filter_operators` rejected dynamic expressions for `is` operator conditions.
  - *Fix*: Updated backend validation routines to accept dynamic expressions starting with `{` or `@` for `is` operator filter leaves.

---

## 3. Test Suite Verification
- **Python Linter (`ruff check flexirule`)**: 100% Passed (All checks passed).
- **JavaScript Linter (`yarn lint`)**: 100% Passed (0 errors).
- **Frontend Unit Tests**:
  - `filter_operators.test.mjs`: Passed.
  - `query_filter_serializer.test.js`: Passed.
  - `tree_builder.test.js`: Passed.
  - `output_fields_model.test.js`: Passed.
- **Backend Frappe Test Suite (`bench --site test_site run-tests --app flexirule`)**:
  - Ran 553 tests in 27.5s.
  - **Result: OK** (553 passed, 0 failures, 2 skipped).
\n\n---\n\n# Consolidated source 7: reports/query_records_fetch_records_backend_implementation_report.md\n\n> Original report content follows. Preserved without rewriting so findings, evidence, caveats, and historical context remain attributable to their source.\n\n# Query Records — "Fetch Records" Backend Operation Implementation Report

## Overview

This report documents the backend implementation of the **Fetch Records** operation under FlexiRule's existing **Query Records** Action Type (`action_type: "Query Records"`, `operation: "Fetch Records"`). The new operation is powered natively by Frappe Framework's modern `frappe.qb.get_query` API.

---

## 1. Existing Query Records Architecture Discovered

FlexiRule's `QueryRecordsHandler` (`flexirule/ruleflow/core/action_handlers/query_records.py`) serves as the action handler for database queries across rule flows. Prior to this task, it supported the following operations:

- **Query List**: Uses `frappe.get_list()` returning a list of dicts.
- **Query Doc**: Uses `frappe.get_doc()` returning a single document dict.
- **Exist Record**: Uses `frappe.db.exists()` returning boolean.
- **Query Report**: Uses `frappe.desk.query_report.run()` returning report dataset.
- **Aggregations** (`Count`, `Sum`, `Average`, `Min`, `Max`, `Group By`): Metrics calculations via `frappe.get_list()`.

The architecture enforces contract declarations per operation via `OperationContract` objects registered in `get_operation_contracts()`. All existing modes remain behaviorally unchanged and intact alongside `Fetch Records`.

---

## 2. New "Fetch Records" Backend Contract

The contract for `fetch_records` is declared in `QueryRecordsHandler.get_operation_contracts()`:

```python
"Fetch Records": OperationContract(
    operation="Fetch Records",
    rule_overrides=standard_trigger_overrides(
        trigger_events=BROAD_TRIGGER_EVENTS,
        trigger_types=STANDARD_TRIGGER_TYPES,
    ),
    action_overrides=[
        {"fieldname": "action_type", "default": "Query Records"},
        {"fieldname": "operation", "default": "Fetch Records"},
        reference_doctype_override(),
        {"fieldname": "reference_docname", "hidden": 1, "reqd": 0},
        config_depends_on_doctype(description="Frappe Query Builder configuration"),
        {
            "fieldname": "mutation_mode",
            "options": [
                "Set Context Variable",
                "Append to Context Variable",
                "Update Context Variable",
            ],
            "reqd": 1,
        },
        {"fieldname": "return_type", "default": "List of Records", "read_only": 1},
        {
            "fieldname": "timeout",
            "hidden": "eval:doc.parent.execution_mode!=='Asynchronous'",
            "description": "Only available for async rules",
        },
        {
            "fieldname": "description",
            "description": "Queries records using Frappe Query Builder (frappe.qb.get_query)",
        },
    ],
    validation={"backend": "validate_fetch_records"},
)
```

### JSON Schema / Payload Structure

The configuration payload stored in `action.config` accepts:

| Property | Type | Required / Default | Description |
|---|---|---|---|
| `doctype_name` / `reference_doctype` | `str` | Required | Target DocType to query |
| `fields` | `list[str]` or `str` or `list[dict]` | Optional (Default: `None` -> selects `name`) | Field paths, aliases (`"email as user_email"`), wildcard `*`, or structured child table fields (`[{"items": ["item_code"]}]`) |
| `filters` | `dict` or `list` | Optional | Dictionary filters, tuple lists, or recursive AND/OR logical filter trees |
| `order_by` | `str` | Optional | Sort ordering (e.g., `"creation desc"`, `"customer asc, grand_total desc"`) |
| `group_by` | `str` | Optional | Grouping field(s) (e.g., `"customer"`) |
| `limit` | `int` or `str` | Optional | Page length |
| `offset` | `int` or `str` | Optional | Record offset for pagination |
| `distinct` | `bool` | Optional (Default: `False`) | Force distinct selection when querying child tables/joins |

---

## 3. Handler Execution Flow

The runtime execution flow inside `QueryRecordsHandler._fetch_records`:

1. **Permission Check**: Checks permissions via `can_ignore_permissions(action, context, throw=True)`. If `ignore_permissions` is `False`, enforces read permission via `frappe.has_permission(reference_doctype, "read", throw=True)`.
2. **Selected Fields**: Parses comma-separated field strings or passes structured field arrays.
3. **Dynamic Value Resolution**:
   - Resolves filter values, order_by, group_by, limit, and offset using `_resolve_filters_with_context` and `_resolve_value_expression_with_context`.
4. **Filter Compilation**:
   - Converts filter trees (including nested AND/OR logic, dicts, tuple lists, and dotted child/link fields) into Pypika / Frappe `Criterion` objects using `_compile_filter_tree`.
5. **Query Builder Construction & Execution**:
   - Invokes `query = frappe.qb.get_query(...)` with target table, fields, filters, order_by, group_by, limit, offset, and distinct.
   - Executes `return query.run(as_dict=True)`.

---

## 4. Permission Behavior & Security Architecture

`Fetch Records` strictly adheres to FlexiRule's security model:

- In FlexiRule, `ignore_permissions` is derived explicitly using `can_ignore_permissions(action, context, throw=True)` (requiring System Manager authorization and mandatory `permission_audit_reason`).
- Frappe Framework's `Engine.get_query` builds raw QueryBuilder objects without taking `ignore_permissions` as a keyword argument. Therefore, permission enforcement is strictly performed prior to query construction:
  - When `ignore_permissions` is `False`, `_fetch_records` explicitly invokes `frappe.has_permission(reference_doctype, "read", throw=True)`, throwing `frappe.PermissionError` if the executing user is unauthorized.
  - When `ignore_permissions` is `True`, permission enforcement is bypassed securely in accordance with FlexiRule audit logging rules.

---

## 5. Dynamic Value Handling

Dynamic variables and expressions (e.g., `{vars.target_id}`, `{doc.status}`, or resolver payloads `{"mode": "variable", "value": "vars.x"}`) are processed through FlexiRule's standard resolution engine before query execution:

- Filters, `order_by`, `group_by`, `limit`, and `offset` support dynamic context values.
- Field names and structural query syntax remain validated string references and are not interpolated as arbitrary SQL expressions.

---

## 6. Supported QB Capabilities

The backend contract safely supports the full spectrum of `frappe.qb.get_query` capabilities:

- **Field Selection & Aliases**: String arrays, comma-delimited strings, wildcard `*`, field aliases (`"email as user_email"`).
- **Nested AND/OR Logical Trees**: Clean compilation of recursive AND/OR filter structures.
- **Operators**: `=`, `!=`, `>`, `>=`, `<`, `<=`, `like`, `not like`, `in`, `not in`, `is`, `between`.
- **Pagination & Ordering**: `limit`, `offset`, `order_by`, `group_by`, `distinct`.
- **Structured Child Records**: Nested child table selection (e.g., `[{"items": ["item_code", "qty"]}]`).

---

## 7. Child & Link Field Behavior

Relationship field traversals (e.g., `customer.customer_name` for Link fields, `items.item_code` for Child Tables) are handled cleanly:

- Dotted field paths in filters and field selections are converted to native child/link DocType references via `_resolve_filter_doctype_and_field` and Frappe QB's implicit joins.
- `_doctype_has_field` recursively inspects both Link fields and Child Table fields on target DocTypes during validation.

---

## 8. Result Structure

In accordance with Query Records conventions:

- `_fetch_records` returns a `list[dict]` directly:
  ```json
  [
    {"name": "TASK-0001", "description": "Review PR", "status": "Open"},
    {"name": "TASK-0002", "description": "Run tests", "status": "Closed"}
  ]
  ```
- No extra wrapping object or separate count query is added.

---

## 9. Validation Rules

Validation is handled by `validate_fetch_records(action, config)` and registered in `OperationContract`:

1. **Reference DocType**: Must be specified and exist in `frappe.db.exists("DocType", ...)` / `frappe.get_meta(...)`.
2. **Field References**: Plain field references in `fields`, `order_by`, and `group_by` are checked against DocType metadata (including dotted Link and Child Table fields).
3. **Filter Fields**: Validated against target or linked DocTypes.
4. **Pagination**: `limit` and `offset` must be non-negative integers or dynamic expression strings.
5. **Distinct**: Must be a boolean value.

---

## 10. Tests Added

Comprehensive backend test coverage is implemented in `flexirule/ruleflow/tests/test_fetch_records.py`:

- `test_basic_fetch_records_default_fields`: Basic record retrieval and default field selection.
- `test_explicit_fields_and_aliases`: Field selection and column aliasing.
- `test_filter_operators`: Tested `=`, `!=`, `like`, `in`, `not in`, `between`, `is`.
- `test_nested_logical_filters_and_or`: Recursive AND/OR filter trees.
- `test_child_table_field_query_and_distinct`: Dotted child table queries and `distinct=True`.
- `test_ordering_limit_and_offset`: Ordering and pagination.
- `test_dynamic_values_resolution`: Resolving `{vars.param}` dynamic filter values.
- `test_permissions_behavior`: Enforces `frappe.PermissionError` for Guest users when `ignore_permissions=False` and allows System Manager when `ignore_permissions=True`.
- `test_validation_rules`: Rejection of invalid DocTypes, missing fields, and negative pagination values.

Historical verification note: an earlier run reported 483 tests passing. This is not evidence for the current Fetch Records review branch; use the dated CI evidence in the latest test-coverage audit below.

---

## 11. Limitations & Intentionally Deferred Capabilities

- **Raw SQL Injection**: Raw SQL string interpolation and arbitrary Pypika object passing from UI are explicitly prohibited to prevent security escapes.
- **Frontend UI**: Frontend components (`QueryRecordsConfig.vue`, etc.) were explicitly out of scope for this task and will be updated in the subsequent task.

---

## 12. Exact Frontend Work for the Next Task

The upcoming frontend task should build upon this finalized backend contract:

1. **Operation Selector**: Add `"Fetch Records"` as an option under `QueryRecordsConfig.vue`.
2. **Field Selection Control**: Bind `config.fields` to multi-select field inputs (supporting dotted Link/Child Table fields and aliases).
3. **Filter Builder**: Expose standard dictionary/tuple filters and nested AND/OR logical filter trees (serializing to `config.filters`).
4. **Ordering & Pagination UI**: Provide inputs for `order_by`, `limit`, `offset`, and `distinct` toggle.
5. **Result Mutation**: Bind output to standard mutation modes (`Set Context Variable`, `Update Context Variable`, `Append to Context Variable`).


## 13. Review-Fix CI Follow-up (2026-10-11)

The review-fix branch adds compatibility handling around frappe.qb.get_query and the permission-aware Frappe v15 frappe.get_list fallback. The first server CI run on this branch executed 543 tests and reported one error (two skipped): test_fetch_records_delegates_native_qb_payload_and_permissions failed because the test unintentionally exercised the installed Frappe v15 fallback against a live mocked DocType lookup instead of isolating the native Query Builder delegation contract.

The test was corrected to explicitly stub the capability descriptor as supporting native permission and logical-filter support for that test, while separate compatibility tests continue to validate the legacy fallback. This is a test-isolation correction, not a production behavior change. The corrected test and configured workflows passed on commit 693971455c0752f45879cee82e91c635a2e07a27; the workflow file was subsequently restored, so its new run is tracked separately.


## 14. Latest CI Rerun: Payload Expectation Correction (2026-10-11)

The next CI run narrowed the remaining failure to the native Query Builder delegation test's expected filter shape. Root-DocType leaves are normalized before delegation, so the expected filters are `["enabled", "=", 1]` and `["email", "like", "%@example.com"]`, connected by `"or"`, rather than four-item leaves prefixed with `"User"`. The assertion correction is test-only. Both CI and Linters passed on commit 693971455c0752f45879cee82e91c635a2e07a27. The original workflow file was restored in commit 47e4b5713c9b2e7dcf99a0d89cffc7478a9d8906; the new run for that restored definition is still in progress, and must be checked before closing verification.

### Recommended next step for filter representation

Keep the persisted Fetch Records filter tree independent of Frappe's version-specific payload format. Normalize only root-DocType field leaves at the QB adapter boundary, after validation has resolved the actual field DocType/path. Do not globally remove the root DocType from saved filter data or from legacy Query Records filters. Add explicit tests for root fields, linked/child paths, and operator/value literals to prove that only the native payload is normalized.

## 12. Revised release decision (2026-10-12)

This section supersedes the earlier report statements that Fetch Records uses a Frappe 15 `frappe.get_list` fallback or has a backend-enforced 1,000-row ceiling.

- Fetch Records always executes through `frappe.qb.get_query`; permission configuration does not switch it to `frappe.get_list`.
- The installed `Engine.get_query` signature is inspected once at module initialization. When it declares `ignore_permissions`, FlexiRule passes the requested flag to the native API. When the signature does not declare that parameter (Frappe 15), a permission-sensitive Fetch Records operation is rejected. The UI enables Skip Permissions by default and prevents disabling it for this mode/version combination. An explicit bypass still goes through FlexiRule's existing authorized-role and mandatory audit-reason checks.
- This does **not** mean Fetch Records on Frappe 15 enforces per-record read permissions. Use Query List for reads that require `frappe.get_list` permission behavior until an upstream-compatible Query Builder permission contract is available.
- The v15 nested filter adapter translates supported root-DocType AND/OR groups into native Pypika criteria before invoking Query Builder. Linked/child-field leaves inside such groups fail closed. This is a known limitation for the first production release; it is not a substitute for native nested-filter support.
- No default result limit or fixed maximum limit/offset is imposed by the backend. Explicit values remain validated as non-negative integers after dynamic resolution. When limit is omitted, FlexiRule omits it from the Query Builder request. An optional UI default can be considered separately. An explicitly configured limit of zero returns no rows because some legacy Query Builder implementations treat a falsey limit as omitted; this preserves the rule author's requested result count and is not an arbitrary cap.
- No Frappe framework source was modified in this PR. The proposal for native v15 permission support remains an upstream discussion item.

The changes require fresh CI and Frappe/MariaDB verification on the current PR head. Prior workflow results do not validate these commits. Do not claim v15 row-level permission parity or production acceptance until the relevant integration evidence exists.
\n\n---\n\n# Consolidated source 8: reports/test-coverage-audit.md\n\n> Original report content follows. Preserved without rewriting so findings, evidence, caveats, and historical context remain attributable to their source.\n\n# Test Coverage Audit — FlexiRule

## 1. Automated Test Suite Execution Results

### Current Fetch Records review-fix run — 2026-10-11

The server CI job ran the test suite on the Fetch Records review-fix branch:

- **Command**: bench --site test_site run-tests --app flexirule
- **Result**: 543 tests run, **1 error**, 0 assertion failures, 2 skipped.
- **Failing test**: test_fetch_records_delegates_native_qb_payload_and_permissions.
- **Observed exception**: KeyError: 0 in Frappe's virtual-DocType metadata lookup after the test unintentionally entered the permission-aware frappe.get_list fallback.

This run is **not green**. The production compatibility layer detected that the installed Frappe v15 Query Builder does not expose native ignore_permissions, and correctly selected the permission-aware fallback. The test was intended to characterize native Query Builder delegation but had not isolated that capability scenario.

A test-only correction has been pushed: the native-delegation test now stubs the capability descriptor to represent native support and explicitly checks the ignore_permissions=False argument. Dedicated compatibility tests remain responsible for exercising the Frappe v15 fallback. The updated run must pass before this item is considered verified.

### Earlier historical run

An earlier test-site run reported **414 tests**, 412 passed, and 2 skipped in 18.21 seconds. That result predates the current branch and must not be used as evidence that the current review-fix changes pass.

**Test suite location**: flexirule/ruleflow/tests/.

---

## 2. Regression Test Suite for Confirmed Findings

A dedicated regression test module `flexirule/ruleflow/tests/test_audit_reproductions.py` was implemented and permanently integrated into the test suite to verify fixes for the key findings:
1. **AST Validation & Sandbox Escape (FR-SEC-001)**: `test_FR_SEC_001_ast_validation_stub_sandbox_escape` verifies `validate_safe_eval` throws `ValidationError` when encountering dunder attribute traversal expressions (`__subclasses__`).
2. **Server-Side Template Injection (FR-SEC-002)**: `test_FR_SEC_002_ssti_in_document_action_rendering` verifies `DocumentActionHandler._render_scalar` does not evaluate raw `frappe` module database calls.
3. **SafeFrappeAPI Parameter Guard (FR-SEC-003)**: `test_FR_SEC_003_safe_frappe_api_format_value_dict_override` verifies `SafeFrappeAPI.format_value` blocks custom dictionary overrides as `df`.
4. **Sub-Rule Recursion Depth Limit Enforcement (FR-ENGINE-002)**: `test_FR_ENGINE_002_sub_rule_recursion_depth_propagated` verifies `SubRuleHandler` enforces `MAX_SUB_RULE_DEPTH = 2` when context depth exceeds the limit.


## 3. Follow-up Verification Status

- [x] Identify the CI failure and trace it to a version-dependent test setup.
- [x] Push a deterministic test-isolation fix to fix/fetch-records-review-findings.
- [x] Confirm the complete server suite passes on commit 693971455c0752f45879cee82e91c635a2e07a27.
- [x] Confirm linter and frontend CI jobs pass on commit 693971455c0752f45879cee82e91c635a2e07a27.
- [ ] Reconfirm CI after restoring the original .github/workflows/ci.yml; the restored workflow's run is the acceptance evidence for the current workflow definition.

Do not convert the unchecked items to complete based only on the code change; the CI results for the new commit are the acceptance evidence.


## 4. Latest CI Rerun: Native Payload Assertion (2026-10-11)

The server failure was a stale assertion among 543 tests (two skipped), not a production failure. Fetch Records normalizes root-DocType filter leaves from `[doctype, field, operator, value]` to `[field, operator, value]` before native QB delegation, so the expected `User` prefix was incorrect. The test expectation was corrected. Both configured workflows then passed on commit `693971455c0752f45879cee82e91c635a2e07a27` (CI run 38182490923; Linters run 38182491032). The original `.github/workflows/ci.yml` was subsequently restored in commit `47e4b5713c9b2e7dcf99a0d89cffc7478a9d8906`; rerun status for that restored workflow definition must be checked before declaring the current head verified.

Design recommendation: keep Fetch Records' persisted filter-tree contract stable and normalize root-DocType leaves only at the Frappe QB adapter boundary. Do not strip root DocType prefixes globally: linked/child paths and legacy Query Records modes have different semantics and must not be changed by this QB-specific compatibility conversion.
\n\n---\n\n# Consolidated source 9: reports/tree-builder-query-records-architecture-audit.md\n\n> Original report content follows. Preserved without rewriting so findings, evidence, caveats, and historical context remain attributable to their source.\n\n> **Lifecycle note:** This document records the architecture audit that preceded implementation. The implementation was subsequently rebuilt against the architecture and acceptance criteria documented here.

# Tree Builder / Query Records Architecture Audit

**Repository:** Sendipad/flexirule  
**Audited branches:** refactor/tree-builder-generic-20261008, refactor/tree-builder-generic-20261009, refactor/query-records  
**Status:** Architecture audit only. No source implementation changes were made by this audit.

## 1. Executive conclusion

### Verdict: NOT READY FOR IMPLEMENTATION

The current Generic Tree Builder is not yet the single structural tree/state owner for Query Records.

The effective current architecture is:

    FetchRecordsConfig
        -> QueryFilterTree
           -> its own reactive tree
           -> filter_tree_adapter normalization/deserialization
           -> legacy serialization
        -> Generic TreeBuilder
           -> useTreeBuilder reactive root
           -> commands
           -> structural validation
        -> FilterLeaf
           -> legacy FilterGroup
              -> filter-row state
              -> field/operator/value logic
              -> validation

This violates the requested architecture.

The main defects are:

1. QueryFilterTree creates a separate reactive tree.
2. TreeBuilder creates another normalized reactive tree.
3. FilterLeaf is only a wrapper around the legacy FilterGroup editor.
4. filter_tree_adapter.js is a compatibility parser/normalizer/validator/serializer, not merely a backend boundary.
5. Generic TreeBuilder hardcodes group, scope, and leaf semantics.
6. Generic TreeBuilder exposes scope-specific context through getNodeContext().
7. Generic normalization silently converts unknown node types into leaves.
8. FetchRecordsConfig has stale relative imports after being moved one directory deeper.
9. The existing ControlRegistry/ControlFactory/FlexValueControl architecture is available and should be reused.
10. Historical representations should not automatically survive on these unmerged pre-release branches.

The correct direction is:

    FetchRecordsConfig
        -> QueryFilterTree
           -> composition/policy only
        -> Generic TreeBuilder
           -> ONE canonical tree state
        -> FilterLeaf
           -> ONE filter leaf
        -> ControlFactory / ControlRegistry / FlexValueControl
        -> ONE explicit Query Filter serializer
        -> Query Records backend contract

## 2. Current state ownership

### Action configuration

node.data.config remains the action configuration state. This is legitimate and should remain outside the generic tree engine.

### FetchRecordsConfig

FetchRecordsConfig creates localConfig with reactive(normalizeConfig(props.modelValue)). This is acceptable as configuration editing state, provided filters are delegated and it does not become a second tree engine.

### QueryFilterTree

QueryFilterTree creates a reactive tree from deserializeFilterPayload(props.modelValue). It then deep-watches, validates, serializes, replaces, clones, and exposes that tree.

Therefore QueryFilterTree is a tree state owner.

### Generic TreeBuilder

useTreeBuilder creates a second reactive root by normalizeTree(modelValue).

It independently watches, normalizes, clones, mutates, validates, and emits that tree.

Therefore:

    QueryFilterTree.tree
        -> TreeBuilder.root

are two distinct in-memory tree objects.

### FilterGroup

FilterLeaf currently renders FilterGroup with singleRow=true. FilterGroup itself contains filter-row state, field lookup, operator selection, value editing, navigation, and validation.

Thus each generic leaf is backed by another filter editor state machine.

## 3. Actual data flow

    node.data.config
      -> FetchRecordsConfig.localConfig
      -> QueryFilterTree.modelValue
      -> deserializeFilterPayload()
      -> QueryFilterTree.tree
      -> TreeBuilder v-model
      -> useTreeBuilder.normalizeTree()
      -> TreeBuilder.root
      -> tree_builder_commands / tree_builder_validation
      -> FilterLeaf
      -> FilterGroup
      -> FilterLeaf update
      -> QueryFilterTree.updateLeaf()
      -> validateFilterTree()
      -> serializeFilterTree()
      -> FetchRecordsConfig
      -> node.data.config

This is too many transformations.

The redundant layers are QueryFilterTree.tree, FilterLeaf -> FilterGroup, adapter normalization, adapter structural validation, and historical compatibility parsing.

## 4. Generic Tree Builder analysis

### Correct responsibilities

The generic layer should own:

- tree state
- hierarchy
- group creation/removal
- leaf creation/removal
- movement/reordering
- nesting
- structural validation
- depth limits
- mutation commands
- operator policy mechanism
- rendering composition

The current extraction of commands, utilities, and validation is directionally good.

### Incorrect responsibilities

The generic layer must not know:

- Frappe
- DocTypes
- fields
- Query Records
- Query Filter syntax
- Value Resolver semantics
- legacy filter arrays
- Query-specific scope semantics

The current implementation makes scope generic through TreeBuilderScope, scopeFactory, allowScopes, validateScope, and getNodeContext().scopes.

That is too domain-specific.

### Unknown node behavior

normalizeTree() currently turns unknown node types into leaves. This is unsafe. An extension node must never silently change semantic type.

## 5. Maximum depth

The 20261009 branch correctly attempts to make maxDepth a structural invariant.

It affects:

- add leaf
- add group
- add scope
- move
- drag/drop
- validation

This is the right direction.

The final implementation must also protect every externally supplied/replaced subtree. Max depth should be a single structural policy rather than scattered checks.

## 6. Logical operators

groupOperators is already a good generic mechanism.

The generic layer should provide the mechanism while the consumer defines:

- allowed values
- labels
- optionally descriptions

Hardcoded AND/OR label semantics should be removed from the generic implementation.

The added operatorLabel mechanism is directionally correct.

## 7. Node visibility

visibleNode is a useful policy hook, but the current behavior means that hiding a container hides its entire subtree.

That is valid for “hide node and subtree”, but not for “hide wrapper while still rendering children”.

Do not add transparent-container complexity unless a real consumer requires it. Visibility must never mutate the canonical tree.

## 8. Scope and collection decision

The audit did not establish a current Query Records-independent need for generic scope semantics.

Recommendation:

- group = generic structural container
- leaf = generic terminal node
- leaf payload = consumer-owned

Do not hardcode collection/scope semantics into the generic core merely because the previous implementation created them.

If a future consumer actually needs custom container node types, introduce a formal node-definition/capability mechanism at that time.

## 9. Query Records analysis

Query Records supports several modes. The backend contract confirms Fetch Records is a Query Records operation using Frappe Query Builder.

QueryRecordsConfig also uses the existing FilterGroup for other modes such as Query List, Exist Record, and aggregation-related filters.

Therefore FilterGroup must not be deleted globally as part of this refactor.

The clean migration boundary is the Fetch Records nested tree editor.

## 10. FilterLeaf decision

**Classification: D/E — rewrite as a genuine domain leaf renderer.**

Current design:

    FilterLeaf
        -> FilterGroup(singleRow=true)

This is not a real leaf renderer. It is a legacy filter editor wrapped to look like a leaf.

The new FilterLeaf should represent one leaf:

    {
      id,
      type: "leaf",
      doctype,
      field,
      operator,
      value
    }

It may own:

- field metadata
- field picker
- operator policy
- value control
- field-specific validation

It must not own:

- children
- groups
- nesting
- movement
- tree mutation
- tree normalization
- tree serialization
- parent/child relationships

The Generic TreeBuilder owns structural remove/move behavior.

## 11. QueryFilterTree decision

**Classification: B — retain, but make it thin.**

QueryFilterTree is a useful Query Filter composition boundary.

It should configure:

- Generic TreeBuilder
- Query Filter operator policy
- max depth
- visibility policy when required
- FilterLeaf renderer
- domain validation

It should not:

- create a second reactive tree
- deep-watch a duplicate tree
- normalize the tree independently
- serialize every mutation
- maintain a second tree API

The current reactive tree in QueryFilterTree should be eliminated.

## 12. filter_tree_adapter decision

**Classification: D/E — replace/minimize.**

The current adapter performs:

- ID generation
- group creation
- leaf creation
- legacy value normalization
- tuple detection
- legacy sequence parsing
- deserialization
- normalization
- structural validation
- serialization

That is a second filter-tree framework, not a simple backend boundary.

The only legitimate remaining boundary is:

    canonical UI tree
        <-> Query Records backend filter representation

If historical representations are not required by the active backend contract, delete their parsing.

Because these branches are unmerged, compatibility with the previous refactor is not a requirement.

## 13. Canonical model

Recommended canonical in-memory model:

    {
      "id": "root",
      "type": "group",
      "operator": "and",
      "children": [
        {
          "id": "filter-1",
          "type": "leaf",
          "doctype": "Sales Order",
          "field": "status",
          "operator": "=",
          "value": {
            "mode": "static",
            "value": "Open"
          }
        }
      ]
    }

The Generic TreeBuilder should treat leaf payload after id/type as opaque.

It knows structure, not Query Filter meaning.

The backend boundary should be:

    canonical UI tree
        -> Query Filter serializer
        -> Query Records backend contract

and, when loading persisted data:

    backend contract
        -> Query Filter deserializer
        -> canonical UI tree

There must not be several intermediate filter-tree representations.

## 14. Responsibility matrix

| Responsibility | Generic TreeBuilder | QueryFilterTree | FilterLeaf | FetchRecordsConfig | Backend boundary |
|---|---:|---:|---:|---:|---:|
| Tree state | YES | NO | NO | NO | NO |
| Tree mutations | YES | NO | NO | NO | NO |
| Group creation | YES | policy | NO | NO | NO |
| Leaf creation | YES | policy | NO | NO | NO |
| Movement/reordering | YES | policy | NO | NO | NO |
| Nesting | YES | policy | NO | NO | NO |
| Max depth | YES | config | NO | NO | NO |
| Structural validation | YES | domain policy | NO | NO | NO |
| Group operators | mechanism | policy | NO | NO | NO |
| Operator labels | mechanism | policy | filter labels | NO | NO |
| Node visibility | mechanism | policy | NO | NO | NO |
| Leaf rendering | framework | configures | YES | NO | NO |
| Field selection | NO | NO | YES | NO | NO |
| Filter operator | NO | policy | YES | NO | NO |
| Filter value | NO | NO | YES | NO | NO |
| Value Resolver | NO | NO | YES | NO | NO |
| Query configuration | NO | NO | NO | YES | NO |
| Backend serialization | NO | NO | NO | NO | YES, if required |

## 15. Existing FlexiRule architecture

The existing frontend already provides the required mechanisms.

### ControlRegistry

core/control_registry.js maps field definitions to registered controls including ComboBoxControl, SelectControl, CheckControl, MultiSelectList, FlexValueControl, and others.

### ControlFactory

rule_builder/controls/ControlFactory.vue resolves controls through ControlRegistry.

Where a field definition naturally determines its control, this should be preferred over a new control-resolution mechanism.

### FlexValueControl

FlexValueControl.vue is already the structured value/resolver integration point.

FilterLeaf should reuse it rather than creating another resolver abstraction.

### useControlContext

useControlContext.js provides dependent-field resolution for Dynamic Link and MultiSelectList. Reuse it.

### useNavigableFields

useNavigableFields.js is the existing Query Records-oriented field-navigation composable. It belongs in Query Records/domain UI, not Generic TreeBuilder.

### useActionConfig

useActionConfig.js already owns action configuration concerns such as reference DocType, metadata, variables, config synchronization, and dirty state.

## 16. Build-error root cause

### FetchRecordsConfig imports

FetchRecordsConfig was moved from:

rule_builder/components/rule_config/types/FetchRecordsConfig.vue

to:

rule_builder/components/rule_config/types/query_records/FetchRecordsConfig.vue

but imports remained at the old relative depth:

- ../../../controls/ControlFactory.vue
- ../../../controls/ComboBoxControl.vue
- ../../../controls/MultiSelectList.vue
- ../../../composables/useNavigableFields

The actual canonical locations are:

- rule_builder/controls/ControlFactory.vue
- rule_builder/controls/ComboBoxControl.vue
- rule_builder/controls/MultiSelectList.vue
- rule_builder/composables/useNavigableFields.js

Therefore the resolution failures are direct consequences of the move without adjusting the import root.

This is a symptom, not the architectural fix.

### frappe-vue-style error

The error about reading outputs from frappe-vue-style should be treated as secondary until the module-resolution failures are removed.

Correct order:

1. resolve module graph
2. rebuild
3. see whether outputs error remains
4. only then investigate plugin behavior

## 17. Directory structure

Responsibility-based target:

    rule_builder/
      components/
        tree_builder/
          TreeBuilder.vue
          TreeBuilderNode.vue
          TreeBuilderGroup.vue
          useTreeBuilder.js
          tree_builder_utils.js
          tree_builder_commands.js
          tree_builder_validation.js
          tree_builder_types.js

        rule_config/
          query_filters/
            QueryFilterTree.vue
            FilterLeaf.vue
            query_filter_serializer.js
            query_filter_policy.js

          types/
            QueryRecordsConfig.vue
            query_records/
              FetchRecordsConfig.vue

The exact serializer/policy filenames may change if an existing FlexiRule pattern is preferable.

The important rule is responsibility, not historical filename placement.

## 18. File classification

| File | Decision | Reason |
|---|---|---|
| FilterLeaf.vue | D/E | Keep concept, rewrite as one domain leaf |
| QueryFilterTree.vue | B | Keep as thin composition; remove duplicate state |
| filter_tree_adapter.js | D/E | Replace with minimal backend boundary if required |
| filter_tree_adapter.test.js | B/D | Rewrite around public serialization contract |
| FetchRecordsConfig.vue | A/B | Keep; delegate filters and own Query Records config |
| QueryRecordsConfig.vue | A/B | Keep as top-level mode configuration |
| FilterGroup.vue | A | Retain for existing non-Fetch-Records consumers |

## 19. Redundant layers

### Redundant 1
QueryFilterTree.tree — Generic TreeBuilder already owns the tree.

### Redundant 2
FilterLeaf -> FilterGroup — a leaf renderer must not mount a filter tree/editor.

### Redundant 3
normalizeFilterTree() — Generic TreeBuilder should normalize the canonical model.

### Redundant 4
validateFilterTree() — Generic TreeBuilder should own structure; Query Filter validates leaf/domain semantics.

### Redundant 5
Historical compatibility parsing — keep only if the active backend/persistence contract requires it.

## 20. Target QueryFilterTree composition

Conceptually:

    QueryFilterTree
        -> receives modelValue
        -> supplies Query Filter policy
        -> supplies FilterLeaf renderer
        -> Generic TreeBuilder

There must be no intermediary reactive tree.

The invariant is:

    TreeBuilder state == QueryFilterTree filter state

## 21. Target FilterLeaf

Conceptually:

    FilterLeaf
      -> field picker
      -> operator picker
      -> FlexValueControl / ControlFactory
      -> domain validation

It receives one canonical leaf and emits one updated leaf.

It does not know about siblings, parent groups, children, drag/drop, tree serialization, or tree normalization.

## 22. Testing strategy

### Generic TreeBuilder

Test:

- add leaf
- add group
- remove
- move/reorder
- circular move prevention
- operator policy
- max depth
- externally supplied too-deep trees
- replacement validation
- visibility policy if public behavior

### QueryFilterTree

Test composition:

- canonical model reaches TreeBuilder
- FilterLeaf receives canonical leaf
- operator policy
- max depth policy
- visibility policy

Do not test duplicate internal state.

### FilterLeaf

Test:

- field selection
- operator selection
- field-dependent operator changes
- value control
- static values
- variable/resolver values
- Between/multi-value semantics
- Dynamic Link/MultiSelect dependencies
- validation

### Serializer

Test only:

    canonical tree <-> active backend representation

Delete compatibility tests if compatibility is intentionally removed.

## 23. Compatibility decision

These branches are pre-release and unmerged.

Preferred policy:

    DELETE obsolete representation
    DELETE duplicate state
    DELETE redundant adapters
    REBUILD around one canonical model

Do not introduce:

    old model -> wrapper -> adapter -> generic model -> compatibility layer

Only compatibility required by the active persisted/backend contract should survive.

## 24. Implementation phases

Implementation should begin only after this audit is accepted.

### Phase 1 — Canonical generic model
Define and test one tree model. Remove generic scope semantics that are not genuinely generic.

### Phase 2 — Single state owner
Remove QueryFilterTree duplicate reactive state. Generic TreeBuilder becomes the tree state owner.

### Phase 3 — Real FilterLeaf
Rewrite FilterLeaf as a one-row domain component. Stop using FilterGroup as its implementation.

### Phase 4 — Serialization boundary
Confirm the active Query Records backend contract and replace the current adapter with one minimal serializer/deserializer if required.

### Phase 5 — QueryFilterTree composition
Configure TreeBuilder with Query Filter policy and renderer only.

### Phase 6 — FetchRecordsConfig integration
Keep FetchRecordsConfig focused on Query Records configuration and delegate filters.

### Phase 7 — Tests/build
Run generic tree, Query Filter, serializer, Fetch Records, lint/build, and targeted UI tests. Investigate frappe-vue-style only after module resolution succeeds.

## 25. Critical acceptance criteria

The implementation must not be considered successful merely because the build passes.

All must be demonstrable:

1. One canonical in-memory tree model.
2. One tree state owner.
3. One tree mutation owner.
4. FilterLeaf contains no tree structure.
5. FilterLeaf does not wrap FilterGroup for Fetch Records.
6. QueryFilterTree contains no second tree state.
7. FetchRecordsConfig does not manipulate tree internals.
8. Generic TreeBuilder contains no Query Records knowledge.
9. Generic TreeBuilder contains no Frappe knowledge.
10. Generic TreeBuilder does not hardcode Query Filter operators.
11. Scope/collection semantics are not hardcoded into generic core without a demonstrated generic requirement.
12. Legacy serialization is removed unless required by the active backend contract.
13. One explicit backend serialization boundary exists.
14. No redundant tree normalization remains.
15. No duplicated group/leaf/scope models remain.
16. Existing ControlRegistry/ControlFactory/FlexValueControl/composables are reused.
17. Build imports reference canonical locations.
18. Tests validate public contracts rather than obsolete implementation details.
19. Max depth applies to external trees, add, move, drag/drop, and validation.
20. Operator values/labels are consumer policy.
21. Visibility is a deliberate composition policy and never mutates canonical state.

## 26. Final architectural decision

The Generic TreeBuilder extraction is a useful foundation, but it is not yet the final architecture.

The correct next step is not to patch the current import errors or add more compatibility wrappers.

The correct next step is to simplify:

    DELETE duplicate QueryFilterTree state
    DELETE FilterLeaf -> FilterGroup tree delegation
    DELETE redundant filter-tree normalization
    DELETE obsolete adapter compatibility
    DELETE hardcoded generic scope semantics unless a real generic consumer requires them

Then rebuild around:

    FetchRecordsConfig
        -> QueryFilterTree (composition/policy)
        -> Generic TreeBuilder (ONE tree state owner)
        -> FilterLeaf (ONE leaf editor)
        -> ControlFactory / ControlRegistry / FlexValueControl
        -> Query Filter serializer
        -> Query Records backend contract

The architecture is acceptable only when Generic Tree Builder owns structure/state/mutations, Query Records owns domain semantics, there is one canonical tree model, one state owner, one mutation owner, one explicit backend serialization boundary, and no hidden legacy tree/serialization layer remains.
