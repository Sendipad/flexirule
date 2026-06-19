<template>
	<div class="loop-config">
		<LoopNodeConfig
			:ref="setControlRef"
			:node="node"
			:showValidation="showValidation"
			@update-json-config="updateJsonConfig"
		/>
		<hr />
		<ConditionStep :ref="setControlRef" :node="node" :showValidation="showValidation" />
	</div>
</template>

<script setup>
import { ref, onBeforeUpdate } from "vue";
import { useStore } from "../../../stores";
import { fromCodeString } from "../../../utils/serialization";
import LoopNodeConfig from "../../node_configs/LoopNodeConfig.vue";
import ConditionStep from "./ConditionStep.vue";

const props = defineProps({
	node: Object,
	showValidation: { type: Boolean, default: false },
});

const store = useStore();
const controlRefs = ref([]);

onBeforeUpdate(() => {
	controlRefs.value = [];
});

function setControlRef(el) {
	if (el) controlRefs.value.push(el);
}

function updateJsonConfig(key, val) {
	if (!props.node.data) return;

	let config =
		typeof props.node.data.config === "string"
			? fromCodeString(props.node.data.config)
			: props.node.data.config || {};

	config[key] = val;
	props.node.data.config = config;
}

async function validate() {
	const results = await Promise.all(
		(controlRefs.value || []).map((ctrl) => {
			if (ctrl && typeof ctrl.validate === "function") {
				return ctrl.validate();
			}
			return { valid: true };
		})
	);
	const errors = results.flatMap((r) => r.errors || []);
	return { valid: errors.length === 0, errors };
}

defineExpose({ validate });
</script>
