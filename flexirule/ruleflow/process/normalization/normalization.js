/**
 * Normalization Process Adapter
 *
 * Normalization now relies on backend-declared config_schema in the Process
 * operation metadata. This adapter intentionally stays thin to avoid keeping
 * a duplicate operation schema implementation in frontend code.
 */

frappe.provide("flexirule.processes");

flexirule.processes["Normalization"] = {
	meta: {
		version: "2.0",
		title: __("Normalization"),
	},

	operations: [
		{
			func_name: "transform_value",
			label: __("Transform Value"),
			description: __("Apply configured normalization transformations to a source value."),
			icon: "edit",
			color: "#3b82f6",
		},
	],

	get_operation(name) {
		return this.operations.find((op) => op.func_name === name);
	},

	get_visible_operations() {
		return this.operations;
	},
};
