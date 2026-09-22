# Deep Architecture Investigation: Frappe Query API vs FlexiRule Query Records

## 1. Executive Summary

This architectural report presents a deep, source-code-driven analysis of how the Frappe Framework implements database querying and permission handling, compared directly with the FlexiRule **Query Records** action handler implementation.

### Key Findings
1. **Direct Child Table Querying Gaps**: Frappe's query APIs do not natively allow executing a `get_list()` or `get_all()` directly on a Child DocType if standard permissions are enabled, because Child DocTypes lack independent document-level permissions. However, using the bypass flag `ignore_permissions=True` or the Query Builder `frappe.qb`, direct Child DocType querying is fully supported.
2. **Implicit Parent-Child Joins and Filtering Gaps**: Frappe supports implicit joins (e.g., `items.item_code` field extraction/filtering) via both its legacy `DatabaseQuery` layer and its modern database `Engine`. Conversely, FlexiRule is currently unable to query or filter across parent-child boundaries.
3. **Database Transformation & SQL Generation Pipeline**: Frappe uses two distinct query execution pipelines: the legacy `DatabaseQuery` class (which builds raw SQL strings with extensive hand-coded string substitutions and `ifnull` wrappers) and the modern PyPika-based `frappe.qb` and database `Engine` class (which compiles structural Python representations directly into parameter-mapped abstract syntax trees).
4. **Security & Sandbox Escape Risks**: FlexiRule's permission-skipping mechanism is extremely robust, requiring explicit administrative roles and auditable justification, but its validation of dynamic python expressions relies on a basic syntax-only check (`compile()`), presenting a latent sandbox-escape vulnerability.

This report documents these architectural mechanisms, presents complete execution call-graphs, evaluates feature compatibility, and delivers a highly prioritized, complexity-estimated roadmap to achieve feature-parity with Frappe's database query capabilities.

---

## 2. Frappe Query API Architecture

Frappe implements database querying through two concurrent layers:
1. **The Legacy Layer (`DatabaseQuery`)**: Used as the primary backing engine for standard desk views, report views, and `frappe.get_list()` / `frappe.get_all()`.
2. **The Modern Layer (Query Builder & Database `Engine`)**: Used when developers write object-oriented programmatic queries via `frappe.qb` or when modern query parameters are processed through the `frappe.database.query.Engine` class.

### 2.1 legacy Layer (`frappe.model.db_query.DatabaseQuery`)
The `DatabaseQuery` class handles:
- **Permission Mapping**: Inspecting role-based user permissions (`frappe.permissions.get_role_permissions`) and appending "match conditions" (ownership limits, user permission filters, share conditions) directly into the SQL query's `WHERE` clause.
- **SQL String Generation**: Iterating over fields and filters to stitch together a raw SQL query string.
- **Table Extraction and Joins**: Dynamically finding referenced tables (such as child tables or linked tables) and performing `left join` operations on the fly.

### 2.2 Modern Layer (Query Builder & Database `Engine`)
The database `Engine` (`frappe/database/query.py`) acts as an intermediate query parser that:
- Uses **PyPika** as its structural Query Builder.
- Parses fields, filters, and ordering into PyPika `Criterion` and `Field` objects.
- Automatically handles parent-child joins by returning `ChildTableField` or `LinkTableField` instances when dot-notation (e.g., `parent_field.child_field` or `link_field.target_field`) is detected.
- Directly compiles queries to safe parameterized SQL, preventing SQL-injection by-design rather than through regex sanitization.

---

## 3. Complete Call Graph

The following call graph traces the execution of `frappe.get_list()` and `frappe.get_all()` from the initial entry point down to database-level SQL execution.

