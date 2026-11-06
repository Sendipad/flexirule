function safeJsonParse(value, fallback = null) {
	if (value === null || value === undefined || value === "") return fallback;
	if (typeof value === "object") return value;
	try {
		const parsed = JSON.parse(value);
		if (typeof parsed === "string") {
			try {
				return JSON.parse(parsed);
			} catch {
				return parsed;
			}
		}
		return parsed;
	} catch {
		return fallback;
	}
}

function isConditionPayloadShape(value) {
	if (Array.isArray(value)) {
		if (value.length === 0) return true;
		// Non-empty array: preserve any array containing objects as condition payload candidates
		return value.some((item) => item && typeof item === "object");
	}
	if (!value || typeof value !== "object") return false;
	const keys = Object.keys(value);
	if (keys.length === 0) return false;

	if (
		value.type === "comparison" ||
		value.type === "group" ||
		value.type === "collection_predicate"
	) {
		return true;
	}
	if (
		Array.isArray(value.conditions) ||
		Boolean(value.left) ||
		(Boolean(value.collection) && Boolean(value.where))
	) {
		return true;
	}

	// Any non-empty object with a type property or other structure stored in condition context
	// is treated as a condition payload shape to preserve unknown/unsupported conditions
	return Boolean(value.type) || keys.length > 0;
}

export function getConditionPayloadFromConfig(configValue) {
	const config = safeJsonParse(configValue, null);
	if (Array.isArray(config)) {
		// Non-empty array or empty condition array
		return isConditionPayloadShape(config) ? config : null;
	}
	if (!config || typeof config !== "object") return null;

	if (
		config.type === "comparison" ||
		config.type === "group" ||
		config.type === "collection_predicate"
	) {
		return config;
	}

	for (const key of ["condition", "condition_tree", "condition_json"]) {
		if (!(key in config)) continue;
		const nested = safeJsonParse(config[key], null);
		if (nested !== null && isConditionPayloadShape(nested)) return nested;
	}

	// Action config objects for non-condition actions (like Assignment, Process) have specific action keys.
	// Don't mistake action configs like { assignment_rows: [...] } for unknown root conditions.
	const nonConditionActionKeys = new Set([
		"assignments",
		"assignment_rows",
		"process_name",
		"sub_rule",
		"output_variable",
		"input_mapping",
		"output_mapping",
	]);
	const hasActionSpecificKeys = Object.keys(config).some((k) => nonConditionActionKeys.has(k));
	if (hasActionSpecificKeys) {
		return null;
	}

	if (isConditionPayloadShape(config)) return config;
	return null;
}

export function getConditionPayload(actionLike = {}) {
	const fromConfig = getConditionPayloadFromConfig(actionLike.config);
	if (fromConfig !== null) return fromConfig;

	const legacy = safeJsonParse(actionLike.condition_json, null);
	return isConditionPayloadShape(legacy) ? legacy : null;
}

export function hasConditionPayload(actionLike = {}) {
	return getConditionPayload(actionLike) !== null;
}
