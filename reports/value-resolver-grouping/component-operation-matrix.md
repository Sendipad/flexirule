# Component-Operation Mapping Matrix

## 1. Executive Strategy Mapping Table

The following matrix provides the explicit, evidence-based mapping from development-era resolver strategies (`kind`) to the proposed canonical user-facing family, operation, and backend execution strategy for FlexiRule v1.0.

| Current Strategy (`kind`) | Current UI Component | Proposed Family (`family`) | Proposed Operation (`operation`) | Internal Strategy Class | Action / Mapping Summary |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `date_formula` | `DateFormulaResolver.vue` | `date` | `calculate` | `DateFormulaResolver` | Consolidated into `DateResolver.vue` as `date.calculate`. |
| `date_diff` | `DateDiffResolver.vue` | `date` | `diff` | `DateDiffResolver` | Consolidated into `DateResolver.vue` as `date.diff`. |
| `format` (for dates) | `FormatResolver.vue` | `date` | `format` | `FormatResolver` | Date formatting moved into `DateResolver.vue` as `date.format`. |
| `string_formula` (`concat`) | `StringFormulaResolver.vue` | `text` | `combine` | `StringFormulaResolver` | String join moved into `TextResolver.vue` as `text.combine`. |
| `string_formula` (`upper`/`lower`)| `StringFormulaResolver.vue` | `text` | `case` | `NormalizationResolver` | Case change merged into `TextResolver.vue` as `text.case`. |
| `string_formula` (`fmt_money`) | `StringFormulaResolver.vue` | `number` | `format_money` | `FormatResolver` | **Moved to Number family** to eliminate duplication. |
| `normalization` | `NormalizationResolver.vue` | `text` | `normalize` | `NormalizationResolver` | Multi-step pipeline moved into `TextResolver.vue` as `text.normalize`. |
| `format` (for text) | `FormatResolver.vue` | `text` | `format` | `FormatResolver` | Text templating moved into `TextResolver.vue` as `text.format`. |
| `math_formula` | `MathFormulaResolver.vue` | `number` | `calculate` | `MathFormulaResolver` | Basic arithmetic moved into `NumberResolver.vue` as `number.calculate`. |
| `math_formula` (`round`) | `MathFormulaResolver.vue` | `number` | `round` | `MathFormulaResolver` | Numeric rounding moved into `NumberResolver.vue` as `number.round`. |
| `format` (`fmt_money`) | `FormatResolver.vue` | `number` | `format_money` | `FormatResolver` | Currency formatting unified in `NumberResolver.vue` as `number.format_money`. |
| `child_aggregation` | `AggregationResolver.vue` | `collection` | `sum`, `average`, `count` | `ChildAggregationResolver` | Exposed under `CollectionResolver.vue`; dispatches to direct child table math. |
| `collection` | `CollectionResolver.vue` | `collection` | `count`, `any`, `all`, `filter`, `pluck`, `unique` | `CollectionResolver` | Memory-safe collection query engine in `CollectionResolver.vue`. |
| `fetch` | `FetchResolver.vue` | `lookup` | `field` | `FetchResolver` | UI renamed from "Fetch From Link" to "Lookup" (`LookupResolver.vue`). |
| `system_context` | `SystemContextResolver.vue` | `system` | `user`, `roles`, `today`, `now` | `SystemContextResolver` | UI renamed to "System & Context" (`SystemResolver.vue`). |
| *New* | N/A | `conversion` | `to_text`, `to_number`, `to_date`, `to_boolean` | `ConversionResolver` | Explicit type casting component (`ConversionResolver.vue`). |
| *New* | N/A | `conditional` | `if_else`, `coalesce` | `ConditionalResolver` | Inline branching component (`ConditionalResolver.vue`). |

---

## 2. In-Depth Analysis of Critical Overlaps

### 2.1 The `fmt_money` Duplication Resolution

Currently, `fmt_money` is defined in three separate UI/backend locations:
1. `StringFormulaResolver.vue` (`str_op: "fmt_money"`)
2. `FormatResolver.vue` (`fmt_op: "fmt_money"`)
3. `flexirule/ruleflow/core/action_handlers/__init__.py`

**Canonical Decision**:
- `fmt_money` is removed from `StringFormulaResolver` and `FormatResolver`.
- It is assigned exclusively to the **Number** family as operation `format_money`.
- **Reasoning**: Currency formatting operates on numeric values (`Float`, `Int`, `Currency`). Rendering currency symbols and precision belongs in the Number domain. Placing it under Text creates confusion when users look for financial formatting.

---

### 2.2 `string_formula` vs `normalization` vs `format`

Currently, `string_formula` provides `uppercase`/`lowercase`, `normalization` provides `upper`/`lower`, and `format` provides general formatting.

**Canonical Decision**:
- All string operations are consolidated under **Text** (`TextResolver.vue`).
- Operations:
  - `combine`: Multi-string or field concatenation.
  - `case`: Single case transformations (`upper`, `lower`, `title`).
  - `normalize`: Pipeline operations (`trim`, `slug`, `snake`, `remove_accents`).
  - `format`: Jinja/Python string interpolation.
- **Backend Strategy**: The backend `NormalizationResolver` class handles both case and pipeline normalization, while `StringFormulaResolver` handles joins.

---

### 2.3 `collection` vs `child_aggregation`

Currently, `child_aggregation` processes Frappe child table columns via SQL/direct iteration, while `collection` filters list variables and child table rows using `ConditionEvaluator`.

**Canonical Decision**:
- Both capabilities are exposed under a single user-facing Component: **Collections & Tables** (`CollectionResolver.vue`).
- The user selects the operation (`Sum`, `Average`, `Count`, `Filter`, `Pluck`, `Any`, `All`).
- The frontend compiler checks if the source is a simple child table field (e.g. `doc.items`) and dispatches to `child_aggregation` internally if numeric aggregation (`sum`/`avg`) is chosen, or to `collection` if predicate filtering/plucking is chosen.
- This preserves the high-performance execution paths of `child_aggregation` while giving the user a unified mental model.
