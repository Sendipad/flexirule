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

			on_change(config, fieldname, value) {
				// Prevent conflicting inputs: clear the other source field when one is filled
				if (fieldname === "source_field" && value) {
					config.source_value = null;
				} else if (fieldname === "source_value" && value) {
					config.source_field = null;
				}
			},

			validate(config) {
				// Production-ready checks to stop bad configs from saving
				if (!config.source_field && !config.source_value) {
					return __(
						"Normalization requires either a Source Field or a Source Value Expression."
					);
				}
				if (config.source_field && config.source_value) {
					return __("Please provide ONLY a Source Field OR a Source Value, not both.");
				}
				if (!config.transformations || config.transformations.length === 0) {
					return __("You must select at least one transformation to apply.");
				}
			},
		},
		{
			func_name: "mask_value",
			label: __("Mask Sensitive Data"),
			description: __("Masks PII like email, phone, or credit card."),
			icon: "shield",
			color: "#f59e0b",

			on_change(config, fieldname, value) {
				if (fieldname === "source_field" && value) {
					config.source_value = null;
				} else if (fieldname === "source_value" && value) {
					config.source_field = null;
				}
			},

			validate(config) {
				if (!config.source_field && !config.source_value) {
					return __(
						"Masking requires either a Source Field or a Source Value Expression."
					);
				}
				if (!config.mask_type) {
					return __("You must select a Mask Type.");
				}
			},
		},
		{
			func_name: "transform_multi_fields",
			label: __("Transform Multiple Fields"),
			description: __(
				"Applies string normalization to multiple document fields simultaneously."
			),
			icon: "layers",
			color: "#10b981",

			validate(config) {
				if (!config.source_fields || config.source_fields.length === 0) {
					return __("You must select at least one Source Field.");
				}
				if (!config.transformations || config.transformations.length === 0) {
					return __("You must select at least one transformation to apply.");
				}
			},
		},
	],

	get_operation(name) {
		return this.operations.find((op) => op.func_name === name);
	},

	get_visible_operations() {
		return this.operations;
	},
};
