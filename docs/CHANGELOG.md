# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **Assignment Action Type**: New powerful assignment system replacing the legacy "Set Value" action.
  - Supports batch mutations and multiple operators: `set`, `clear`, `increment`, `decrement`, `append`, `merge`, and `toggle`.
  - Managed via a new `AssignmentOperatorRegistry`.
  - Preliminary support for deep document path assignments (currently optimized for root-level fields).
- **Switch Action Type**: Multi-path branching based on expression evaluation, allowing for complex decision trees within a single rule.
- **Condition System V2**:
  - Support for recursive collection logic (`Any`, `All`, `None`) for advanced child table evaluation.
  - Custom iterator aliases for defining nested loop contexts.
- **Reusable Vue Controls**:
  - `ValueResolverControl`: Advanced viewport positioning (auto-flipping) and intelligent Jinja snippet generation.
  - `ResourceMapperControl`: For mapping external data structures to internal fields.
  - `TextGeneratorControl` and `TransformControl`: For dynamic content generation and data transformation.
  - `ComboBoxControl` and `FilterGroup`: Enhanced UI components for complex selections and filtering.
- **Engine Enhancements**:
  - Exponential backoff for action retries (`wait_time = 2 ** current_attempt`).
  - Atomic savepoints for action execution using `flexirule_action_{action_id}` naming convention.
  - Global reentrancy guard to prevent infinite rule loops.
- **Rule Builder UX**:
  - Global keyboard shortcuts (e.g., `Ctrl+S` to save, `Shift+?` for help).
  - Integrated shortcuts help overlay.
- **Documentation**:
  - Comprehensive documentation for reusable controls in `docs/CONTROLS.md`.
  - Full system documentation audit with expanded coverage of core engine and action types.

### Changed
- **UI Architecture**: Migrated Rule Builder from `frappe-ui` to custom Tailwind-based components for better flexibility and performance.
- **Template Migration**: `Rule.compile_action_templates` now automatically migrates legacy `value` keys to `value_template` on save.
- **Caching Layer**: `RuleCoordinator` now utilizes a layered caching strategy (request-local, Redis, and Database) for optimal performance.
- **Branding**: Completed the transition and branding unification from "Bolton" to **FlexiRule**.
- **Backend Extensibility**: Refactored `ActionHandler` and `HandlerRegistry` to use a more robust Strategy pattern.

### Fixed
- **CI/CD**: Resolved critical `KeyError` in assignment processing by unifying key schemas across the engine and builder.
- **Security**: Hardened rule execution sandbox using `SafeFrappeAPI` and improved `frappe.safe_eval` integrations.
- **Stability**: Fixed various core logic bugs in the execution engine and resolved numerous linter/Mypy warnings.
- **Compatibility**: Maintained runtime backward compatibility for legacy `value` fields in assignments.
