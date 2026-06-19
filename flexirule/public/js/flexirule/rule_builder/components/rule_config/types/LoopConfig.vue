<template>
	<div class="loop-config">
		<LoopNodeConfig
			ref="controlRefs"
			:node="node"
			:showValidation="showValidation"
			@update-json-config="updateJsonConfig"
		/>
		<hr />
		<ConditionStep ref="controlRefs" :node="node" :showValidation="showValidation" />
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
	const results = await Promise.all(
		(controlRefs.value || []).map((ref) => {
			if (ref && typeof ref.validate === "function") {
				return ref.validate();
			}
			return { valid: true };
		})
	);
	const errors = results.flatMap((r) => r.errors || []);
	return { valid: errors.length === 0, errors };
}

defineExpose({ validate });
</script>
