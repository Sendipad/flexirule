<script setup>
import { fromCodeString } from "../../../utils/serialization";
import WaitNodeConfig from "../../node_configs/WaitNodeConfig.vue";

const props = defineProps({
	node: Object,
});

const emit = defineEmits(["update:field"]);

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
	const config =
		typeof props.node.data.config === "string"
			? flexirule.utils.safe_json_parse(props.node.data.config, {})
			: props.node.data.config || {};
	const errors = [];
	if (!config.value || config.value <= 0) {
		errors.push(__("Delay Value must be greater than 0"));
	}
	return { valid: errors.length === 0, errors };
}

defineExpose({ validate });
</script>

<template>
	<div class="wait-config">
		<WaitNodeConfig :nodeData="node.data" @update-field="updateJsonConfig" />
	</div>
</template>
