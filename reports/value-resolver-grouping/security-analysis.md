# Security Analysis & Source Verification

## 1. Verified Security Claims Matrix

Every security claim in the Value Resolver architecture was audited against actual source code in `flexirule/ruleflow/core/`.

| Security Claim | Source File | Relevant Class / Function | Verified Implementation Status | Identified Risk / Required Action |
| :--- | :--- | :--- | :--- | :--- |
| **Non-Eval Collection Execution** | `flexirule/ruleflow/core/evaluator.py` | `ConditionEvaluator` | **VERIFIED**: Evaluates structured JSON nodes via Python `operator` module (`operator.gt`, `operator.eq`). Zero string `eval()` or `exec()`. | **Low Risk**: Maintain non-eval execution paradigm in `CollectionResolver`. |
| **SafeEval AST Whitelist** | `flexirule/ruleflow/core/permissions.py` | `SafeEvalVisitor(ast.NodeVisitor)` | **VERIFIED**: Inspects AST nodes. Permits `BinOp`, `UnaryOp`, `Name`, `Constant`, `Call`, `Attribute`. | **Medium Risk**: Refine `visit_Attribute` to explicitly block `node.attr.startswith("__")`. |
| **Blocked AST Constructs** | `flexirule/ruleflow/core/permissions.py` | `validate_safe_eval(expr)` | **VERIFIED**: Blocks import statements, lambda expressions, function definitions, and dunder attributes. | **Low Risk**: Enforce `validate_safe_eval` before compiling expressions in `MathFormulaResolver`. |
| **Jinja SSTI Shield** | `flexirule/ruleflow/core/action_handlers/document_action.py` | `_template_context()` | **VERIFIED**: Raw `frappe` module is excluded from context. Only `doc`, `old_doc`, `vars`, and standard format functions exposed. | **Low Risk**: Maintain strict Jinja context sanitization in `FormatResolver`. |
| **Lookup Permission Enforcement** | `flexirule/ruleflow/utils/field_resolver.py` & `value_resolver.py` | `FetchResolver.resolve()` | **PARTIALLY VERIFIED**: Resolves link field via `FieldResolver`. However, `FetchResolver.resolve()` bypasses explicit `frappe.has_permission()` if executed in background job. | **High Risk**: Add explicit `frappe.has_permission(linked_doctype, "read")` check in `FetchResolver`. |
| **Dynamic DocType Validation** | `flexirule/ruleflow/utils/field_resolver.py` | `FieldResolver` | **VERIFIED**: Sanitizes target DocType string against `frappe.get_meta(doctype)`. | **Low Risk**: Validate metadata prior to query execution. |
| **Collection Row Safety Guard** | `flexirule/ruleflow/core/value_resolver.py` | `CollectionResolver.MAX_COLLECTION_ROWS` | **VERIFIED**: `MAX_COLLECTION_ROWS = 10000` enforced. Raises `MethodExecutionError` if exceeded. | **Low Risk**: Preserve 10,000 row safety limit. |

---

## 2. Recommended Security Enhancements for Phase 2

1. **Explicit Permission Checking in `FetchResolver` / `LookupResolver`**:
   ```python
   if not frappe.has_permission(self.linked_doctype, "read"):
       raise frappe.PermissionError(f"User lacks read permission on {self.linked_doctype}")
   ```

2. **Dunder Attribute Guard in `SafeEvalVisitor`**:
   Ensure `SafeEvalVisitor.visit_Attribute` explicitly raises `PermissionError` if `node.attr.startswith("__")`.
