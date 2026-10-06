/**
 * Enrichment Process Adapter
 * Provides high-quality UI for document enrichment operations.
 */

frappe.provide("flexirule.processes");

flexirule.processes["Enrichment"] = {
	meta: {
		version: "1.0",
		title: __("Enrichment"),
	},

	get_schema(operation_name, ctx) {
		const operation = this.get_operation(operation_name);
		if (!operation) return null;

		return {
			title: operation.label || operation_name,
			size: "extra-large",
			fields:
				typeof operation.get_config_fields === "function"
					? operation.get_config_fields(ctx)
					: [],
		};
	},

	get_output_schema(operation_name, config, context) {
		const operation = this.get_operation(operation_name);
		if (operation && typeof operation.get_output_schema === "function") {
			return operation.get_output_schema(config, context);
		}
		return [];
	},

	operations: [
		{
			func_name: "calculate_value",
			label: __("Calculate Value"),
			description: __("Compute field values using Python formulas."),
			icon: "calculator",
			get_config_fields: (ctx) => {
				const doc_fields = flexirule.processes.Enrichment.get_doc_fields(ctx);
				return [
					{
						fieldname: "target_field",
						fieldtype: "Select",
						label: __("Target Field"),
						options: doc_fields,
						reqd: 1,
					},
					{
						//TODO : Better have another no code implementation here
						fieldname: "formula",
						fieldtype: "Code",
						label: __("Formula"),
						options: "Python",
						description: __("Expression like: doc.base_amount * doc.conversion_rate"),
						reqd: 1,
					},
				];
			},
			get_output_schema: (config, ctx) => {
				if (config.target_field) {
					return [
						{
							label: config.target_field,
							value: config.target_field,
							type: "Data", // Could be more specific based on field type
						},
					];
				}
				return null;
			},
		},
		{
			func_name: "linked_doc_autocomplete",
			label: __("Linked Doc Autocomplete"),
			description: __("Copy data from a document linked to the current record."),
			icon: "link",
			get_config_fields: (ctx) => {
				const doc_fields = flexirule.processes.Enrichment.get_doc_fields(ctx);
				const link_fields = doc_fields.filter(
					(f) => ["Link", "Dynamic Link"].includes(f.fieldtype) || f.value === ""
				);

				return [
					{
						fieldname: "source_link_field",
						fieldtype: "Select",
						label: __("Link Field"),
						description: __("Select the Link/Dynamic Link field to pull data from."),
						options: link_fields,
						reqd: 1,
					},
					{
						fieldname: "field_mapping",
						fieldtype: "Table",
						label: __("Field Mapping"),
						reqd: 1,
						fields: [
							{
								fieldname: "source_field",
								fieldtype: "Data", // This needs to be dynamic based on the selected link field
								label: __("Source Field (Linked Doc)"),
								reqd: 1,
								columns: 6,
							},
							{
								fieldname: "target_field",
								fieldtype: "Select",
								label: __("Target Field (Current Doc)"),
								options: doc_fields,
								reqd: 1,
								columns: 6,
							},
						],
					},
				];
			},
			get_output_schema: (config, ctx) => {
				const mappings = config.field_mapping || [];
				return mappings.map((mapping) => {
					return {
						label: mapping.target_field,
						value: mapping.target_field,
						type: "Data", // Could be more specific based on field type
					};
				});
			},
		},
		{
			func_name: "copy_from_template",
			label: __("Copy from Template"),
			description: __("Populate fields from a predefined template document."),
			icon: "copy",
			get_config_fields: (ctx) => {
				return [
					{
						fieldname: "template_doctype",
						fieldtype: "Link",
						label: __("Template DocType"),
						options: "DocType",
						reqd: 1,
						onchange: (val, row, ctx) => {
							ctx.update_field("template_name", { options: val });
							ctx.update_field("field_list", {
								options: "DocField",
								get_query: () => ({ filters: { parent: val } }),
							});
						},
					},
					{
						fieldname: "template_name",
						fieldtype: "Dynamic Link",
						label: __("Template Document"),
						options: "template_doctype",
						reqd: 1,
					},
					{
						fieldname: "field_list",
						fieldtype: "MultiSelect",
						label: __("Fields to Copy"),
						description: __(
							"Select one or more fields to overwrite from the template."
						),
						reqd: 1,
					},
				];
			},
			get_output_schema: (config, ctx) => {
				const fields = Array.isArray(config.field_list)
					? config.field_list
					: typeof config.field_list === "string"
					? config.field_list.split("\n").filter((f) => f.trim())
					: [];

				return fields.map((field) => {
					return {
						label: field,
						value: field,
						type: "Data", // Could be more specific based on field type
					};
				});
			},
		},
	],

	get_operation(name) {
		return this.operations.find((op) => op.func_name === name);
	},

	get_doc_fields(context) {
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
