# FlexiRule — Agent and Developer Guidelines

These instructions apply to the entire repository. Before changing code, inspect the relevant implementation, tests, DocType metadata, and any more-specific AGENTS.md files. More-specific repository instructions take precedence for their directory.

## 1. Project status and working principles

- **FlexiRule is not in production.** The project is in active development and is currently described as beta. Do not describe it as production-ready, assume production deployment constraints have been satisfied, or represent an audit recommendation as an implemented feature.
- Treat the checked-out source, current tests, DocType JSON, CI configuration, and runtime call paths as the authority. Architecture notes, issue descriptions, PR descriptions, generated type hints, and comments can be stale. Verify important claims in current code before changing behavior.
- Make the smallest complete change that solves the stated problem. Avoid unrelated refactors, broad formatting churn, speculative abstractions, and opportunistic renaming.
- Trace behavior across the full lifecycle when needed: builder or API input → validation and compilation → persistence → trigger dispatch → engine and handlers → mutations and side effects → cache invalidation and logs.
- Preserve existing public API payloads, action/trigger contracts, DocType fields, and persisted data formats unless the task explicitly requires a change. For a contract change, identify all consumers and provide migration/backward-compatibility handling where necessary.
- Never claim a test, build, lint, migration, browser flow, or manual verification passed unless you actually ran it and observed the result. State what could not be run and why.
- Do not push task changes directly to develop. Use a focused branch and pull request unless the repository owner explicitly requests another workflow.
- Do not run destructive commands or migrations against an unknown or valuable site. Use a dedicated development/test site and inspect the command's impact first.

## 2. Supported stack and repository conventions

- The app targets the Frappe Framework. The repository README advertises Frappe v15+, and CI explicitly checks against Frappe's version-15 branch. Do not assume compatibility with later major versions without checking the relevant API and tests.
- Python support is declared as Python 3.10 or newer in pyproject.toml. CI currently uses Python 3.10 and Node.js 18.
- Backend lint configuration is in pyproject.toml. Ruff is configured with a 110-character line length, lint rules, double quotes, and tab indentation for formatting. Respect the configuration and nearby file style.
- The frontend uses Vue 3 and Frappe Desk integration. Keep changes compatible with the repository's existing Vue, JavaScript, and bundling setup.
- The documented frontend lint command is yarn lint. The package.json test script is currently a placeholder that exits with an error; do not treat yarn test as a real test suite.
- Avoid formatting entire directories or rewriting generated files just to make a change. Keep formatting changes limited to the touched code unless formatting is the explicit task.

## 3. Architecture map

Use this map as a starting point, then verify details against current code.

- **Frappe hooks:** flexirule/hooks.py registers broad DocType lifecycle hooks and scheduler jobs. It is a sensitive hot path: do not add hooks or widen event coverage casually.
- **Hook adaptation and event mapping:** flexirule/ruleflow/hooks.py maps Frappe lifecycle method names to FlexiRule event names, handles exclusions, and delegates execution.
- **Discovery and dispatch:** flexirule/ruleflow/core/coordinator.py selects applicable rules, checks eligibility, and coordinates execution. It also uses cached/request-local runtime discovery state.
- **Graph execution:** flexirule/ruleflow/core/engine.py traverses the rule graph and delegates action behavior through the handler registry.
- **Action handlers:** flexirule/ruleflow/core/action_handlers/ contains action-specific validation/execution behavior. Follow the existing handler and registry patterns rather than adding action-specific conditionals to the engine.
- **Contracts and validation:** flexirule/ruleflow/core/contracts.py defines backend contract metadata; flexirule/ruleflow/core/validation_service.py provides shared rule/action validation. The Rule controller still has lifecycle, compilation, and domain checks, so do not remove controller validation blindly or assume the service is the only validation path.
- **Process execution:** flexirule/ruleflow/core/process_runtime_v2.py and related contract/registry modules enforce the declarative Process Operation contract. Process definitions are file-backed and synced by flexirule/ruleflow/core/process_sync.py during migration hooks.
- **Scheduling:** Rule Scheduler is the implemented scheduling DocType. Keep scheduling concerns in the existing scheduler path unless the task explicitly changes that architecture.
- **DocType schema and controllers:** DocType JSON files and their Python controllers define persisted data, fields, lifecycle validation, permissions, and child tables. Update these coherently when changing the data model.
- **Rule Builder:** frontend sources live under flexirule/public/js/flexirule/. Stores coordinate builder state; node/config components present the action contracts to users. Inspect the relevant store, component, API call, and serializer before changing save behavior.
- **Frontend contract loading:** flexirule/public/js/flexirule/core/contracts.js loads backend contract data through the contract DTO API. Keep backend contracts authoritative and maintain the frontend consumer in sync; do not introduce an independent set of conflicting action or operation definitions.
- **Tests:** backend tests exist in multiple package test directories, including flexirule/ruleflow/tests/ and DocType-specific test modules. Cypress UI test guidance is in E2E_TESTING.md.

