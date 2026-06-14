// Registry for mapping Frappe fieldtypes to Vue components

class Registry {
	constructor() {
		this.rules = [];
	}

	/**
	 * Register a new control mapping rule.
	 * @param {Object} rule
	 * @param {Function} rule.match - function(df, context) => boolean
	 * @param {String} rule.component - The string name of the globally registered Vue component
	 * @param {Function} [rule.mapProps] - function(df, context) => Object of props to bind
	 */
	register(rule) {
		this.rules.push(rule); // Append, so earlier matches win if we use find, wait, if we push, we should use find. We want newer plugins to override, so unshift is better. Let's stick to unshift so latest registered wins.
		// Wait, unshift means the LAST registered rule runs FIRST.
	}

	/**
	 * For internal default rules, append them so they run last.
	 */
	registerDefault(rule) {
		this.rules.push(rule);
	}

	resolve(df, context = {}) {
		if (!df) {
			df = { fieldtype: "Data" };
		}
		for (const rule of this.rules) {
			if (rule.match(df, context)) {
				return {
					component: rule.component,
					props: rule.mapProps ? rule.mapProps(df, context) : {},
				};
			}
		}
		// Fallback
		return {
			component: "DataControl",
			props: {},
		};
	}
}

export const ControlRegistry = new Registry();

// --- Default Registrations ---

// 1. ComboBox (Link, Dynamic Link, Autocomplete, FieldPicker, DocField)
ControlRegistry.registerDefault({
	match: (df, context) => {
		const isDocFieldType =
			["Link", "Dynamic Link", "Autocomplete", "FieldPicker", "DocField"].includes(
				df?.fieldtype
			) || df?.options === "DocField";
		return isDocFieldType;
	},
	component: "ComboBoxControl",
	mapProps: (df, context) => {
		let doctype = null;
		if (df.fieldtype === "Link") {
			doctype = df.options || df.target_doctype || null;
		} else if (df.fieldtype === "Dynamic Link") {
			doctype = context.doc?.[df.options] || "";
		}

		let options = [];
		const isDocFieldType =
			["DocField", "FieldPicker"].includes(df.fieldtype) || df.options === "DocField";

		if (isDocFieldType) {
			if (Array.isArray(df?.options) && df.options.length > 0) {
				options = df.options;
			}
		} else {
			options =
				df?.autocomplete_options ||
				(["Autocomplete", "Select"].includes(df?.fieldtype) ? df?.options : null) ||
				context.options ||
				[];
		}

		const overrideContext =
			["FieldPicker", "DocField"].includes(df.fieldtype) || df.options === "DocField"
				? df.context || context.doc
				: null;

		// Default get_query for DocField
		let get_query = context.get_options || df.get_query || null;
		if (isDocFieldType && !options.length && !get_query) {
			const targetDoctype =
				df.target_doctype ||
				(typeof df.options === "string" &&
				!df.options.startsWith("vars.") &&
				!df.options.startsWith("doc.") &&
				!["DocField", "Field Picker", "Variables"].includes(df.options)
					? df.options
					: context.engine?.rule_doc?.document_type || null);

			if (targetDoctype) {
				get_query = async (search_term) => {
					try {
						// Fallback to global window object if needed
						const fields = await window.flexirule.utils.get_doctype_fields(
							targetDoctype
						);
						if (!search_term) return fields;
						const q = search_term.toLowerCase();
						return fields.filter(
							(f) =>
								(f.label || "").toLowerCase().includes(q) ||
								(f.value || "").toLowerCase().includes(q) ||
								(f.description || "").toLowerCase().includes(q)
						);
					} catch (e) {
						console.error("FlexiRule: DocField options fetch failed", e);
						return [];
					}
				};
			}
		}

		return {
			rule: context.engine?.rule_doc,
			doctype: doctype,
			options: options,
			get_query: get_query,
			filters: df.get_query ? null : df.filters,
			context: overrideContext,
			trigger: df.fieldtype === "FieldPicker" ? "button" : "input",
		};
	},
});

