<script setup>
import { computed, inject, ref } from "vue";
import { isCollectionNode, isGroupNode, isLeafNode } from "./tree_builder_utils.js";
import TreeBuilderCollection from "./TreeBuilderCollection.vue";
import TreeBuilderGroup from "./TreeBuilderGroup.vue";
import TreeBuilderLeaf from "./TreeBuilderLeaf.vue";

defineOptions({ name: "TreeBuilderNode" });

const props = defineProps({
	node: { type: Object, required: true },
	index: { type: Number, required: true },
	parent: { type: Object, required: true },
	readOnly: Boolean,
	allowGroups: Boolean,
	allowCollections: Boolean,
	collectionLabel: { type: String, default: "Collection" },
	groupOperators: { type: Array, default: () => ["and", "or"] },
	operatorLabel: { type: Function, default: (v) => v },
	visibleNode: { type: Function, default: () => true },
});

const emit = defineEmits(["remove", "operator"]);
const api = inject("treeBuilderContext", null);
const dragOver = ref(false);
const dropPosition = ref(null);
const kind = computed(() => props.node.type);
const children = computed(() => props.node.children || []);

function dragStart(e) {
	if (props.readOnly) return;
	e.stopPropagation();
	api?.beginDrag(props.node.id);
	e.dataTransfer.effectAllowed = "move";
	e.dataTransfer.setData("text/plain", props.node.id || "");
}

function getDropIntent(e) {
	const rect = e.currentTarget.getBoundingClientRect();
	const ratio = rect.height > 0 ? (e.clientY - rect.top) / rect.height : 0.5;
	const isContainer = isGroupNode(props.node) || isCollectionNode(props.node);

	if (isContainer && ratio >= 0.25 && ratio <= 0.75) {
		return { targetId: props.node.id, position: -1, visualPosition: "inside" };
	}

	const after = ratio > (isContainer ? 0.75 : 0.5);
	return {
		targetId: props.parent.id,
		position: props.index + (after ? 1 : 0),
		visualPosition: after ? "after" : "before",
	};
}

function dragOverNode(e) {
	if (props.readOnly || !api?.dragState?.nodeId) return;
	const intent = getDropIntent(e);
	if (!api.canMove(api.dragState.nodeId, intent.targetId)) {
		dragOver.value = false;
		dropPosition.value = null;
		return;
	}

	e.preventDefault();
	e.stopPropagation();
	dragOver.value = true;
	dropPosition.value = intent.visualPosition;
}

function dragLeave(e) {
	// dragleave also fires when the pointer crosses into this node's own children.
	// Keep the target active for those internal transitions.
	if (e.relatedTarget instanceof Node && e.currentTarget.contains(e.relatedTarget)) return;
	dragOver.value = false;
	dropPosition.value = null;
}

function dragEnd(e) {
	e.stopPropagation();
	dragOver.value = false;
	dropPosition.value = null;
	api?.endDrag();
}

function drop(e) {
	e.preventDefault();
	e.stopPropagation();
	const intent = getDropIntent(e);
	dragOver.value = false;
	dropPosition.value = null;
	if (api?.dragState?.nodeId && api.canMove(api.dragState.nodeId, intent.targetId)) {
		api.dropNode(intent.targetId, intent.position);
	} else {
		api?.endDrag();
	}
}
</script>

<template>
	<div
		v-if="visibleNode(node)"
		class="tree-node"
		:class="{
			'drag-over': dragOver && dropPosition === 'inside',
			'drop-before': dragOver && dropPosition === 'before',
			'drop-after': dragOver && dropPosition === 'after',
		}"
		draggable="true"
		@dragstart="dragStart"
		@dragend="dragEnd"
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
			:allowCollections="allowCollections"
			:collectionLabel="collectionLabel"
			@operator="$emit('operator', $event)"
			@add-leaf="api?.addLeaf(node.id)"
			@add-group="api?.addGroup(node.id)"
			@add-collection="api?.addCollection(node.id)"
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
					:allowCollections="allowCollections"
					:collectionLabel="collectionLabel"
					:groupOperators="groupOperators"
					:operatorLabel="operatorLabel"
					:visibleNode="visibleNode"
					@remove="api?.removeNode(child.id)"
					@operator="api?.setOperator(child.id, $event)"
				>
					<template #default="p"><slot v-bind="p" /></template>
					<template #collection="p"><slot name="collection" v-bind="p" /></template>
				</TreeBuilderNode>
			</template>
		</TreeBuilderGroup>

		<TreeBuilderCollection
			v-else-if="isCollectionNode(node)"
			:node="node"
			:label="collectionLabel"
			:readOnly="readOnly"
			:allowGroups="allowGroups"
			:allowCollections="allowCollections"
			@add-leaf="api?.addLeaf(node.id)"
			@add-group="api?.addGroup(node.id)"
			@add-collection="api?.addCollection(node.id)"
			@remove="$emit('remove')"
		>
			<template #label="{ node: collectionNode }">
				<slot name="collection" :node="collectionNode">
					<strong>{{ collectionLabel }}</strong>
				</slot>
			</template>
			<template #children>
				<TreeBuilderNode
					v-for="(child, i) in children"
					:key="child.id"
					:node="child"
					:index="i"
					:parent="node"
					:readOnly="readOnly"
					:allowGroups="allowGroups"
					:allowCollections="allowCollections"
					:collectionLabel="collectionLabel"
					:groupOperators="groupOperators"
					:operatorLabel="operatorLabel"
					:visibleNode="visibleNode"
					@remove="api?.removeNode(child.id)"
					@operator="api?.setOperator(child.id, $event)"
				>
					<template #default="p"><slot v-bind="p" /></template>
					<template #collection="p"><slot name="collection" v-bind="p" /></template>
				</TreeBuilderNode>
			</template>
		</TreeBuilderCollection>

		<TreeBuilderLeaf
			v-else-if="isLeafNode(node)"
			:node="node"
			:context="{ path: [] }"
			:index="index"
			:parent="parent"
			:readOnly="readOnly"
			@remove="$emit('remove')"
		>
			<template #default="p"><slot v-bind="p" /></template>
		</TreeBuilderLeaf>
	</div>
</template>

<style scoped>
.tree-node {
	position: relative;
	min-width: 0;
}
.tree-node.drag-over {
	background: var(--fxr-node-accent-light, var(--fxr-accent-soft));
	border-radius: var(--fxr-radius-lg);
	box-shadow: inset 0 0 0 2px var(--fxr-node-accent, var(--fxr-accent));
}
.tree-node.drop-before::before,
.tree-node.drop-after::after {
	position: absolute;
	z-index: 2;
	right: 0;
	left: 0;
	height: 3px;
	border-radius: 3px;
	background: var(--fxr-node-accent, var(--fxr-accent));
	content: "";
	pointer-events: none;
}
.tree-node.drop-before::before {
	top: -4px;
}
.tree-node.drop-after::after {
	bottom: -4px;
}
</style>
