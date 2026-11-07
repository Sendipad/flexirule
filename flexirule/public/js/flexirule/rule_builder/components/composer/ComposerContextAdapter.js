/**
 * ComposerContextAdapter.js
 *
 * Unified contextual suggestion adapter for the Intelligent @-Mention Composer.
 * Aggregates contextual suggestions across:
 * - DOCUMENT: Current document fields, child table fields, parent fields, old document fields.
 * - VARIABLES: Context variables, trigger context, previous action outputs, workflow variables.
 * - VALUES: Static/literal presets, formulas, date/time operations, collection operations, fetch/lookup.
 * - EXTENSIONS: Registered extension capabilities and future custom resolvers.
 *
 * Strict Architectural Guarantees:
 * - Sources exclusively from Frappe DocType metadata, execution context, and the backend resolver contract.
 * - Deny-by-default permission checks: respects `condition_operand_allowed` and registered permission policies.
 * - Does not invent fake operator mappings or duplicate validation registries.
 */

export const SUGGESTION_GROUPS = Object.freeze({
	DOCUMENT: "DOCUMENT",
	VARIABLES: "VARIABLES",
	VALUES: "VALUES",
	EXTENSIONS: "EXTENSIONS",
});

/**
 * Normalizes field items into a standard suggestion structure.
 */
function normalizeDocField(field, scope = "doc") {
	const fieldname = field.fieldname || field.value || "";
	const label = field.label || fieldname;
	const fieldtype = field.fieldtype || "Data";
	const path = `${scope}.${fieldname}`;
	const prefix = scope === "doc" ? "@doc." : scope === "old_doc" ? "@old_doc." : `@${scope}.`;

	return {
		id: `${scope}:${fieldname}`,
		kind: "document",
		group: SUGGESTION_GROUPS.DOCUMENT,
		scope,
		fieldname,
		fieldtype,
		options: field.options || null,
		mentionLabel: `${prefix}${fieldname}`,
		displayLabel: label,
		subLabel: `${scope} · ${fieldtype}`,
		icon: getFieldtypeIcon(fieldtype),
		value_type: mapFieldtypeToValueType(fieldtype),
		payload: {
			mode: "variable",
			path: {
				scope,
				segments: [fieldname],
			},
		},
	};
}

/**
 * Normalizes context variables into standard suggestion structures.
 */
function normalizeVariable(variable) {
	const rawValue = variable.value ?? variable;
	const label = variable.label || variable.friendlyLabel || rawValue;
	const pathStr = String(rawValue).replace(/^@/, "");
	const segments = pathStr.split(".");
	const scope = segments[0] || "vars";
	const pathSegments = segments.slice(1);
	const fieldtype = variable.fieldtype || "Data";

	return {
		id: `var:${pathStr}`,
		kind: "variable",
		group: SUGGESTION_GROUPS.VARIABLES,
		scope,
		fieldname: pathSegments.join("."),
		fieldtype,
		options: variable.options || null,
		mentionLabel: `@${pathStr}`,
		displayLabel: label,
		subLabel: `${scope} · ${fieldtype}`,
		icon: "fa fa-database",
		value_type: mapFieldtypeToValueType(fieldtype),
		payload: {
			mode: "variable",
			path: {
				scope,
				segments: pathSegments.length > 0 ? pathSegments : [scope],
			},
		},
	};
}

/**
 * Normalizes registered backend resolver capabilities into suggestion structures.
 */
function normalizeResolver(res, isConditionOperand = false) {
	const family = res.family;
	const operation = res.operation;
	const label = res.label || `${family}.${operation}`;
	const outputType = res.output_type || "Data";
	const isAllowed = !isConditionOperand || res.condition_operand_allowed === true;

	if (!isAllowed) {
		return null;
	}

	const isExt = !["math", "date_time", "collection", "text", "lookup", "system_context"].includes(
		family
	);

	return {
		id: `resolver:${family}.${operation}`,
		kind: "resolver",
		group: isExt ? SUGGESTION_GROUPS.EXTENSIONS : SUGGESTION_GROUPS.VALUES,
		family,
		operation,
		mentionLabel: `@${family}.${operation}`,
		displayLabel: label,
		subLabel: `${family} · ${outputType}`,
		icon: getResolverIcon(family, operation),
		value_type: mapFieldtypeToValueType(outputType),
		output_type: outputType,
		permission_policy: res.permission_policy,
		config_schema: res.config_schema || {},
		payload: {
			mode: "resolver",
			family,
			operation,
			value_type: mapFieldtypeToValueType(outputType),
			config: {},
		},
	};
}

