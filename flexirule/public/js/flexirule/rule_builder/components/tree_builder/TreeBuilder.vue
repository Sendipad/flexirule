<template>
	<div class="tree-builder fxr-accent-scope">
		<div class="tree-builder__header">
			<div class="tree-builder__logic">
				<button
					v-for="operator in groupOperators"
					:key="operator"
					type="button"
					class="logic-btn"
					:class="{ active: root.operator === operator }"
					:disabled="readOnly"
					@click="setOperator(root, operator)"
				>
					{{ operatorLabel(operator) }}
				</button>
			</div>
			<div v-if="!readOnly" class="tree-builder__actions">
				<button type="button" class="fxr-btn" @click="addLeaf(root)">
					<i class="fa fa-plus"></i>
					<span>{{ leafLabel }}</span>
				</button>
				<button v-if="allowGroups" type="button" class="fxr-btn" @click="addGroup(root)">
					<i class="fa fa-folder-open-o"></i>
					<span>{{ groupLabel }}</span>
				</button>
			</div>
		</div>

		<div class="tree-builder__content">
			<div v-if="!root.children.length" class="tree-builder__empty">
				<i class="fa fa-filter"></i>
				<span>{{ emptyLabel }}</span>
			</div>

			<TreeBuilderNode
				v-for="(node, index) in root.children"
				:key="node.id"
				:node="node"
				:index="index"
				:parent="root"
				:readOnly="readOnly"
				:allowGroups="allowGroups"
				:groupOperators="groupOperators"
				:leafLabel="leafLabel"
				:groupLabel="groupLabel"
				:operatorLabel="operatorLabel"
				:leafFactory="leafFactory"
				@remove="removeNode(root, index)"
			>
				<template #leaf="slotProps">
					<slot name="leaf" v-bind="slotProps" />
				</template>
			</TreeBuilderNode>
		</div>
	</div>
</template>

<script setup>
import { computed, nextTick, reactive, watch, provide } from "vue";
import TreeBuilderNode from "./TreeBuilderNode.vue";
import {
	cloneTree,
	createId,
	normalizeTree,
	isGroupNode,
	isDescendant,
} from "./tree_builder_utils.js";

const props = defineProps({
	modelValue: {
		type: Object,
		default: () => ({ type: "group", operator: "and", children: [] }),
	},
	readOnly: { type: Boolean, default: false },
	allowGroups: { type: Boolean, default: true },
	groupOperators: {
		type: Array,
		default: () => ["and", "or"],
	},
	leafLabel: { type: String, default: __("Condition") },
	groupLabel: { type: String, default: __("Group") },
	emptyLabel: {
		type: String,
		default: __("No conditions yet. Add a condition or group to begin."),
	},
	logicalOperations: { type: Array, default: () => [] },
	onLeafAdded: { type: Function, default: null },
	leafFactory: {
		type: Function,
		default: () => ({ type: "leaf" }),
	},
});

const emit = defineEmits(["update:modelValue", "change"]);

const root = reactive(normalizeTree(props.modelValue));
let syncing = false;

const logicalOperationMap = computed(() =>
	new Map(
		props.logicalOperations
			.filter((item) => item && item.value)
			.map((item) => [String(item.value).toLowerCase(), item])
	)
);

const operatorLabel = (operator) =>
	logicalOperationMap.value.get(String(operator).toLowerCase())?.label || operator;

function setOperator(group, operator) {
	if (!groupOperators.value.includes(operator) || props.readOnly) return;
	group.operator = operator;
}

const groupOperators = computed(() => props.groupOperators.filter(Boolean));

function addLeaf(group) {
	if (props.readOnly) return null;
	const node = {
		id: createId(),
		type: "leaf",
		...cloneTree(props.leafFactory()),
	};
	group.children.push(node);
	handleLeafAdded(node);
	return node;
}

function insertLeafAfter(parent, index) {
	if (props.readOnly || !parent?.children) return null;
	const node = {
		id: createId(),
		type: "leaf",
		...cloneTree(props.leafFactory()),
	};
	parent.children.splice(index + 1, 0, node);
	handleLeafAdded(node);
	return node;
}

function handleLeafAdded(node) {
	if (typeof props.onLeafAdded === "function") props.onLeafAdded(node);
}

