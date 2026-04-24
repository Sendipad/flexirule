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

const { removeNode } = inject("conditionActions");

function handleRemove() {
	removeNode(props.parentGroup, props.index);
}
</script>

<template>
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
	<div v-else class="text-danger p-2 border rounded">
		{{ __("Unknown condition type") }}
	</div>
</template>
