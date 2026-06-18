<template>
	<div class="loop-config">
		<LoopNodeConfig
			ref="loopNodeRef"
			:node="node"
			:showValidation="showValidation"
			@update-json-config="updateJsonConfig"
		/>
		<hr />
		<ConditionStep ref="conditionStepRef" :node="node" :showValidation="showValidation" />
	</div>
</template>

<script setup>
import { ref } from "vue";
import { useStore } from "../../../stores";
import { fromCodeString } from "../../../utils/serialization";
import LoopNodeConfig from "../../node_configs/LoopNodeConfig.vue";
import ConditionStep from "./ConditionStep.vue";

const props = defineProps({
	node: Object,
	showValidation: { type: Boolean, default: false },
});

const store = useStore();
const loopNodeRef = ref(null);
const conditionStepRef = ref(null);

function updateJsonConfig(key, val) {
	if (!props.node.data) return;

	let config =
		typeof props.node.data.config === "string"
			? fromCodeString(props.node.data.config)
			: props.node.data.config || {};

	config[key] = val;
	props.node.data.config = config;

	const isDraft = !store.nodes.some((n) => n === props.node);
	if (!isDraft) {
		store.mark_dirty();
	}
}

async function validate() {
	const errors = [];
	if (loopNodeRef.value && typeof loopNodeRef.value.validate === "function") {
		const res = await loopNodeRef.value.validate();
		if (!res.valid) errors.push(...res.errors);
	}
	if (conditionStepRef.value && typeof conditionStepRef.value.validate === "function") {
		const res = await conditionStepRef.value.validate();
		if (!res.valid) errors.push(...res.errors);
	}
	return { valid: errors.length === 0, errors };
}

defineExpose({ validate });
</script>