```
frappe.get_list() / frappe.get_all()  [frappe/__init__.py]
  │
  ├──► [If ignore_permissions is True or limit_page_length is omitted]
  │      Sets kwargs["ignore_permissions"] = True / sets limit_page_length
  │
  └──► DatabaseQuery.execute()  [frappe/model/db_query.py]
         │
         ├──► check_read_permission()  (If ignore_permissions is False)
         │      └─► _set_permission_map()
         │            └─► frappe.has_permission()
         │
         ├──► [If Virtual DocType]
         │      └─► controller.get_list()  (Redirects execution to virtual controller)
         │
         ├──► DatabaseQuery.build_and_run()
         │      │
         │      ├──► DatabaseQuery.prepare_args()
         │      │      │
         │      │      ├──► parse_args()  (Converts string lists/dicts to parsed fields & filters)
         │      │      │
         │      │      ├──► sanitize_fields()  (Applies SQL-injection checks/blacklist filter)
         │      │      │
         │      │      ├──► extract_tables()  (Dynamically extracts tabChild or tabLink tables from fields)
         │      │      │      └─► append_table() / append_link_table()
         │      │      │            └─► check_read_permission()
         │      │      │
         │      │      ├──► build_conditions()
         │      │      │      ├─► build_filter_conditions()
         │      │      │      │     └─► prepare_filter_condition()
         │      │      │      │           ├─► get_filter() [via hooks]
         │      │      │      │           ├─► get_nested_set_hierarchy_result() (For descendants/ancestors)
         │      │      │      │           └─► frappe.db.escape()
         │      │      │      └─► build_match_conditions() (User-specific permission constraints)
         │      │      │
         │      │      └──► apply_fieldlevel_read_permissions() (Removes unauthorized fields)
         │      │
         │      ├──► DatabaseQuery.add_limit()
         │      │
         │      └──► frappe.db.sql()  [frappe/database/database.py]
         │             └─► execute()  (Sends compiled raw SQL string directly to MariaDB/PostgreSQL connector)
```

---

## 4. Query Execution Pipeline

The Frappe database layer maps python objects into SQL via a highly structured pipeline.

### Step 1: Entry Point & Initialization
- `frappe.get_list(doctype, fields, filters, ...)` initializes `DatabaseQuery(doctype)`.
- It accepts a mix of formats for `fields` (string, list, or tuple) and `filters` (dict, list of lists, or PyPika criteria).

### Step 2: Parameter Normalization (`parse_args`)
- Filters are converted into lists of `Filter` tuples via `make_filter_tuple(doctype, key, value)`.
- Dot-notated fields (e.g., `customer.customer_name`) are detected and mapped to linked table definitions.

### Step 3: Security & Schema Resolution
- Blacklisted keywords (`select`, `union`, `insert`, `sleep`) are evaluated via SQL-parse regexes.
- Fields not present in the DocType metadata (`frappe.get_meta`) are rejected, and fields the user does not have permission to read are stripped out.

### Step 4: Table and Condition Building
- `extract_tables` identifies joins based on fields.
- `build_conditions` iterates through filters. If a filter field belongs to a child table or a linked table, the system registers the join and constructs the `ON` condition (e.g., `tabChild.parent = tabParent.name`).
- It applies `ifnull(column, fallback)` wrappers for nullable fields unless `ignore_ifnull` is enabled or the field cannot be null.

### Step 5: SQL Interpolation & Execution
- The query arguments are stitched together using string formatting:
  ```sql
  select {fields} from {tables} {conditions} {group_by} {order_by} {limit}
  ```
- The query is sent to `frappe.db.sql()`, which executes the raw query string and returns a list of dictionaries (`as_dict=True`).

---

## 5. Supported Features Matrix

