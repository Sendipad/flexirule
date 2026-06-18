<template>
	<div class="loop-config">
		<LoopNodeConfig ref="configRef" :node="node" @update-json-config="updateJsonConfig" />
		<hr />
		<ConditionStep ref="conditionRef" :node="node" />
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
});

const store = useStore();
const configRef = ref(null);
const conditionRef = ref(null);

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
	if (configRef.value?.validate) {
		const res = configRef.value.validate();
		if (!res.valid) errors.push(res.message);
	}
	if (conditionRef.value?.validate) {
		const res = await conditionRef.value.validate();
		if (!res.valid) errors.push(...res.errors);
	}
	return { valid: errors.length === 0, errors };
}

defineExpose({ validate });
</script>
