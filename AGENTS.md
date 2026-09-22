# Agent Guidelines - FlexiRule

As an agent working on FlexiRule, you must adhere to the following behavioral and reasoning contracts to maintain the architectural integrity of the system.

## 1. Architectural Reasoning
-   **V2 First:** Always prioritize the V2 declarative runtime. Treat V1 (file-backed processes) as legacy. Do not design new features around V1.
-   **Deterministic Invariants:** Maintain the "What you see is what executes" promise. Ensure that graph execution is unambiguous and fully traceable.
-   **Constraint over Flexibility:** Favor constrained logic (structured assignments, DSL expressions) over arbitrary Python execution.

## 2. Security & Boundaries
-   **Proxy Awareness:** Respect the `SafeFrappeAPI` and `ReadOnlyDocument` boundaries. Do not attempt to bypass these for "convenience."
-   **Mutation Control:** All state changes should ideally pass through the `ContextManager` to ensure they are tracked and reversible (where applicable via savepoints).

## 3. Documentation & Memory
-   **Externalize Truth:** Update `ARCHITECTURE_LOG.md` and `RUNTIME_SPEC.md` as you discover or implement significant changes. Do not rely solely on internal conversational memory.
-   **Technical Structure:** When providing insights, use the structure:
    -   **What exists**
    -   **How it works internally**
    -   **Why it exists**
    -   **Risks / technical debt**
    -   **Suggested improvement**

## 4. Testing & Verification
-   **Semantic Replay:** When modifying logging or execution logic, ensure that the output remains sufficient for semantic replay of decisions.
-   **Fail-Fast:** Maintain the fail-fast behavior for synchronous rules to ensure data consistency.
