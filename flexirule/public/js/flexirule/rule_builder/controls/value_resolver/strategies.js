import { markRaw } from "vue";

/**
 * Registry for Value Resolver Strategies.
 * Each strategy defines:
 * - label: Human readable name
 * - icon: Icon class
 * - component: Vue component for configuration
 * - defaultState: Function returning initial state
 * - compileToCode: Function returning Python expression
 * - compileToLabel: Function returning human-readable label
 * - validate: Function returning validation errors/status
 */

export const RESOLVER_STRATEGIES = {};

export function registerStrategy(kind, strategy) {
	RESOLVER_STRATEGIES[kind] = {
		...strategy,
		component: strategy.component ? markRaw(strategy.component) : null,
	};
}

export function getStrategy(kind) {
	return RESOLVER_STRATEGIES[kind] || null;
}

export function getAllStrategies() {
	return Object.entries(RESOLVER_STRATEGIES).map(([kind, s]) => ({
		kind,
		...s,
	}));
}
