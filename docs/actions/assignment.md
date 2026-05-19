# Assignment Action

The **Assignment** action is a powerful tool for performing batch state mutations on the current document or context variables. It replaces the legacy **Set Value** action with a more robust system that supports multiple operators and sequential execution.

## Key Features

- **Batch Processing**: Define multiple mutations within a single action node.
- **Dual-Mode Editor**: Seamlessly switch between a visual **Formula Resolver** (for dates, math, and aggregations) and a **Template Editor** (for rich text and complex Jinja logic).
- **Conditional Execution**: Each assignment row can have its own **"Run If"** condition using the visual Condition Builder, allowing for granular control over which mutations are applied.
- **Multiple Operators**: Beyond simple assignment, it supports math, list operations, and object merging.
- **Path Validation**: Prevents accidental mutation of protected system paths.

## Value Editors

The Assignment action provides two modes for defining values:

### 1. Formula Resolver

A "no-code" interface for common operations:

- **Date Math**: `Today + 5 Days`, `doc.posting_date - 1 Month`.
- **Numeric Calculations**: Basic math between fields or constants.
- **Aggregations**: `SUM`, `AVG`, or `COUNT` of child table rows.
- **String Helpers**: Concatenation, Case conversion, and Currency formatting.

### 2. Template Editor

A rich-text interface for:

- **Jinja Templates**: Dynamic strings with full access to the execution context.
- **Variable Insertion**: Easily pick fields from `doc` or `vars`.
- **Manual Overrides**: Write custom logic when the visual resolver isn't enough.

## Operators

The Assignment action utilizes a registry of operators, each designed for specific data types:

| Operator                       | Description                                                           | Supported Types | Idempotent |
| :----------------------------- | :-------------------------------------------------------------------- | :-------------- | :--------- |
| **Set Value** (`set`)          | Replaces the target with a new value.                                 | All             | Yes        |
| **Clear** (`clear`)            | Resets the target to its default empty state (null, empty list, etc). | All             | Yes        |
| **Increment By** (`increment`) | Adds a numeric value to the target.                                   | Numeric         | No         |
| **Decrement By** (`decrement`) | Subtracts a numeric value from the target.                            | Numeric         | No         |
| **Append To List** (`append`)  | Adds an item to the end of a list.                                    | Tables, Lists   | No         |
| **Merge Object** (`merge`)     | Merges a dictionary into the target object.                           | JSON, Dicts     | No         |
| **Toggle Boolean** (`toggle`)  | Flips a boolean value (1 to 0, 0 to 1).                               | Check           | No         |

## Target Paths

Assignments can target two primary scopes:

### 1. Document (`doc.*`)

Mutates fields on the document that triggered the rule.

- **Root Fields**: `doc.status`, `doc.naming_series`.
- **Note**: In V1, deep document path assignments for child tables (e.g., `doc.items.0.qty`) are not supported directly via this action.

### 2. Context Variables (`vars.*`)

Mutates variables in the execution context.

- **Nesting**: Supports deep paths like `vars.totals.tax_amount`.
- **Auto-Initialization**: Intermediate dictionaries are created automatically if they don't exist.

## Configuration (JSON)

The configuration is stored as a JSON array of assignment objects. The engine handles both simple legacy formats and the modern structured UI state:

```json
[
	{
		"target": "doc.status",
		"operator": "set",
		"value_mode": "template",
		"value_template": "Closed",
		"when_condition": null
	},
	{
		"target": "vars.counter",
		"operator": "increment",
		"value_mode": "resolver",
		"value_template": "{% raw %}{{ 1 }}{% endraw %}",
		"value_template_ui": {
			"kind": "math_formula",
			"constant_b": 1
		},
		"when_condition": {
			"op": "and",
			"conditions": [
				{
					"left": "doc.docstatus",
					"op": "==",
					"right": 0
				}
			]
		}
	}
]
```

## Safety & Restrictions

- **System Protection**: Mutations to paths starting with `meta.`, `frappe.`, `rule.`, or `caller.` are blocked.
- **Event Awareness**: `doc.*` mutations are prohibited during `after_save` and other read-only events to prevent inconsistent states.
- **Sandboxed Evaluation**: Values are evaluated using Jinja templates with a restricted `SafeFrappeAPI` context.
