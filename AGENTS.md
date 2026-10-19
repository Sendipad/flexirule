# FlexiRule coding-agent guidance

Use the repository-local skills for matching work when they are installed under `.agents/skills/`:

- **Frappe / ERPNext backend, DocTypes, hooks, queries, permissions, jobs, tests, and Vue integration:** use `frappe-app-dev`; read only the references relevant to the task.
- **Pull-request or diff review:** use `frappe-code-review`.
- **Refactoring and implementation structure:** use `code-style`.
- **Rule Builder and other UI/UX changes:** use `ui-design`, together with the Frappe Vue guidance when applicable.
- **Documentation, plans, release notes, and pull-request text:** use `technical-writing`.

## FlexiRule-specific rules

1. Inspect the actual FlexiRule implementation and the relevant Frappe / ERPNext source for the supported version before proposing or changing behavior. Do not rely on a skill or memory as a substitute for source verification.
2. Prefer native Frappe APIs, lifecycle hooks, permission checks, query-builder support, fixtures, and established app patterns before introducing custom mechanisms. Explain why a custom layer is needed when native support is insufficient.
3. Preserve existing contracts and behavior unless a change is explicitly intended. Check security boundaries and backward compatibility, and avoid unrelated refactors.
4. For bugs and reviews, identify root cause and cite concrete files/functions or framework APIs; distinguish verified findings from assumptions and compare maintainable alternatives.
5. Run focused tests for the changed behavior. For changes to backend/frontend contracts, queries, Vue components, or serialization, include the relevant backend and frontend checks when available. Report any checks that could not be run.

If a relevant skill is missing, install the selected skills with `bash scripts/install-frappe-agent-skills.sh`. Do not load every reference file for unrelated tasks.
