<div align="center">
  <img width="180" alt="flexiRule" src="https://github.com/user-attachments/assets/e3724231-fccc-4f92-89af-6dd7b93c640f" />

  <h1>FlexiRule</h1>

[![CI](https://github.com/Sendipad/flexirule/actions/workflows/ci.yml/badge.svg?branch=develop)](https://github.com/Sendipad/flexirule/actions/workflows/ci.yml?query=branch%3Adevelop)
![Beta Release](https://img.shields.io/badge/release-beta-orange)
![Frappe](https://img.shields.io/badge/built%20for-Frappe%20v15%2B-blue)

  <p><strong>Visual Rule Engineer & Orchestration Engine for Frappe apps and ERPNext</strong></p>

</div>

<div align="center">
<img width="1307" height="751" alt="rule_builder" src="https://github.com/user-attachments/assets/8ff096b5-09b9-467a-925b-42530542c73d" />

  <p>
    <em>The Visual Rule Builder is the canonical representation of FlexiRule logic — what you see is exactly what executes.</em>
  </p>
</div>

---

## 🚀 Overview

In modern enterprise systems like **Frappe / ERPNext**, business logic often evolves into a fragmented web of Python hooks scattered across multiple custom apps. This technical debt leads to "hook-hell," where execution order is implicit, debugging is a nightmare, and upgrades are risky.

**FlexiRule** changes the paradigm by providing a **visual, graph-based orchestration layer**. Instead of writing hidden code, you design executable business logic visually — with full control, observability, and safety.

### 💎 Why FlexiRule?

- **Centralized Logic**: Move rules out of scattered `.py` files into a single, auditable dashboard.
- **No-Code Configuration**: Custom UI controls (pickers, autocomplete) allow complex logic setup without a single line of code.
- **Explicit Execution**: Connections define deterministic paths. No more guessing which hook runs first.
- **Schema-Driven UI**: Configuration forms for custom logic are auto-generated from JSON schemas.

---

## 🖼️ Visual Tour

<details>
<summary><strong>View Detailed Screenshots</strong></summary>

<br/>
<img width="1280" height="583" alt="IMG_20260509_194450_181" src="https://github.com/user-attachments/assets/212b96bf-9259-426b-90c1-dd55efce0bd7" />

<img
  src="https://github.com/user-attachments/assets/41ac7963-f334-4fb2-bf0a-49409956c4a3"
  alt="Condition node configuration"
  width="900"
  style="border-radius:14px;"
/>
<img width="1294" height="648" alt="IMG-20260422-WA0039" src="https://github.com/user-attachments/assets/b5e00fd1-c171-48bf-abc6-93c4de93f6a1" />
<img width="1331" height="627" alt="IMG-20260422-WA0041" src="https://github.com/user-attachments/assets/e1e7bf85-7f27-4be1-9999-f9dcdd511603" />

<p align="center"><em>Declarative, deeply nested condition trees with deterministic evaluation.</em></p>
<img width="1029" height="722" alt="IMG-20260422-WA0037" src="https://github.com/user-attachments/assets/2bc38417-092e-4623-8324-dc736629213f" />
<img width="1029" height="722" alt="IMG-20260422-WA0036" src="https://github.com/user-attachments/assets/1e9201fc-b8fc-4308-86b5-2b80cc6ac25a" />
<img width="1029" height="722" alt="SAVE_20260422_211618" src="https://github.com/user-attachments/assets/fedaf6aa-63d8-418d-9e32-30c422fe93cf" />

<img
  src="https://github.com/user-attachments/assets/97c23be2-f939-4190-ad34-c1318bd2dece"
  alt="Process Operation configuration"
  width="900"
  style="border-radius:14px;"
/>

<p align="center"><em>Process Operations — schema-driven configuration rendered dynamically at runtime.</em></p>

</details>

---

## 🧠 The Mental Model

FlexiRule is built around three core pillars that bridge the gap between design and execution.

### 1. The Rule (The Entry Point)

A **Rule** defines _when_ logic should trigger. It serves as the gateway to the graph and binds to one of three context sources:

- **DocType Event**: Tied to database hooks (e.g., `Before Save`, `On Submit`).
- **Scheduler Event**: Scheduled CRON-based executions via background jobs.
- **Callable Event**: A sub-rule meant strictly to be executed by other parent rules via `Priority: 0`.

### 2. The Rule Action (The Node)

Each node in the graph is a **Rule Action**. It represents a specific step in your business process. Actions accept structured inputs and define the next step in the flow based on their outcome (e.g., `Success` → `Next Step`, `Error` → `Rollback`).

### 3. Process & Operations (The Logic)

A **Process** is a file-backed module (similar to Frappe Reports/Dashboards) that acts as a container for reusable logic.

- **File-Backed**: Logic is stored in code (`.py`) for performance and version control.
- **Operations**: Individual functions within a process that declare their own **JSON Schema** for configuration parameters.

---

## ⚡ Execution Flow Example

FlexiRule uses a deterministic graph-based execution engine with built-in cycle detection (preventing infinite loops over 100 iterations natively). The following example shows a more detailed flow with error handling and branching paths.

```mermaid
graph LR
    Trigger[Rule Trigger]
    --> Validate[Validate Data]

    Validate -->|Valid| Dedup[Check Duplicates]
    Validate -->|Invalid| Stop[Stop & Notify]

    Dedup -->|Found| Block[Block Save]
    Dedup -->|None| Enrich[Enrich Document]

    Enrich -->|Success| Success[Finalize]
    Enrich -->|Failure| ErrorHandler[Error Handling]

    ErrorHandler -->|Retry| Retry[Retry Operation]
    ErrorHandler -->|Escalate| Escalate[Escalate to Supervisor]

    Retry -->|Success| Success
    Retry -->|Max Retries| Escalate
```

---

## 🛠️ Key Features

- **Vue 3 Visual Builder**: Smooth graph-editing via a VueFlow canvas rendered dynamically from Frappe backend schemas.
- **Condition Compilation**: Visual engine builds JSON `trigger_conditions` that are transparently pre-compiled into ultra-fast, single-pass pure Python strings `compiled_expression` on Save to avoid runtime overhead.
- **Node Execution State Management**: Real-time tracking of execution state across components for visualization and debugging.
- **Compiled Runtime Registry**: Layered caching system (request-local → Redis → DB) for compiled rules and dependencies.
- **Role-Based Execution Control**: `skip_for_roles` field to prevent rule execution for specific roles.
- **Permission Audit Logging**: `skip_permissions` with audit reason for tracking bypassed permission checks.
- **Watched Fields Optimization**: Automatic extraction and change-based filtering for event-driven rules.
- **Comprehensive Error Handling**:
    - Retry with exponential backoff
    - Rollback with savepoints
    - Escalate to caller
    - Continue or Stop (default)
- **Async Execution via Background Queues**: Offload long-running rules to background jobs.
- **Timeout Protection**: Per-rule and per-action timeout limits.
- **Asynchronous Execution Log Enqueuing**: Non-blocking persistence of execution traces.
- **Graph Validation with Cycle Detection**: Prevents infinite loops with visit counting and iteration limits.
- **Deterministic Graph Execution**: Zero ambiguity in execution order via Registry strategy pattern.
- **Safety First**: Sandboxed execution via `SafeFrappeAPI`, savepoint rollbacks, and input validation.

---

## 📦 Installation

```bash
# Get the app
bench get-app flexirule https://github.com/Sendipad/flexirule.git

# Install to your site
bench --site [your-site] install-app flexirule

# Build assets
bench build --app flexirule
```

---

## 🔧 Extensibility

Developers can extend FlexiRule by creating **Standard Processes**:

1. Create a `Process` document and check **Is Standard**.
2. Frappe will generate `.py` and `.js` controllers in your app.
3. Define your logic in Python and your config UI schema in JSON.
4. Your custom logic immediately appears as a selectable operation in the Visual Builder.

---

## 🔌 API Reference

FlexiRule provides a comprehensive set of whitelisted backend methods for programmatic interaction:

- **`test_rule`** - Test rule execution with `dry_run` and `save_log` options
- **`simulate_rule`** - Dry-run simulation without persisting logs
- **`execute_rule`** - Manual/API execution of a rule
- **`transition_rule`** - Lifecycle management (enable/disable rules)
- **`get_execution_preview`** - Path prediction for rule execution
- **`get_contract_dto`** - Frontend introspection of rule contracts
- **`get_node_config_schema`** - Dynamic configuration schema generation
- **`get_action_context_schema`** - Variable resolution context inspection
- **`clone_rule`** / **`amend_rule`** - Rule versioning operations
- **`get_rule_stats`** - Monitoring and performance metrics

All APIs are accessible via `frappe.call()` and follow standard Frappe whitelisted method conventions.

---

## 📝 Recent Changes (Last 3 Months)

The FlexiRule codebase has undergone significant architectural improvements:

### Core Engine Enhancements

- **Node Execution State Management**: Real-time tracking of execution state across components for visualization and debugging
- **Compiled Runtime Registry**: Layered caching system (request-local → Redis → DB) for compiled rules and dependencies
- **Graph Validation Improvements**: Enhanced cycle detection with visit counting and iteration limits
- **Async Execution Refinements**: Better background job handling and timeout protection

### Security & Reliability

- **Permission Audit Logging**: `skip_permissions` with audit reason for tracking bypassed permission checks
- **Role-Based Execution Control**: `skip_for_roles` field to prevent rule execution for specific roles
- **Watched Fields Optimization**: Automatic extraction and change-based filtering for event-driven rules
- **Comprehensive Error Handling**: Retry with exponential backoff, rollback with savepoints, escalate to caller

### Developer Experience

- **Dynamic Configuration Schemas**: Improved `get_node_config_schema` and `get_action_context_schema` APIs
- **Extended Process Operation Metadata**: New fields like `writes_to`, `requires_doc`, `transactional`, `has_side_effect`, `config_schema`, `output_schema`, `action_overrides`
- **Enhanced Rule Lifecycle APIs**: Better `clone_rule`, `amend_rule`, `transition_rule` functionality
- **Improved Monitoring**: Enhanced `get_rule_stats` and execution tracing capabilities

### Frontend Improvements

- **Vue 3 + Pinia Architecture**: Modular state management with 5 dedicated stores
- **Real-time Execution Visualization**: `useNodeExecutionState` composable for test runs
- **Enhanced Condition Builder**: Improved visual multi-condition builder with nested AND/OR groups
- **Dynamic Control Factory**: Schema-driven UI generation for Process Operations

These changes solidify FlexiRule as a production-ready, enterprise-grade workflow automation platform for Frappe/ERPNext.

---

<details>
<summary><strong>How to Contribute</strong></summary>

<br/>

**Join the FlexiRule Community!**

FlexiRule is evolving fast. Whether you are a developer, designer, or documenter, your expertise helps shape the future of visual automation in the Frappe ecosystem.

### How You Can Help

- 🐛 **Bug Reports**: Open an issue for any glitches.
- 💡 **Feature Requests**: Suggest new Nodes or Process Operations.
- 📖 **Documentation**: Help us clarify concepts or add examples.
- 🔧 **Pull Requests**: We welcome fixes, optimizations, and new features.

Follow [Frappe Coding Standards](https://frappeframework.com/docs/v14/user/en/guidelines/coding-standards) and ensure all tests pass.

</details>

---

<div align="center">
  <p><strong>FlexiRule</strong> — Declarative, Visual, and Safe Business Logic for Frappe.</p>
  <p>Built with ❤️ by the community.</p>
</div>