// 2. Select
ControlRegistry.registerDefault({
	match: (df) => df?.fieldtype === "Select",
	component: "SelectControl",
});

// 3. Check
ControlRegistry.registerDefault({
	match: (df) => df?.fieldtype === "Check",
	component: "CheckControl",
	mapProps: (df, context) => ({
		modelValue: Boolean(context.modelValue),
	}),
});

// 4. TimePickerControl (Date, Datetime)
ControlRegistry.registerDefault({
	match: (df) => ["Date", "Datetime"].includes(df?.fieldtype),
	component: "TimePickerControl",
});

// 5. TextControl
ControlRegistry.registerDefault({
	match: (df) => ["Text", "Small Text", "Long Text"].includes(df?.fieldtype),
	component: "TextControl",
});

// 6. CodeControl / Editors
ControlRegistry.registerDefault({
	match: (df) =>
		["Code", "JSON", "Text Editor", "HTML Editor", "Markdown Editor"].includes(df?.fieldtype),
	component: "CodeControl",
});

// 7. FlexiGrid
ControlRegistry.registerDefault({
	match: (df) => ["Table", "FlexiGrid", "flexigrid"].includes(df?.fieldtype),
	component: "FlexiGrid",
	mapProps: (df, context) => ({
		engine: context.engine,
	}),
});

// 8. MultiSelectList
ControlRegistry.registerDefault({
	match: (df) =>
		["MultiSelect", "MultiFieldPicker", "MultiSelectList", "MultiCheck"].includes(
			df?.fieldtype
		),
	component: "MultiSelectList",
	mapProps: (df, context) => {
		let displayMode = df.displayMode;
		if (!displayMode) {
			if (df.fieldtype === "MultiSelect" || df.fieldtype === "MultiFieldPicker")
				displayMode = "badges";
			else if (df.fieldtype === "MultiSelectList") displayMode = "list";
			else if (df.fieldtype === "MultiCheck") displayMode = "columns";
			else displayMode = "badges";
		}

		const documentType =
			df.fieldtype === "MultiFieldPicker"
				? df.target_doctype || context.engine?.rule_doc?.document_type
				: undefined;

		return {
			displayMode,
			columns: df.fieldtype === "MultiCheck" ? 2 : undefined,
			get_data: context.get_data || df.get_data,
			documentType,
			expanded: df.fieldtype === "MultiCheck" ? !context.hideLabel : undefined,
		};
	},
});

// 9. ResourceMapperControl
ControlRegistry.registerDefault({
	match: (df) => df?.fieldtype === "Resource Mapper",
	component: "ResourceMapperControl",
	mapProps: (df) => ({
		targetDoctype: df.target_doctype || "",
		targetFields: df.target_fields || [],
		sourceOptions: df.source_options || [],
	}),
});

// 10. TextGeneratorControl
ControlRegistry.registerDefault({
	match: (df) => df?.fieldtype === "Text Generator",
	component: "TextGeneratorControl",
	mapProps: (df, context) => ({
		variableOptions: df.variable_options || context.injectedVariableOptions,
		docFieldOptions: df.doc_field_options || context.injectedDocFields,
	}),
});

// 11. FlexValueControl
ControlRegistry.registerDefault({
	match: (df) => df?.fieldtype === "Structured Value",
	component: "FlexValueControl",
	mapProps: (df, context) => ({
		variableOptions: df.variable_options || context.injectedVariableOptions,
		compact: df.compact || false,
		placeholder: df.placeholder || "",
		disabled: df.read_only || context.read_only,
		engine: context.engine,
		doc: context.doc,
		context: {
			...(df.context || {}),
			df: {
				...(df || {}),
				fieldtype: df.target_fieldtype || df.context?.df?.fieldtype || "Data",
				options: df.target_options || df.options,
			},
			referenceDoctype:
				df.context?.referenceDoctype ||
				df.target_doctype ||
				context.engine?.rule_doc?.document_type,
		},
	}),
});

// 12. Default DataControl
ControlRegistry.registerDefault({
	match: (df) => !["Table", "Signature", "Button", "Heading"].includes(df?.fieldtype),
	component: "DataControl",
});
