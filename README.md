<div align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="assets/logo-dark.svg">
    <img width="180" alt="flexiRule" src="assets/logo-light.svg">
  </picture>

  <h1>FlexiRule</h1>

[![CI](https://github.com/Sendipad/flexirule/actions/workflows/ci.yml/badge.svg?branch=develop)](https://github.com/Sendipad/flexirule/actions/workflows/ci.yml?query=branch%3Adevelop)
![Beta Release](https://img.shields.io/badge/release-beta-orange)
![Frappe](https://img.shields.io/badge/built%20for-Frappe%20v15%2B-blue)
[![Listed on Frappe Gems](https://frappegems.com/api/method/frappe_gems.seo.badge?app=Sendipad%2Fflexirule)](https://frappegems.com/gems/apps/Sendipad/flexirule)

  <p><strong>Declarative Business Automation & Visual Orchestration Platform for Frappe and ERPNext</strong></p>

</div>

<div align="center">
  <img width="1307" height="751" alt="rule_builder" src="https://github.com/user-attachments/assets/8ff096b5-09b9-467a-925b-42530542c73d" />
  <p>
    <em>The visual, graph-based canvas serves as the single source of truth for your business workflows.</em>
  </p>
</div>

---

## Overview

Business logic in Frappe applications and ERPNext is commonly implemented through a combination of framework hooks, server scripts, controller methods, and custom application code. As projects grow, this logic often becomes distributed across multiple locations, making it increasingly difficult to understand, maintain, test, and evolve.

Common challenges include:

- Distributed Execution Flow — Business logic is spread across hooks, controllers, server scripts, and custom modules, making execution paths difficult to follow and reason about.
- Limited Observability — Understanding why a rule executed, tracing failures, or inspecting runtime state often requires manual debugging and code analysis.
- Maintenance Overhead — Custom code tied to framework internals or application-specific implementations can increase the effort required for upgrades, refactoring, and long-term maintenance.
- Inconsistent Reliability — Validation, error handling, and transaction management may vary across implementations, increasing the risk of unexpected behavior.

FlexiRule provides a visual, graph-based orchestration engine that complements the Frappe framework. Instead of embedding business rules across multiple code locations, workflows are modeled declaratively in a centralized rule engine. This enables predictable execution, built-in validation, comprehensive debugging and execution tracing, transaction-aware processing, and a clear separation between business logic and application code.

Beyond orchestration, FlexiRule enables sophisticated business logic to be designed visually rather than implemented programmatically. Dynamic value resolution, variables, conditional expressions, branching, loops, data transformations, calculations, document operations, integrations with external services, and reusable rule components can all be composed through the Rule Builder.

As a result, many business scenarios that traditionally require custom Python development can instead be implemented declaratively. This empowers both developers and power users to build, test, and evolve business processes more rapidly while improving maintainability, consistency, and visibility, and significantly reducing the amount of custom code required.

---

## ⚖️ Why Not Server Scripts?

| Traditional Hooks / Server Scripts | FlexiRule                                                                                     |
| :--------------------------------- | :-------------------------------------------------------------------------------------------- |
| **Scattered Python Code**          | **Centralized Rules**: View all business rules from a single, auditable dashboard.            |
| **Hidden Execution Order**         | **Visual Graph**: Connections define clear, deterministic execution paths on canvas.          |
| **Hard to Debug**                  | **Execution Tracing**: Real-time trace lines highlight the exact path and state of each node. |
| **Duplicate Logic**                | **Reusable Processes**: Package core logic once and share it securely across multiple rules.  |
| **Manual Forms & Controls**        | **Schema-Driven UI**: Forms and fields auto-generate from standard JSON schemas.              |
| **Difficult Governance**           | **Built-in Safety**: Advanced sandboxing, role exclusions, and permission audits.             |

---

## 💎 Why FlexiRule?

FlexiRule provides a modern, structured alternative to scattered custom hooks:

- **Centralized Logic**: Consolidate your business rules into a single, auditable dashboard instead of maintaining custom hooks across multiple repositories.
- **Deterministic Orchestration**: Define clear execution paths using direct visual connections, resolving hook execution ordering issues.
- **Safe Sandboxed Evaluation**: Evaluates condition checks in a read-only environment using a sandboxed API, preventing accidental state changes during criteria checks.
- **Schema-Driven UI**: Forms and configuration panels are auto-generated from dynamic schemas, providing developers with structured inputs and validations.
- **Enterprise Governance**: Includes built-in execution safeguards, including savepoint-based transaction rollbacks, role-based execution bypasses, and permission audit logs.

---

## 🖼️ Visual Tour

<details>
<summary><strong>View Visual Walkthrough</strong></summary>

<br/>
<div align="center">
  <img width="1280" height="583" alt="Rule List Overview" src="https://github.com/user-attachments/assets/212b96bf-9259-426b-90c1-dd55efce0bd7" />
  <p><em>Centralized Rule Management Interface for filtering and managing active flows.</em></p>

  <img src="https://github.com/user-attachments/assets/41ac7963-f334-4fb2-bf0a-49409956c4a3" alt="Declarative condition tree builder" width="900" style="border-radius:14px;" />
  <p><em>Declarative condition tree builder with nested AND/OR evaluation.</em></p>

  <img width="1294" height="648" alt="Rule Builder Interface" src="https://github.com/user-attachments/assets/b5e00fd1-c171-48bf-abc6-93c4de93f6a1" />
  <p><em>VueFlow Rule Builder with drag-and-drop node configurations and topological routing.</em></p>

  <img width="1331" height="627" alt="Debugger Path Tracing" src="https://github.com/user-attachments/assets/e1e7bf85-7f27-4be1-9999-f9dcdd511603" />
  <p><em>Real-time execution path tracing and state tracing directly on the canvas.</em></p>

  <img width="1029" height="722" alt="Query Records Configuration" src="https://github.com/user-attachments/assets/2bc38417-092e-4623-8324-dc736629213f" />
  <p><em>Query node configuration for introspecting fields, mapping inputs, and filtering database records.</em></p>

  <img width="1029" height="722" alt="Custom Field Assignment" src="https://github.com/user-attachments/assets/1e9201fc-b8fc-4308-86b5-2b80cc6ac25a" />
  <p><em>Batch assignment step supporting multi-operator mutations on document fields and context variables.</em></p>

  <img width="1029" height="722" alt="Notification Designer" src="https://github.com/user-attachments/assets/fedaf6aa-63d8-418d-9e32-30c422fe93cf" />
  <p><em>Flexible notifications supporting toasts, system alerts, or standard emails.</em></p>

  <img src="https://github.com/user-attachments/assets/97c23be2-f939-4190-ad34-c1318bd2dece" alt="Process Operation configuration" width="900" style="border-radius:14px;" />
  <p><em>Process Operations for running file-backed custom code with schema-driven inputs.</em></p>
</div>

</details>

---

## 🧠 Core Concepts

FlexiRule separates trigger criteria, execution paths, and business logic into structured components:

- **Rule**: The entry point that defines _when_ execution should trigger, binding to DocType database hooks, background scheduler intervals, or manual callable events.
- **Action Type**: Reusable visual action definitions declaring layout styles, required parameters, and outcome capabilities.
- **Rule Action**: A specific step (node) in the execution graph that processes input configurations and routes control to successor nodes based on execution outcomes.
- **Process**: A file-backed Python module that acts as a secure, performance-optimized container for custom code. Processes are highly reusable across multiple rules, allowing developers to share critical business logic instead of duplicating it.
- **Operation**: An individual function within a Process that exposes its parameters through a declarative JSON Schema.
- **Runtime Context**: An isolated execution namespace carrying the root document, context variables, and metadata.
- **Execution Graph**: The topologically ordered sequence of steps representing your business workflow.

---

## 🛠️ Key Features

- **Visual Rule Builder**: Drag, drop, and connect steps with automatic topological sorting to organize your workflows easily.
- **No-Code Configuration**: Custom UI controls let you set up complex database queries, field assignments, and operations without writing code.
- **Deterministic Execution**: Run logic along explicit paths with built-in loop limits to guarantee safe, infinite-recursion-free routing.
- **Rule Simulation**: Test your rules safely using a dry-run mode that evaluates criteria, traces execution paths, and rolls back transaction changes.
- **Runtime Debugging**: Gain complete observability with real-time execution path tracing, detailed state snapshots, and error traces.
- **Process Reusability**: Bundle core logical routines into reusable file-backed Processes, allowing them to be shared across multiple active rules.
- **Extensible Action Types**: Expand the platform easily with custom action types to connect with external systems and services.
- **Enterprise Safety**: Restrict rule executions by user roles, bypass permissions with mandatory audit reasons, and handle errors with safe database savepoint rollbacks.
- **High-Performance Runtime**: Designed for zero-overhead event execution through layered metadata caching, pre-compiled condition strings, and watched-field pruning.

### 💻 Developer Experience (DX)

- **Schema-Driven UI**: Configuration panels and forms are automatically generated from standard JSON schemas, ensuring perfect alignment between frontend controls and backend data.
- **Dynamic Control Factory**: Automatically renders standard Vue 3 form inputs, link autocompletes, and collection controls based on dynamic parameters.
- **Custom UI Controls**: Embed customized input widgets or advanced data selectors directly into action configurations.

---

## 🏗️ Architecture Overview

FlexiRule decouples event-driven triggers from execution mechanics and business logic processing:

```mermaid
graph TD
    Trigger[Rule Trigger: Hook, CRON, or Callable] --> Coordinator[Rule Coordinator: Filters & Prunes]
    Coordinator --> Registry[Runtime Registry: Cache Layer]
    Registry --> Engine[Rule Engine: Node Traversal Manager]
    Engine --> ActionRegistry[Action Registry: Strategy Handlers]
    ActionRegistry --> ProcessRuntime[Process Runtime: Dynamic Schema-Validated Code]
    ProcessRuntime --> Logging[Execution Logging: Non-blocking Background Queue]
```

### Component Responsibilities

- **Rule Trigger**: Binds database lifecycle events, scheduler intervals, or programmatic calls to start execution.
- **Rule Coordinator**: Resolves active rules and performs early eligibility pruning using pre-compiled conditions.
- **Runtime Registry**: Caches compiled runtime metadata to minimize database access during event hooks.
- **Rule Engine**: Traverses the execution graph topologically, manages context state, and handles retry and transaction boundaries.
- **Action Registry**: Maps individual execution steps to their respective strategy implementations (e.g., Conditions, Assignments, Loops).
- **Process Runtime**: Orchestrates custom processes, maps context variables, and validates configurations against JSON schemas.
- **Execution Logging**: Persists detailed execution traces asynchronously to keep user transactions fast and lightweight.

---

## 🔄 Execution Lifecycle

The following diagram illustrates how FlexiRule coordinates execution, from event matching to transaction completion:

```mermaid
flowchart TD
    A([Trigger Event]) --> B[Rule Discovery]
    B --> C{Watched Fields Change?}
    C -- No --> Skip[Skip Execution]
    C -- Yes --> D[Load Rule from Registry Cache]
    D --> E{Eligible: Evaluate Pre-compiled Conditions}
    E -- No --> LogSkip[Log Early Skip & Exit]
    E -- Yes --> F[Initialize Isolated Runtime Context]
    F --> G{Traverse Nodes Topologically}
    G --> H[Resolve Input Mappings]
    H --> I[Execute Pluggable Action Handler]
    I --> J{Execution Success?}

    J -- No --> K{On Error Policy?}
    K -- Retry --> Retry[Apply Exponential Backoff]
    Retry --> H
    K -- Continue --> L[Advance to True Node]
    L --> G
    K -- Rollback --> Roll[Rollback to Savepoint]
    Roll --> Fail[Throw ValidationError]
    K -- Stop/Escalate --> Fail

    J -- Yes --> M[Map Result to Context Variables]
    M --> N{Has Next Node?}
    N -- Yes --> G
    N -- No --> O[Enqueue Execution Log Asynchronously]
    O --> P([Complete Transaction])
```

The execution flow begins with **Rule Discovery** and optimizes database performance via **Watched Fields**. If checked fields have changed, the pre-compiled criteria are evaluated in a read-only sandboxed environment. Upon passing, an isolated **Runtime Context** is initialized, and nodes are executed topologically. Errors are caught and handled according to the node's configured policy (`Retry`, `Continue`, `Rollback` to savepoint, or `Stop`). Once the path is completed, audit logs are pushed to an asynchronous background worker before the transaction commits.

---

## ⚡ Performance Architecture

FlexiRule is engineered for high throughput to ensure database transaction event loops remain fast and lightweight:

- **Runtime Registry Cache**: Rule metadata and structures are cached in a dedicated Redis registry (`flexirule_runtime_registry_v2`). The platform avoids expensive SQL operations by bypassing database queries during event hooks.
- **Watched Fields Optimization**: Event listeners analyze changed fields first. If a modified database field does not overlap with fields evaluated by the rule, execution is pruned immediately before compiling criteria.
- **Compiled Expressions**: Visual condition trees are pre-compiled into optimized Python expressions on Rule save, facilitating fast, single-pass evaluations.
- **Action Plan Caching**: Compiled execution actions and strategy plans are cached locally to eliminate parsing overhead during runtime execution.
- **Asynchronous Execution Log Persistence**: Logging and heavy notification tasks are enqueued to background workers (`short` / `default` queues), removing them from the critical request path.
- **Minimal Database Lookups**: State variables and resolved inputs are stored exclusively in the in-memory execution context, avoiding redundant database lookups.

---

## 🔌 Extensibility Model

Developers can extend FlexiRule at multiple layers to integrate custom business logic:

- **Action Types**: Custom execution blocks can be registered to provide reusable, platform-wide capabilities (e.g., custom integrations or formatters).
- **Processes & Operations**: Package custom logic into file-backed Python classes. FlexiRule automatically discovers these methods, letting you expose inputs through standard JSON schemas that automatically render as validated forms in the UI.
- **Dynamic Config Schemas**: Define dynamic layout fields, allowing the builder UI to generate user-friendly configuration panels on the fly.
- **Custom UI Controls**: Wire custom controls directly into action properties, supporting advanced data selectors and interactive widgets.

---

## 📦 Installation

```bash
# Get the app from the repository
bench get-app flexirule https://github.com/Sendipad/flexirule.git

# Install to your target site
bench --site [your-site] install-app flexirule
```

---

## 🤝 Contributing

Contributions are welcome! If you are interested in improving FlexiRule, please consider:

- Opening a **Bug Report** or submitting a **Feature Request** on GitHub.
- Improving documentation or writing custom Process Operations.
- Submitting a **Pull Request** with bug fixes or optimizations, ensuring you follow [Frappe Coding Guidelines](https://frappeframework.com/docs/v15/user/en/guidelines/coding-standards) and confirm that all tests pass.

---

<div align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="assets/logo-dark.svg">
    <img width="50" alt="flexiRule" src="assets/logo-light.svg">
  </picture>
  <p><strong>FlexiRule</strong> — Declarative, Visual, and Safe Business Logic for Frappe.</p>
  <p>Built with ❤️ by the community. Distributed under the MIT License.</p>
</div>
