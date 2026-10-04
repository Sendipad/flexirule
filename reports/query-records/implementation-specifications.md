Query Records Refactor — Implementation Requirements & Rules

Branch: refactor/query-records
Repository: Sendipad/flexirule
Status: Implementation Specification
Purpose: Authoritative requirements and engineering rules for the Query Records refactor

1. Objective

Refactor the FlexiRule Query Records action into a clean, maintainable, fully UI-driven query configuration experience while preserving compatibility with the existing backend contract and leveraging Frappe's native query capabilities.

The refactor must:

Support all required Query Records query modes.

Support nested field traversal and nested filters.

Use frappe.qb.get_query capabilities rather than maintaining a parallel custom query engine.

Reuse existing FlexiRule components and controls wherever they already satisfy the requirement.

Keep frontend configuration aligned with the backend's expected configuration signatures.

Make the UI understandable to non-technical rule designers.

Avoid exposing SQL, Python, JSON, or implementation details to normal users.

Preserve existing behavior where the behavior is already correct.

Avoid unnecessary architectural changes outside Query Records.

Keep the implementation compatible with the existing FlexiRule rule/action architecture.

2. Core Architectural Principle

Backend contract is authoritative

The frontend must configure queries according to the backend contract.

Do not invent a frontend-specific configuration model and then transform it through multiple incompatible representations.

The preferred flow is:

UI ↓ Query Records configuration ↓ backend-compatible config ↓ Query Records handler ↓ frappe.qb.get_query ↓ database 

The frontend should therefore model the concepts the backend actually needs.

If a backend field/configuration already exists and is correct, reuse it rather than introducing a duplicate representation.

3. Implementation Rules

Rule 1 — Analyze before modifying

Before changing Query Records code:

inspect the complete existing Query Records frontend;

inspect all Query Records backend handlers;

inspect related condition/filter components;

inspect resolver/value components;

inspect existing tests;

inspect all callers of the existing APIs;

inspect the current configuration payload;

inspect the current debug/test-query path;

inspect frappe.qb.get_query capabilities already established by the capability tests.

Do not make assumptions based on component names alone.

Rule 2 — Reuse existing components

Prefer existing FlexiRule components over creating new controls.

Particularly investigate and reuse:

ComboBoxControl

FlexValueControl

existing condition/filter controls

field selectors

DocType selectors

value resolver controls

field metadata utilities

validation utilities

existing query preview/debug components

A new component is justified only when an existing component cannot satisfy the requirement without becoming excessively complicated or violating its existing contract.

Rule 3 — Do not duplicate existing controls

Do not create another implementation of:

searchable field selection;

DocType selection;

value selection;

operator selection;

resolver selection;

condition rows;

nested condition groups;

field metadata lookup.

Extend existing infrastructure where practical.

4. Field Browser Requirements

The Query Records field selector must use a navigable field browser, not a flat list.

4.1 Current context

The field browser always operates within a current DocType context.

For example:

Sales Invoice 

Search results are initially limited to fields belonging to:

Sales Invoice 

4.2 Navigable fields

Fields that represent another record structure must expose navigation.

Examples include:

Link fields

Table fields

A navigable field should provide:

Field Name → 

The user can:

select the field itself;

navigate into the related DocType.

These are separate actions.

4.3 Link traversal

Example:

Sales Invoice Customer → 

Navigating produces:

Sales Invoice > Customer 

The next field context is the linked DocType.

4.4 Child Table traversal

Example:

Sales Invoice Items → 

Navigating produces:

Sales Invoice > Items 

The context becomes the child DocType.

The UI must understand that a Table field represents a child-table relationship rather than treating it as an ordinary scalar field.

4.5 Breadcrumb navigation

Navigation must preserve context.

Example:

Sales Invoice > Customer > Customer Group 

The user must be able to go back:

Sales Invoice > Customer 

without rebuilding the previous context.

4.6 Search behavior

Search must be scoped to the current context.

For example:

Sales Invoice 

searches Sales Invoice fields.

After navigating to:

Sales Invoice > Customer 

the search searches Customer fields.

Do not search every DocType globally unless the user explicitly requests global search.

5. Field Selection Rules

A field can be selected independently of whether it is navigable.

For example:

Customer 

may be selected as the query field.

If it is a Link field, it can also be navigated.

Therefore:

