<template>
	<div class="switch-config">
		<SwitchNodeConfig
			:ref="setControlRef"
			:nodeData="node.data"
			:availableNodes="availableNodes"
			:getNodeLabel="getNodeLabel"
			:showValidation="showValidation"
			@update-json-config="updateJsonConfig"
		/>
	</div>
</template>

<script setup>
import { computed, ref, onBeforeUpdate } from "vue";
import { useRuleStore, useGraphStore } from "../../../stores";
import { fromCodeString } from "../../../utils/serialization";
import SwitchNodeConfig from "../../node_configs/SwitchNodeConfig.vue";

const props = defineProps({
	node: Object,
	showValidation: { type: Boolean, default: false },
});

const ruleStore = useRuleStore();
const graphStore = useGraphStore();
const controlRefs = ref([]);

onBeforeUpdate(() => {
	controlRefs.value = [];
});

function setControlRef(el) {
	if (el) controlRefs.value.push(el);
}

const availableNodes = computed(() => {
	return (graphStore.nodes || [])
		.filter((n) => n.id !== props.node.id && n.id !== "start")
		.map((n) => ({
			id: n.id,
			label: n.data?.action_label || n.label || n.id,
		}));
});

function getNodeLabel(id) {
	const n = (graphStore.nodes || []).find((el) => el.id === id);
	return n ? n.data?.action_label || n.label || n.id : id;
}

function updateJsonConfig(key, val) {
	if (!props.node.data) return;

	let config =
		typeof props.node.data.config === "string"
			? fromCodeString(props.node.data.config)
			: props.node.data.config || {};

	config[key] = val;
	props.node.data.config = config;

	// If cases changed, we might need to update edges
	if (key === "cases") {
		syncEdges(val);
	}

	const isDraft = !graphStore.nodes.some((n) => n === props.node);
	if (!isDraft) {
		ruleStore.mark_dirty();
	}
}

function syncEdges(cases) {
	const nodeId = props.node.id;

	// Remove all existing conditional edges from this node
	graphStore.edges = graphStore.edges.filter((e) => !(e.source === nodeId && e.sourceHandle !== "default"));

	// Add new edges for each case
	Object.entries(cases).forEach(([val, target]) => {
		if (target) {
			graphStore.edges.push({
				id: `e-${nodeId}-${target}-${val}`,
				source: nodeId,
				target: target,
				sourceHandle: val, // Use case value as handleId
			});
		}
	});
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
