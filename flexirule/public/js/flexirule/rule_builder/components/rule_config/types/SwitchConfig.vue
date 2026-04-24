<template>
	<div class="switch-config">
		<SwitchNodeConfig
			:nodeData="node.data"
			:availableNodes="availableNodes"
			:getNodeLabel="getNodeLabel"
			@update-json-config="updateJsonConfig"
		/>
	</div>
</template>

<script setup>
import { computed } from "vue";
import { useStore } from "../../../stores";
import SwitchNodeConfig from "../../node_configs/SwitchNodeConfig.vue";

const props = defineProps({
	node: Object,
});

const store = useStore();

const availableNodes = computed(() => {
	return (store.nodes || [])
		.filter((n) => n.id !== props.node.id && n.id !== "start")
		.map((n) => ({
			id: n.id,
			label: n.data?.action_label || n.label || n.id,
		}));
});

function getNodeLabel(id) {
	const n = (store.nodes || []).find((el) => el.id === id);
	return n ? n.data?.action_label || n.label || n.id : id;
}

function updateJsonConfig(key, val) {
	if (!props.node.data) return;

	let config = props.node.data.config || {};
	if (typeof config === "string") {
		try {
			config = JSON.parse(config || "{}");
		} catch (e) {
			config = {};
		}
	}

	config[key] = val;
	props.node.data.config = config;

	// If cases changed, we might need to update edges
	if (key === "cases") {
		syncEdges(val);
	}

	store.mark_dirty();
}

function syncEdges(cases) {
	const nodeId = props.node.id;

	// Remove all existing conditional edges from this node
	store.edges = store.edges.filter((e) => !(e.source === nodeId && e.sourceHandle !== "default"));

	// Add new edges for each case
	Object.entries(cases).forEach(([val, target]) => {
		if (target) {
			store.edges.push({
				id: `e-${nodeId}-${target}-${val}`,
				source: nodeId,
				target: target,
				sourceHandle: val, // Use case value as handleId
			});
		}
	});
}
</script>
