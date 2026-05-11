# Process Adapter Standards

This document defines the standard structure and requirements for FlexiRule Process Adapters. Following these standards ensures compatibility with the Rule Builder's `ConfigurableAction` runtime.

## Recent Enhancements
- **`writes_to`** field now supports values: `"None"`, `"Context"`, `"Document"`, `"Database"`
- **`has_side_effect`** flag indicates operations that modify external systems
- **`config_schema`** now supports full JSON Schema with nested objects/arrays
- **`output_schema`** usage in return type inference for context variables
- **`action_overrides`** JSON can specify `policy` and `fields` for customizing behavior
- **`visible_in_builder`** flag controls operation discoverability in the Rule Builder UI
- **`for_doctype`** + **`doctype_filters`** restrict operation to specific DocTypes
- **Note**: `get_schema()` and `get_output_schema()` methods are **Priority 1** if defined; backend contract is fallback

## File Location

Process adapters should be placed in `apps/[app_name]/[app_name]/[Module def]/process/[process_name]/[process_name].js`.

## Example Structure

```javascript
frappe.provide("flexirule.processes");

flexirule.processes["ProcessName"] = {
	meta: {
		version: "1.0",
		title: __("Process Title"),
	},

	/**
	 * Optional: Setup function called once when the adapter is loaded.
	 * Use for global context enrichment.
	 */
	setup(context) {
		// Global setup for the entire adapter
	},

	/**
	 * Required: Returns the configuration schema for a specific operation.
	 * Priority 1: If this method exists, it takes precedence.
	 */
	get_schema(operation_name, context) {
		const operation = this.get_operation(operation_name);
		if (!operation) return [];

		return typeof operation.get_config_fields === "function"
			? operation.get_config_fields(context)
			: [];
	},

	/**
	 * Optional: Returns the output schema for a specific operation.
	 * This is used to determine what variables the operation contributes to the context.
	 * Priority 1: If this method exists, it takes precedence.
	 */
	get_output_schema(operation_name, config, context) {
		const operation = this.get_operation(operation_name);
		if (operation && typeof operation.get_output_schema === "function") {
			return operation.get_output_schema(config, context);
		}
		return [];
	},

	/**
	 * Optional: Returns custom buttons (Quick Actions) for the dialog header.
	 */
	get_actions(operation_name, context) {
		return [
			{
				label: __("Preview JSON"),
				click: (config) => {
					frappe.msgprint("<pre>" + JSON.stringify(config, null, 2) + "</pre>");
				},
			},
		];
	},

	/**
	 * Optional: Validates the configuration before saving.
	 * Should return an error message string if validation fails, or null/undefined if valid.
	 */
	validate(operation_name, config, context) {
		// Return error message if validation fails, or null if valid
		return null;
	},

	/**
	 * Optional: Returns default configuration for an operation.
	 */
	get_default_config(operation_name) {
		const operation = this.get_operation(operation_name);
		if (!operation || typeof operation.get_config_fields !== "function") {
			return {};
		}

		const defaults = {};
		const raw_fields = operation.get_config_fields({});

		raw_fields.forEach((field) => {
			// Skip layout fields
			if (["Section Break", "Column Break", "HTML"].includes(field.fieldtype)) {
				return;
			}

			// Handle Table fields
			if (field.fieldtype === "Table") {
				defaults[field.fieldname] = [];
				return;
			}

			// Regular field
			if (field.default !== undefined) {
				defaults[field.fieldname] = field.default;
			}
		});

		return defaults;
	},

	operations: [
		{
			func_name: "operation_method",
			label: __("Operation Label"),
			description: __("Brief description of what this does"),
			icon: "edit",
			color: "#3b82f6",

			/**
			 * Optional: Setup function called when this operation is loaded.
			 */
			setup: (config, context) => {
				// Operation-specific setup
			},

			/**
			 * Returns the raw Frappe field definitions for the UI.
			 */
			get_config_fields: (ctx) => {
				return [
					{
						fieldname: "field_name",
						fieldtype: "Data",
						label: __("Field Label"),
						reqd: 0,
					},
				];
			},

			/**
			 * Optional: Returns the output schema for this operation.
			 * This is used to determine what variables this operation contributes to the context.
			 */
			get_output_schema: (config, ctx) => {
				// Return array of {label, value, type} for variables this operation creates
				return [
					{
						label: __("Output Variable"),
						value: "output_var",
						type: "Data",
					},
				];
			},

			/**
			 * Optional: Validates this operation's configuration.
			 * Should return an error message string if validation fails, or null/undefined if valid.
			 */
			validate: (config, ctx) => {
				// Return error message if validation fails, or null if valid
				return null;
			},

			/**
			 * Optional: Operation-specific quick actions.
			 */
			get_actions: (ctx) => {
				return [
					{
						label: __("Reset"),
						click: (config, ctx) => ctx.update_field("source_field", null),
					},
				];
			},
		},
	],

	// Utility Helpers
	get_operation(name) {
		return this.operations.find((op) => op.func_name === name);
	},

	get_doc_fields(context) {
		// Helper to get document fields for autocomplete
		const doctype = context.document_type;
		if (!doctype) return [{ label: __("Select DocType first"), value: "" }];

		const fields = frappe
			.get_meta(doctype)
			.fields.filter((f) => !frappe.model.no_value_type.includes(f.fieldtype))
			.map((f) => ({
				label: `${__(f.label)} (${f.fieldname})`,
				value: f.fieldname,
				fieldtype: f.fieldtype,
			}));

		return [{ label: __("Select a field..."), value: "" }, ...fields];
	},
};
```