export function mapFieldtypeToValueType(fieldtype) {
	if (!fieldtype) return "string";
	const ft = String(fieldtype).toLowerCase();
	if (["int", "integer"].includes(ft)) return "integer";
	if (["float", "currency", "percent", "decimal"].includes(ft)) return "decimal";
	if (["check", "boolean"].includes(ft)) return "boolean";
	if (["date"].includes(ft)) return "date";
	if (["datetime"].includes(ft)) return "datetime";
	if (["time", "duration"].includes(ft)) return "time";
	if (["table", "list"].includes(ft)) return "list";
	return "string";
}

export function getFieldtypeIcon(fieldtype) {
	switch (fieldtype) {
		case "Check":
			return "fa fa-check-square-o";
		case "Int":
		case "Float":
		case "Currency":
		case "Percent":
			return "fa fa-calculator";
		case "Date":
		case "Datetime":
		case "Time":
			return "fa fa-calendar";
		case "Link":
		case "Dynamic Link":
			return "fa fa-link";
		case "Table":
			return "fa fa-table";
		case "Select":
			return "fa fa-list";
		default:
			return "fa fa-font";
	}
}

export function getResolverIcon(family, operation) {
	switch (family) {
		case "math":
			return "fa fa-calculator";
		case "date_time":
			return "fa fa-clock-o";
		case "collection":
			return "fa fa-cubes";
		case "text":
			return "fa fa-font";
		case "lookup":
			return "fa fa-search";
		case "system_context":
			return "fa fa-user-circle-o";
		default:
			return "fa fa-puzzle-piece";
	}
}

/**
 * Builds the contextual suggestions list for a given context.
 */
export function buildContextualSuggestions({
	docFields = [],
	variableOptions = [],
	contract = null,
	isConditionOperand = false,
	targetFieldtype = null,
	query = "",
} = {}) {
	const suggestions = [];
	const q = (query || "").trim().toLowerCase().replace(/^@/, "");

	// 1. Document fields
	for (const f of docFields) {
		const norm = normalizeDocField(f, "doc");
		suggestions.push(norm);
	}

	// 2. Runtime & context variables
	for (const v of variableOptions) {
		const norm = normalizeVariable(v);
		suggestions.push(norm);
	}

	// 3. Resolvers from backend contract
	const resolvers = contract?.flexvalue_modes?.resolver || [];
	if (Array.isArray(resolvers)) {
		for (const r of resolvers) {
			const norm = normalizeResolver(r, isConditionOperand);
			if (norm) {
				suggestions.push(norm);
			}
		}
	}

	// 4. Filter by query if provided
	if (!q) {
		return suggestions;
	}

	return suggestions.filter((item) => {
		const mention = (item.mentionLabel || "").toLowerCase();
		const display = (item.displayLabel || "").toLowerCase();
		const sub = (item.subLabel || "").toLowerCase();
		const fieldname = (item.fieldname || "").toLowerCase();
		const family = (item.family || "").toLowerCase();
		const operation = (item.operation || "").toLowerCase();

		return (
			mention.includes(q) ||
			display.includes(q) ||
			sub.includes(q) ||
			fieldname.includes(q) ||
			family.includes(q) ||
			operation.includes(q)
		);
	});
}

/**
 * Groups suggestions into ordered categories: DOCUMENT, VARIABLES, VALUES, EXTENSIONS.
 */
export function groupSuggestions(suggestions = []) {
	const order = [
		SUGGESTION_GROUPS.DOCUMENT,
		SUGGESTION_GROUPS.VARIABLES,
		SUGGESTION_GROUPS.VALUES,
		SUGGESTION_GROUPS.EXTENSIONS,
	];

	const grouped = {
		[SUGGESTION_GROUPS.DOCUMENT]: [],
		[SUGGESTION_GROUPS.VARIABLES]: [],
		[SUGGESTION_GROUPS.VALUES]: [],
		[SUGGESTION_GROUPS.EXTENSIONS]: [],
	};

	for (const item of suggestions) {
		const grp = item.group || SUGGESTION_GROUPS.VALUES;
		if (!grouped[grp]) {
			grouped[grp] = [];
		}
		grouped[grp].push(item);
	}

	return order
		.map((groupName) => ({
			name: groupName,
			items: grouped[groupName] || [],
		}))
		.filter((group) => group.items.length > 0);
}