## 4. Frappe framework best practices

### Documents, persistence, and transactions

- Prefer the Frappe Document lifecycle and supported framework APIs over direct SQL or manual table manipulation. Use the established APIs for reading, creating, saving, deleting, and validating documents.
- Choose permission-aware and permission-bypassing APIs deliberately. For example, get_list and get_all have different permission semantics. Do not change that behavior implicitly while optimizing a query.
- Avoid direct SQL unless there is a demonstrated need. When it is needed, parameterize values, keep the query narrow, consider database portability, and test its behavior. Use the project's established query style and supported Frappe query facilities where practical.
- Do not use frappe.db.set_value as a drop-in replacement for Document.save. It bypasses normal document validation and lifecycle hooks. Use it only when bypassing those hooks is intentional and safe.
- Do not call frappe.db.commit() as a routine part of request handlers, DocType hooks, validation, or individual rule actions. Let Frappe own the transaction boundary. Add commits only in an established background/batch boundary with a clear reason.
- Use savepoints and rollback only where the surrounding transaction design requires them. Ensure error paths are handled consistently. Database rollback cannot undo email delivery, HTTP calls, queued jobs, or other external effects.
- A field change made to an in-memory document is not the same as a database write. Respect the triggering Frappe lifecycle event and avoid calling doc.save() from a hook without analyzing recursion and re-entry consequences.
- For database schema changes, follow Frappe DocType/patch conventions. Patches must be safe to re-run where appropriate, work on supported databases, and must not silently delete user data.

### Hooks, API methods, permissions, and background work

- Hook targets configured in hooks.py must be importable module-level functions when required by Frappe; follow the existing hook registration pattern.
- Treat the wildcard DocType dispatch path as performance- and correctness-sensitive. Preserve exclusions, re-entry protections, event mapping, and cache invalidation when modifying it.
- Enforce authorization on the server. Frontend visibility, disabled controls, and client-side schema validation are usability features, not security boundaries.
- Whitelisted APIs must validate inputs and verify the caller is authorized for the requested operation. Never expose arbitrary document reads, method invocation, permission bypass, or execution of user-controlled code through a public endpoint.
- Do not introduce ignore_permissions=True or ignore_links=True without establishing why the bypass is required, who may reach the code path, and what audit or validation protections apply.
- Use frappe.enqueue for work that genuinely belongs in a background job. Define clear idempotency, error reporting, retry, and transaction assumptions; do not block synchronous document hooks with long waits or network calls.
- Preserve Frappe's error semantics. Use the repository's established exceptions and translated user-facing messages instead of swallowing failures or returning success-shaped payloads after errors.

## 5. Rule engine and contract invariants

