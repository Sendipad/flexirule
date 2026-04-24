import { useRuleStore } from "./useRuleStore";
import { useGraphStore } from "./useGraphStore";
import { useUIStore } from "./useUIStore";
import { useMetaStore } from "./useMetaStore";
import { useHistoryStore } from "./useHistoryStore";

export { useRuleStore, useGraphStore, useUIStore, useMetaStore, useHistoryStore };

/**
 * Unified store facade (Legacy support)
 * Encouraged to use domain stores directly.
 */
export function useStore() {
	return {
		...useRuleStore(),
		...useGraphStore(),
		...useUIStore(),
		...useMetaStore(),
		...useHistoryStore(),
	};
}
