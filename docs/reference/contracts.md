# Action & Operation Contracts

FlexiRule uses a "Contract-First" approach to ensure consistency between the Python backend and the Vue 3 frontend. Contracts define the rules, constraints, and UI behavior for every action in the system.

## The Unified Contract (`contracts.py`)

The source of truth for all actions is `flexirule/ruleflow.core.contracts.py`. This file contains two primary dictionaries:

### 1. `ACTION_TYPE_CONTRACT`

Defines the global behavior for a category of actions (e.g., `Process`, `Condition`, `Loop`).

- **Required Fields**: Fields that must be present for the action to be valid.
- **Handle Configuration**: Specifies if the node has a `True` (`next_step_if_true`) or `False` (`next_step_if_false`) exit.
- **Terminal Flag**: If `True`, the engine knows no further actions can follow.
- **Visual Metadata**: Defines the icon and color used on the builder canvas.
- **Mutation Policies**: Lists allowed `mutation_mode` options (e.g., a `Condition` cannot mutate a document).

### 2. `OPERATION_CONTRACTS`

Provides fine-grained overrides for specific operations (e.g., `Query List` vs `Query Doc`).

- **Field Overrides**: Can change a field's label, description, or requirement status based on the selected mode.
- **Validation Hooks**: Links to backend Python functions (e.g., `validate_stop_error`) or frontend JS functions for real-time integrity checks.

---

## Contract-Driven Architecture

### Design-Time (Builder)

The frontend calls the `get_contract_dto` API, which exports these Python dictionaries as a JSON object.

- **Dynamic UI**: The `ControlFactory` uses the contract to decide which fields to show and how to label them.
- **Client-Side Validation**: The builder prevents users from connecting nodes or saving configurations that violate the contract (e.g., connecting a `False` path to a `Process` node).

### Runtime (Engine)

The `RuleEngine` uses the contract during execution to:

- **Policy Enforcement**: Before applying a result, the engine checks the `allowed_mutations` and `allowed_return_types` defined in the contract.
- **Schema Validation**: If a contract defines an `output_schema`, the engine validates the returned data before allowing it to enter the execution context.

---

## Benefits of This Approach

1.  **Single Source of Truth**: Adding a new feature or changing a field's requirement only requires a change in one Python file.
2.  **Type Safety**: Prevents "logic-leaking" where a designer might attempt an operation that the engine doesn't support.
3.  **Extensibility**: Third-party developers can register their own custom action types by following the contract schema.
