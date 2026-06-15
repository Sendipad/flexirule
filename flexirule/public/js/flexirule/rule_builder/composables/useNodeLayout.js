import { computed } from "vue";
import { Position } from "@vue-flow/core";
import { getContract } from "../core/contracts";

export function useNodeLayout(props, ruleStore) {
	const isHorizontal = computed(() => ruleStore.settings?.layout_direction !== "Top to Bottom");

	const targetPos = computed(
		() => props.targetPosition || (isHorizontal.value ? Position.Left : Position.Top)
	);
	const sourcePos = computed(
		() => props.sourcePosition || (isHorizontal.value ? Position.Right : Position.Bottom)
	);

	const nodeMeta = computed(() => {
		const actionType = props.data?.action_type || "Process";
		const contract = getContract(actionType);
		const css = contract.css || {};

		return {
			color: css.color || "#0d6efd",
			icon: css.icon || "fa-cog",
			typeLabel: (actionType || "PROCESS").toUpperCase(),
			isTerminal: contract.terminal || false,
		};
	});

	return {
		isHorizontal,
		targetPos,
		sourcePos,
		nodeMeta,
	};
}
