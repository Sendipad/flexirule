# Value Resolver Consolidation & Canonical Architecture Specification

## Overview

This directory contains the complete, evidence-based architectural specification for FlexiRule's Value Resolver system, prepared for the first public/installable release.

FlexiRule is currently in pre-release development. This architectural investigation defines the target first-release Value Resolver taxonomy, user-facing component structure, canonical `family + operation + config` contract, compiler/runtime dispatch architecture, security bounds, performance profile, test strategy, and Phase 2 implementation plan.

---

## Architectural Reports Index

| Report File | Description |
| :--- | :--- |
| [`executive-summary.md`](executive-summary.md) | High-level summary of findings, architectural shift, core taxonomy, and key decisions. |
| [`current-resolver-inventory.md`](current-resolver-inventory.md) | Exhaustive inventory of current development-era resolvers across frontend and backend. |
| [`proposed-user-taxonomy.md`](proposed-user-taxonomy.md) | User-facing taxonomy design optimized for Rule Designers and Business Analysts. |
| [`component-operation-matrix.md`](component-operation-matrix.md) | Detailed mapping matrix between current strategy kinds, user-facing families, and operations. |
| [`canonical-resolver-contract.md`](canonical-resolver-contract.md) | Formal JSON schema and specification for the canonical `family + operation + config` model. |
| [`frontend-architecture.md`](frontend-architecture.md) | Component boundaries, operation registry design, Vue state management, and control integration. |
| [`backend-architecture.md`](backend-architecture.md) | Compiler dispatch, runtime resolution, AST generation, and backward-compatible normalization. |
| [`development-compatibility.md`](development-compatibility.md) | Impact analysis on test rules, fixtures, tests, and lightweight migration/normalization layer. |
| [`security-analysis.md`](security-analysis.md) | AST sandbox verification, SafeEval/Jinja security boundaries, and field reference safety. |
| [`performance-analysis.md`](performance-analysis.md) | Micro-benchmarks, algorithmic bounds, caching strategy, and frontend rendering optimization. |
| [`test-strategy.md`](test-strategy.md) | Component, contract, compiler, runtime, and migration test suite specifications. |
| [`documentation-impact.md`](documentation-impact.md) | Required changes to User Guide, Developer Guide, API reference, and internal specs. |
| [`implementation-plan.md`](implementation-plan.md) | Phase 2 step-by-step implementation roadmap with clear dependency sequencing. |

---

## Core Architectural Principle

```
User-Facing Taxonomy (What kind of data/value am I working with?)
       ↓
User-Facing Component (Cohesive operation component, e.g. TextResolver.vue)
       ↓
Operation (Specific operation choice, e.g. "normalize")
       ↓
Canonical Resolver Contract ({ "family": "text", "operation": "normalize", "config": {...} })
       ↓
Execution Strategy / Compiler (Internal compilation to SafeEval expression or execution pipeline)
       ↓
Backend Runtime Execution (Safe execution against Frappe document context)
```
