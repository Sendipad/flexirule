# Documentation Impact & Refactoring Requirements

## 1. Documentation Scope

Updating FlexiRule's Value Resolver system to a consolidated 8-family architecture requires documentation updates across both public user-facing manuals and developer technical guides.

```
┌────────────────────────────────────────────────────────────────────────┐
│                      Documentation Update Scope                        │
├────────────────────────┬───────────────────────┬───────────────────────┤
│ 1. User Guide          │ 2. Developer Guide    │ 3. In-App Tooltips    │
└────────────────────────┴───────────────────────┴───────────────────────┘
```

---

## 2. Required Document Changes

### 2.1 User Guide (`docs/user-guide/value-resolvers.md`)
- **Structure**: Reorganize chapter from 10 implementation strategy topics into **8 Family Sections** (Date & Time, Text, Number, Collections & Tables, Lookup, System & Context, Conversion, Conditional).
- **Operation Catalog**: Provide step-by-step UI guides for non-technical Rule Designers detailing each family's operation dropdown choices.
- **Currency Formatting**: Move money formatting examples out of Text/Format chapters and place them prominently in the **Number Family (Format Money)** chapter.

### 2.2 Developer Guide (`docs/developer-guide/resolvers-and-contracts.md`)
- **Canonical Schema**: Document the canonical `{ "family": "...", "operation": "...", "config": { ... } }` JSON structure.
- **Custom Operation Registration**: Provide code examples showing how developers can register custom operations in `operations.js` and extend backend strategy classes.
- **Migration & Normalization**: Explain the runtime load-time normalizer and how legacy `{ "kind": "..." }` structures are processed.

### 2.3 In-App Tooltips & Metadata (`families.js` / `operations.js`)
- Update `description` fields across family and operation registries so floating tooltips and `v-fxr-fieldname` overlays show clear business analyst descriptions.