function addGroup(group) {
	if (props.readOnly || !props.allowGroups) return;
	group.children.push({
		id: createId(),
		type: "group",
		operator: groupOperators.value[0] || "and",
		children: [],
	});
}

function removeNode(parent, index) {
	if (props.readOnly || !parent?.children?.[index]) return;
	parent.children.splice(index, 1);
}

function moveNode(fromParent, fromIndex, toParent, toIndex = -1) {
	if (props.readOnly || !fromParent?.children?.[fromIndex] || !toParent) return;

	const node = fromParent.children[fromIndex];
	if (isGroupNode(node) && isDescendant(node, toParent.id)) return;

	fromParent.children.splice(fromIndex, 1);
	const targetIndex = toIndex < 0 ? toParent.children.length : toIndex;
	toParent.children.splice(targetIndex, 0, node);
}

const dragState = reactive({ parent: null, index: -1 });

function beginDrag(parent, index) {
	if (props.readOnly) return;
	dragState.parent = parent;
	dragState.index = index;
}

function dropNode(targetParent, targetIndex = -1) {
	if (!dragState.parent) return;
	moveNode(dragState.parent, dragState.index, targetParent, targetIndex);
	dragState.parent = null;
	dragState.index = -1;
}

provide("treeBuilderActions", {
	addLeaf,
	insertLeafAfter,
	addGroup,
	removeNode,
	beginDrag,
	dropNode,
});

watch(
	root,
	(value) => {
		if (syncing) return;
		const next = cloneTree(value);
		emit("update:modelValue", next);
		emit("change", next);
	},
	{ deep: true }
);

watch(
	() => props.modelValue,
	async (value) => {
		const next = normalizeTree(value);
		if (JSON.stringify(next) === JSON.stringify(root)) return;
		syncing = true;
		Object.keys(root).forEach((key) => delete root[key]);
		Object.assign(root, next);
		await nextTick();
		syncing = false;
	},
	{ deep: true }
);

defineExpose({
	addLeaf: () => addLeaf(root),
	addGroup: () => addGroup(root),
	getTree: () => cloneTree(root),
});
</script>

<style scoped>
.tree-builder {
	display: flex;
	flex-direction: column;
	gap: var(--fxr-space-2);
	padding: var(--fxr-space-3);
	background: var(--fxr-bg-page);
	border: 1px solid var(--fxr-border-subtle);
	border-radius: var(--fxr-radius-lg);
}

.tree-builder__header {
	display: flex;
	align-items: center;
	justify-content: space-between;
	gap: var(--fxr-space-3);
	padding-bottom: var(--fxr-space-2);
	border-bottom: 1px solid var(--fxr-border-subtle);
}

.tree-builder__logic {
	display: flex;
	gap: 2px;
	padding: 3px;
	background: var(--fxr-surface-2);
	border: 1px solid var(--fxr-border-subtle);
	border-radius: var(--fxr-radius-lg);
}

.logic-btn {
	border: 0;
	background: transparent;
	color: var(--fxr-text-soft);
	padding: 4px 12px;
	border-radius: var(--fxr-radius-md);
	font-size: 11px;
	font-weight: 800;
	cursor: pointer;
}

.logic-btn.active {
	background: var(--fxr-node-accent, var(--fxr-accent));
	color: #fff;
}

.tree-builder__actions {
	display: flex;
	gap: var(--fxr-space-2);
}

.tree-builder__content {
	display: flex;
	flex-direction: column;
	gap: var(--fxr-space-2);
	min-height: 52px;
}

.tree-builder__empty {
	display: flex;
	align-items: center;
	justify-content: center;
	gap: var(--fxr-space-2);
	min-height: 72px;
	padding: var(--fxr-space-4);
	color: var(--fxr-text-muted);
	border: 1px dashed var(--fxr-border-subtle);
	border-radius: var(--fxr-radius-md);
	text-align: center;
}

@media (max-width: 768px) {
	.tree-builder__header {
		flex-direction: column;
		align-items: stretch;
	}
	.tree-builder__logic {
		width: 100%;
	}
	.logic-btn {
		flex: 1;
		height: 40px;
	}
	.tree-builder__actions {
		flex-wrap: wrap;
	}
	.tree-builder__actions .fxr-btn {
		flex: 1;
		justify-content: center;
		min-height: 40px;
	}
}
</style>
