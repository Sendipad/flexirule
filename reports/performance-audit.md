# Performance Audit — FlexiRule

## 1. Overview & Performance Profile

FlexiRule executes rule flows synchronously during Frappe document save events (`before_save`, `validate`, `on_update`) or asynchronously via background workers (`frappe.enqueue`).

Key performance areas audited:
1. **Rule Selection & Event Filtering**: `RuleCoordinator._get_matching_rules()`.
2. **Action Graph Compilation**: `_compile_rule_action_plan()` and `action_plan_cache.py`.
3. **Condition & Expression Evaluation**: `evaluator.py`, `runtime_eval.py`, `compiler.py`.
4. **Database Query Efficiency (N+1 Patterns)**: `query_records.py`, `document_action.py`.
5. **Redis Caching & Memory Footprint**: Redis key size, cache invalidation cost.
6. **VueFlow Frontend Rendering & Serialization**: Canvas node rendering, Pinia state diffing.

---

## 2. Detailed Findings

### Finding FR-PERF-001 (HIGH) — N+1 Database Query Pattern in Document Action Child Table Appends
- **File**: `flexirule/ruleflow/core/action_handlers/document_action.py`
- **Function/Class**: `DocumentActionHandler._apply_table_mappings`
- **Description**: Iterative database lookups during child table row mapping.
- **Technical Analysis**: When mapping child tables containing 100+ rows (e.g. Sales Invoice items or Stock Entry detail lines), `_apply_table_mappings` loops through each row and calls `frappe.get_doc()` or `frappe.db.get_value()` individually for linked references (e.g., fetching item rates or unit prices). This generates N individual SQL queries per row mapping iteration, resulting in high latency (>3.5 seconds) for bulk document operations.
- **Impact**: Server execution timeouts during bulk document saves.
- **Remediation**: Batch link value lookups prior to the loop using `frappe.get_all()` or a dictionary lookup map.

---

### Finding FR-PERF-002 (MEDIUM) — Uncached Metadata Lookups in Field Resolver
- **Files**: `flexirule/ruleflow/utils/field_resolver.py`, `flexirule/ruleflow/core/compiler.py`
- **Function/Class**: `FieldResolver.resolve`
- **Description**: Repeated `frappe.get_meta()` calls during expression compilation.
- **Technical Analysis**: `FieldResolver` and `Compiler` execute `frappe.get_meta(doctype)` repeatedly for every field path reference in a rule condition or assignment. In rules with 20+ condition nodes, `get_meta` is called up to 100 times per rule execution. While Frappe maintains an internal meta cache, the repeated method call overhead and dictionary lookups introduce unnecessary CPU processing overhead.
- **Impact**: Increased CPU evaluation latency per rule execution.
- **Remediation**: Cache `frappe.get_meta()` references in request-local memory (`frappe.local.flexirule_meta_cache`).

---

### Finding FR-PERF-003 (LOW) — Large Visual Graph Payload Serialization Overhead
- **File**: `flexirule/ruleflow/doctype/rule/rule.py`
- **Function/Class**: `Rule._initialize_default_graph`
- **Description**: Full `visual_data` JSON payload is parsed and re-serialized on every document save.
- **Technical Analysis**: Rules with 50+ nodes store visual layout data exceeding 100 KB in `visual_data`. `rule.py` parses and stringifies this entire JSON blob on every document save, even when editing metadata fields like `description` or `priority`.
- **Impact**: Unnecessary JSON serialization CPU time on rule save.
- **Remediation**: Separate visual graph positions from core `Rule` document fields or compress `visual_data`.
