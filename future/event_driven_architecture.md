# Future: Event-Driven Architecture

## 📡 Moving Beyond DocType Hooks
While FlexiRule currently excels at document-level automation, its architecture is perfectly positioned to become a **Global Event Orchestrator**.

---

## 🏗️ The Event Bridge Concept
By decoupling the `RuleEngine` from the `RuleCoordinator`, FlexiRule can ingest events from multiple sources:

### 1. System Events
-   User login/logout.
-   Cache clearing.
-   Background job completion.

### 2. External Webhooks
-   An incoming payload from Stripe or Shopify could be mapped into an `ExecutionContext` and dispatched to a Rule.

### 3. Redis / Pub-Sub
-   Rules could subscribe to specific "Channels" and trigger logic as messages arrive.

---

## ⚡ Real-Time Orchestration
With the addition of an **Event Registry**, FlexiRule could support:
-   **Debouncing**: Only trigger a rule once if 10 events arrive in 1 second.
-   **Throttling**: Limiting the execution rate of expensive integration rules.
-   **Fan-Out**: Triggering 5 different Rules from a single "Order Placed" event.

---

## 🔮 Implementation Path
1.  **Generalize the Trigger**: Create an "Event" Trigger type in the Rule DocType.
2.  **Schema-Mapped Payload**: Use the existing contract system to define the expected JSON schema of an event payload.
3.  **Global Dispatcher**: Create a specialized `RuleCoordinator` that listens to Frappe's event hooks and matches them against "Event" Rules.

The result would be a **No-Code Event Processing Engine** that rivals standalone tools like n8n or Zapier, but with the inherent safety and performance of being inside the Frappe stack.