- The engine is a graph executor, not merely a list of actions. Preserve node identifiers and branch/edge references such as action_id and next-step pointers. Do not infer execution semantics from child-table idx or visual node order unless the code explicitly uses it for that purpose.
- Use the existing condition payload normalization, condition compiler, comparison semantics, and validation helpers. Do not implement a second comparator or hand-build compiled expressions in a handler.
- Treat persisted action config and legacy fields as compatibility-sensitive. Before removing or renaming a field, search all controller, validation, builder, migration, test, and runtime consumers.
- Reuse the shared validation service and action contracts for save, draft, node-config, and activation flows where applicable. Keep the intended distinction between draft validation, single-node validation, and full/activation validation. Add regression tests for parity across the relevant entry points.
- A validation fix must not simply move the error to a later stage. Validate a rule or action as early as appropriate while preserving legitimate incomplete-draft workflows and the backend contract.
- Follow the existing action-handler interface and registry. Handlers are designed to be reusable and should not retain per-execution document/context state in class-level or singleton mutable fields.
- Route runtime state changes through the established execution context, result processing, and mutation handling. Do not bypass the mutation policy or alter document/database state from a condition-evaluation path.
- Keep process operation execution behind its declarative contract: resolve the registered process and operation, validate configuration/results against the declared schemas and policies, respect capabilities such as document requirements and async support, and preserve the defined mutation rules.
- Do not treat adapter names, schema fields, return types, or UI metadata as cosmetic. They are cross-layer contracts. Update producers and consumers together and test valid and invalid payloads.
- Trigger-event mutation rules matter. Before permitting a write in a different event, inspect the Frappe lifecycle semantics and the engine's current restrictions rather than weakening a blocklist based only on a failing example.
- Do not assume caches are the source of truth. When changing a rule, process, contract, DocType metadata, or settings that affect runtime behavior, inspect every relevant cache key and invalidation path. Add tests for stale-cache regressions when feasible.
- Do not rely on inferred field dependencies to skip rule execution unless the current implementation proves the dependency information is complete. A missed execution is a correctness bug, not merely a performance issue.
- Keep Rule Scheduler distinct from Rule unless the requested design intentionally changes that boundary. Verify trigger types, linked-rule validation, filters, due calculations, and error policies across both scheduler and rule code.
- Treat unfinished, release-disabled, legacy, or apparently unused features carefully. Search call sites and tests before extending or deleting them; document uncertainty instead of describing a guessed status as fact.

## 6. Backend Python implementation guidance

- Keep code at the narrowest responsible layer: DocType lifecycle rules in the controller, reusable domain validation in the core service, action behavior in a handler, event orchestration in the coordinator, and graph traversal in the engine.
- Avoid creating circular imports. Keep imports local only when existing dependency boundaries or initialization behavior require it, and explain that choice when it is non-obvious.
- Use clear type hints consistent with nearby code and the supported Python version. Avoid overly generic exception handling; if catching broad exceptions is necessary at a framework boundary, log or propagate the failure with sufficient context.
- Keep validation deterministic and side-effect-light. Do not send notifications, mutate business documents, enqueue durable work, or commit transactions as a by-product of validating a draft.
- For JSON fields, normalize and validate the shape at a boundary, handle malformed/empty values deliberately, and avoid silently turning invalid user input into a valid but semantically different value.
- Avoid N+1 database access in loops when a bulk query or existing registry pattern is appropriate. Do not add a cache or an index based solely on assumption; identify the access pattern, invalidation requirements, and testable benefit.
- Preserve translation conventions with frappe.\_ where user-facing messages need translation.

## 7. Rule Builder and frontend implementation guidance

- Trace data from the component back to its state store, backend DTO/API, save serializer, and server validation before fixing a builder issue. A visible error may originate in persisted state, DTO shape, backend validation, or serialization rather than the component displaying it.
- The backend DTO and contracts are authoritative for action capabilities, required fields, trigger requirements, process operations, and return/mutation policies. Do not hard-code a frontend-only rule that conflicts with the server.
- Keep frontend validation helpful but consistent with backend validation. Optional, empty, missing, and JSON-null values can have distinct meanings; do not conflate them without checking the contract and persistence semantics.
- Preserve graph identity and connections during save/load, edits, and serialization. Test that the UI representation round-trips without losing node configuration, branching, conditions, or metadata.
- Avoid JavaScript eval, new Function, frappe.dom.eval, or equivalent dynamic-code execution. Use structured data, explicit parsers, and existing safe expression/condition handling.
- Follow existing Vue 3 component and store patterns. Keep business rules out of presentation components when a shared contract, store, or backend validator is the right owner.
- Handle API errors visibly and preserve unsaved user input when possible. Do not silently swallow contract-load, schema-resolution, or save failures.
- Build changes must use the existing Frappe asset pipeline. Do not add a new bundler or test framework without a concrete need and an explicit project-level decision.

## 8. Security and privacy

