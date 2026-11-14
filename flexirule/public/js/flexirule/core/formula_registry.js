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
	Data: FORMULA_GROUPS.TEXT,
	"Small Text": FORMULA_GROUPS.TEXT,
	"Long Text": FORMULA_GROUPS.TEXT,
	Text: FORMULA_GROUPS.TEXT,
	"Text Editor": FORMULA_GROUPS.TEXT,
	Code: FORMULA_GROUPS.TEXT,
	Int: FORMULA_GROUPS.NUMERIC,
	Float: FORMULA_GROUPS.NUMERIC,
	Currency: FORMULA_GROUPS.NUMERIC,
	Percent: FORMULA_GROUPS.NUMERIC,
	Duration: FORMULA_GROUPS.NUMERIC,
	Date: FORMULA_GROUPS.DATE,
	Datetime: FORMULA_GROUPS.DATE,
	Time: FORMULA_GROUPS.DATE,
	Check: FORMULA_GROUPS.BOOLEAN,
	Link: FORMULA_GROUPS.LINK,
	"Dynamic Link": FORMULA_GROUPS.LINK,
	Select: FORMULA_GROUPS.SELECT,
	MultiSelect: FORMULA_GROUPS.MULTISELECT,
	Table: FORMULA_GROUPS.TABLE,
	"Table MultiSelect": FORMULA_GROUPS.TABLE,
};

export function getGroupForFieldtype(ft) {
	return FIELDTYPES_GROUP_MAP[ft] || FORMULA_GROUPS.TEXT;
}

const translate = typeof globalThis.__ === "function" ? globalThis.__ : (s) => s;

export const SLASH_COMMANDS = [
	{
		id: "clear",
		label: translate("Clear Editor"),
		type: "logic",
		icon: "fa fa-trash",
		description: translate("Clear current value and reset editor"),
		groups: [FORMULA_GROUPS.GENERAL],
	},
];

/**
 * Domain-appropriate FontAwesome icons for resolver functions and formulas.
 */
export const FUNCTION_ICON_MAP = {
	// Text operations
	concat: "fa fa-link",
	normalize: "fa fa-refresh",
	format: "fa fa-align-left",
	replace: "fa fa-exchange",
	trim: "fa fa-scissors",
	upper: "fa fa-font",
	lower: "fa fa-font",
	slug: "fa fa-barcode",

	// Numeric operations
	sum: "fa fa-plus-square-o",
	round: "fa fa-calculator",
	avg: "fa fa-bar-chart",
	min: "fa fa-arrow-down",
	max: "fa fa-arrow-up",
	percentage: "fa fa-percent",
	abs: "fa fa-superscript",

	// Date & Time operations
	today: "fa fa-calendar-check-o",
	now: "fa fa-clock-o",
	add_days: "fa fa-calendar-plus-o",
	add_months: "fa fa-calendar",
	date_diff: "fa fa-hourglass-half",
	format_date: "fa fa-calendar-o",
	start_of: "fa fa-step-backward",
	end_of: "fa fa-step-forward",

	// Boolean & Logic
	if: "fa fa-random",
	equals: "fa fa-check-circle-o",
	not: "fa fa-ban",

	// Lookup & Link
	lookup: "fa fa-search",

	// Table / Collections
	count: "fa fa-list-ol",
	any: "fa fa-filter",
	all: "fa fa-check-square-o",
	first: "fa fa-angle-double-up",
	find: "fa fa-search-plus",
	filter: "fa fa-filter",
	pluck: "fa fa-list-alt",
	unique: "fa fa-dot-circle-o",
	map: "fa fa-th-list",
	reduce: "fa fa-compress",
};

export function getFunctionIcon(id, fallback = "fa fa-calculator") {
	return FUNCTION_ICON_MAP[id] || fallback;
}

