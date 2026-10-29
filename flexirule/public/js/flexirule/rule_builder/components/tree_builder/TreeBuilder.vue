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
				<button
					v-if="allowCollections"
					type="button"
					class="fxr-btn"
					@click="addCollection()"
				>
					<i class="fa fa-sitemap"></i><span>{{ collectionLabel }}</span>
				</button>
			</div>
		</div>
		<div
			role="tree"
			:aria-label="ariaLabel"
			tabindex="0"
			@keydown="handleTreeKeydown"
			class="tree-builder__content"
			:class="{ 'tree-builder__content--drop-target': rootDragOver }"
			@dragover="onRootDragOver"
			@dragleave="onRootDragLeave"
			@drop="onRootDrop"
		>
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
				:presentationMode="presentationMode"
				:editorLayout="editorLayout"
				:isLeafNew="isLeafNew"
				:isLeafValid="isLeafValid"
				@remove="removeNode(node.id)"
				@operator="setOperator(node.id, $event)"
			>
				<template #default="p"><slot name="leaf" v-bind="p" /></template>
				<template #leaf="p"><slot name="leaf" v-bind="p" /></template>
				<template #leaf-summary="p"><slot name="leaf-summary" v-bind="p" /></template>
				<template #collection="p"><slot name="collection" v-bind="p" /></template>
			</TreeBuilderNode>
		</div>
	</div>
</template>
<script setup>
import { computed, provide, ref, useSlots } from "vue";
import { findNode } from "./tree_builder_utils.mjs";
import {
	getInlinePresentation,
	resolvePresentationMode,
} from "../../controls/inline_presentation_policy.mjs";
import { isInputTarget, matchesShortcut } from "../../utils/keyboard_shortcuts.mjs";
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
	presentationMode: { type: String, default: "hybrid" },
	editorLayout: { type: String, default: "replace" },
	isLeafNew: { type: Function, default: null },
	isLeafValid: { type: Function, default: null },
	canEditRule: { type: Boolean, default: false },
	ariaLabel: { type: String, default: () => __("Condition tree") },
	editShortcut: { type: String, default: "Ctrl+Shift+E" },
});
const emit = defineEmits(["update:modelValue", "change", "validation-error"]);
const slots = useSlots();
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

const resolvedCanEditRule = computed(() => Boolean(props.canEditRule));

const hasSummarySlot = computed(() => Boolean(slots["leaf-summary"]));
provide("treeBuilderContext", {
	...api,
	presentationMode: computed(() => props.presentationMode),
	editorLayout: computed(() => props.editorLayout),
	isLeafNew: computed(() => props.isLeafNew),
	isLeafValid: computed(() => props.isLeafValid),
	canEditRule: resolvedCanEditRule,
	hasSummarySlot,
});
const {
	root,
	operators,
	addLeaf,
	addCollection,
	addGroup,
	removeNode,
	setOperator,
	selectedNodeId,
	focusedNodeId,
	editingNodeId,
	setEditing,
	finishEditing,
} = api;
const operatorLabel = (op) => props.operatorLabel(op);
const visibleNode = (node) => props.visibleNode(node) !== false;
const rootDragOver = ref(false);

function getLeafState(node) {
	const isNew = api.isTransientNew?.(node.id)
		? true
		: typeof props.isLeafNew === "function"
			? Boolean(props.isLeafNew(node))
			: typeof api.isLeafNew?.value === "function"
				? Boolean(api.isLeafNew.value(node))
				: Boolean(node?.isNew);
	const isValid =
		typeof props.isLeafValid === "function"
			? Boolean(props.isLeafValid(node))
			: typeof api.isLeafValid?.value === "function"
				? Boolean(api.isLeafValid.value(node))
				: node?.isValid !== false;
	return { isNew, isValid };
}