Click field = select field Click navigation arrow = enter related context 

Do not make navigation mutually exclusive with field selection.

6. Nested Field Representation

Nested fields must have a deterministic representation.

For example:

Sales Invoice → Customer → Customer Group 

must produce a backend-compatible field path.

The exact representation must follow the existing backend contract.

Do not introduce a UI-only path representation that requires unnecessary conversion.

The implementation must verify how nested fields are represented by:

Query Records backend;

Frappe query builder;

existing filter configuration;

selected-field configuration.

7. Nested Filters

Nested filters are a required feature of this refactor.

The implementation must support filters against related fields.

Examples:

Customer.customer_group = "Wholesale" 

and:

Sales Invoice → Items → Item Group = "Raw Material" 

The UI must allow users to construct these filters through navigation rather than manually entering field paths.

8. Nested Filter UI

Nested filters must use the same navigable field-browser concept.

A filter should conceptually be:

[Field] [Operator] [Value] 

where [Field] can be selected through the navigable field browser.

Example:

Customer → Customer Group 

then:

Customer Group | equals | Wholesale 

For child tables:

Items → Item Group 

then:

Item Group | equals | Raw Material 

9. Filter Groups

The implementation must preserve/support logical grouping.

At minimum, the configuration must be capable of representing:

A AND B A OR B 

and nested groups such as:

(A AND B) OR (C AND D) 

The UI must make the grouping understandable to normal users.

Do not expose raw boolean-expression syntax.

10. Filter UI Ownership

Do not create a Query Records-specific condition implementation if an existing FlexiRule condition/filter component already provides the required behavior.

Instead:

identify the existing condition implementation;

determine what Query Records requires;

extend it where appropriate;

preserve existing consumers.

Query Records-specific behavior should be implemented through configuration/context rather than duplicated components whenever possible.

11. Operators

Operators must come from a centralized/authoritative definition.

Do not duplicate operator lists independently in multiple Vue components.

Operators must remain compatible with the backend query representation.

The UI must not expose an operator that the backend cannot execute.

12. Value Handling

Filter values must use the existing FlexiRule value/resolver infrastructure where applicable.

The UI must support dynamic values where Query Records already supports them.

Examples include:

Static value Document field Resolver System context 

Do not implement an independent Query Records value-resolution system.

13. Between Operator

The Between operator requires special handling.

The UI must represent its value as:

[value1, value2] 

For example:

Posting Date Between [01-01-2026] [31-01-2026] 

The frontend must preserve the existing backend-compatible [val1, val2] payload.

Do not change the backend payload merely to simplify the UI.

The date/time resolver architecture should own date-specific behavior where appropriate.

14. Query Modes

All existing Query Records modes must be explicitly audited and preserved.

The implementation must account for at least:

Query List

Query Document

Exist Record

Query Report

Aggregations

The refactor must not accidentally make one mode behave like another.

Each mode must have a clearly defined configuration contract.

15. Selected Fields

Selected fields must use the same navigable field browser.

Example:

Fields ☑ Customer ☑ Posting Date ☑ Grand Total ☑ Customer → Customer Group 

The configuration must distinguish between:

query/filter fields 

and:

returned/selected fields 

Do not assume that selecting a filter field automatically means that the field should be returned.

16. Full Document vs Selected Fields

The implementation must preserve the distinction between:

Return full document 

and:

Return selected fields 

The UI should make this distinction explicit.

Do not silently change existing behavior.

17. Ordering

Ordering must be represented through structured configuration.

Example:

Posting Date Descending Grand Total Descending Customer Ascending 

Ordering fields must use the same field browser and nested-field traversal system.

Do not allow arbitrary SQL ORDER BY strings.

18. Limit / Pagination

Where supported by the existing backend contract, limits must remain structured.

The frontend must not construct raw SQL fragments.

Backend validation remains authoritative.

19. Aggregations

Aggregation functionality must use native query-builder capabilities.

Supported operations should follow the backend-supported capabilities rather than implementing custom SQL.

Examples may include:

Count Sum Average Minimum Maximum 

The implementation must verify each operation against the actual Frappe query-builder capability before exposing it in the UI.

20. Query Report

Query Report must remain a distinct query mode.

Do not force Query Report into the same assumptions as Query List or Query Document.

The implementation must inspect:

report configuration;

report filters;

test-query behavior;

