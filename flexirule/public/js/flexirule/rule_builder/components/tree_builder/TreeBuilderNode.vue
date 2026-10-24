<script setup>
import { computed, inject, ref } from "vue";
import { isCollectionNode, isGroupNode, isLeafNode } from "./tree_builder_utils.mjs";
import { getSiblingDropIntent } from "./tree_builder_drag_model.mjs";
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
	presentationMode: { type: String, default: "hybrid" },
	editorLayout: { type: String, default: "replace" },
	isLeafNew: { type: Function, default: null },
	isLeafValid: { type: Function, default: null },
});

const emit = defineEmits(["remove", "operator"]);
const api = inject("treeBuilderContext", null);
const dragOver = ref(false);
const dropPosition = ref(null);
const nodeDragging = ref(false);
const kind = computed(() => props.node.type);
const children = computed(() => props.node.children || []);
const isDraggableNode = computed(
	() => isLeafNode(props.node) || isGroupNode(props.node) || isCollectionNode(props.node)
);
let dragOriginWasInteractive = false;
const interactiveSelector = [
	"button",
	"input",
	"select",
	"textarea",
	"option",
	"a",
	'[contenteditable="true"]',
	'[role="button"]',
	'[role="combobox"]',
	"[data-no-drag]",
	".fxr-control",
	".fxr-input-group",
	".combobox-container",
	".combobox-wrapper",
	".flex-value-control",
	".flex-value-control-button",
	".form-control",
].join(", ");

function rememberDragOrigin(e) {
	const target = e.target;
	dragOriginWasInteractive =
		target instanceof Element && Boolean(target.closest(interactiveSelector));
}

function startNodeDrag(e) {
	// Only the node whose draggable surface initiated this event may own the drag.
	// Stop propagation so an ancestor group cannot replace a leaf's drag ID.
	e.stopPropagation();
	if (props.readOnly || !isDraggableNode.value || dragOriginWasInteractive) {
		e.preventDefault();
		dragOriginWasInteractive = false;
		return;
	}

	nodeDragging.value = true;
	api?.beginDrag(props.node.id);
	if (e.dataTransfer) {
		e.dataTransfer.effectAllowed = "move";
		e.dataTransfer.setData("text/plain", props.node.id || "");
	}
}

