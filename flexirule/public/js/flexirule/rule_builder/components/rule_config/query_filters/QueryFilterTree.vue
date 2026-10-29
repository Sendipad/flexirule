<template>
	<TreeBuilder
		ref="treeBuilderRef"
		:modelValue="canonicalTree"
		:readOnly="readOnly"
		:allowGroups="true"
		:allowCollections="false"
		:groupOperators="GROUP_OPERATORS"
		:leafLabel="__('Filter')"
		:groupLabel="__('Group')"
		:emptyLabel="__('No filters yet. Add a filter or group to begin.')"
		:leafFactory="createLeaf"
		:maxDepth="maxDepth"
		:operatorLabel="operatorLabel"
		:visibleNode="visibleNode"
		:presentationMode="presentationMode"
		:isLeafNew="isLeafNew"
		:isLeafValid="isLeafValid"
		:canEditRule="canEditRule"
		@update:modelValue="emitSerialized"
	>
		<template #leaf-summary="{ node }">
			<FilterLeafSummary
				:node="node"
				:doctype="node.doctype || doctype"
				:variableOptions="variableOptions"
			/>
		</template>
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
import FilterLeafSummary from "./FilterLeafSummary.vue";
import { deserializeQueryFilters, toPersistedQueryFilterTree } from "./query_filter_serializer.mjs";
import { isFilterLeafValid, validateFilterLeaf } from "./query_filter_validation.mjs";

const GROUP_OPERATORS = ["and", "or"];
const props = defineProps({
	modelValue: { type: [Array, Object], default: () => [] },
	doctype: { type: String, required: true },
	nodeId: { type: String, default: null },
	readOnly: { type: Boolean, default: false },
	variableOptions: { type: Array, default: null },
	showValidation: { type: Boolean, default: false },
	maxDepth: { type: Number, default: Infinity },
	operatorLabels: {
		type: Object,
		default: () => ({ and: __("Match All"), or: __("Match Any") }),
	},
	visibleNode: { type: Function, default: () => true },
	presentationMode: { type: String, default: "hybrid" },
	canEditRule: { type: Boolean, default: false },
});
const emit = defineEmits(["update:modelValue", "change"]);
const treeBuilderRef = ref(null);
const leafRefs = new Map();
const canonicalTree = computed(() =>
	deserializeQueryFilters(props.modelValue, { defaultDoctype: props.doctype })
);

function createLeaf() {
	return {
		doctype: props.doctype,
		field: "",
		operator: "=",
		value: { mode: "static", value: "" },
	};
}
function isLeafNew(node) {
	return !node?.field;
}
function isLeafValid(node) {
	return isFilterLeafValid(node, { doctype: props.doctype });
}
function operatorLabel(operator) {
	return props.operatorLabels[operator] || operator;
}
function setLeafRef(id, instance) {
	if (instance) leafRefs.set(id, instance);
	else leafRefs.delete(id);
}
function emitSerialized(tree) {
	const payload = toPersistedQueryFilterTree(tree);
	emit("update:modelValue", payload);
	emit("change", payload);
}
function updateLeaf(id, value) {
	if (!props.readOnly && value) treeBuilderRef.value?.replaceNode(id, value);
}
async function validate() {
	const errors = [];
	if (typeof treeBuilderRef.value?.validate !== "function") {
		errors.push(__("Filter tree structural validation is unavailable."));
	} else {
		const structural = treeBuilderRef.value.validate();
		errors.push(...(structural.errors || []).map((error) => error.message));
		if (!structural.valid && !(structural.errors || []).length) {
			errors.push(__("The filter tree structure is invalid."));
		}
	}

	const tree = treeBuilderRef.value?.getTree?.();
	if (!tree || typeof tree !== "object") {
		errors.push(__("Filter tree data is unavailable."));
	}

	// An empty root intentionally means "match all"; nested groups must contain
	// at least one condition or group.
	async function visit(node, isRoot = false) {
		if (!node || typeof node !== "object") {
			errors.push(__("Filter tree contains a malformed node."));
			return;
		}
		if (node.type === "group") {
			if (!Array.isArray(node.children)) {
				errors.push(__("Filter group children must be a list."));
				return;
			}
			if (!isRoot && node.children.length === 0) {
				errors.push(__("Nested filter groups cannot be empty."));
			}
			for (const child of node.children) await visit(child, false);
			return;
		}
		if (node.type !== "leaf") {
			errors.push(__("Filter tree contains an unsupported node type."));
			return;
		}
		const instance = leafRefs.get(node.id);
		let result;
		if (typeof instance?.validate === "function") {
			result = await instance.validate();
		} else {
			const rawResult = validateFilterLeaf(node, { doctype: props.doctype });
			result = { valid: rawResult.valid, errors: rawResult.errors.map((msg) => __(msg)) };
		}
		if (!result?.valid) {
			errors.push(...(result.errors || []));
			if (!(result.errors || []).length) errors.push(__("A filter leaf is invalid."));
		}
	}
	if (tree && typeof tree === "object") await visit(tree, true);

	const uniqueErrors = [...new Set(errors)];
	return { valid: uniqueErrors.length === 0, errors: uniqueErrors };
}
defineExpose({
	validate,
	getTree: () => treeBuilderRef.value?.getTree?.(),
	getPayload: () => toPersistedQueryFilterTree(treeBuilderRef.value?.getTree?.()),
	addFilter: () => treeBuilderRef.value?.addLeaf(),
	addGroup: () => treeBuilderRef.value?.addGroup(),
});
</script>

<style scoped>
.query-filter-leaf {
	min-width: 0;
}
</style>
