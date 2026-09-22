# Frontend Logical Commands Audit & UI Gap Analysis

## 1. Executive Summary
*   **Total Logical Commands Identified:** 25
*   **Fully Configurable (Complete):** 16 / 64%
*   **Gaps / Incomplete UI Integration:** 9 / 36%

Overall, the core logical commands (ValueResolver kinds) are well-integrated with the `ValueResolverControl.vue` component, maintaining high parity with the Python `ValueResolver` implementation. However, more advanced features like the `TransformControl` visual mapper and the `TextGeneratorControl` (Jinja builder) have significant gaps—notably the missing "Expression Editor" in the mapper and incomplete support for complex Jinja structures like `elif` branches in the visual editor. Additionally, several logical kinds (e.g., `fetch`, `lookup`) are registered in the frontend metadata but lack both backend execution logic and proper UI configuration panels, leading to dead-end features.

## 2. Command Inventory & UI Mapping Matrix

| Command / Function Name | Type | Source Code File | UI Config Component File | Implementation Status | Required Props Missing from UI |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `math_formula` | Resolver | `value_resolver.py` | `ValueResolverControl.vue` | Complete | None |
| `date_formula` | Resolver | `value_resolver.py` | `ValueResolverControl.vue` | Complete | `offset_sign` (handled via local state) |
| `date_diff` | Resolver | `value_resolver.py` | `ValueResolverControl.vue` | Complete | None |
| `child_aggregation` | Resolver | `value_resolver.py` | `ValueResolverControl.vue` | Complete | None |
| `string_formula` | Resolver | `value_resolver.py` | `ValueResolverControl.vue` | Complete | None |
| `normalization` | Resolver | `value_resolver.py` | `ValueResolverControl.vue` | Complete | None |
| `format` | Resolver | `value_resolver.py` | `ValueResolverControl.vue` | Complete | None |
| `system_context` | Resolver | `value_resolver.py` | `ValueResolverControl.vue` | Complete | None |
| `fetch` | Resolver | `value_resolver.py` (Missing) | `ValueResolverControl.vue` | Missing UI | Entire config panel missing |
| `lookup` | Resolver | N/A | `ValueResolverControl.vue` | Missing UI | Entire config panel missing |
| `Assignment` | Engine | `assignment.py` | `AssignmentConfig.vue` | Complete | None (Uses FlexValueControl) |
| `Jinja segments` | Text Gen | `text_generator.js` | `TextGeneratorControl.vue` | Incomplete | `elif` branches in visual mode |
| `Translation` | Text Gen | `text_generator.js` | `TextGeneratorControl.vue` | Complete | None |
| `Scalar Mapping` | Mapper | `mapping.py` | `ResourceMapperControl.vue` | Complete | None |
| `Child Table Mapping` | Mapper | `mapping.py` | `ResourceMapperControl.vue` | Complete | None |
| `Visual Mapper` | Mapper | `transform.js` | `TransformControl.vue` | Incomplete | Expression Editor, Child Table support |
| `Simple Condition` | Condition | `compiler.py` | `SimpleCondition.vue` | Complete | None |
| `Group Condition` | Condition | `compiler.py` | `ConditionBuilder.vue` | Complete | None |
| `Collection Condition`| Condition | `compiler.py` | `ConditionBuilder.vue` | Complete | None |
| `is_submittable` | Operator | `compiler.py` | `SimpleCondition.vue` | Incomplete | UI Value input (unary in backend) |
| `has_changed` | Operator | `compiler.py` (Deprecated) | `SimpleCondition.vue` | Incomplete | Deprecated but still in UI |
| `length_eq/gt/...` | Operator | `compiler.py` | `SimpleCondition.vue` | Complete | None |
| `starts/ends with` | Operator | `query_records.py` | `FilterGroup.vue` | Complete | None |
| `Timespan` | Operator | `query_records.py` | `FilterGroup.vue` | Complete | None |
| `Between` | Operator | `query_records.py` | `FilterGroup.vue` | Complete | None |
| `SafeEval` | Resolver | `value_resolver.py` | `FlexValueControl.vue` | Complete | None |

## 3. Detailed Gap Breakdown
*   **Assignment Config Integration:** The `AssignmentConfig.vue` acts as a heavy orchestration layer for the `ValueResolver` system. It utilizes `FlexValueControl.vue` for every assignment row, correctly passing context (target field type and operator) to filter available resolver kinds. It implements intelligent defaulting (e.g., defaulting to `math_formula` for numeric targets). The integration is programmatically complete, relying on the underlying controls for actual logic configuration.
*   **fetch / lookup Resolvers:** These kinds are registered in `formula_registry.js` and appear in the `/` command list, but `ValueResolverControl.vue` has no template block to configure them, and the `ValueResolver` backend does not yet implement the `FetchResolver` (though it exists in historical PRs).
*   **TextGeneratorControl (Conditional Block):** The visual editor supports `if` and `else` blocks, but the `elif_branches` support defined in `text_generator.js` is not exposed in the `TextGeneratorControl.vue` settings panel, making complex branching logic hard to build visually.
*   **TransformControl:** The visual mapping interface is a "shell" that lacks the "Future: Add expression editor here" functionality. Users can draw lines but cannot apply logic to the transformation (e.g., mapping `first_name + last_name` to `full_name`).
*   **Visual Mapper (Integration):** The `DocumentActionConfig.vue` integration of the visual mapper currently only supports scalar fields. Any child table mappings configured in the classic mapper are lost or hidden when switching to the visual view.
*   **is_submittable / unary operators:** In the `ConditionBuilder`, these operators still show a value input field (via `FlexValueControl`) even though the backend implementation is unary (it doesn't use the `right` operand).

## 4. Recommended Action Items
1.  **Prioritized UI Enhancement:** Implement the `fetch` and `lookup` configuration panels in `ValueResolverControl.vue` to bring them online.
2.  **Mapper Completion:** Build the inline expression editor for `TransformControl.vue` to allow functional data transformations during visual mapping.
3.  **Visual Logic Parity:** Add "Add Elif Branch" functionality to the `TextGeneratorControl.vue` bottom panel for conditional nodes.
4.  **UX Cleanup:** Update `SimpleCondition.vue` to hide the value input column when unary operators (like `is_set`, `is_submittable`) are selected.
5.  **Deprecation:** Formally remove `has_changed` from the `ConditionBuilder` UI to align with its deprecated status in the backend `ConditionCompiler`.
