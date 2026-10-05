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
				<FilterGroup
					:ref="(el) => setLeafRef(node.id, el)"
					:doctype="node.doctype || doctype"
					:modelValue="[toFilterRow(node)]"
					:readOnly="readOnly"
					:showValidation="showValidation"
					:nodeId="nodeId"
					:variableOptions="variableOptions"
					:singleRow="true"
					:hideActions="true"
					@update:modelValue="(value) => updateLeaf(node, value)"
				/>
			</div>
		</template>
	</TreeBuilder>
</template>

<script setup>
import { nextTick, reactive, ref, watch } from "vue";
import TreeBuilder from "../tree_builder/TreeBuilder.vue";
import FilterGroup from "./FilterGroup.vue";
import { cloneTree, createId } from "../tree_builder/tree_builder_utils.js";

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
const tree = reactive(parseFilterPayload(props.modelValue));
const leafRefs = new Map();
let syncing = false;

function createLeaf() {
	return {
		id: createId(),
		type: "leaf",
		doctype: props.doctype,
		field: "",
		operator: "=",
		value: { mode: "static", value: "" },
	};
}

function normalizeLeaf(value) {
	if (!value || typeof value !== "object") return createLeaf();

	if (Array.isArray(value)) {
		if (value.length >= 4) {
			return {
				id: createId(),
				type: "leaf",
				doctype: value[0] || props.doctype,
				field: value[1] || "",
				operator: value[2] || "=",
				value: cloneTree(value[3]),
			};
		}
		if (value.length === 3) {
			return {
				id: createId(),
				type: "leaf",
				doctype: props.doctype,
				field: value[0] || "",
				operator: value[1] || "=",
				value: cloneTree(value[2]),
			};
		}
	}

	if (value.field || value.fieldname) {
		return {
			id: value.id || createId(),
			type: "leaf",
			doctype: value.doctype || props.doctype,
			field: value.field || value.fieldname || "",
			operator: value.operator || value.op || "=",
			value: cloneTree(value.value),
		};
	}

	return createLeaf();
}

function looksLikeLeaf(value) {
	if (!Array.isArray(value)) return false;
	return (
		value.length >= 3 &&
		typeof value[0] === "string" &&
		typeof value[1] === "string" &&
		typeof value[2] === "string" &&
		!["and", "or"].includes(value[0].toLowerCase())
	);
}

function parseFilterPayload(value) {
	if (!value) {
		return { id: createId(), type: "group", operator: "and", children: [] };
	}

	if (value && typeof value === "object" && !Array.isArray(value)) {
		if (value.type === "group") {
			return {
				id: value.id || createId(),
				type: "group",
				operator: value.operator || "and",
				children: (value.children || []).map(parseNode),
			};
		}
		return {
			id: createId(),
			type: "group",
			operator: "and",
			children: [normalizeLeaf(value)],
		};
	}

	if (looksLikeLeaf(value)) {
		return {
			id: createId(),
			type: "group",
			operator: "and",
			children: [normalizeLeaf(value)],
		};
	}

	if (Array.isArray(value)) {
		const children = [];
		let pendingOperator = "and";
		for (const item of value) {
			if (typeof item === "string" && ["and", "or"].includes(item.toLowerCase())) {
				pendingOperator = item.toLowerCase();
				continue;
			}
			const node = parseNode(item);
			if (!node) continue;
			children.push(node);
		}

		// A single explicit nested group should retain its own operator.
		const inferredOperator =
			value.find(
				(item) =>
					typeof item === "string" &&
					["and", "or"].includes(item.toLowerCase())
			)?.toLowerCase() || pendingOperator;

		return {
			id: createId(),
			type: "group",
			operator: inferredOperator || "and",
			children,
		};
	}

	return { id: createId(), type: "group", operator: "and", children: [] };
}

function parseNode(value) {
	if (Array.isArray(value)) {
		if (looksLikeLeaf(value)) return normalizeLeaf(value);
		return parseFilterPayload(value);
	}

	if (value && typeof value === "object") {
		if (value.type === "group") return parseFilterPayload(value);
		return normalizeLeaf(value);
	}

	return null;
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

function serializeNode(node) {
	if (node.type === "leaf") {
		const row = toFilterRow(node);
		return [row.doctype, row.field, row.operator, cloneTree(row.value)];
	}

	const children = (node.children || []).map(serializeNode).filter(Boolean);
	if (!children.length) return [];
	if (children.length === 1) return children[0];

	const result = [children[0]];
	for (let i = 1; i < children.length; i++) {
		result.push(node.operator || "and", children[i]);
	}
	return result;
}

function serializeTree(value = tree) {
	return serializeNode(value);
}

function setLeafRef(id, instance) {
	if (instance) leafRefs.set(id, instance);
	else leafRefs.delete(id);
}

async function validate() {
	const errors = [];
	const refs = Array.from(leafRefs.values());
	const results = await Promise.all(
		refs.map((instance) =>
			instance && typeof instance.validate === "function"
				? instance.validate()
				: { valid: true, errors: [] }
		)
	);
	for (const result of results) {
		if (!result?.valid && result.errors) errors.push(...result.errors);
	}

	function validateStructure(node, isRoot = false) {
		if (node.type === "leaf") {
			if (!node.field) errors.push(__("A filter field is required."));
			return;
		}
		if (!node.children?.length) {
			if (!isRoot) errors.push(__("Filter groups cannot be empty."));
			return;
		}
		node.children.forEach((child) => validateStructure(child, false));
	}
	validateStructure(tree, true);

	return { valid: errors.length === 0, errors };
}

watch(
	tree,
	(value) => {
		if (syncing) return;
		const payload = serializeTree(value);
		emit("update:modelValue", payload);
		emit("change", payload);
	},
	{ deep: true }
);

watch(
	() => props.modelValue,
	async (value) => {
		const next = parseFilterPayload(value);
		if (JSON.stringify(next) === JSON.stringify(tree)) return;
		syncing = true;
		Object.keys(tree).forEach((key) => delete tree[key]);
		Object.assign(tree, next);
		await nextTick();
		syncing = false;
	},
	{ deep: true }
);

defineExpose({
	validate,
	getTree: () => cloneTree(tree),
	getPayload: () => serializeTree(tree),
	addFilter: () => treeBuilderRef.value?.addLeaf(),
	addGroup: () => treeBuilderRef.value?.addGroup(),
});
</script>

<style scoped>
.query-filter-leaf {
	min-width: 0;
}

:deep(.filter-group-wrapper) {
	padding: 0;
	border: 0;
	background: transparent;
}

:deep(.filter-list) {
	gap: 0;
}

:deep(.filter-row) {
	border: 0;
	padding: 0;
}

@media (max-width: 768px) {
	.query-filter-leaf {
		width: 100%;
	}
}
</style>
