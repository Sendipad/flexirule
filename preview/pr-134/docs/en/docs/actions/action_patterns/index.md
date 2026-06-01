# <no value>
# Actions: Action Patterns

## 🎼 The Art of Orchestration

Business automation emerges not from single actions, but from the **composition** of action patterns.

### 1. CRUD Automation

Automating the lifecycle of a document:

- **Before Save**: Validation and data normalization.
- **After Save**: Triggering notifications or updating related records.
- **On Submit**: Finalizing financial entries or initiating workflows.

### 2. Guarded Transitions

Using the `Condition` node as a "Gatekeeper":

- Ensure an action only runs if specific criteria are met, without nesting if-else blocks in code.
- Pattern: `Condition [Eligible?]` -> `True` -> `[Actual Action]`.

### 3. Collection Processing

Handling child tables effectively:

- Using `Loop` to apply logic to every row.
- Using `ChildAggregation` resolvers to summarize data before making a decision.

### 4. Integration Orchestration

Connecting to external systems:

- Use `Assignment` to prepare a payload in `vars.api_payload`.
- Use `Process (Webhook/API)` to send the data.
- Use `Switch` on the API response to handle success/failure cases.

---

## 🏛️ Reusable Enterprise Flows

### The "Approval Gate"

- **Action 1**: Query for approvers based on department.
- **Action 2**: Switch based on "Total Amount".
- **Action 3**: Send different notification templates to different roles.

### The "Data Sync"

- **Action 1**: Query external ID.
- **Action 2**: Switch (Exists?).
- **True**: Update external system.
- **False**: Create new record in external system.

---

## 🔮 Hidden Power: Graph Recursion

The `Sub-Rule` action enables **Modular Automation Architecture**:

- One Rule can act as a "Utility" (e.g., "Calculate Tax") and be called by many other "Parent" Rules.
- This creates a **Service-Oriented Automation Layer** within the Frappe app.
