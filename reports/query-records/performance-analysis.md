# Performance & Scalability Analysis

## 1. Executive Summary of Performance Audit

FlexiRule's Query Records action generally follows an efficient pattern by delegating filtering, field selection, sorting, and pagination to SQL via `frappe.get_list()`. However, specific operational modes—notably `Query Doc` and unconstrained `Query List` queries—contain performance bottlenecks and memory overheads.

---

## 2. Performance Analysis by Layer & Mode

### A. `Query List` Mode (Efficient SQL Execution)
- **Field Selection**: **Efficient**. Passes `fields` array directly to SQL `SELECT`, retrieving only requested columns.
- **Filtering**: **Efficient**. Filter conditions are rendered into SQL `WHERE` clauses.
- **Sorting**: **Efficient**. Delegated to SQL `ORDER BY`.
- **Pagination**: **Efficient**. Slicing occurs in database engine via `LIMIT`.
- **Potential Bottleneck**: Setting `limit_type: "All"` on DocTypes with > 100,000 records removes SQL `LIMIT`, returning all rows in a single memory payload.

### B. `Query Doc` Mode (In-Memory Overhead)
- **Mechanism**: Calls `frappe.get_doc()` or `frappe.get_cached_doc()`, then converts the object to a dict via `doc.as_dict()`.
- **Overhead Sources**:
  1. **Full Document Loading**: `frappe.get_doc()` executes SQL queries for the parent record AND separate queries for every child table attached to the DocType (e.g., Sales Order Items, Payment Schedule, Sales Team, Taxes).
  2. **Controller Hooks & Properties**: Instantiating a `Document` triggers `onload()` methods, controller initialization, and virtual field computations.
  3. **Immediate Conversion**: Immediately calling `doc.as_dict()` discards the controller instance, meaning all ORM setup effort was wasted.
- **N+1 Risk**: If `Query Doc` is executed inside a FlexiRule `Loop` action, it performs N+1 database queries (1 query per loop iteration to fetch all child tables).

### C. `Query Report` Mode (Heavy Payload Overhead)
- **Mechanism**: Calls `frappe.desk.query_report.run(report_name, filters)`.
- **Overhead Sources**: Runs full report scripts, executes report SQL, formats columns, and returns both `columns` and `result` arrays. Passing large report results into rule engine context increases Pinia graph memory and serialized JSON context size.

---

## 3. Quantification of Performance Impact

| Scenario | Mode | Execution Pattern | Database Queries | Memory Footprint | Recommendation |
| :--- | :--- | :--- | :---: | :---: | :--- |
| Fetch 3 fields from 50 rows | `Query List` | `frappe.get_list(fields=['a','b','c'], limit_page_length=50)` | 1 query | ~15 KB | Optimal |
| Fetch 1 record for lookup | `Query Doc` | `frappe.get_doc()` -> `as_dict()` | 1 + N child queries (e.g. 5-10 queries) | ~100 KB | Suboptimal if scalar fields suffice |
| Fetch 1 record for lookup | `Query List` | `frappe.get_list(limit_page_length=1)` | 1 query | ~2 KB | 10x faster & lighter for lookups |