| Feature | Legacy Layer (`DatabaseQuery`) | Modern Layer (`Engine` / `qb`) | FlexiRule `Query Records` |
| :--- | :--- | :--- | :--- |
| **Normal Fields** | ✅ | ✅ | ✅ |
| **Link Field Resolving** | ✅ (via `append_link_table`) | ✅ (via `LinkTableField`) | ❌ |
| **Dynamic Links** | ❌ (Not supported directly) | ❌ (Not supported directly) | ❌ |
| **Field Aliasing** | ✅ (e.g. `fieldname as alias`) | ✅ (e.g. `field.as_(alias)`) | ✅ |
| **SQL Expressions** | ✅ (Escaped/checked via parse) | ✅ (Supported through pypika) | ❌ |
| **COUNT Aggregate** | ✅ | ✅ | ✅ |
| **SUM Aggregate** | ✅ | ✅ | ✅ |
| **AVG Aggregate** | ✅ | ✅ | ✅ |
| **DISTINCT Aggregates**| ✅ | ✅ | ❌ |
| **CONCAT / CASE** | ❌ (Blocked by SQL injection check)| ✅ (Supported inside pypika) | ❌ |
| **Filter Operators** | `=`, `!=`, `>`, `<`, `>=`, `<=`, `like`, `not like`, `between`, `in`, `not in`, `is`, `is not`, `descendants of`, `ancestors of` | `=`, `!=`, `>`, `<`, `>=`, `<=`, `like`, `not like`, `between`, `in`, `not in`, `is`, `is not`, `descendants of`, `ancestors of` | `=`, `!=`, `>`, `<`, `>=`, `<=`, `like`, `not like`, `between`, `in`, `not in`, `is` |
| **Nested/OR Filters** | ✅ (via `or_filters` array) | ✅ (via `or_` PyPika operators) | ✅ (via `or_filters` config) |
| **Timespan Range Filters**| ✅ (via hook date resolution) | ✅ (mapped via `OPERATOR_MAP`) | ✅ (via timespan date-coercion)|
| **Multiple Order Clauses**| ✅ (Comma-separated order-by) | ✅ (orderby chain) | ✅ (via UI sorting arrays) |
| **Pagination** | ✅ (`limit_start`, `limit_page_length`) | ✅ (`limit`, `offset`) | ✅ (`limit` / `limit_type`) |

---

## 6. Child DocType Investigation (Critical)

This section directly answers the core architectural questions regarding Child DocType querying in Frappe.

### 6.1 Can `get_list()` query a Child DocType directly?
**Answer**: **No (under standard user contexts)**.
- **Why?**: Child DocTypes (e.g., `Sales Invoice Item`) do not have independent, document-level permissions. In Frappe, permissions are defined on the Parent DocType.
- **Evidence**: In `frappe/model/db_query.py` under `check_read_permission()`, the legacy system checks user permission on the target doctype:
  ```python
  def check_read_permission(self, doctype: str, parent_doctype: str | None = None):
      if self.flags.ignore_permissions:
          return
      # ...
      self._set_permission_map(doctype, parent_doctype)
  ```
  Since `Sales Invoice Item` lacks direct permission entries, `frappe.has_permission()` throws a `PermissionError` for non-Administrators.
- **How to bypass?**: If called with `ignore_permissions=True` (or by the `Administrator`), `get_list()` can query a child table directly.

### 6.2 Can `get_all()` query a Child DocType?
**Answer**: **Yes**.
- **Evidence**: `frappe.get_all()` explicitly forces `ignore_permissions = True` by design. In `frappe/__init__.py`:
  ```python
  def get_all(doctype, *args, **kwargs):
      kwargs["ignore_permissions"] = True
      if "limit_page_length" not in kwargs:
          kwargs["limit_page_length"] = 0
      return get_list(doctype, *args, **kwargs)
  ```
  Because permissions are bypassed, the query executes directly against the Child DocType table (e.g., `tabSales Invoice Item`) without throwing a permission error.

### 6.3 Can filters reference child tables?
**Answer**: **Yes**.
- **Evidence**: Frappe's modern database `Engine` (`frappe/database/query.py`) supports implicit parent-child table joining through both filtering and field-selection syntax. When applying filters, `apply_filters` parses list filters:
  ```python
  elif len(filter) == 4:
      doctype, field, operator, value = filter
      self._apply_filter(field, value, operator, doctype)
  ```
  And `_apply_filter()` automatically joins the child table if the target doctype is a child table:
  ```python
  # apply implicit join if child table is referenced
  if doctype and doctype != self.doctype:
      meta = frappe.get_meta(doctype)
      table = frappe.qb.DocType(doctype)
      if meta.istable and not self.query.is_joined(table):
          self.query = self.query.left_join(table).on(
              (table.parent == self.table.name) & (table.parenttype == self.doctype)
          )
  ```

### 6.4 Does Frappe automatically JOIN child tables?
**Answer**: **Yes**.
- **Evidence**: In `DatabaseQuery.prepare_args()`, child tables found in `self.tables` are automatically joined using a left join:
  ```python
  # left join parent, child tables
  for child in self.tables[1:]:
      parent_name = cast_name(f"{self.tables[0]}.name")
      args.tables += f" {self.join} {child} on ({child}.parenttype = {frappe.db.escape(self.doctype)} and {child}.parent = {parent_name})"
  ```

