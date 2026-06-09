<template>
	<div class="loop-config">
		<LoopNodeConfig :node="node" @update-json-config="updateJsonConfig" />
		<hr />
		<ConditionStep :node="node" />
	</div>
</template>

<script setup>
import { useStore } from "../../../stores";
import { fromCodeString } from "../../../utils/serialization";
import LoopNodeConfig from "../../node_configs/LoopNodeConfig.vue";
import ConditionStep from "./ConditionStep.vue";

const props = defineProps({
	node: Object,
});

const store = useStore();

function updateJsonConfig(key, val) {
	if (!props.node.data) return;

	let config =
		typeof props.node.data.config === "string"
			? fromCodeString(props.node.data.config)
			: props.node.data.config || {};

	config[key] = val;
	props.node.data.config = config;
	store.mark_dirty();
}
</script>
