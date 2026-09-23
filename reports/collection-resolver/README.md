# FlexiRule Collection Resolver Design Documentation

This directory contains the detailed architectural design reports for introducing the **Collection Resolver** to FlexiRule.

## Overview

FlexiRule Beta requires a native mechanism to query, filter, check, and extract values from Frappe child tables (e.g. `doc.items`, `doc.taxes`) and list variables.

The design strictly follows FlexiRule's existing Value Resolver architecture, reusing `CompiledResolver`, `ConditionEvaluator`, and `FieldResolver` while preserving full backward compatibility.

## Document Index

1. **[Executive Summary](executive-summary.md)**: High-level overview, exact scope, matrix, risks, and recommendations.
2. **[Architecture](architecture.md)**: Core architectural principles, integration points, and system boundary map.
3. **[Operations Analysis](operations.md)**: Detailed specification for all candidate operations (`count`, `any`, `all`, `first`, `last`, `find`, `filter`, `pluck`, `unique`).
4. **[Collection vs Loop vs Aggregation](collection-vs-loop-vs-aggregation.md)**: Clear boundary definition between Collection Resolver, Loop Action, and Child Aggregation.
5. **[Data Model](data-model.md)**: Complete JSON schema specifications, serialization contracts, and example payloads.
6. **[Frontend Design](frontend-design.md)**: UI controls, Vue component structure (`CollectionResolver.vue`), Tiptap token integration, and slash commands.
7. **[Backend Design](backend-design.md)**: `CollectionResolver` python implementation details, `ValueResolver` compiler extensions, and `ConditionEvaluator` row context handling.
8. **[Security & Performance](security-and-performance.md)**: Memory safety, DoS prevention, complexity bounds, and non-eval execution analysis.
9. **[Testing Strategy](testing-strategy.md)**: Comprehensive test suite outline including unit, edge case, security, and performance benchmarks.
10. **[Implementation Plan](implementation-plan.md)**: Step-by-step roadmap for post-Beta review implementation.

---
*Status: Design Review Ready (No production code changes applied).*
