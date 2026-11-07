/**
 * Adapter between real Resolver Strategy registry (getAllStrategies()) and source catalogue / FlexValue.
 */

const KIND_FAMILY_MAP = {
	date_time: "date_time",
	text: "text",
	math_formula: "math",
	collection: "collection",
	child_aggregation: "collection",
	lookup: "lookup",
	fetch: "lookup",
	system_context: "system_context",
};

export function getCanonicalFamilyForKind(kind) {
	return KIND_FAMILY_MAP[kind] || kind || "text";
}

/**
 * Normalizes state produced by strategy.defaultState(contextProps) into canonical { operation, config, family }
 */
export function normalizeStrategyDefaultState(kind, strategyState = {}) {
	const family = getCanonicalFamilyForKind(kind);
	const state = strategyState && typeof strategyState === "object" ? { ...strategyState } : {};

	let operation = state.operation;
	let config = state.config;

	if (kind === "date_time") {
		operation = operation || "calculate";
		// Preserve the strategy's expected envelope { operation, config }
		config = state.config || state;
	} else if (kind === "text") {
		operation = operation || "combine";
		config = state.config || state;
	} else if (kind === "collection") {
		operation = operation || state.operation || "any";
		config = state;
	} else if (kind === "math_formula") {
		operation = operation || "formula";
		config = state;
	} else if (kind === "lookup" || kind === "fetch") {
		operation = operation || "fetch";
		config = state;
	} else if (kind === "system_context") {
		operation = operation || (state.sys_token === "role_check" ? "role_check" : "get");
		config = state;
	} else {
		operation = operation || "default";
		config = state.config || state;
	}

	return {
		family,
		operation,
		config,
		fullState: state,
	};
}

/**
 * Adapts an array of strategy objects into normalized resolver entries for buildSourceCatalogue.
 */
export function adaptStrategiesForCatalogue(strategies = [], contextProps = {}) {
	return strategies.map((strategy) => {
		const kind = strategy.kind;
		let rawState = {};
		if (typeof strategy.defaultState === "function") {
			try {
				rawState = strategy.defaultState(contextProps);
			} catch (e) {
				rawState = {};
			}
		}

		const normalized = normalizeStrategyDefaultState(kind, rawState);

		// Retain the expected { family, operation, config } shape while ensuring direct property access compatibility
		const innerConfig =
			normalized.config && typeof normalized.config === "object" ? normalized.config : {};
		const payloadConfig =
			kind === "date_time" || kind === "text"
				? {
						...innerConfig,
						family: normalized.family,
						operation: normalized.operation,
						config: innerConfig,
				  }
				: {
						...innerConfig,
						family: normalized.family,
						operation: normalized.operation,
				  };

		return {
			kind,
			label: strategy.label || kind,
			icon: strategy.icon || "fa fa-bolt",
			description: strategy.description || "",
			family: normalized.family,
			operation: normalized.operation,
			defaultConfig: payloadConfig,
		};
	});
}