function endNodeDrag(e) {
	e.stopPropagation();
	nodeDragging.value = false;
	dragOriginWasInteractive = false;
	api?.endDrag();
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

function clearDropIndicator() {
	dragOver.value = false;
	dropPosition.value = null;
}

function canAcceptDrop(intent, draggedId) {
	return Boolean(
		!props.readOnly &&
			draggedId &&
			draggedId !== props.node.id &&
			intent &&
			api?.canMove(draggedId, intent.targetId)
	);
}

function dragOverSibling(position, e) {
	e.stopPropagation();
	const draggedId = api?.dragState?.nodeId || e.dataTransfer?.getData("text/plain");
	const intent = getSiblingDropIntent(props.parent?.id, props.index, position);
	if (!canAcceptDrop(intent, draggedId)) {
		clearDropIndicator();
		if (e.dataTransfer) e.dataTransfer.dropEffect = "none";
		return;
	}

	e.preventDefault();
	if (e.dataTransfer) e.dataTransfer.dropEffect = "move";
	dragOver.value = true;
	dropPosition.value = intent.visualPosition;
}

function dropOnSibling(position, e) {
	e.preventDefault();
	e.stopPropagation();
	const draggedId = api?.dragState?.nodeId || e.dataTransfer?.getData("text/plain");
	const intent = getSiblingDropIntent(props.parent?.id, props.index, position);
	clearDropIndicator();

	try {
		if (!canAcceptDrop(intent, draggedId)) return;
		if (api?.dragState?.nodeId) api.dropNode(intent.targetId, intent.position);
		else api?.moveNode(draggedId, intent.targetId, intent.position);
	} finally {
		api?.endDrag();
	}
}

function dragOverNode(e) {
	const draggedId = api?.dragState?.nodeId || e.dataTransfer?.getData("text/plain");
	if (props.readOnly || !draggedId) return;
	if (draggedId === props.node.id) {
		// Never reinterpret hovering over the source row as a valid sibling/inside drop.
		e.stopPropagation();
		clearDropIndicator();
		if (e.dataTransfer) e.dataTransfer.dropEffect = "none";
		return;
	}
	const intent = getDropIntent(e);
	if (!api?.canMove(draggedId, intent.targetId)) {
		e.stopPropagation();
		dragOver.value = false;
		dropPosition.value = null;
		return;
	}

	e.preventDefault();
	e.stopPropagation();
	if (e.dataTransfer) e.dataTransfer.dropEffect = "move";
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

function drop(e) {
	e.preventDefault();
	e.stopPropagation();
	const intent = getDropIntent(e);
	const draggedId = api?.dragState?.nodeId || e.dataTransfer?.getData("text/plain");
	dragOver.value = false;
	dropPosition.value = null;
	if (draggedId && api?.canMove(draggedId, intent.targetId)) {
		if (api.dragState?.nodeId) api.dropNode(intent.targetId, intent.position);
		else api.moveNode(draggedId, intent.targetId, intent.position);
	}
	api?.endDrag();
}
</script>

<template>
	<div
		v-if="visibleNode(node)"
		class="tree-node"
		:draggable="!readOnly && isDraggableNode"
		@pointerdown.capture="rememberDragOrigin"
		@dragstart="startNodeDrag"
		@dragend="endNodeDrag"
		:class="{
			'is-dragging': nodeDragging,
			'is-tree-drag-active': Boolean(api?.dragState?.nodeId),
			'is-drag-source': api?.dragState?.nodeId === node.id,
			'drag-over': dragOver && dropPosition === 'inside',
			'drop-before': dragOver && dropPosition === 'before',
			'drop-after': dragOver && dropPosition === 'after',
		}"
		@dragover="dragOverNode"
		@dragleave="dragLeave"
		@drop="drop"
	>
		<div
			v-if="!readOnly"
			class="tree-node__drop-zone tree-node__drop-zone--before"
			aria-hidden="true"
			@dragover="dragOverSibling('before', $event)"
			@drop="dropOnSibling('before', $event)"
		></div>
		<div
			v-if="!readOnly"
			class="tree-node__drop-zone tree-node__drop-zone--after"
			aria-hidden="true"
			@dragover="dragOverSibling('after', $event)"
			@drop="dropOnSibling('after', $event)"
		></div>
		<div class="tree-node__body">
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
						:presentationMode="presentationMode"
						:editorLayout="editorLayout"
						:isLeafNew="isLeafNew"
						:isLeafValid="isLeafValid"
						@remove="api?.removeNode(child.id)"
						@operator="api?.setOperator(child.id, $event)"
					>
						<template #default="p"><slot v-bind="p" /></template>
						<template #leaf="p"><slot name="leaf" v-bind="p" /></template>
						<template v-if="api?.hasSummarySlot?.value" #leaf-summary="p">
							<slot name="leaf-summary" v-bind="p" />
						</template>
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
						:presentationMode="presentationMode"
						:editorLayout="editorLayout"
						:isLeafNew="isLeafNew"
						:isLeafValid="isLeafValid"
						@remove="api?.removeNode(child.id)"
						@operator="api?.setOperator(child.id, $event)"
					>
						<template #default="p"><slot v-bind="p" /></template>
						<template #leaf="p"><slot name="leaf" v-bind="p" /></template>
						<template v-if="api?.hasSummarySlot?.value" #leaf-summary="p">
							<slot name="leaf-summary" v-bind="p" />
						</template>
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
				:presentationMode="presentationMode"
				:editorLayout="editorLayout"
				:isLeafNew="isLeafNew"
				:isLeafValid="isLeafValid"
				@remove="$emit('remove')"
			>
				<template #default="p"><slot v-bind="p" /></template>
				<template #leaf="p"><slot name="leaf" v-bind="p" /></template>
				<template v-if="api?.hasSummarySlot?.value" #leaf-summary="p"
					><slot name="leaf-summary" v-bind="p"
				/></template>
			</TreeBuilderLeaf>
		</div>
	</div>
</template>

<style scoped>
.tree-node {
	position: relative;
	width: 100%;
	min-width: 0;
}
.tree-node__body {
	min-width: 0;
	width: 100%;
}
.tree-node__drop-zone {
	position: absolute;
	z-index: 4;
	right: 0;
	left: 0;
	height: 14px;
	background: transparent;
	pointer-events: none;
}
.tree-node__drop-zone--before {
	top: -7px;
}
.tree-node__drop-zone--after {
	bottom: -7px;
}
.tree-node.is-tree-drag-active:not(.is-drag-source) > .tree-node__drop-zone {
	pointer-events: auto;
}
.tree-node[draggable="true"] {
	cursor: grab;
}
.tree-node.is-dragging {
	cursor: grabbing;
	opacity: 0.82;
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
