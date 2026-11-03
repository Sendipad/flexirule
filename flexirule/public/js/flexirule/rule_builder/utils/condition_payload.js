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
	if (Array.isArray(value)) return true;
	if (!value || typeof value !== "object") return false;
	if (
		value.type === "comparison" ||
		value.type === "group" ||
		value.type === "collection_predicate"
	) {
		return true;
	}
	return (
		Array.isArray(value.conditions) ||
		Boolean(value.left) ||
		(Boolean(value.collection) && Boolean(value.where))
	);
}

export function getConditionPayloadFromConfig(configValue) {
	const config = safeJsonParse(configValue, null);
	if (Array.isArray(config)) return config;
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
		if (isConditionPayloadShape(nested)) return nested;
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
