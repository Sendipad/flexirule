# Proposed Canonical Value Resolver Taxonomy

## Executive Summary

Based on deep analysis of actual repository implementations, execution models, frontend strategy builders, and data types, this document presents the proposed canonical **Value Resolver Taxonomy**.

The proposed taxonomy organizes all existing and future resolvers into **4 Canonical Resolver Families** with clear operational verbs.

---

## 1. Master Taxonomy Structure

```
Value Resolver Framework
├── 1. Transform Family (Scalar Value Transformation)
│   ├── Math Arithmetic (math)
│   ├── Date Arithmetic (date_add)
│   ├── Date Difference (date_diff)
│   ├── Text Manipulation (text_op)
│   ├── Text Normalization (normalize)
│   └── Value Formatting (format)
│
├── 2. Collection Family (Array & Table Operations)
│   ├── Query & Filter (filter)
│   ├── Property Extraction (pluck)
│   ├── Distinct Extraction (unique)
│   ├── Existence Validation (any / all)
│   ├── Match Selection (first / find)
│   ├── Row Counting (count)
│   └── Numeric Aggregation (sum / avg / min / max)
│
├── 3. Retrieval Family (Data Lookup)
│   ├── Link Field Record Lookup (fetch)
│   └── Direct Variable Reference (variable)
│
└── 4. Environment Family (System & Session Context)
    ├── Session User (user)
    └── Role Check (role_check)
```

---

## 2. Family Classification & Grouping Strength

| Resolver Kind | Proposed Family | Proposed Operation | Grouping Classification | Justification & Architectural Evidence |
| :--- | :--- | :--- | :--- | :--- |
| `math_formula` | **Transform** | `math` | **Strong Grouping** | Operates on scalar numbers, returns scalar float/int. Pure calculation. |
| `date_formula` | **Transform** | `date_add` | **Strong Grouping** | Operates on scalar dates, returns scalar date. Pure date arithmetic. |
| `date_diff` | **Transform** | `date_diff` | **Strong Grouping** | Measures difference between 2 dates, returns integer delta. |
| `string_formula` | **Transform** | `text_op` | **Strong Grouping** | Combines or alters string scalar inputs (concat, case). |
| `normalization` | **Transform** | `normalize` | **Strong Grouping** | Executes multi-step pipeline text transformations. |
| `format` | **Transform** | `format` | **Strong Grouping** | Converts scalar values into formatted string representations. |
| `collection` | **Collection** | `filter`/`pluck`/`unique`/`any`/`all`/`first` | **Strong Grouping** | Primary engine for array/table row iteration, evaluation, and extraction. |
| `child_aggregation` | **Collection** | `sum`/`avg`/`count` | **Strong Grouping** | Performs math on child tables; logically belongs inside Collection. |
| `fetch` | **Retrieval** | `fetch` | **Strong Grouping** | Fetches external database field value across Link relation. |
| `system_context` | **Environment** | `user`/`role_check` | **Strong Grouping** | Accesses session context (`frappe.session.user`, `frappe.get_roles`). |

---

## 3. Operations Maintained vs Unified

1. **`child_aggregation` -> Integrated into `Collection`**:
   `child_aggregation` operations (`sum`, `avg`, `count`) are unified under `Collection Family`. `count` is native; `sum` and `avg` are added to `CollectionResolver`.
2. **`string_formula.fmt_money` -> Unified into `Transform.Format`**:
   The duplicate currency formatting verb in `string_formula` is folded into `format`.
3. **`find` -> Maintained as UI Alias**:
   `find` remains an alias for `first` in `CollectionResolver` to maintain compatibility with user expectations.
