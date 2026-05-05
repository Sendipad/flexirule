<script setup>
import { inject } from "vue";
/**
 * ConditionNode - Routes to correct component based on node type
 */
import SimpleCondition from "./SimpleCondition.vue";
import ConditionGroupUI from "./ConditionGroupUI.vue";
import CollectionUI from "./CollectionUI.vue";

const props = defineProps({
	node: { type: Object, required: true },
	index: { type: Number, required: true },
	parentGroup: { type: Object, required: true },
	docFields: { type: Array, default: () => [] },
	readOnly: { type: Boolean, default: false },
});

const { removeNode, onDragStart } = inject("conditionActions");

function handleRemove() {
	removeNode(props.parentGroup, props.index);
}

function handleDragStart(e) {
	// CRITICAL: Stop propagation so parent ConditionNode wrappers
	// don't overwrite dragInfo with their own (parent group) data.
	// Without this, dragging a child condition inside a group causes
	// the group itself to be registered as the drag source.
	e.stopPropagation();
	onDragStart(props.node, props.parentGroup, props.index);
	e.dataTransfer.effectAllowed = "move";
	e.dataTransfer.setData("text/plain", props.node.id || "");
}
</script>

<template>
	<div class="condition-node-draggable" draggable="true" @dragstart="handleDragStart">
		<!-- Leaf Condition: has left operand -->
		<SimpleCondition
			v-if="node.left"
			:node="node"
			:docFields="docFields"
			:readOnly="readOnly"
			@remove="handleRemove"
		/>

		<!-- Nested Group: has conditions array, no where -->
		<ConditionGroupUI
			v-else-if="node.conditions && !node.where"
			:group="node"
			:docFields="docFields"
			:readOnly="readOnly"
			@remove="handleRemove"
		/>

		<!-- Collection: has where clause -->
		<CollectionUI
			v-else-if="node.where"
			:node="node"
			:docFields="docFields"
			:readOnly="readOnly"
			@remove="handleRemove"
		/>

		<!-- Fallback for unknown node types -->
		<div v-else class="unknown-node">
			{{ __("Unknown condition type") }}
		</div>
	</div>
</template>

<style scoped>
.condition-node-draggable {
	cursor: grab;
	transition: opacity var(--fr-transition-fast);
}

.condition-node-draggable:active {
	cursor: grabbing;
}

.condition-node-draggable[draggable="true"]:hover {
	opacity: 0.9;
}

.unknown-node {
	padding: var(--fr-space-2);
	border: 1px solid var(--fr-border-danger);
	border-radius: var(--fr-radius-md);
	background: var(--fr-bg-danger);
	color: var(--fr-text-danger);
	font-size: var(--fr-text-sm);
}
</style>
