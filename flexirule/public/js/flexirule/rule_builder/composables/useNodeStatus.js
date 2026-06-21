import { computed, watch } from "vue";
import { useRuleStore } from "../stores";
import { getNodeStatus, validateAgainstContract } from "../../core/contracts";

/**
 * useNodeStatus Composable
 *
 * Provides reactive status and validation errors for a specific node.
 * Automatically re-validates when node data or rule-level metadata changes.
 *
 * @param {Ref<String>|ComputedRef<String>} nodeIdRef - Reference to the node ID
 * @returns {Object} { status, errors, isValid, isConfigured }
 */
export function useNodeStatus(nodeIdRef) {
	const ruleStore = useRuleStore();

	const node = computed(() => {
		const id = typeof nodeIdRef === "string" ? nodeIdRef : nodeIdRef.value;
		return ruleStore.nodes.find((n) => n.id === id);
	});

	const nodeData = computed(() => node.value?.data || {});

	// Status is derived using the centralized logic in contracts.js
	const status = computed(() => getNodeStatus(nodeData.value));

	const validation = computed(() => validateAgainstContract(nodeData.value));

	const errors = computed(() => validation.value.errors || []);
	const isValid = computed(() => validation.value.valid);
	const isConfigured = computed(() => status.value === "configured" || status.value === "invalid");
	const isInvalid = computed(() => status.value === "invalid");

	return {
		status,
		errors,
		isValid,
		isConfigured,
		isInvalid,
	};
}