### 6.5 Can fields reference child table fields?
**Answer**: **Yes**.
- **Example**: `fields=["name", "items.item_code"]` is fully supported.
- **Evidence**: In `DatabaseQuery.parse_args()`, dot-notated fields are resolved into child-table definitions:
  ```python
  # convert child_table.fieldname to `tabChild DocType`.`fieldname`
  for field in self.fields:
      if "." in field:
          # ...
          linked_field = frappe.get_meta(self.doctype).get_field(linked_fieldname)
          # ...
          linked_doctype = linked_field.options
          if linked_field.fieldtype == "Link":
              linked_table = self.append_link_table(linked_doctype, linked_fieldname)
              field = f"{linked_table.table_alias}.`{fieldname}`"
          else:
              field = f"`tab{linked_doctype}`.`{fieldname}`"
  ```
- **Execution**: The child doctype is added to `self.tables`, which subsequently triggers the automatic left join in `prepare_args()`.

### 6.6 Performance and Duplicate Prevention
Child table joins create one-to-many relationships, producing duplicate parent rows in the SQL result set. Frappe handles this duplicate row problem in two ways:
1. **At the Database level**: Using explicit `DISTINCT` flags or `GROUP BY parent.name` constructs.
2. **At the ORM level (`ChildQuery` / `patch_query_execute`)**: Instead of a flat join, the modern database `Engine` executes a main query for the parent records, then runs a separate query (`ChildQuery.get_query`) to fetch child table rows in a single batch using an `IN` clause on parent IDs. These child rows are then mapped back to their respective parents inside python code, avoiding duplicate parent records and preventing the cartesian product overhead entirely.

---

## 7. Parent/Child Join Behavior

The legacy and modern layers generate joins differently:

### 7.1 Legacy Layer (`DatabaseQuery`)
Joins are triggered purely by **string-level field scanning** in `extract_tables()`. When `items.item_code` is passed, `DatabaseQuery` splits the string on the dot, detects that `items` is a Table fieldtype in the parent doctype, and pushes `tabSales Invoice Item` into `self.tables`.
During SQL compilation, `prepare_args` loops over `self.tables[1:]` and appends:
```sql
LEFT JOIN `tabSales Invoice Item` ON (
    `tabSales Invoice Item`.parenttype = 'Sales Invoice'
    AND `tabSales Invoice Item`.parent = `tabSales Invoice`.name
)
```

### 7.2 Modern Layer (`Engine` / `frappe.qb`)
The database `Engine` parses dot-notated fields into structural instances of `ChildTableField` or `LinkTableField` (defined in `frappe/database/query.py`).
- When `apply_select` or `apply_join` is executed on a `ChildTableField`, the engine calls `apply_join()`:
  ```python
  def apply_join(self, query: QueryBuilder) -> QueryBuilder:
      table = frappe.qb.DocType(self.doctype)
      main_table = frappe.qb.DocType(self.parent_doctype)
      if not query.is_joined(table):
          query = query.left_join(table).on(
              (table.parent == main_table.name) & (table.parenttype == self.parent_doctype)
          )
      return query
  ```
- This ensures clean, programmatic joins built using PyPika's AST rather than string interpolation.

---

## 8. Permission Model

Frappe applies access controls at several levels during query execution:

### 8.1 standard query (`frappe.get_list`)
Checks role permissions for the current user and session.
- Invokes `self.check_read_permission()`, which raises `PermissionError` if the user has no permissions.
- Appends `match_conditions` to the SQL query. For example, if a user can only read their own documents, the system appends:
  ```sql
  AND `tabToDo`.owner = 'user@example.com'
  ```
- If a document is shared with the user, the system injects `tabToDo`.name IN (shared document names list).

### 8.2 Bypassed query (`frappe.get_all`)
- Forces `ignore_permissions = True`.
- Standard user restrictions (role checks, owner constraints, sharing) are skipped entirely.
- Executes clean, unconstrained database selections.

### 8.3 Modern Engine (`frappe.database.query.Engine`)
- Validates permissions during execution using the static helper class `Permission`:
  ```python
  class Permission:
      @classmethod
      def check_permissions(cls, query, **kwargs):
          # ...
          for dt in doctype:
              if not frappe.has_permission(dt, "select", ...) and not frappe.has_permission(dt, "read", ...):
                  frappe.throw(_("Insufficient Permission for {0}"))
  ```
