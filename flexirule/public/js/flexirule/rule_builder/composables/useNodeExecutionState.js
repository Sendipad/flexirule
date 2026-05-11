import { computed } from "vue";
import { useUIStore } from "../stores/useUIStore";

export function useNodeExecutionState(nodeIdRef) {
	const uiStore = useUIStore();

	const executionState = computed(() => {
		const nodeId = nodeIdRef?.value;
		if (!nodeId) return null;
		return uiStore.node_execution_state?.[nodeId] || null;
	});

	const isExecuted = computed(() => !!executionState.value);
	const isRunning = computed(() => executionState.value?.status === "running");
	const isErrored = computed(() => executionState.value?.status === "error");
	const executionOrder = computed(() => executionState.value?.order || null);

	return {
		executionState,
		isExecuted,
		isRunning,
		isErrored,
		executionOrder,
	};
}
