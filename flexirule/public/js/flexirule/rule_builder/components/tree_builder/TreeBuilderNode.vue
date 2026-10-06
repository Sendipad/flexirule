<script setup>
import { computed, inject, ref } from "vue";
import { isGroupNode } from "./tree_builder_utils.js";

defineOptions({ name: "TreeBuilderNode" });

const props = defineProps({
	node: { type: Object, required: true },
	index: { type: Number, required: true },
	parent: { type: Object, required: true },
	readOnly: { type: Boolean, default: false },
	allowGroups: { type: Boolean, default: true },
	canAddLeaf: { type: Boolean, default: true },
	canAddGroup: { type: Boolean, default: true },
	canDelete: { type: Boolean, default: true },
	canDrag: { type: Boolean, default: true },
	canDrop: { type: Boolean, default: true },
	groupOperators: { type: Array, default: () => ["and", "or"] },
	leafLabel: { type: String, default: __("Condition") },
	groupLabel: { type: String, default: __("Group") },
	operatorLabel: { type: Function, default: (v) => v },
	leafFactory: { type: Function, default: () => ({ type: "leaf" }) },
	activeNodeId: { type: String, default: null },
});

const emit = defineEmits(["remove", "setActive"]);
const actions = inject("treeBuilderActions");
const dragOver = ref(false);

const isGroup = computed(() => isGroupNode(props.node));
const children = computed(() => (isGroup.value ? props.node.children || [] : []));
const isActive = computed(() => props.activeNodeId === props.node.id);

function markActive() {
	emit("setActive", props.node.id);
	actions?.setActiveNodeId?.(props.node.id);
}

function remove() {
	emit("remove");
}

function addLeaf() {
	actions?.addLeaf(props.node);
}

function addGroup() {
	actions?.addGroup(props.node);
}

function handleDragStart(event) {
	if (props.readOnly || !props.canDrag || !actions) return;
	event.stopPropagation();
	actions.beginDrag(props.parent, props.index);
	event.dataTransfer.effectAllowed = "move";
	event.dataTransfer.setData("text/plain", props.node.id || "");
}

function handleDrop() {
	dragOver.value = false;
	if (!actions || !props.canDrop) return;
	if (isGroup.value) actions.dropNode(props.node);
}

function handleGroupDragOver(event) {
	if (!isGroup.value || !props.canDrop) return;
	event.preventDefault();
	event.stopPropagation();
	dragOver.value = true;
}

function handleDragLeave() {
	dragOver.value = false;
}
</script>

<template>
	<div
		class="tree-node"
		:class="{ 'is-group': isGroup, 'drag-over': dragOver, 'is-active': isActive }"
		:draggable="!readOnly && canDrag"
		@click.stop="markActive"
		@dragstart="handleDragStart"
		@dragover="handleGroupDragOver"
		@dragleave="handleDragLeave"
		@drop.prevent.stop="handleDrop"
	>
		<div v-if="isGroup" class="tree-group">
			<div class="tree-group__header">
				<div class="tree-group__logic">
					<button
						v-for="operator in groupOperators"
						:key="operator"
						type="button"
						class="logic-btn"
						:class="{ active: node.operator === operator }"
						:disabled="readOnly"
						@click="node.operator = operator"
					>
						{{ operatorLabel(operator) }}
					</button>
				</div>

				<div v-if="!readOnly" class="tree-group__actions">
					<button
						v-if="canAddLeaf"
						type="button"
						class="fxr-btn fxr-btn--icon"
						:title="__('Add Condition')"
						@click="addLeaf"
					>
						<i class="fa fa-plus"></i>
					</button>
					<button
						v-if="allowGroups && canAddGroup"
						type="button"
						class="fxr-btn fxr-btn--icon"
						:title="__('Add Group')"
						@click="addGroup"
					>
						<i class="fa fa-folder-open-o"></i>
					</button>
					<div class="action-divider"></div>
					<button
						v-if="canDelete"
						type="button"
						class="fxr-btn fxr-btn--icon fxr-btn--danger"
						:title="__('Remove Group')"
						@click="remove"
					>
						<i class="fa fa-times"></i>
					</button>
				</div>
			</div>

			<div class="tree-group__children">
				<div v-if="!children.length" class="tree-group__empty">
					{{ __("Empty group. Add a condition using the + button.") }}
				</div>
				<TreeBuilderNode
					v-for="(child, childIndex) in children"
					:key="child.id"
					:node="child"
					:index="childIndex"
					:parent="node"
					:readOnly="readOnly"
					:allowGroups="allowGroups"
					:canAddLeaf="canAddLeaf"
					:canAddGroup="canAddGroup"
					:canDelete="canDelete"
					:canDrag="canDrag"
					:canDrop="canDrop"
					:groupOperators="groupOperators"
					:leafLabel="leafLabel"
					:groupLabel="groupLabel"
					:operatorLabel="operatorLabel"
					:leafFactory="leafFactory"
					:activeNodeId="activeNodeId"
					@setActive="(id) => emit('setActive', id)"
					@remove="actions?.removeNode(node, childIndex)"
				>
					<template #leaf="slotProps">
						<slot name="leaf" v-bind="slotProps" />
					</template>
				</TreeBuilderNode>
			</div>
		</div>

		<div v-else class="tree-leaf">
			<slot name="leaf" :node="node" :index="index" :parent="parent" />
			<button
				v-if="!readOnly && canDelete"
				type="button"
				class="tree-leaf__remove"
				:title="__('Remove condition')"
				@click="remove"
			>
				<i class="fa fa-trash"></i>
			</button>
		</div>
	</div>