- Rejects executing the query if permission is lacking for any table involved.

---

## 9. Query Builder Comparison

The Query Builder (`frappe.qb`) allows writing structured SQL-like queries directly in Python using PyPika.

### Capabilities of Query Builder Unavailable in `get_list()` / `get_all()`
1. **Arbitrary Complex Joins**: `frappe.qb` can join any two DocTypes on arbitrary fields (e.g., `User.name == ToDo.owner`), whereas `get_list()` only supports child tables and standard link-field-to-name relationships.
2. **Subqueries**: Developers can write nested SQL subqueries inside filters or fields.
3. **Complex Aggregations**: Supports advanced SQL functions such as `CASE WHEN`, `COALESCE`, `CONCAT`, and grouping metrics that are normally blocked by legacy regex checks in `DatabaseQuery`.
4. **Union & Intersection**: Combine multiple query objects using `.union()` or `.intersect()`.
5. **No Strict Regex Blocking**: `frappe.qb` generates SQL programmatically; it bypassing regex checking because PyPika compiles python objects directly, eliminating SQL-injection vectors.

---

## 10. FlexiRule Architecture

FlexiRule implements its querying interface in the action handler **Query Records** (`query_records.py`).

### 10.1 Complete Architecture Diagram

```
[ Frontend: QueryRecordsConfig.vue ]
          │ (Saves Config JSON containing reference_doctype, operation, filters, fields)
          ▼
[ Backend: QueryRecordsHandler.execute() ] ───► [ permissions.py: can_skip_permissions() ]
          │ (Parses & validates inputs)                  │ (Checks Audit Reason & Roles)
          ▼                                              ▼
[ apply_input_mapping() ]                          [ Sets ignore_permissions ]
          │ (Injects context variables into config)
          ▼
[ Mode Dispatcher (mode_handlers) ]
   ├─► "Query List"  ───► _query_list()  ───► frappe.get_list()
   ├─► "Query Doc"   ───► _query_doc()   ───► frappe.get_doc() / frappe.get_cached_doc()
   ├─► "Exist Record"───► _exist_record()───► frappe.get_all() (limit 1)
   ├─► "Query Report"───► _query_report()───► frappe.desk.query_report.run()
   ├─► "Count"       ───► _count_records()───► frappe.get_all() (with count(name))
   └─► Aggregate (Sum/Average/Min/Max)   ───► frappe.get_all() (with sum/avg/min/max)
```

### 10.2 Component Analysis
- **Execution Flow**: The frontend user builds filter and field requirements in `QueryRecordsConfig.vue`. When executed, the Pinia/JSON configuration is dispatched to the backend `QueryRecordsHandler.execute()`.
- **Parsing**: Variables inside `{}` are extracted and evaluated dynamically using safe-evaluation context helpers.
- **Validation**: Re-evaluates metadata and confirms that fields specified in filters, order-by clauses, and selections actually exist on the target DocType.
- **Query Construction**: Translates FlexiRule operators (such as "starts with" and "Timespan") into normalized, standard Frappe operator lists (e.g., `like` with `%` suffix or `between` dates) before executing standard Frappe API wrapper functions.

---

## 11. Feature-by-Feature Comparison

| Capability | Frappe Core | FlexiRule | Status |
| :--- | :--- | :--- | :--- |
| **Child DocType Queries** | ✅ (via `get_all` or `ignore_permissions=True`) | ✅ (Indirectly via `frappe.get_list` wrapper) | Supported |
| **Child Table Filtering** | ✅ (Automatic left join parsing) | ❌ (Blocks dots in filter field validations) | **Gapped** |
| **Child Field Selections**| ✅ (Automatic join resolution) | ❌ (Rejects fields with dots) | **Gapped** |
| **Permission Skipping** | ✅ (`ignore_permissions=True`) | ⚠️ (Excellent audit logs, needs AST check validation) | **Partial Gaps** |
| **Query Reports** | ✅ | ✅ | Supported |
| **Aggregations & Metrics**| ✅ | ✅ (Supports Count, Sum, Avg, Min, Max) | Supported |
| **Complex Joins / Unions**| ✅ (Via Query Builder `frappe.qb`) | ❌ | **Missing** |