## Field Type Mapping

The runtime automatically maps these custom field types to Frappe equivalents:

-   `DocField` → `Autocomplete` (with document field options)
-   `MultiDocField` → `MultiSelectList` (with document field options)
-   `FlexiAutocomplete` → Enhanced autocomplete with descriptions

## Context Object

The context object passed to adapter functions contains:

-   `doc`: Current configuration object (or row in tables)
-   `row`: Current row object (in table contexts)
-   `parent`: Parent configuration object
-   `config`: Root configuration object
-   `document_type`: Target document type
-   `process_name`: Current process name
-   `operation_name`: Current operation name
-   `vars`: Context variables dictionary
-   `update_field`: Function to update field values: `(fieldname, value) => void`

## Dependency Handling

The runtime supports standard Frappe dependency attributes:

-   `depends_on`: Controls field visibility
-   `mandatory_depends_on`: Controls field requirement
-   `read_only_depends_on`: Controls field editability

## Best Practices

1. **Use `DocField` for Field Selection**: Always use `fieldtype: "DocField"` for fields that select from the document. The runtime automatically resolves these to high-performance, cached `Autocomplete` fields with system field support.

2. **Use `MultiDocField` for Multiple Fields**: Similarly, use `MultiDocField` for multiple field selection; it maps to `MultiSelectList`.

3. **Strict Context**: Never mutate the global state. All updates should happen via the `ctx` (context) provided to hooks like `onchange`.

4. **Async Friendly**: Hooks like `get_options` or `onchange` should be `async` if they perform metadata lookups.

5. **Standard Labels**: Use `__()` for all user-facing labels to support translation.

6. **Rich Fields**: Prefer `options: ctx.document_type` for field selectors to ensure they are scoped correctly.

7. **Validation**: Implement validation at both operation and adapter levels to ensure configuration integrity.

8. **Memory Management**: Implement proper cleanup in setup functions to prevent memory leaks.

## Common Utilities

The runtime provides several utilities at `flexirule.utils`:

-   `flexirule.utils.get_doctype_fields(doctype)`: Returns cached fields for any DocType.
-   `flexirule.utils.get_combined_fields(doctype, variables)`: Combines DocType fields with action variables.
-   `flexirule.utils.load_process_adapter(process_name)`: Loads a process adapter dynamically.
-   `flexirule.utils.get_process_adapter(process_name)`: Gets a loaded process adapter instance.