- Treat rule configurations, expressions, process configuration, document content, and API parameters as untrusted input.
- Never use Python eval/exec or browser dynamic evaluation to run user-provided expressions. Use the existing safe compiler and evaluation boundary, and validate the allowed data and capabilities at runtime as well as at save time.
- Frappe safe_eval is not a substitute for resource limits, authorization, input validation, or careful exposure of objects and methods. Keep the execution context narrow and read-only where the operation is intended only to evaluate a condition.
- Minimize sensitive data in logs, errors, snapshots, and test fixtures. Avoid logging credentials, tokens, full documents, or private field values unless explicitly required by a justified and controlled debug policy.
- Do not trust client-provided roles, ownership, DocType names, process names, method paths, return schemas, or policy flags. Re-resolve and validate security-sensitive values on the server.
- External integrations need bounded timeouts, clear failure handling, and no secrets committed to source control.

## 9. Testing expectations

### General approach

- Add or update tests for every behavior change and bug fix. Prefer a regression test that fails before the fix and passes after it.
- Use the existing Frappe test stack, especially frappe.tests.utils.FrappeTestCase and the repository's shared helpers, when exercising framework behavior. Use plain unittest only for code that is genuinely independent of Frappe.
- Prefer realistic document and contract behavior for lifecycle, permissions, database, cache, and schema problems. Mock external services or isolated boundaries when appropriate, but do not mock away the behavior the test is supposed to prove.
- Prefer standard Frappe DocTypes for tests when they model the scenario adequately. Use custom test DocTypes only when necessary to represent FlexiRule-specific fields or behavior, and keep their setup/cleanup deterministic.
- Keep tests isolated and repeatable. Use unique test names or prefixes where collisions are possible, clean up created state, and avoid relying on execution order or pre-existing site data.
- Assert meaningful outcomes: returned payloads, error content/type where appropriate, persisted state, mutation results, branch path, permission denial, or cache invalidation. A test that only asserts that no exception occurred is insufficient for a complex behavioral fix.
- Include negative cases: malformed JSON/schema, missing fields, unauthorized callers, stale cache, empty values, invalid graph references, unsupported event/action combinations, and failure/rollback paths where relevant.
- Test at the public or shared boundary most likely to regress. If save flows are involved, consider backend validation, document save/activation, and the frontend serializer instead of testing only a private helper.
- Do not add flaky sleeps or network-dependent tests. Use deterministic mocks, controlled fixtures, and Frappe's test utilities for jobs/time where practical.
- Do not mark an unrun test as passed. If an existing failure is unrelated, record the exact command and observed failure and separate it from failures caused by the change.

### Common validation commands

Run commands from the appropriate Bench or app environment. Substitute a dedicated test site for <test-site>.

```sh
ruff check flexirule
yarn lint
bench --site <test-site> run-tests --app flexirule
bench --site <test-site> run-tests --module flexirule.ruleflow.tests.test_engine
bench build --app flexirule
bench --site <test-site> run-ui-tests flexirule --headless
```

- Use a focused backend test module during development, then run the app suite when feasible. Replace the example module with the actual test module covering the change.
- UI tests use the repository's Frappe/Cypress path described in E2E_TESTING.md and require a prepared test site/Bench environment.
- Check .github/workflows/ci.yml when a change affects CI or when selecting final verification. CI path filters may skip workflows for documentation-only changes; this is not evidence that code tests ran.
- For documentation-only changes, review links, commands, filenames, and architecture claims rather than running unrelated tests.

## 10. Definition of done

Before calling a task complete:

1. Confirm the change solves the reported behavior and does not merely suppress the error.
2. Confirm relevant contracts, DocType metadata, API code, runtime consumers, and cache invalidation are aligned.
3. Add or update regression tests for behavior changes.
4. Run focused tests and relevant lint/build checks when the environment permits; report exact results.
5. Review the diff for unrelated edits, insecure permission bypasses, new dynamic evaluation, raw SQL, transaction boundary changes, and logging of sensitive data.
6. Update documentation when behavior or developer workflow materially changes. Keep documentation accurate about current implementation versus proposed future work.
7. Summarize what changed, what was tested, what remains unverified, and any follow-up risks.
