# <no value>
# Architecture: System Philosophy

## 📝 What FlexiRule Is
FlexiRule is a **declarative automation orchestration platform** built for the Frappe ecosystem. It bridges the gap between hardcoded Python hooks and complex business requirements by providing a graph-based execution runtime.

### The Foundational Shift
- **Traditional Frappe**: Logic is buried in `.py` files, scattered across hooks. Changing it requires code deployment.
- **FlexiRule**: Logic is a **data structure** (Rule DocType) that is interpreted at runtime. Changing it is a metadata update.

---

## 🏛️ Orchestration Philosophy
FlexiRule views business logic as a **Directed Acyclic Graph (DAG)** of actions. This "graph-thinking" allows for:
1. **Visual Clarity**: The flow of logic is explicit, not implicit.
2. **Predictable Execution**: The engine handles the "how" (loops, errors, context), while the user defines the "what."
3. **Reusability**: Logic is encapsulated into "Processes" which are then orchestrated by "Rules."

### The "Process" vs "Rule" Distinction
This is a critical architectural pillar:
- **Process**: A reusable, file-backed (or DB-defined) library of **Operations**. It is the "What" can be done. It is rigid, version-controlled, and defined by developers.
- **Rule**: A database-native **Orchestration**. It is the "When" and "How" operations are combined. It is flexible, user-defined, and can change without code changes.

---

## 📐 Schema-First & Metadata-First Design
The system is built on **Contracts**.
- A Process defines its **Config Schema** and **Output Schema**.
- The Rule engine uses these schemas to generate UI and validate data flow.
- This creates a **Low-Code Safety Net**: Users can't pass invalid data because the system "knows" the requirements of every node.

---

## 🌍 Comparison with Other Platforms

| Platform | Orchestration Model | Integration Level | Philosophy |
| :--- | :--- | :--- | :--- |
| **Salesforce Flow** | Graph-based | Deep (Object-level) | Metadata-driven enterprise automation. |
| **Node-RED / n8n** | Node-based | Wide (API-level) | General purpose integration/automation. |
| **Zapier** | Linear / Branching | Surface (Webhooks) | Simple user-facing connectivity. |
| **FlexiRule** | **Graph-based** | **Deep (Doc-level)** | **In-database automation with developer-grade extensibility.** |

### Why FlexiRule is Uniquely Powerful
Unlike external tools (Zapier/n8n), FlexiRule lives **inside the database transaction**. It has access to the "old_doc" and "new_doc" states simultaneously, allowing for complex validation and side effects that external tools cannot perform reliably without excessive API roundtrips.

---

## 🚀 Low-Code Foundations
FlexiRule isn't just an automation tool; it is a **Low-Code Framework**.
- **Primitives**: Assignment, Condition, Switch, Loop.
- **Extenders**: Custom Processes.
- **Orchestrator**: Rule Engine.

By combining these, one can build entire "Apps" that are essentially collections of orchestrated Processes.
