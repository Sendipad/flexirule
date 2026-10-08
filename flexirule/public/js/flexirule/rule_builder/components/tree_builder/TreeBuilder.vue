<template>
	<div class="tree-builder fxr-accent-scope">
		<div class="tree-builder__header">
			<div class="tree-builder__logic">
				<button
					v-for="op in operators"
					:key="op"
					type="button"
					class="logic-btn"
					:class="{ active: root.operator === op }"
					:disabled="readOnly"
					@click="setOperator(root.id, op)"
				>
					{{ operatorLabel(op) }}
				</button>
			</div>
			<div v-if="!readOnly" class="tree-builder__actions">
				<button type="button" class="fxr-btn" @click="addLeaf()">
					<i class="fa fa-plus"></i><span>{{ leafLabel }}</span>
				</button>
				<button v-if="allowGroups" type="button" class="fxr-btn" @click="addGroup()">
					<i class="fa fa-folder-open-o"></i><span>{{ groupLabel }}</span>
				</button>
				<button v-if="allowCollections" type="button" class="fxr-btn" @click="addCollection()">
					<i class="fa fa-sitemap"></i><span>{{ collectionLabel }}</span>
				</button>
			</div>
		</div>
		<div class="tree-builder__content">
			<div v-if="!root.children.length" class="tree-builder__empty">
				<i class="fa fa-sitemap"></i><span>{{ emptyLabel }}</span>
			</div>
			<TreeBuilderNode
				v-for="(node, index) in root.children"
				:key="node.id"
				:node="node"
				:index="index"
				:parent="root"
				:readOnly="readOnly"
				:allowGroups="allowGroups"
				:allowCollections="allowCollections"
				:collectionLabel="collectionLabel"
				:groupOperators="operators"
				:operatorLabel="operatorLabel"
				:visibleNode="visibleNode"
				@remove="removeNode(node.id)"
				@operator="setOperator(node.id, $event)"
			>
				<template #default="p"><slot name="leaf" v-bind="p" /></template>
			</TreeBuilderNode>
		</div>
	</div>
</template>
<script setup>
import { computed, provide } from "vue";
import TreeBuilderNode from "./TreeBuilderNode.vue";
import { useTreeBuilder } from "./useTreeBuilder.js";

const props = defineProps({
	modelValue: {
		type: Object,
		default: () => ({ id: "root", type: "group", operator: "and", children: [] }),
	},
	readOnly: Boolean,
	allowGroups: { type: Boolean, default: true },
	allowCollections: { type: Boolean, default: false },
	groupOperators: { type: Array, default: () => ["and", "or"] },
	leafLabel: { type: String, default: __("Condition") },
	groupLabel: { type: String, default: __("Group") },
	collectionLabel: { type: String, default: __("Collection") },
	emptyLabel: { type: String, default: __("No items yet. Add an item to begin.") },
	leafFactory: { type: Function, default: () => ({}) },
	collectionFactory: { type: Function, default: () => ({}) },
	maxDepth: { type: Number, default: Infinity },
	operatorLabel: { type: Function, default: (op) => op },
	visibleNode: { type: Function, default: () => true },
	allowEmptyGroups: { type: Boolean, default: true },
	validateLeaf: { type: Function, default: null },
	validateCollection: { type: Function, default: null },
});
const emit = defineEmits(["update:modelValue", "change", "validation-error"]);
const api = useTreeBuilder({
	modelValue: computed(() => props.modelValue),
	emit,
	readOnly: props.readOnly,
	groupOperators: props.groupOperators,
	leafFactory: props.leafFactory,
	collectionFactory: props.collectionFactory,
	allowGroups: props.allowGroups,
	allowCollections: props.allowCollections,
	allowEmptyGroups: props.allowEmptyGroups,
	maxDepth: props.maxDepth,
	validateLeaf: props.validateLeaf,
	validateCollection: props.validateCollection,
});
provide("treeBuilderContext", api);
const { root, operators, addLeaf, addCollection, addGroup, removeNode, setOperator } = api;
const operatorLabel = (op) => props.operatorLabel(op);
const visibleNode = (node) => props.visibleNode(node) !== false;
defineExpose({ ...api });
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
.tree-builder__logic,
.tree-builder__actions {
	display: flex;
	gap: var(--fxr-space-1);
	align-items: center;
}
.logic-btn {
	border: 0;
	background: transparent;
	padding: 4px 12px;
	border-radius: var(--fxr-radius-md);
	font-size: 11px;
	font-weight: 800;
}
.logic-btn.active {
	background: var(--fxr-node-accent, var(--fxr-accent));
	color: #fff;
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
}
@media (max-width: 768px) {
	.tree-builder__header {
		flex-direction: column;
		align-items: stretch;
	}
}
</style>
