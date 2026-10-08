<script setup>
import { computed, inject, ref } from "vue";
import { isGroupNode, isLeafNode } from "./tree_builder_utils.js";
import TreeBuilderGroup from "./TreeBuilderGroup.vue";
import TreeBuilderLeaf from "./TreeBuilderLeaf.vue";
defineOptions({ name: "TreeBuilderNode" });
const props = defineProps({
	node: { type: Object, required: true },
	index: { type: Number, required: true },
	parent: { type: Object, required: true },
	readOnly: Boolean,
	allowGroups: Boolean,
	groupOperators: { type: Array, default: () => ["and", "or"] },
	operatorLabel: { type: Function, default: (v) => v },
	visibleNode: { type: Function, default: () => true },
});
const emit = defineEmits(["remove", "operator"]);
const api = inject("treeBuilderContext", null),
	dragOver = ref(false);
const kind = computed(() => props.node.type),
	children = computed(() => props.node.children || []);
function dragStart(e) {
	if (props.readOnly) return;
	e.stopPropagation();
	api?.beginDrag(props.node.id);
	e.dataTransfer.effectAllowed = "move";
	e.dataTransfer.setData("text/plain", props.node.id || "");
}
function dragOverNode(e) {
	if (props.readOnly || (!isGroupNode(props.node) && !isLeafNode(props.node))) return;
	e.preventDefault();
	e.stopPropagation();
	dragOver.value = true;
}
function dragLeave() {
	dragOver.value = false;
}
function drop(e) {
	e.preventDefault();
	e.stopPropagation();
	dragOver.value = false;
	if (isGroupNode(props.node)) api?.dropNode(props.node.id);
	else if (isLeafNode(props.node)) api?.dropNode(props.parent.id, props.index);
}
</script>
<template>
	<div
		v-if="visibleNode(node)"
		class="tree-node"
		:class="{ 'drag-over': dragOver }"
		draggable="true"
		@dragstart="dragStart"
		@dragover="dragOverNode"
		@dragleave="dragLeave"
		@drop="drop"
	>
		<TreeBuilderGroup
			v-if="kind === 'group'"
			:node="node"
			:operators="groupOperators"
			:operatorLabel="operatorLabel"
			:readOnly="readOnly"
			:allowGroups="allowGroups"
			@operator="$emit('operator', $event)"
			@add-leaf="api?.addLeaf(node.id)"
			@add-group="api?.addGroup(node.id)"
			@remove="$emit('remove')"
		>
			<template #children>
				<TreeBuilderNode
					v-for="(child, i) in children"
					:key="child.id"
					:node="child"
					:index="i"
					:parent="node"
					:readOnly="readOnly"
					:allowGroups="allowGroups"
					:groupOperators="groupOperators"
					:operatorLabel="operatorLabel"
					:visibleNode="visibleNode"
					@remove="api?.removeNode(child.id)"
					@operator="api?.setOperator(child.id, $event)"
				>
					<template #default="p"><slot v-bind="p" /></template>
				</TreeBuilderNode>
			</template>
		</TreeBuilderGroup>
		<TreeBuilderLeaf
			v-else-if="isLeafNode(node)"
			:node="node"
			:context="{ path: [] }"
			:index="index"
			:parent="parent"
			:readOnly="readOnly"
			@remove="$emit('remove')"
			><template #default="p"><slot v-bind="p" /></template
		></TreeBuilderLeaf>
	</div>
</template>
<style scoped>
.tree-node {
	min-width: 0;
}
.tree-node__unsupported {
	padding: var(--fxr-space-2);
	color: var(--fxr-text-danger);
}
.tree-node.drag-over {
	background: var(--fxr-node-accent-light, var(--fxr-accent-soft));
	border-radius: var(--fxr-radius-lg);
	box-shadow: inset 0 0 0 2px var(--fxr-node-accent, var(--fxr-accent));
}
</style>
