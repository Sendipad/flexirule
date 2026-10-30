# Sub-Rule Public Interface Contract

## Purpose

A Rule exposed as a callable Sub-Rule is a reusable component. Its public contract describes the inputs a caller must provide and the outputs a caller may consume. Internal action variables are implementation details unless exposed by the public output schema.

## Stored contract

The Rule DocType adds two JSON fields, available when `trigger_type = Callable Event` and `exposed_as_subrule = 1`:

- `input_schema`: array of public input definitions.
- `output_schema`: array of public output definitions.

Each field supports `fieldname`, `label`, `fieldtype`, `options`, `reqd`, optional `default` and `description`. Output definitions additionally support `source` provenance and recursive `children` for fields inside object/list outputs. `reqd` is normalized to 0/1. It means input requiredness for `input_schema`; on `output_schema` it is metadata and does not guarantee that an execution value is non-null.

Example input schema:

```json
[
	{
		"fieldname": "party",
		"label": "Customer",
		"fieldtype": "Link",
		"options": "Customer",
		"reqd": 1
	},
	{ "fieldname": "from_date", "label": "From Date", "fieldtype": "Date", "reqd": 0 }
]
```

Example output schema:

```json
[
	{
		"fieldname": "document_counts",
		"label": "Document Counts",
		"fieldtype": "Table",
		"reqd": 0,
		"source": { "kind": "sub_rule_output" },
		"children": [
			{
				"fieldname": "document_type",
				"label": "Document Type",
				"fieldtype": "Data",
				"reqd": 0,
				"source": { "kind": "literal" }
			},
			{
				"fieldname": "issued_count",
				"label": "Issued Count",
				"fieldtype": "Int",
				"reqd": 0,
				"source": { "kind": "aggregate" }
			}
		]
	}
]
```

## Inferred compatibility mode

If a schema field is empty, FlexiRule infers that side of the interface for legacy Rules:

- Input fields are inferred from required variables currently discovered by the rule validator.
- Output fields are inferred from action return variables, Process `writes_vars`, and Assignment writes to `vars.*`. An action's `resolved_output_schema` becomes the inferred output's recursive `children`.

Inferred schemas improve configuration and variable discovery, but the inference algorithm is necessarily conservative and is not a substitute for an explicitly reviewed contract. Explicit input schemas must declare every required variable detected by the current validator. Explicit output schemas may expose only fields actually produced by the Rule. Callers must map every required input and cannot map undeclared targets when the target has an explicit input schema.

## Resolution and propagation

`flexirule.ruleflow.api.get_sub_rule_contract` returns the active exposed callable Rule's interface. The Sub-Rule editor consumes its input schema to populate mapping targets and sets the caller action's `resolved_output_schema` from the target output schema. The graph variable catalogue recursively propagates child fields, so downstream controls can discover paths such as:

`vars.customer_summary.document_counts.issued_count`

## Compatibility and security

This increment does not remove the existing `SubRuleVarsOverlay` parent fallback. Runtime context isolation is a separate compatibility-sensitive change and should be done only after existing rules relying on implicit parent visibility have been identified and migrated. Explicit contracts improve authoring and validation now, while strict runtime input binding and output projection remain follow-up work.

The API resolves only an active, exposed Callable Event Rule and requires Rule read permission. Drafts without explicit schemas continue to use inferred behavior.
