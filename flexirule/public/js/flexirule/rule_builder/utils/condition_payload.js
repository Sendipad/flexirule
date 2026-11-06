/**
 * Shared condition payload extraction for Rule Builder consumers.
 *
 * A condition is identified by a canonical/known legacy structure, or by the
 * action type when preserving an unknown or malformed Condition-action value.
 * Arbitrary action configuration must never be inferred to be a condition.
 */

function parseSerialized(value) {
	if (value === null || value === undefined || value === "") {
		return { value: null, malformed: false };
	}
	if (typeof value !== "string") return { value, malformed: false };

	try {
		let parsed = JSON.parse(value);
		if (typeof parsed === "string") {
			const inner = parsed.trim();
			if (inner.startsWith("{") || inner.startsWith("[")) {
				parsed = JSON.parse(inner);
			}
		}
		return { value: parsed, malformed: false };
	} catch {
		return { value, malformed: true };
	}
}

function isCanonicalRoot(value) {
	return Boolean(
		value &&
			typeof value === "object" &&
			!Array.isArray(value) &&
			["comparison", "group", "collection_predicate"].includes(value.type)
	);
}

function isKnownLegacyCondition(value) {
	if (Array.isArray(value)) return value.length === 0;
	if (!value || typeof value !== "object") return false;
	return (
		Array.isArray(value.conditions) ||
		(Boolean(value.left) && Boolean(value.op || value.operator)) ||
		(Boolean(value.collection) && Boolean(value.where))
	);
}

function isNonEmptyUnknownStructuredValue(value) {
	if (Array.isArray(value))
		return value.length > 0 && value.some((item) => item && typeof item === "object");
	return Boolean(value && typeof value === "object" && Object.keys(value).length);
}

/**
 * Extract a condition from an Action.config value.
 *
 * Unknown structures and malformed serialized values are only preserved when
 * the caller has positively identified a Condition action. This prevents
 * unrelated action configs (notably Fetch Records and Loop) from being
 * misinterpreted as unsupported condition ASTs.
 */
export function getConditionPayloadFromConfig(
	configValue,
	{ preserveUnknown = false, preserveMalformed = false, allowCanonicalRoot = true } = {}
) {
	const parsed = parseSerialized(configValue);
	if (parsed.malformed) return preserveMalformed ? configValue : null;

	const config = parsed.value;
	if (config === null || config === undefined) return null;
	if ((allowCanonicalRoot && isCanonicalRoot(config)) || isKnownLegacyCondition(config))
		return config;

	if (config && typeof config === "object" && !Array.isArray(config)) {
		for (const key of ["condition", "condition_tree", "condition_json"]) {
			if (!(key in config)) continue;
			const nested = parseSerialized(config[key]);
			if (nested.malformed) {
				if (preserveMalformed) return config[key];
				continue;
			}
			if (
				nested.value !== null &&
				(isCanonicalRoot(nested.value) ||
					isKnownLegacyCondition(nested.value) ||
					preserveUnknown)
			) {
				return nested.value;
			}
		}
	}

	return preserveUnknown && isNonEmptyUnknownStructuredValue(config) ? config : null;
}

export function getConditionPayload(actionLike = {}) {
	const actionType = String(actionLike.action_type || "")
		.trim()
		.toLowerCase();
	const isConditionAction = actionType === "condition";
	const options = {
		preserveUnknown: isConditionAction,
		preserveMalformed: isConditionAction,
		allowCanonicalRoot: !actionType || isConditionAction,
	};

	const fromConfig = getConditionPayloadFromConfig(actionLike.config, options);
	if (fromConfig !== null) return fromConfig;

	const legacy = parseSerialized(actionLike.condition_json);
	if (legacy.malformed) return isConditionAction ? actionLike.condition_json : null;
	if (legacy.value === null) return null;

	if (
		(options.allowCanonicalRoot && isCanonicalRoot(legacy.value)) ||
		isKnownLegacyCondition(legacy.value)
	) {
		return legacy.value;
	}
	return options.preserveUnknown && isNonEmptyUnknownStructuredValue(legacy.value)
		? legacy.value
		: null;
}

export function hasConditionPayload(actionLike = {}) {
	return getConditionPayload(actionLike) !== null;
}
