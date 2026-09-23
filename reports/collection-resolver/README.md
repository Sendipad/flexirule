# FlexiRule Collection Resolver Design Documentation

This directory contains the verified architectural design reports for introducing the **Collection Resolver** to FlexiRule.

## Overview

FlexiRule Beta requires a native mechanism to query, filter, check, and extract values from Frappe child tables (e.g. `doc.items`, `doc.taxes`) and list variables.

The design strictly follows FlexiRule's existing Value Resolver architecture, reusing `CompiledResolver`, `ConditionEvaluator`, and `get_context_value` while preserving full backward compatibility.

## Document Index

1. **[Executive Summary](executive-summary.md)**: High-level overview, verified scope, matrix, risks, and recommendations.
2. **[Architecture](architecture.md)**: Core architectural principles, verified API integration points, and system boundary map.
3. **[Operations Analysis](operations.md)**: Detailed classification and specifications for candidate operations (`count`, `any`, `all`, `first`, `find`, `filter`, `pluck`, `unique`).
4. **[Collection vs Loop vs Aggregation](collection-vs-loop-vs-aggregation.md)**: Clear boundary definition between Collection Resolver, Loop Action, and Child Aggregation.
5. **[Data Model](data-model.md)**: Verified JSON schema specifications, serialization contracts, and example payloads.
6. **[Frontend Design](frontend-design.md)**: UI controls, Vue component structure (`CollectionResolver.vue`), Tiptap token integration, and slash commands.
7. **[Backend Design](backend-design.md)**: Verified `CollectionResolver` python class implementation, `ValueResolver` compiler extensions, and `ConditionEvaluator` row context handling.
8. **[Security & Performance](security-and-performance.md)**: Memory safety, DoS prevention (10,000 row exception guard), complexity bounds, and non-eval execution analysis.
9. **[Testing Strategy](testing-strategy.md)**: Comprehensive test suite outline including unit, edge case, security, and performance benchmarks.
10. **[Implementation Plan](implementation-plan.md)**: Step-by-step roadmap for post-Beta review implementation.
11. **[Design Review & Decision](design-review.md)**: Master decision document verifying all 16 architectural contracts and providing the final implementation status.

---
*Status: READY FOR IMPLEMENTATION (No production code changes applied).*