function handleTreeKeydown(event) {
	if (event.defaultPrevented || event.isComposing) return;
	const target = event.target;
	const nodeElement = target?.closest?.("[data-node-id]");
	const nodeId = nodeElement?.getAttribute("data-node-id") || null;

	if (matchesShortcut(event, props.editShortcut)) {
		if (props.readOnly && !resolvedCanEditRule.value) return;
		const activeId =
			nodeId || editingNodeId.value || focusedNodeId.value || selectedNodeId.value;
		const node = activeId ? findNode(root, activeId) : null;
		if (!node || node.type !== "leaf" || !hasSummarySlot.value) return;
		const mode = resolvePresentationMode(props.presentationMode);
		if (mode === "form") return;
		const { isNew, isValid } = getLeafState(node);
		if (editingNodeId.value === activeId) {
			if (mode === "hybrid" && !isValid) return;
			event.preventDefault();
			event.stopPropagation();
			finishEditing(activeId);
		} else {
			const policy = getInlinePresentation({
				mode,
				isNew,
				isValid,
				isEditing: false,
				readOnly: false,
				hasSummary: true,
			});
			if (!policy.canToggle) return;
			event.preventDefault();
			event.stopPropagation();
			setEditing(activeId);
		}
		return;
	}

	if (isInputTarget(target) || target?.closest?.("button, a, [role='button']")) return;
	if (event.altKey || event.ctrlKey || event.metaKey || event.shiftKey) return;
	const treeItems = Array.from(event.currentTarget.querySelectorAll(".tree-node[data-node-id]"));
	if (!treeItems.length) return;
	const currentIndex = nodeElement
		? treeItems.indexOf(nodeElement)
		: treeItems.findIndex(
				(element) => element.getAttribute("data-node-id") === focusedNodeId.value
			);
	let nextIndex = null;
	if (event.key === "ArrowDown") {
		nextIndex = currentIndex < 0 ? 0 : Math.min(treeItems.length - 1, currentIndex + 1);
	} else if (event.key === "ArrowUp") {
		nextIndex = currentIndex < 0 ? treeItems.length - 1 : Math.max(0, currentIndex - 1);
	}
	else if (event.key === "Home") nextIndex = 0;
	else if (event.key === "End") nextIndex = treeItems.length - 1;
	else if (event.key === " " || event.key === "Spacebar") {
		const activeId = nodeId || focusedNodeId.value || selectedNodeId.value;
		if (!activeId) return;
		event.preventDefault();
		event.stopPropagation();
		api.selectNode(activeId);
		api.focusNode(activeId);
		return;
	}
	if (nextIndex === null) return;
	const nextElement = treeItems[nextIndex];
	const nextId = nextElement?.getAttribute("data-node-id");
	if (!nextId) return;
	event.preventDefault();
	event.stopPropagation();
	api.focusNode(nextId);
	nextElement.focus({ preventScroll: true });
}

function onRootDragOver(e) {
	const draggedId = api.dragState.nodeId || e.dataTransfer?.getData("text/plain");
	if (props.readOnly || !draggedId || !api.canMove(draggedId, root.id)) return;
	e.preventDefault();
	if (e.dataTransfer) e.dataTransfer.dropEffect = "move";
	rootDragOver.value = true;
}

function onRootDragLeave(e) {
	if (e.relatedTarget instanceof Node && e.currentTarget.contains(e.relatedTarget)) return;
	rootDragOver.value = false;
}

function onRootDrop(e) {
	e.preventDefault();
	e.stopPropagation();
	rootDragOver.value = false;
	const draggedId = api.dragState.nodeId || e.dataTransfer?.getData("text/plain");
	if (draggedId && api.canMove(draggedId, root.id)) {
		if (api.dragState.nodeId) api.dropNode(root.id);
		else api.moveNode(draggedId, root.id);
	}
	api.endDrag();
}

defineExpose({ ...api });
</script>
<style scoped>
.tree-builder {
	display: flex;
	flex-direction: column;
	gap: var(--fxr-space-1);
	width: 100%;
	min-width: 0;
	padding: var(--fxr-space-1);
	background: var(--fxr-bg-card, var(--fxr-surface));
	border: 1px solid var(--fxr-border-subtle);
	border-radius: var(--fxr-radius-lg);
}
.tree-builder__header {
	display: flex;
	align-items: center;
	justify-content: space-between;
	gap: var(--fxr-space-2);
	padding-bottom: var(--fxr-space-1);
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
	padding: 3px 8px;
	border-radius: var(--fxr-radius-sm);
	font-size: var(--fxr-text-xs);
	font-weight: var(--fxr-weight-bold, 700);
	color: var(--fxr-text-soft);
	cursor: pointer;
	transition: background-color var(--fxr-transition-fast), color var(--fxr-transition-fast);
}
.logic-btn:hover:not(.active):not(:disabled) {
	background: var(--fxr-bg-muted);
	color: var(--fxr-text-strong);
}
.logic-btn:disabled {
	cursor: default;
	opacity: 0.7;
}
.logic-btn.active {
	background: var(--fxr-node-accent, var(--fxr-accent));
	color: #fff;
	box-shadow: var(--fxr-shadow-sm);
}
.tree-builder__content {
	display: flex;
	flex-direction: column;
	gap: 2px;
	width: 100%;
	min-width: 0;
	min-height: 32px;
	padding: 0;
	border-radius: var(--fxr-radius-md);
	overflow: visible;
	transition: background-color var(--fxr-transition-fast), box-shadow var(--fxr-transition-fast);
}
.tree-builder__content--drop-target {
	background: var(--fxr-node-accent-light, var(--fxr-accent-soft));
	box-shadow: inset 0 0 0 2px var(--fxr-node-accent, var(--fxr-accent));
}
.tree-builder__empty {
	display: flex;
	align-items: center;
	justify-content: center;
	gap: var(--fxr-space-2);
	min-height: 48px;
	padding: var(--fxr-space-2);
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