</template>

<style scoped>
.tree-node {
	min-width: 0;
	border-radius: var(--fxr-radius-md);
	transition: box-shadow var(--fxr-transition-fast);
}

.tree-node.is-active {
	box-shadow: 0 0 0 2px var(--fxr-node-accent, var(--fxr-accent));
}

.tree-group {
	padding: var(--fxr-space-3);
	background: var(--fxr-bg-hover);
	border: 1px solid var(--fxr-border-subtle);
	border-radius: var(--fxr-radius-lg);
}

.tree-group.drag-over {
	background: var(--fxr-node-accent-light, var(--fxr-accent-soft));
	box-shadow: inset 0 0 0 2px var(--fxr-node-accent, var(--fxr-accent));
}

.tree-group__header {
	display: flex;
	align-items: center;
	justify-content: space-between;
	gap: var(--fxr-space-2);
	margin-bottom: var(--fxr-space-2);
}

.tree-group__logic {
	display: flex;
	gap: 2px;
	padding: 2px;
	border-radius: var(--fxr-radius-md);
	background: var(--fxr-surface-2);
}

.logic-btn {
	border: 0;
	background: transparent;
	padding: 3px 9px;
	border-radius: var(--fxr-radius-sm);
	font-size: 10px;
	font-weight: 800;
	color: var(--fxr-text-soft);
}

.logic-btn.active {
	background: var(--fxr-node-accent, var(--fxr-accent));
	color: #fff;
}

.tree-group__actions {
	display: flex;
	align-items: center;
	gap: var(--fxr-space-1);
}

.tree-group__children {
	display: flex;
	flex-direction: column;
	gap: var(--fxr-space-2);
}

.tree-group__empty {
	padding: var(--fxr-space-3);
	color: var(--fxr-text-muted);
	font-size: var(--fxr-text-sm);
	text-align: center;
}

.tree-leaf {
	display: grid;
	grid-template-columns: minmax(0, 1fr) auto;
	gap: var(--fxr-space-2);
	align-items: start;
}

.tree-leaf__remove {
	width: 30px;
	height: 30px;
	margin-top: 4px;
	border: 0;
	background: transparent;
	color: var(--fxr-text-danger, #ef4444);
	border-radius: var(--fxr-radius-sm);
	cursor: pointer;
}

.tree-leaf__remove:hover {
	background: var(--fxr-bg-danger);
}

@media (max-width: 768px) {
	.tree-group {
		padding: var(--fxr-space-2);
	}
	.tree-group__header {
		align-items: stretch;
		flex-direction: column;
	}
	.tree-leaf {
		grid-template-columns: minmax(0, 1fr) 30px;
	}
}
</style>
