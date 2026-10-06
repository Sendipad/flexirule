<template>
	<TreeBuilder
		ref="treeBuilderRef"
		v-model="tree"
		:readOnly="readOnly"
		:allowGroups="true"
		:groupOperators="['and', 'or']"
		:leafLabel="__('Filter')"
		:groupLabel="__('Group')"
		:emptyLabel="__('No filters yet. Add a filter or group to begin.')"
		:leafFactory="createLeaf"
	>
		<template #leaf="{ node }">
			<div class="query-filter-leaf">
				<FilterLeaf
					:ref="(el) => setLeafRef(node.id, el)"
					:doctype="node.doctype || doctype"
					:modelValue="[toFilterRow(node)]"
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
import { nextTick, reactive, ref, watch } from "vue";
import TreeBuilder from "../tree_builder/TreeBuilder.vue";
import FilterLeaf from "./FilterLeaf.vue";
import {
	createFilterLeaf,
	deserializeFilterPayload,
	serializeFilterTree,
	validateFilterTree,
} from "./filter_tree_adapter.js";
import { cloneTree } from "../tree_builder/tree_builder_utils.js";

const props = defineProps({
	modelValue: { type: [Array, Object], default: () => [] },
	doctype: { type: String, required: true },
	nodeId: { type: String, default: null },
	readOnly: { type: Boolean, default: false },
	variableOptions: { type: Array, default: null },
	showValidation: { type: Boolean, default: false },
});

const emit = defineEmits(["update:modelValue", "change"]);
const treeBuilderRef = ref(null);
const tree = reactive(
	deserializeFilterPayload(props.modelValue, { defaultDoctype: props.doctype })
);
const leafRefs = new Map();
let syncing = false;

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

async function validate() {
	const structural = validateFilterTree(tree, { allowEmptyRoot: true });
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

function emitSerialized(value) {
	const payload = serializeFilterTree(value, {
		defaultDoctype: props.doctype,
		allowIncomplete: true,
	});
	emit("update:modelValue", payload);
	emit("change", payload);
}

watch(
	tree,
	(value) => {
		if (syncing) return;
		emitSerialized(value);
	},
	{ deep: true }
);

watch(
	() => props.modelValue,
	async (value) => {
		const next = deserializeFilterPayload(value, { defaultDoctype: props.doctype });
		if (JSON.stringify(next) === JSON.stringify(tree)) return;
		syncing = true;
		Object.keys(tree).forEach((key) => delete tree[key]);
		Object.assign(tree, next);
		await nextTick();
		syncing = false;
	},
	{ deep: true }
);

watch(
	() => props.doctype,
	(value) => {
		if (!value) return;
		const next = deserializeFilterPayload(props.modelValue, { defaultDoctype: value });
		syncing = true;
		Object.keys(tree).forEach((key) => delete tree[key]);
		Object.assign(tree, next);
		nextTick().then(() => {
			syncing = false;
		});
	}
);

defineExpose({
	validate,
	getTree: () => cloneTree(tree),
	getPayload: () => serializeFilterTree(tree, { defaultDoctype: props.doctype }),
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