---

## 12. Gaps, Design Flaws, and Missing Features

### 12.1 Child Table Filtering Gap
- **Evidence**: In `query_records.py`, the validation function `_doctype_has_field` allows dot-notation for validation, but the backend query executor `_resolve_query_filters` does not perform parent-to-child join translations. Furthermore, the frontend `FilterGroup` and `ComboBoxControl` controls explicitly limit options to top-level fields of the reference doctype, preventing users from selecting child table fields.
- **Impact**: Users cannot run queries such as "Get all Sales Invoices where `items.item_code` is X".

### 12.2 Child Field Selection Gap
- **Evidence**: Passing dot-notation fields (e.g. `items.item_code`) to the `fields` array of `frappe.get_list` from FlexiRule fails because the backend field validation `_doctype_has_field` rejects any field references containing dots unless they represent a valid Link/Table relation. The frontend `MultiSelectList` also filters choices to immediate fields only.
- **Impact**: It is impossible to flatten and fetch parent-child combinations in a single action step.

### 12.3 AST Sandboxing Security Flaw
- **Evidence**: `permissions.py` implements `validate_safe_eval` using a standard `compile` pass:
  ```python
  def validate_safe_eval(expression):
      try:
          compile(expression, "<string>", "eval")
      except SyntaxError as e:
          # ...
  ```
  This is a stub check. Since the expression is later passed to `frappe.safe_eval`, an attacker could construct malicious AST payloads (e.g., utilizing list comprehension or class constructor traversals) to bypass standard safe evaluation and achieve a sandbox escape.

---

## 13. Bugs and Behavioral Differences

1. **Strict SQL Check Blockages**: Frappe `DatabaseQuery` utilizes `sanitize_fields` which regex-blocks keywords like `coalesce` or `concat` in legacy strings. If a user tries to map these into `fields` via FlexiRule, the query will crash with "Illegal SQL Query".
2. **PostgreSQL Order By Requirements**: In PostgreSQL, when querying with `distinct=True`, all order-by fields must appear in the selection list. FlexiRule does not ensure that sorting fields are added to the field selections, causing query failures under PostgreSQL backends.

---

## 14. Recommended Improvements

### Improvement 1: Dynamic Child Join Support
- **Reference**: `frappe/database/query.py` -> `ChildTableField.apply_join`
- **Behavior**: Introduce child table dot-notation mapping. When a dot-notated field (e.g., `items.item_code`) is detected in filter groups or selected fields, dynamically join the child table.
- **Priority**: High | **Complexity**: Medium

### Improvement 2: AST Node Validation for Safe Eval
- **Reference**: `flexirule/ruleflow/core/permissions.py` -> `validate_safe_eval`
- **Behavior**: Replace the basic `compile()` check with a robust AST parsing check utilizing Python's `ast` module. Restrict expression nodes to `ast.Expression`, `ast.Name`, `ast.Attribute`, and specific safe mathematical operators. Reject any `ast.Call` nodes unless the function name is explicitly in an approved allowlist.
- **Priority**: Critical | **Complexity**: Medium

### Improvement 3: Query Builder Integration
- **Reference**: `frappe.query_builder` (Pypika engine)
- **Behavior**: Add a "Raw Query Builder" mode to the action handler, allowing developers to construct queries programmatically with PyPika criteria, bypassing string-substitution vulnerabilities entirely.
- **Priority**: Medium | **Complexity**: Large

---

## 15. Prioritized Action Plan

| Step | Action Item | Target File | Priority | Complexity |
| :--- | :--- | :--- | :--- | :--- |
| **1** | Implement Robust AST Node Whitelisting | `flexirule/ruleflow/core/permissions.py` | **Critical** | Medium |
| **2** | Enable Child Table Field Selection & Validation | `flexirule/ruleflow/core/action_handlers/query_records.py` | **High** | Medium |
| **3** | Extend Frontend Filter UI for Child Tables | `QueryRecordsConfig.vue` | **High** | Large |
| **4** | Add Automatic SQL Order-by Selections for Postgres | `flexirule/ruleflow/core/action_handlers/query_records.py` | **Medium** | Small |
| **5** | Integrate Pypika Query Builder Engine Mode | `query_records.py` | **Low** | Large |
