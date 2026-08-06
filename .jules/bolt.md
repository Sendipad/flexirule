## 2025-06-16 - [Rule Execution Bottlenecks]
**Learning:** Re-computing rule version hashes by iterating over all actions during every action plan lookup results in $O(N^2)$ complexity per execution. Additionally, re-defining helper functions inside `_build_eval_locals` for every expression evaluation adds significant overhead in hot paths.
**Action:** Use `frappe.local` to cache computed rule hashes for the duration of the request. Extract static expression helpers to the module level and use a base context dictionary for shallow copying to minimize CPU churn during evaluation.
