import { computed } from "vue";
import { Position } from "@vue-flow/core";
import { useRuleStore } from "../stores/useRuleStore";
import { useUIStore } from "../stores/useUIStore";
import { useRuleGraph } from "./useRuleGraph";

export function useCanvasLayout() {
	const ruleStore = useRuleStore();
	const uiStore = useUIStore();
	const { layoutGraph } = useRuleGraph();

	const layoutOrientation = computed({
		get: () => {
			return uiStore.layout_preference || "LR";
		},
		set: (val) => {
			uiStore.layout_preference = val;
		},
	});

	const isHorizontal = computed(() => layoutOrientation.value === "LR");

	const sourcePosition = computed(() => (isHorizontal.value ? Position.Right : Position.Bottom));
	const targetPosition = computed(() => (isHorizontal.value ? Position.Left : Position.Top));

	return {
		layoutOrientation,
		isHorizontal,
		sourcePosition,
		targetPosition,
	};
}
