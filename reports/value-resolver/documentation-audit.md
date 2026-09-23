# Documentation Audit: Value Resolver Subsystem

## Overview

This audit compares repository documentation (including `README.md`, `flexirule/ruleflow/README.md`, and `docs/`) against the actual codebase implementation of the Value Resolver subsystem.

---

## Findings Matrix

| Feature / Concept | Documented Status | Codebase Implementation Status | Discrepancy / Gap |
| :--- | :--- | :--- | :--- |
| **FlexValue Control (`/` & `@`)** | Mentioned in feature highlights | Fully implemented in `FlexValueControl.vue` | User guide lacks step-by-step instructions for slash command workflows. |
| **Value Resolver Level Settings** | Documented in RuleFlow Settings | Implemented in UI (`RESOLVER_LEVEL_KIND_MAP`), missing in Backend | Documentation implies site-wide enforcement, but backend executes all levels (`VR-AUDIT-001`). |
| **`fetch` Resolver** | Documented as Link Fetching | Fully implemented in `FetchResolver` | Config parameter `link_source_type` is undocumented in API specs. |
| **Normalization Profiles** | Mentioned in release notes | Fully implemented in `normalization.py` and `NormalizationResolver` | Available profiles (`Clean Text`, `System Key`, `Slug Only`) are not indexed in docs. |
| **Legacy Mode Aliases** | Undocumented | Supported in `FlexValueControl` and `value_resolver.py` | Legacy modes (`formula`, `format`, `normalize`) are unmentioned in current guides. |

---

## Recommended Documentation Improvements

1. **Add Value Resolver Authoring Guide**:
   - Document how to use `/` slash commands, `@` variable mentions, and token editing modals.
2. **Update API Architecture Docs**:
   - Publish explicit JSON Schema definitions for all 9 canonical resolver `config` payloads.
3. **Clarify Security Boundaries**:
   - Clarify expression evaluation rules, allowed `frappe.utils` functions, and `resolverLevel` capabilities.