export const FORMULA_REGISTRY = {
	[FORMULA_GROUPS.TEXT]: [
		{
			id: "concat",
			label: "concat",
			icon: "fa fa-link",
			description: "Concatenate multiple strings",
		},
		{
			id: "normalize",
			label: "normalize",
			icon: "fa fa-refresh",
			description: "Normalize text (trim, lower, etc.)",
		},
		{
			id: "format",
			label: "format",
			icon: "fa fa-align-left",
			description: "Format string using template",
		},
		{
			id: "replace",
			label: "replace",
			icon: "fa fa-exchange",
			description: "Replace substring",
		},
		{
			id: "trim",
			label: "trim",
			icon: "fa fa-scissors",
			description: "Remove leading/trailing whitespace",
		},
		{ id: "upper", label: "upper", icon: "fa fa-font", description: "Convert to uppercase" },
		{ id: "lower", label: "lower", icon: "fa fa-font", description: "Convert to lowercase" },
		{
			id: "slug",
			label: "slug",
			icon: "fa fa-barcode",
			description: "Generate URL-friendly slug",
		},
	],
	[FORMULA_GROUPS.NUMERIC]: [
		{ id: "sum", label: "sum", icon: "fa fa-plus-square-o", description: "Sum of values" },
		{
			id: "round",
			label: "round",
			icon: "fa fa-calculator",
			description: "Round to decimal places",
		},
		{ id: "avg", label: "avg", icon: "fa fa-bar-chart", description: "Average of values" },
		{ id: "min", label: "min", icon: "fa fa-arrow-down", description: "Minimum value" },
		{ id: "max", label: "max", icon: "fa fa-arrow-up", description: "Maximum value" },
		{
			id: "percentage",
			label: "percentage",
			icon: "fa fa-percent",
			description: "Calculate percentage",
		},
		{ id: "abs", label: "abs", icon: "fa fa-superscript", description: "Absolute value" },
	],
	[FORMULA_GROUPS.DATE]: [
		{
			id: "today",
			label: "today",
			icon: "fa fa-calendar-check-o",
			description: "Current date",
		},
		{ id: "now", label: "now", icon: "fa fa-clock-o", description: "Current datetime" },
		{
			id: "add_days",
			label: "add_days",
			icon: "fa fa-calendar-plus-o",
			description: "Add or subtract days",
		},
		{
			id: "add_months",
			label: "add_months",
			icon: "fa fa-calendar",
			description: "Add or subtract months",
		},
		{
			id: "date_diff",
			label: "date_diff",
			icon: "fa fa-hourglass-half",
			description: "Difference between two dates",
		},
		{
			id: "format_date",
			label: "format_date",
			icon: "fa fa-calendar-o",
			description: "Format date/time",
		},
		{
			id: "start_of",
			label: "start_of",
			icon: "fa fa-step-backward",
			description: "Start of week/month/year",
		},
		{
			id: "end_of",
			label: "end_of",
			icon: "fa fa-step-forward",
			description: "End of week/month/year",
		},
	],
	[FORMULA_GROUPS.BOOLEAN]: [
		{ id: "if", label: "if", icon: "fa fa-random", description: "Conditional value" },
		{
			id: "equals",
			label: "equals",
			icon: "fa fa-check-circle-o",
			description: "Check equality",
		},
		{ id: "not", label: "not", icon: "fa fa-ban", description: "Negate boolean" },
	],
	[FORMULA_GROUPS.LINK]: [
		{
			id: "lookup",
			label: "lookup",
			icon: "fa fa-search",
			description: "Look up record by filters",
		},
	],
	[FORMULA_GROUPS.TABLE]: [
		{
			id: "sum",
			label: "sum",
			icon: "fa fa-plus-square-o",
			description: "Sum of a child table field",
		},
		{
			id: "count",
			label: "count",
			icon: "fa fa-list-ol",
			description: "Count of child table rows",
		},
		{
			id: "any",
			label: "any",
			icon: "fa fa-filter",
			description: "Check if any row matches condition",
		},
		{
			id: "all",
			label: "all",
			icon: "fa fa-check-square-o",
			description: "Check if all rows match condition",
		},
		{
			id: "first",
			label: "first",
			icon: "fa fa-angle-double-up",
			description: "Find first matching child table row",
		},
		{
			id: "find",
			label: "find",
			icon: "fa fa-search-plus",
			description: "Find matching child table row",
		},
		{
			id: "filter",
			label: "filter",
			icon: "fa fa-filter",
			description: "Filter child table rows",
		},
		{
			id: "pluck",
			label: "pluck",
			icon: "fa fa-list-alt",
			description: "Extract array of field values",
		},
		{
			id: "unique",
			label: "unique",
			icon: "fa fa-dot-circle-o",
			description: "Extract array of unique field values",
		},
		{
			id: "map",
			label: "map",
			icon: "fa fa-th-list",
			description: "Extract values from child table",
		},
		{
			id: "reduce",
			label: "reduce",
			icon: "fa fa-compress",
			description: "Reduce child table to a single value",
		},
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

/**
 * Retrieve allowed builder resolver kinds for a given field type.
 * Centralizes the metadata mapping instead of hardcoding resolver types locally.
 * @param {string} fieldtype - The field type (e.g. 'Date', 'Int', 'Data')
 * @returns {string[]|null} - Array of allowed kinds, or null if all are allowed
 */
export function getAllowedBuilderKinds(fieldtype) {
	if (!fieldtype) return null;
	if (["Table", "Table MultiSelect", "MultiSelect"].includes(fieldtype)) {
		return ["collection", "fetch", "system_context"];
	}
	if (["Date", "Datetime", "Time"].includes(fieldtype)) {
		return ["date_time", "fetch", "system_context", "collection"];
	}
	if (["Int", "Float", "Currency", "Percent", "Duration"].includes(fieldtype)) {
		return ["math_formula", "collection", "date_time", "fetch", "system_context"];
	}
	if (
		["Data", "Small Text", "Text", "Long Text", "Text Editor", "Code", "Select"].includes(
			fieldtype
		)
	) {
		return ["text", "fetch", "collection", "system_context"];
	}
	if (["Check"].includes(fieldtype)) {
		return ["fetch", "collection", "system_context"];
	}
	if (["Link", "Dynamic Link"].includes(fieldtype)) {
		return ["text", "fetch", "collection", "system_context"];
	}
	return null;
}
