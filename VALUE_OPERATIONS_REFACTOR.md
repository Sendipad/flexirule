# FlexiRule Value Operations Architecture Refactor

This document outlines the proposed target architecture for Value Operations in FlexiRule, moving from a fragmented "Resolver-Kind" system to a unified, capability-driven "Operation Registry."

---

## 1. Resolver Evaluation Matrix

Challenge the status quo of existing resolver boundaries.

| Resolver Type | Purpose | Unique Capabilities | Overlap | Recommendation | Justification |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **String Formula** | Simple text/currency ops | None | Normalization, Format, Formulas | **Remove / Merge** | Redundant. Its logic exists in more specialized or functional entry points. |
| **Math Formula** | Simple arithmetic | None | Formulas, Python `flt()` | **Remove / Merge** | Pure UX wrapper for basic Python operators. Should be atomic operations in a registry. |
| **Date Formula** | Date arithmetic | None | Formulas, `frappe.utils` | **Remove / Merge** | UX wrapper. "Add Days" is an operation, not a standalone architecture category. |
| **Normalization** | Data cleaning/standardization | Arabic unification, specialized cleaning | Casing, slugging | **Keep** | Highly specialized domain with deep logic that shouldn't be diluted into general transformation. |
| **Format** | Presentation logic | String Templates, Locale-aware formatting | Currency formatting | **Keep** | Solves the specific problem of *display* vs *value*, which is conceptually distinct. |
| **Child Aggregation** | List math | Table-to-Scalar reduction | `sum`, `count` formulas | **Keep** | Essential for handling list context which requires specific configuration UI. |
| **Fetch** | Remote data | Cross-DocType retrieval | Lookup formula | **Keep** | Distinct capability requiring unique UI for DocType/Field selection. |
| **System Context** | Global state | Role checking, session data | None | **Keep** | Unique source of truth (the environment, not the document). |

---

## 2. Proposed Capability Taxonomy

Operations should be grouped by **author intent**, maintaining distinct domains for specialized data handling.

1.  **Text Operations:** Trimming, casing, slugging, snake_case, find/replace, concatenation.
2.  **Numeric & Math:** Arithmetic, rounding, absolute value, percentages.
3.  **Date & Time:** Adding/subtracting time units, date differences, relative dates (today, now).
4.  **Data Normalization:** Cleaning phone numbers, emails, tax IDs, Arabic/Persian unification.
5.  **Masking & Privacy:** Masking emails, credit cards, or partial strings (security-centric).
6.  **Formatting & Localization:** Currency formatting, date/time formatting, string templates, locale overrides.
7.  **Collection & Aggregation:** Sum, average, count, min/max across child tables.
8.  **Data Retrieval:** Fetching values from linked documents or remote DocTypes.
9.  **Environment & Context:** Current user, role checks, rule metadata.

---

## 3. Proposed Backend Architecture

**Core Principle:** Registry-bound operations with flexible input signatures.

-   **`flexirule.ruleflow.operations.registry`**: A centralized singleton registry that maps `operation_id` to an implementation class.
-   **`ValueOperation` (Base Class)**:
    -   `execute(context, config)`: Standard non-unary interface. Configuration handles all specific inputs (including target values if applicable).
    -   `get_meta()`: Returns required parameters, return type, and description.
-   **Module Structure:**
    -   `operations/text.py`
    -   `operations/math.py`
    -   `operations/date.py`
    -   `operations/normalization.py`
    -   `operations/masking.py`
-   **Compiler**: `ValueResolver.compile` simply looks up the `operation_id` in the registry and builds a standard execution call passing the context and pre-parsed config.

---

## 4. Proposed Frontend Architecture

**Core Principle:** Hybrid configuration for optimal UX.

-   **`ValueRegistry`**: A shared registry between `formula_registry.js` and `ValueResolverControl`.
-   **`OperationBrowser.vue`**: A "Command Palette" style component used in `FlexValueControl` that allows searching all categories at once.
-   **Hybrid Configuration System**:
    -   **Metadata-Driven Renderer**: For simple operations (e.g., Round, Trim, Add Days), the UI is automatically generated from the operation's metadata/schema.
    -   **Dedicated Vue Components**: For complex operations where a generic form is insufficient (e.g., `Aggregation`, `Fetch`, `System Context`, `Template Formatting`), the registry allows mapping an `operation_id` to a specialized Vue configuration component.
-   **Orchestrator**: A unified modal that determines whether to show the generic renderer or the dedicated component based on the selected operation.

---

## 5. Recommended End-State

The new architecture eliminates the need for users to understand "Resolver Kinds" before they start searching for functionality.

### The Author Experience:
1.  User clicks into a value field.
2.  User types `/` to open the **Operation Palette**.
3.  User searches for what they want to *do* (e.g., "mask", "sum", "days").
4.  FlexiRule displays a unified list of matches categorized by domain:
    -   **Add Days** (Date & Time)
    -   **Mask Email** (Masking & Privacy)
    -   **Normalize Phone** (Data Normalization)
5.  Selection opens the configuration flyout:
    -   *Simple ops:* Use the generic renderer.
    -   *Complex ops:* Use the dedicated Vue component.
6.  The token in the editor is an **Operation Token** (e.g., `[Add 5 Days]`).

### Why this is better:
-   **No "Type-First" Friction:** Users don't need to know if "Slug" is a "Normalization" or a "String Formula."
-   **Flexible API:** Supporting `execute(context, config)` allows for N-ary operations (Concat), null-input operations (System Context), and complex retrieval (Fetch).
-   **Maintainability:** Most new operations can be added via metadata alone. Dedicated components are only written when the UX requires a specialized interface.
-   **Discoverability:** Surfaces powerful hidden capabilities (Arabic Unification, Masking) alongside standard ones.
