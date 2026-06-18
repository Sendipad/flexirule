<script setup>
import { ref } from "vue";
import { fromCodeString } from "../../../utils/serialization";
import WaitNodeConfig from "../../node_configs/WaitNodeConfig.vue";

const props = defineProps({
	node: Object,
	showValidation: { type: Boolean, default: false },
});

const emit = defineEmits(["update:field"]);
const waitNodeRef = ref(null);

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

function validate() {
	if (waitNodeRef.value && typeof waitNodeRef.value.validate === "function") {
		return waitNodeRef.value.validate();
	}
	return { valid: true };
}

defineExpose({ validate });
</script>

<template>
	<div class="wait-config">
		<WaitNodeConfig
			ref="waitNodeRef"
			:nodeData="node.data"
			:showValidation="showValidation"
			@update-field="updateJsonConfig"
		/>
	</div>
</template>
