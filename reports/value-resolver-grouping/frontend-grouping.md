# Frontend Resolver UX Grouping Analysis

## Executive Summary

This report evaluates how Value Resolvers are presented to users in the Vue.js frontend interface and proposes a structured UX taxonomy for command menus, strategy builders, and modal selectors.

Currently, the frontend exposes resolvers through two primary interaction patterns:
1. **Strategy Selection Menu** in `ValueResolverControl.vue` (strategy buttons rendered from registered strategies in `index.js`).
2. **Slash Command & Formula Registry** in `FlexValueControl.vue` driven by `SLASH_COMMANDS` and `FORMULA_REGISTRY` (`formula_registry.js`).

---

## 1. Current Frontend UX Architecture

### 1.1 Strategy Buttons (`ValueResolverControl.vue`)
Currently, `ValueResolverControl.vue` renders a **flat list** of resolver strategies:
- Date Formula (`date_formula`)
- Collection Query (`collection`)
- Math Formula (`math_formula`)
- Date Difference (`date_diff`)
- Child Table Aggregation (`child_aggregation`)
- String Manipulation (`string_formula`)
- Normalization (`normalization`)
- Format (`format`)
- Fetch From Link (`fetch`)
- System Context (`system_context`)

```
+---------------------------------------------------------------------------------+
|                              ValueResolverControl                               |
+---------------------------------------------------------------------------------+
| [Date Formula] [Collection Query] [Math Formula] [Date Difference]              |
| [Child Aggregation] [String Manipulation] [Normalization] [Format]               |
| [Fetch From Link] [System Context]                                              |
+---------------------------------------------------------------------------------+
```

### 1.2 Slash Command Dropdown (`FlexValueControl.vue` / `formula_registry.js`)
When typing `/` in `FlexValueControl`, users see commands categorized by type:
- `/formula` (Math)
- `/resolver` (Generic)
- `/formatter` (Format)
- `/normalize` (Normalization)
- `/fetch` (Fetch From Link)
- `/collection` (Collection Query)

---

## 2. Conceptual UX Grouping Proposal

Rather than presenting 10 flat buttons, the frontend should organize resolvers into **4 high-level Families**, each containing intuitive **Operations**:

```
+---------------------------------------------------------------------------------+
|                       PROPOSED UX RESOLVER SELECTOR                             |
+---------------------------------------------------------------------------------+
| 1. TRANSFORM & CALCULATION (Scalar Transformation)                              |
|    ├── Math Arithmetic (+, -, *, /)                                            |
|    ├── Date Arithmetic (+/- Days/Months/Years)                                 |
|    ├── Date Difference (Delta in Days/Months/Years)                            |
|    ├── Text Manipulation (Concat, Upper, Lower)                                |
|    ├── Text Normalization (Trim, Slug, Snake Case)                             |
|    └── Value Formatting (Date Mask, Currency)                                  |
|                                                                                 |
| 2. COLLECTION & TABLE (Array Operations)                                        |
|    ├── Query & Filter (Filter rows by condition)                               |
|    ├── Extraction (Pluck field array, Unique values)                           |
|    ├── Membership & Checks (Any match, All match)                              |
|    └── Aggregation (Sum, Avg, Min, Max, Count)                                 |
|                                                                                 |
| 3. DATA RETRIEVAL (Document & Context Lookup)                                   |
|    ├── Fetch Link Record (frappe.db.get_value)                                 |
|    └── Direct Reference (doc.field, vars.variable)                             |
|                                                                                 |
| 4. SYSTEM & SESSION (Environmental Context)                                     |
|    ├── Session User (frappe.session.user)                                      |
|    └── Role Validation ("System Manager" in roles)                             |
+---------------------------------------------------------------------------------+
```

---

## 3. Benefits of Frontend UX Grouping

1. **Cognitive Load Reduction**: Users choose among 4 clear categories instead of scanning 10 unorganized choices.
2. **Elimination of Confusing Overlaps**: Presenting `Collection & Table` as a single family removes the confusion between `child_aggregation` and `collection`.
3. **Fieldtype Filtering Consistency**: The `getAllowedBuilderKinds(fieldtype)` function in `formula_registry.js` can filter entire families (e.g., hiding `Collection` when editing a scalar Int field, showing `Collection` when editing a Table field).
