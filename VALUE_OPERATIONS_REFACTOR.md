# FlexiRule Value Operations Architecture Refactor (v2)

This document outlines the proposed architectural refactor for Value Operations in FlexiRule, moving from a fragmented "Resolver-Kind" system to a unified, capability-driven "Operation Registry."

---

## 1. Resolver Evaluation Matrix

Challenge the status quo of existing resolver boundaries.

| Resolver Type | Purpose | Unique Capabilities | Overlap | Recommendation | Justification |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **String Formula** | Simple text/currency ops | None | Normalization, Format, Formulas | **Remove / Merge** | Redundant. Its logic exists in more specialized or functional entry points. |
| **Math Formula** | Simple arithmetic | None | Formulas, Python `flt()` | **Remove / Merge** | Pure UX wrapper for basic Python operators. Should be atomic operations in a registry. |
| **Date Formula** | Date arithmetic | None | Formulas, `frappe.utils` | **Remove / Merge** | UX wrapper. "Add Days" is an operation, not a standalone architecture category. |
| **Normalization** | Data cleaning/standardization | Arabic unification, specialized cleaning | Casing, slugging | **Keep & Rename** | Purpose is valid, but should be renamed to **"Transformation"** and expanded. |
| **Format** | Presentation logic | String Templates, Locale-aware formatting | Currency formatting | **Keep** | Solves the specific problem of *display* vs *value*, which is conceptually distinct. |
| **Child Aggregation** | List math | Table-to-Scalar reduction | `sum`, `count` formulas | **Keep** | Essential for handling list context which requires specific configuration UI. |
| **Fetch** | Remote data | Cross-DocType retrieval | Lookup formula | **Keep** | Distinct capability requiring unique UI for DocType/Field selection. |
| **System Context** | Global state | Role checking, session data | None | **Keep** | Unique source of truth (the environment, not the document). |

---

## 2. Proposed Capability Taxonomy

Operations should be grouped by **author intent**, not implementation logic.

1.  **Text Transformation:** Trimming, casing, slugging, snake_case, find/replace.
2.  **Numeric & Math:** Arithmetic, rounding, absolute value, percentages.
3.  **Date & Time:** Adding/subtracting time units, date differences, relative dates (today, now).
4.  **Data Normalization:** Cleaning phone numbers, emails, tax IDs, Arabic/Persian unification.
5.  **Masking & Privacy:** Masking emails, credit cards, or partial strings (security-centric).
6.  **Formatting & Display:** Currency formatting, date/time formatting, string templates.
7.  **Collection & Aggregation:** Sum, average, count, min/max across child tables.
8.  **Data Retrieval:** Fetching values from linked documents or remote DocTypes.
9.  **Environment & Context:** Current user, role checks, rule metadata.

---

## 3. Proposed Backend Architecture

**Core Principle:** Atomic, registry-bound operations.

-   **`flexirule.ruleflow.operations.registry`**: A centralized singleton registry that maps `operation_id` to an implementation class.
-   **`ValueOperation` (Base Class)**:
    -   `execute(value, context, config)`: Standard interface.
    -   `get_meta()`: Returns required parameters, return type, and description.
-   **Module Structure:**
    -   `operations/text.py`
    -   `operations/math.py`
    -   `operations/date.py`
    -   `operations/normalization.py` (Centralizes all logic from `normalization.py` and `NormalizationResolver`).
-   **Compiler**: `ValueResolver.compile` no longer needs kind-specific logic. It simply looks up the `operation_id` in the registry and builds a standard execution chain.

---

## 4. Proposed Frontend Architecture

**Core Principle:** Discoverability through unified browsing.

-   **`ValueRegistry`**: A shared registry between `formula_registry.js` and `ValueResolverControl`.
-   **`OperationBrowser.vue`**: A "Command Palette" style component used in `FlexValueControl` that allows searching all categories at once.
-   **`GenericOperationConfigurator.vue`**: A metadata-driven UI component that renders inputs based on the operation's parameter definitions (Schema-driven UI).
    -   *Example:* If "Add Days" is selected, it renders a "Base Date" picker and a "Number" input.
-   **Specific Configurators**: Only reserved for complex logic like `Aggregation` (Table selection) or `Fetch` (Link selection).

---

## 5. Recommended End-State (v2)

In FlexiRule v2, the concept of selecting a "Resolver Type" first is eliminated.

### The Author Experience:
1.  User clicks into a value field.
2.  User types `/` to open the **Operation Palette**.
3.  User searches for what they want to *do* (e.g., "mask", "sum", "days").
4.  FlexiRule displays a unified list of matches:
    -   **Add Days** (Date & Time)
    -   **Mask Email** (Masking & Privacy)
    -   **Sum Child Table** (Aggregation)
5.  Selection opens a consistent configuration flyout.
6.  The token in the editor is simply an **Operation Token** (e.g., `[Add 5 Days]`).

### Why this is better:
-   **Zero dead ends:** Users don't need to know if "Slug" is a "Normalization" or a "String Formula."
-   **Higher discoverability:** Powerful features like "Arabic Unification" or "Partial Masking" are surfaced alongside basic tasks.
-   **Maintainability:** Adding a new capability involves adding one class on the backend and one entry in the registry. The UI handles the rest.
-   **Consistency:** All value manipulation follows the same "Search -> Configure -> Tokenize" lifecycle.
