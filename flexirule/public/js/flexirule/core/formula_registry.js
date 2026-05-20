/**
 * Formula and Command Registry for FlexiRule
 * Centralizes the definition of available formulas and commands by field type.
 */

export const FORMULA_GROUPS = {
	TEXT: "text",
	NUMERIC: "numeric",
	DATE: "date",
	BOOLEAN: "boolean",
	LINK: "link",
	SELECT: "select",
	MULTISELECT: "multiselect",
	TABLE: "table",
	GENERAL: "*",
};

export const FIELDTYPES_GROUP_MAP = {
	"Data": FORMULA_GROUPS.TEXT,
	"Small Text": FORMULA_GROUPS.TEXT,
	"Long Text": FORMULA_GROUPS.TEXT,
	"Text": FORMULA_GROUPS.TEXT,
	"Text Editor": FORMULA_GROUPS.TEXT,
	"Code": FORMULA_GROUPS.TEXT,
	"Int": FORMULA_GROUPS.NUMERIC,
	"Float": FORMULA_GROUPS.NUMERIC,
	"Currency": FORMULA_GROUPS.NUMERIC,
	"Percent": FORMULA_GROUPS.NUMERIC,
	"Duration": FORMULA_GROUPS.NUMERIC,
	"Date": FORMULA_GROUPS.DATE,
	"Datetime": FORMULA_GROUPS.DATE,
	"Time": FORMULA_GROUPS.DATE,
	"Check": FORMULA_GROUPS.BOOLEAN,
	"Link": FORMULA_GROUPS.LINK,
	"Dynamic Link": FORMULA_GROUPS.LINK,
	"Select": FORMULA_GROUPS.SELECT,
	"MultiSelect": FORMULA_GROUPS.MULTISELECT,
	"Table": FORMULA_GROUPS.TABLE,
	"Table MultiSelect": FORMULA_GROUPS.TABLE,
};

export function getGroupForFieldtype(ft) {
	return FIELDTYPES_GROUP_MAP[ft] || FORMULA_GROUPS.TEXT;
}

export const SLASH_COMMANDS = [
	{ id: "formula", label: __("Formula"), type: "logic", icon: "🧮", groups: [FORMULA_GROUPS.GENERAL] },
	{ id: "resolver", label: __("Resolver"), type: "logic", icon: "⚡", groups: [FORMULA_GROUPS.GENERAL] },
	{
		id: "formatter",
		label: __("Formatter"),
		type: "logic",
		icon: "🎨",
		groups: [FORMULA_GROUPS.TEXT, FORMULA_GROUPS.NUMERIC],
	},
	{ id: "normalize", label: __("Normalize"), type: "logic", icon: "🔄", groups: [FORMULA_GROUPS.TEXT] },
	{ id: "localization", label: __("Translation"), type: "logic", icon: "🌐", groups: [FORMULA_GROUPS.TEXT] },
	{ id: "condition", label: __("Condition"), type: "logic", icon: "🔀", groups: [FORMULA_GROUPS.GENERAL] },
	{ id: "link", label: __("Link Picker"), type: "logic", icon: "🔗", groups: [FORMULA_GROUPS.LINK] },
	{ id: "dynamic-link", label: __("Dynamic Link"), type: "logic", icon: "🧩", groups: [FORMULA_GROUPS.LINK] },
	{ id: "json", label: __("JSON Editor"), type: "logic", icon: "📦", groups: [FORMULA_GROUPS.GENERAL] },
	{ id: "add-key", label: __("Add Key/Value"), type: "logic", icon: "🔑", groups: [FORMULA_GROUPS.GENERAL] },
	{ id: "clear", label: __("Clear Editor"), type: "logic", icon: "🗑️", groups: [FORMULA_GROUPS.GENERAL] },
	{ id: "select", label: __("Select Option"), type: "logic", icon: "⌄", groups: [FORMULA_GROUPS.SELECT] },
	{ id: "boolean", label: __("Toggle"), type: "logic", icon: "🔘", groups: [FORMULA_GROUPS.BOOLEAN] },
	{
		id: "multiselect",
		label: __("Multi Select"),
		type: "logic",
		icon: "📑",
		groups: [FORMULA_GROUPS.MULTISELECT],
	},
];

export const FORMULA_REGISTRY = {
	[FORMULA_GROUPS.TEXT]: [
		{ id: "concat", label: "concat", description: "Concatenate multiple strings" },
		{ id: "normalize", label: "normalize", description: "Normalize text (trim, lower, etc.)" },
		{ id: "format", label: "format", description: "Format string using template" },
		{ id: "replace", label: "replace", description: "Replace substring" },
		{ id: "trim", label: "trim", description: "Remove leading/trailing whitespace" },
		{ id: "upper", label: "upper", description: "Convert to uppercase" },
		{ id: "lower", label: "lower", description: "Convert to lowercase" },
		{ id: "slug", label: "slug", description: "Generate URL-friendly slug" },
	],
	[FORMULA_GROUPS.NUMERIC]: [
		{ id: "sum", label: "sum", description: "Sum of values" },
		{ id: "round", label: "round", description: "Round to decimal places" },
		{ id: "avg", label: "avg", description: "Average of values" },
		{ id: "min", label: "min", description: "Minimum value" },
		{ id: "max", label: "max", description: "Maximum value" },
		{ id: "percentage", label: "percentage", description: "Calculate percentage" },
		{ id: "abs", label: "abs", description: "Absolute value" },
	],
	[FORMULA_GROUPS.DATE]: [
		{ id: "today", label: "today", description: "Current date" },
		{ id: "now", label: "now", description: "Current datetime" },
		{ id: "add_days", label: "add_days", description: "Add or subtract days" },
		{ id: "add_months", label: "add_months", description: "Add or subtract months" },
		{ id: "date_diff", label: "date_diff", description: "Difference between two dates" },
		{ id: "format_date", label: "format_date", description: "Format date/time" },
		{ id: "start_of", label: "start_of", description: "Start of week/month/year" },
		{ id: "end_of", label: "end_of", description: "End of week/month/year" },
	],
	[FORMULA_GROUPS.BOOLEAN]: [
		{ id: "if", label: "if", description: "Conditional value" },
		{ id: "equals", label: "equals", description: "Check equality" },
		{ id: "not", label: "not", description: "Negate boolean" },
	],
	[FORMULA_GROUPS.LINK]: [
		{ id: "fetch", label: "fetch", description: "Fetch field from linked document" },
		{ id: "lookup", label: "lookup", description: "Look up record by filters" },
	],
	[FORMULA_GROUPS.TABLE]: [
		{ id: "sum", label: "sum", description: "Sum of a child table field" },
		{ id: "count", label: "count", description: "Count of child table rows" },
		{ id: "map", label: "map", description: "Extract values from child table" },
		{ id: "filter", label: "filter", description: "Filter child table rows" },
		{ id: "reduce", label: "reduce", description: "Reduce child table to a single value" },
	],
};

export function getCommandsForFieldtype(ft) {
	const group = getGroupForFieldtype(ft);
	return SLASH_COMMANDS.filter((c) => {
		if (c.groups.includes(FORMULA_GROUPS.GENERAL)) return true;
		if (c.groups.includes(group)) return true;
		return false;
	});
}

export function getFormulasForFieldtype(ft) {
	const group = getGroupForFieldtype(ft);
	return FORMULA_REGISTRY[group] || [];
}