execution behavior;

returned schema;

aggregation behavior.

21. Debug Query / Test Query

The existing Query Records debug/test-query functionality must be audited before modification.

The following paths must be compared:

test_query ↓ debounced_schema_update ↓ test_action_query 

against:

QueryRecordsHandler.execute 

The refactor must avoid maintaining two independent query implementations.

Ideally:

test/debug ↓ same configuration ↓ same query-building logic 

with only execution behavior differing where necessary.

22. Query Builder Requirement

The implementation must use the established Frappe Query Builder capabilities.

Prefer:

frappe.qb.get_query(...) 

and supported query-builder APIs.

Do not introduce custom SQL generation when the required behavior is already supported by Frappe Query Builder.

Raw SQL is not an acceptable shortcut for ordinary Query Records functionality.

23. Backend Query Contract

The backend must remain the final authority for:

valid fields;

valid operators;

valid DocTypes;

permissions;

query structure;

aggregation;

ordering;

limits;

nested relationships;

returned fields.

Frontend validation improves UX but must never replace backend validation.

24. Permissions and Security

Query Records must continue to respect Frappe permission semantics.

The refactor must not:

bypass permissions;

introduce arbitrary SQL;

allow arbitrary field access;

allow arbitrary DocType access;

expose internal implementation details.

Any existing ignore_permissions behavior must be explicitly reviewed rather than accidentally preserved or expanded.

25. Configuration Contract

Configuration should be declarative.

Prefer:

{ "doctype": "...", "filters": [...], "fields": [...], "order_by": [...], "limit": ... } 

over UI-specific state such as:

{ "selectedTab": "...", "expandedNode": "...", "searchText": "..." } 

UI state must not become part of the persisted backend configuration.

26. No Raw JSON UI

Normal users must not need to write or understand JSON.

No configuration screen should require users to manually construct:

{ "field": "...", "operator": "...", "value": "..." } 

The UI generates the configuration.

27. No Raw SQL UI

Never expose SQL as the normal configuration mechanism.

The user should configure:

Field → Operator → Value 

rather than:

WHERE ... 

28. No Python UI

Do not require Python expressions or Python code for Query Records configuration.

29. Component Responsibility

Each component should have one clear responsibility.

For example:

QueryRecordsConfig orchestration FieldBrowser field discovery/navigation FilterGroup logical grouping FilterRow field/operator/value FlexValueControl value configuration OrderingControl order configuration 

Do not allow a single component to become a monolithic Query Records editor.

30. State Management

Avoid duplicating the same configuration in:

component state Pinia state computed state backend payload 

There should be a clear source of truth.

Temporary UI state such as:

search text;

expanded navigation;

selected browser context;

must remain separate from persisted query configuration.

31. Validation

Validation must happen at appropriate levels.

UI validation

Provide immediate feedback for:

missing DocType;

missing field;

missing operator;

missing required value;

invalid Between values;

incomplete nested filter;

invalid aggregation configuration.

Backend validation

Backend remains authoritative and must validate the final configuration.

32. Error Handling

Errors must be understandable to users.

Avoid exposing raw errors such as:

Unknown column tabJournal Entry.accounts.party_master 

when the error can be translated into a useful configuration message.

However, developer/debug mode may retain the original technical error for diagnosis.

33. Existing Bug Regression

The refactor must explicitly prevent regressions related to nested/child-table fields.

The known class of failure:

tabJournal Entry.accounts.party_master 

must not reappear when querying child-table fields.

The implementation must correctly distinguish:

Parent DocType Child Table DocType Field Relationship/path 

rather than treating a child field as a field belonging directly to the parent SQL table.

34. Tests

Tests must cover the complete configuration pipeline.

Backend

At minimum:

simple field filter;

nested Link filter;

child Table filter;

multiple filters;

nested filter groups;

AND;

OR;

selected fields;

nested selected fields;

ordering;

limit;

aggregation;

Query Document;

Query List;

Exist Record;

Query Report;

Between;

dynamic values;

permissions;

invalid configuration.

Frontend

At minimum:

field search;

field navigation;

breadcrumb navigation;

selecting a navigable field;

nested field selection;

nested filter creation;

nested filter grouping;

operator changes;

Between value editing;

resolver/value changes;

selected fields;

ordering;

mode-specific configuration;

validation;

configuration serialization.

