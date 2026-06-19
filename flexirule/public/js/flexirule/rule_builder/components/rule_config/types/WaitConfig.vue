<script setup>
import { ref, onBeforeUpdate } from "vue";
import { fromCodeString } from "../../../utils/serialization";
import WaitNodeConfig from "../../node_configs/WaitNodeConfig.vue";

const props = defineProps({
	node: Object,
	showValidation: { type: Boolean, default: false },
});

const emit = defineEmits(["update:field"]);
const controlRefs = ref([]);

onBeforeUpdate(() => {
	controlRefs.value = [];
});

function setControlRef(el) {
	if (el) controlRefs.value.push(el);
}

function updateJsonConfig(key, val) {
	// This component handles the 'config' field specifically
	const config =
		typeof props.node.data.config === "string"
			? fromCodeString(props.node.data.config)
			: props.node.data.config || {};
	config[key] = val;
	// Internal state: config is Object
	emit("update:field", "config", config);
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

<template>
	<div class="wait-config">
		<WaitNodeConfig
			:ref="setControlRef"
			:nodeData="node.data"
			:showValidation="showValidation"
			@update-field="updateJsonConfig"
		/>
	</div>
</template>
