<template>
	<TreeBuilder
		ref="treeBuilderRef"
		:modelValue="tree"
		:readOnly="readOnly"
		:allowGroups="true"
		:groupOperators="['and', 'or']"
		:leafLabel="__('Filter')"
		:groupLabel="__('Group')"
		:emptyLabel="__('No filters yet. Add a filter or group to begin.')"
		:leafFactory="createLeaf"
		@update:modelValue="handleTreeUpdate"
	>
		<template #leaf="{ node }">
			<div class="query-filter-leaf">
				<FilterLeaf
					:ref="(el) => setLeafRef(node.id, el)"
					:doctype="node.doctype || doctype"
					:modelValue="toFilterRow(node)"
					:readOnly="readOnly"
					:showValidation="showValidation"
					:nodeId="nodeId"
					:variableOptions="variableOptions"
					@update:modelValue="(value) => updateLeaf(node, value)"
				/>
			</div>
		</template>
	</TreeBuilder>
</template>

<script setup>
import { ref, watch } from "vue";
import TreeBuilder from "../tree_builder/TreeBuilder.vue";
import FilterLeaf from "./FilterLeaf.vue";
import {
	createFilterLeaf,
	serializeFilterTree,
	validateFilterTree,
} from "./filter_tree_adapter.js";
import { cloneTree, normalizeTree } from "../tree_builder/tree_builder_utils.js";

const props = defineProps({
	// This component owns an editor AST, not the persisted/backend filter payload.
	// The parent is responsible for deserializing persisted filters once when
	// creating the editor draft.
	modelValue: {
		type: Object,
		default: () => ({ type: "group", operator: "and", children: [] }),
	},
	doctype: { type: String, required: true },
	nodeId: { type: String, default: null },
	readOnly: { type: Boolean, default: false },
	variableOptions: { type: Array, default: null },
	showValidation: { type: Boolean, default: false },
});

const emit = defineEmits(["update:modelValue", "change"]);
const treeBuilderRef = ref(null);
const tree = ref(normalizeTree(props.modelValue));
const leafRefs = new Map();
let syncingFromParent = false;

function createLeaf() {
	return createFilterLeaf({ doctype: props.doctype });
}

function toFilterRow(node) {
	return {
		doctype: node.doctype || props.doctype,
		field: node.field || "",
		operator: node.operator || "=",
		value: cloneTree(node.value),
	};
}

function updateLeaf(node, value) {
	const row = Array.isArray(value) ? value[0] : value;
	if (!row) return;

	Object.assign(node, {
		doctype: row.doctype || props.doctype,
		field: row.field || row.fieldname || "",
		operator: row.operator || row.op || "=",
		value: cloneTree(row.value),
	});

}

function setLeafRef(id, instance) {
	if (instance) leafRefs.set(id, instance);
	else leafRefs.delete(id);
}

function handleTreeUpdate(value) {
	if (syncingFromParent) return;
	const next = cloneTree(value);
	tree.value = next;
	emit("update:modelValue", cloneTree(next));
	emit("change", cloneTree(next));
}

watch(
	() => props.modelValue,
	async (value) => {
		const next = normalizeTree(value);
		if (JSON.stringify(next) === JSON.stringify(tree.value)) return;

		syncingFromParent = true;
		tree.value = next;
		await Promise.resolve();
		syncingFromParent = false;
	},
	{ deep: true, immediate: true }
);

async function validate() {
	const currentTree = treeBuilderRef.value?.getTree() || tree.value;
	const structural = validateFilterTree(currentTree, { allowEmptyRoot: true });
	const errors = structural.errors.map((error) => error.message);

	const results = await Promise.all(
		Array.from(leafRefs.values()).map((instance) =>
			instance && typeof instance.validate === "function"
				? instance.validate()
				: { valid: true, errors: [] }
		)
	);

	for (const result of results) {
		if (!result?.valid && result.errors) errors.push(...result.errors);
	}

	return { valid: errors.length === 0, errors };
}

function getTree() {
	return cloneTree(treeBuilderRef.value?.getTree() || tree.value);
}

function getPayload() {
	return serializeFilterTree(getTree(), {
		defaultDoctype: props.doctype,
	});
}

defineExpose({
	validate,
	getTree,
	getPayload,
	addFilter: () => treeBuilderRef.value?.addLeaf(),
	addGroup: () => treeBuilderRef.value?.addGroup(),
});
</script>

<style scoped>
.query-filter-leaf {
	min-width: 0;
}

@media (max-width: 768px) {
	.query-filter-leaf {
		width: 100%;
	}
}
</style>