35. Test Contract

Tests must verify both:

UI configuration 

and:

actual backend behavior 

A test that only checks that a component renders is insufficient for important Query Records behavior.

36. Backward Compatibility

Existing saved Query Records configurations must remain readable whenever technically possible.

If migration is required:

document the old format;

define the new format;

implement deterministic migration;

add regression tests;

avoid silently changing query semantics.

Do not break existing rules merely to simplify the new UI.

37. Documentation

Implementation changes must update relevant documentation when user-visible behavior changes.

Documentation should explain Query Records from the user's perspective:

Choose what records to query ↓ Choose fields ↓ Add filters ↓ Navigate into related records when needed ↓ Choose returned fields ↓ Optionally sort/limit/aggregate ↓ Save 

Do not document internal Python classes as the primary user experience.

38. Scope Control

The branch is specifically for the Query Records refactor.

Do not use this branch to perform unrelated refactors.

Avoid changing:

unrelated action types;

unrelated resolver families;

unrelated UI infrastructure;

unrelated backend architecture;

unless the change is directly required by Query Records.

If shared infrastructure must change, keep the change minimal and backward compatible.

39. No Premature Abstraction

Do not create generic frameworks merely because Query Records contains repeated patterns.

First determine whether an existing FlexiRule abstraction already solves the problem.

Create a new abstraction only when:

the responsibility is clearly reusable;

at least two real consumers require it;

the abstraction reduces complexity rather than moving it elsewhere.

40. No Duplicate Query Engines

There must be one authoritative query-building path.

Avoid:

Frontend preview query builder Backend test query builder Backend execution query builder Report query builder 

when they are implementing the same semantics independently.

The goal is:

Configuration ↓ Authoritative query builder ↓ Frappe Query Builder ↓ Execution 

41. Implementation Sequence

Implementation should proceed in this order:

Step 1 — Existing architecture audit

Confirm:

current components;

current configuration;

backend contract;

query modes;

tests;

existing reusable controls.

Step 2 — Configuration contract

Finalize the configuration representation before redesigning the UI.

Step 3 — Field browser

Implement/extend navigable field selection.

Step 4 — Nested filter model

Implement nested filter configuration using the field browser.

Step 5 — Filter UI

Integrate existing condition/value controls.

Step 6 — Selected fields

Integrate the same field browser.

Step 7 — Ordering

Integrate the same field browser.

Step 8 — Query modes

Verify mode-specific configuration.

Step 9 — Backend integration

Ensure the configuration maps directly to the backend contract.

Step 10 — Debug/test query

Unify test/debug behavior with actual query construction.

Step 11 — Regression tests

Add backend and frontend coverage.

Step 12 — UX cleanup

Only after functionality is correct, improve layout, labels, descriptions, empty states, and interaction details.

42. Definition of Done

The Query Records refactor is complete only when:

[ ] Existing Query Records behavior is understood and covered.

[ ] Backend configuration contract is documented.

[ ] frappe.qb.get_query is used for supported query construction.

[ ] No unnecessary raw SQL is introduced.

[ ] Existing reusable controls are reused.

[ ] Field browser supports scoped search.

[ ] Link navigation works.

[ ] Child Table navigation works.

[ ] Breadcrumb/back navigation works.

[ ] Navigable fields can still be selected.

[ ] Nested filters work.

[ ] Nested filter groups work.

[ ] AND/OR behavior works.

[ ] Between preserves [val1, val2].

[ ] Dynamic values work.

[ ] Selected fields work.

[ ] Nested selected fields work.

[ ] Ordering works.

[ ] Aggregations work where supported.

[ ] Query List works.

[ ] Query Document works.

[ ] Exist Record works.

[ ] Query Report works.

[ ] Debug/test query uses the authoritative query logic.

[ ] Permissions are preserved.

[ ] Existing configurations remain compatible or have a migration.

[ ] Backend tests pass.

[ ] Relevant frontend tests pass.

[ ] Known child-table field regression is covered.

[ ] No unrelated architectural changes are introduced.

[ ] User documentation reflects the new UI.

43. Final Engineering Rule

When choosing between two implementation approaches, prefer the one that produces:

less duplicated logic + clearer configuration + stronger reuse + native Frappe capabilities + simpler user interaction.

The Query Records UI should be a visual configuration layer over the backend query contract, not a second query language.

