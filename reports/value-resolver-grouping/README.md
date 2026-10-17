# FlexiRule Value Resolver Grouping & Taxonomy Report

## Executive Summary

This repository contains a comprehensive architectural audit and design analysis of FlexiRule's Value Resolver system.

The objective of this analysis is to evaluate all existing Value Resolver implementations (`date_formula`, `math_formula`, `date_diff`, `child_aggregation`, `string_formula`, `normalization`, `format`, `fetch`, `system_context`, and the newly implemented `collection` resolver) and propose a clean, maintainable, evidence-based **Resolver Taxonomy**.

---

## Answers to Key Executive Questions

### 1. How many resolver kinds currently exist?
There are **10 explicit registered resolver kinds** (`date_formula`, `math_formula`, `date_diff`, `child_aggregation`, `string_formula`, `normalization`, `format`, `fetch`, `system_context`, `collection`) plus **5 implicit core evaluation modes** (`static`, `variable`, `expression`, `jinja`, `safe_eval`), totaling **15 resolver mechanisms**.

### 2. How many logical resolver families exist?
There are **4 logical resolver families**:
1. **Transform Family** (Scalar math, date arithmetic, date diff, text operations, normalization, formatting)
2. **Collection Family** (Child table and array filtering, extraction, membership, counting, and aggregation)
3. **Retrieval Family** (Cross-document Link database fetching and variable reference)
4. **Environment Family** (Session user and role context checks)

### 3. Which resolvers strongly overlap?
- **`child_aggregation` and `collection`**: `child_aggregation.count` is 100% identical to `collection.count`. `child_aggregation.sum/avg` overlap with `collection.pluck` + sum/avg.
- **`format` and `string_formula`**: Currency formatting (`fmt_money`) is defined independently in both resolvers.
- **`string_formula` and `normalization`**: String casing (`uppercase`/`lowercase` vs `upper`/`lower`) is defined independently in both resolvers.

### 4. Does Collection Resolver duplicate any existing functionality?
Yes. `collection.count` completely duplicates `child_aggregation.count`.

### 5. Does `child_aggregation` overlap with Collection Resolver?
Yes. `child_aggregation` is a specialized, condition-less subset of Collection table operations.

### 6. Are any resolvers effectively aliases of one another?
Within `CollectionResolver`, `operation = "find"` is an explicit in-memory alias for `operation = "first"`.

### 7. Which resolver kinds should conceptually be grouped?
- `math_formula`, `date_formula`, `date_diff`, `string_formula`, `normalization`, and `format` should be grouped into the **Transform Family**.
- `collection` and `child_aggregation` should be grouped into the **Collection Family**.
- `fetch` and `variable` references should be grouped into the **Retrieval Family**.
- `system_context` should be grouped into the **Environment Family**.

### 8. Which should remain independent?
Each family's operational verbs (e.g. `pluck` vs `filter` vs `date_add` vs `math`) should remain independent operations inside their parent family.

### 9. What should the canonical resolver taxonomy look like?
A 2-level hierarchy: **Resolver Family -> Resolver Operation** (e.g. `Collection -> Filter`, `Transform -> Math`).

### 10. What would be the migration impact?
**Zero downtime / Zero breakage**. Using in-memory alias routing in `ValueResolver.compile_resolver_config`, existing stored rules with legacy `kind` properties will compile seamlessly without database SQL migrations.

### 11. What should be done before implementing any consolidation?
First, add numeric aggregation operations (`sum`, `avg`, `min`, `max`) directly to `CollectionResolver` so that `child_aggregation` can be completely represented by `CollectionResolver`.

---

## Detailed Audit Reports

1. [Canonical Resolver Inventory](resolver-inventory.md)
   - Complete inventory of all 10 registered resolvers and 5 implicit evaluation modes.
2. [Deep Collection Resolver Analysis](collection-resolver-analysis.md)
   - Architectural analysis of the Collection Resolver, its 8 operations, predicate evaluation, and alias relationships.
3. [Resolver Overlap Analysis](resolver-overlap.md)
   - Detailed analysis of overlapping capabilities between resolvers and non-resolver codebase utilities.
4. [Proposed Resolver Taxonomy](resolver-taxonomy.md)
   - The proposed 4-family taxonomy proposal with strong/weak grouping classifications.
5. [Frontend UX Grouping Analysis](frontend-grouping.md)
   - Analysis of strategy button selectors, command menus, and UI category organization.
6. [Backend Architecture Grouping Analysis](backend-grouping.md)
   - Proposed 3-tier backend dispatch hierarchy (`Resolver -> Family -> Operation -> Executor`).
7. [Configuration Consistency Analysis](configuration-analysis.md)
   - Comparison of configuration schemas and standardized schema proposal.
8. [Compatibility & Migration Analysis](compatibility-analysis.md)
   - In-memory alias routing, token serialization impact, and master compatibility matrix.
9. [Architectural Findings](findings.md)
   - Structured findings (`VR-GROUP-001` through `VR-GROUP-005`).
10. [Remediation & Execution Roadmap](remediation-plan.md)
    - Phased, zero-breakage implementation roadmap for future execution.
