<template>
	<TreeBuilder
		ref="treeBuilderRef"
		:modelValue="canonicalTree"
		:readOnly="readOnly"
		:allowGroups="true"
		:groupOperators="GROUP_OPERATORS"
		:leafLabel="__('Filter')"
		:groupLabel="__('Group')"
		:emptyLabel="__('No filters yet. Add a filter or group to begin.')"
		:leafFactory="createLeaf"
		:maxDepth="maxDepth"
		:operatorLabel="operatorLabel"
		:visibleNode="visibleNode"
		@update:modelValue="emitSerialized"
		@change="emitSerialized"
	>
		<template #leaf="{ node }">
			<FilterLeaf
				:ref="(el) => setLeafRef(node.id, el)"
				:modelValue="node"
				:doctype="node.doctype || doctype"
				:readOnly="readOnly"
				:showValidation="showValidation"
				:nodeId="nodeId"
				:variableOptions="variableOptions"
				@update:modelValue="updateLeaf(node.id, $event)"
			/>
		</template>
	</TreeBuilder>
</template>

<script setup>
import { computed, ref } from "vue";
import TreeBuilder from "../../tree_builder/TreeBuilder.vue";
import FilterLeaf from "./FilterLeaf.vue";
import { deserializeQueryFilters, serializeQueryFilters } from "./query_filter_serializer.js";

const GROUP_OPERATORS = ["and", "or"];
const props = defineProps({
	modelValue: { type: [Array, Object], default: () => [] },
	doctype: { type: String, required: true },
	nodeId: { type: String, default: null },
	readOnly: { type: Boolean, default: false },
	variableOptions: { type: Array, default: null },
	showValidation: { type: Boolean, default: false },
	maxDepth: { type: Number, default: Infinity },
	operatorLabels: { type: Object, default: () => ({ and: __("Match All"), or: __("Match Any") }) },
	visibleNode: { type: Function, default: () => true },
});
const emit = defineEmits(["update:modelValue", "change"]);
const treeBuilderRef = ref(null);
const leafRefs = new Map();
const canonicalTree = computed(() => deserializeQueryFilters(props.modelValue, { defaultDoctype: props.doctype }));

function createLeaf() {
	return { doctype: props.doctype, field: "", operator: "=", value: { mode: "static", value: "" } };
}
function operatorLabel(operator) {
	return props.operatorLabels[operator] || operator;
}
function setLeafRef(id, instance) {
	if (instance) leafRefs.set(id, instance);
	else leafRefs.delete(id);
}
function emitSerialized(tree) {
	const payload = serializeQueryFilters(tree, { defaultDoctype: props.doctype });
	emit("update:modelValue", payload);
	emit("change", payload);
}
function updateLeaf(id, value) {
	if (!props.readOnly && value) treeBuilderRef.value?.replaceNode(id, value);
}
async function validate() {
	const structural = treeBuilderRef.value?.validate?.() || { valid: true, errors: [] };
	const errors = [...(structural.errors || []).map((error) => error.message)];
	for (const instance of leafRefs.values()) {
		const result = await instance?.validate?.();
		if (!result?.valid && result.errors) errors.push(...result.errors);
	}
	return { valid: errors.length === 0, errors };
}
defineExpose({
	validate,
	getTree: () => treeBuilderRef.value?.getTree?.(),
	getPayload: () => serializeQueryFilters(treeBuilderRef.value?.getTree?.(), { defaultDoctype: props.doctype }),
	addFilter: () => treeBuilderRef.value?.addLeaf(),
	addGroup: () => treeBuilderRef.value?.addGroup(),
});
</script>

<style scoped>
.query-filter-leaf{min-width:0}
</style>
