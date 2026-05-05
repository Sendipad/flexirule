<script setup>
import { inject, ref } from "vue";
/**
 * ConditionGroupUI - Nested group editor with AND/OR toggle
 */
import ConditionNode from "./ConditionNode.vue";

const props = defineProps({
	group: { type: Object, required: true },
	docFields: { type: Array, default: () => [] },
	readOnly: { type: Boolean, default: false },
});

const emit = defineEmits(["remove"]);

const { addCondition, addGroup, addCollection, removeNode, onDrop } = inject("conditionActions");

const isDragOver = ref(false);

function handleDrop(e) {
	isDragOver.value = false;
	onDrop(props.group);
}
</script>

<template>
	<div
		class="condition-group-ui"
		:class="{ 'drag-over': isDragOver }"
		@dragover.prevent.stop="isDragOver = true"
		@dragleave.stop="isDragOver = false"
		@drop.prevent.stop="handleDrop"
	>
		<!-- Header -->
		<div class="group-header">
			<div class="logic-toggle small">
				<button
					type="button"
					class="logic-btn"
					:class="{ active: group.op === 'and' }"
					@click="group.op = 'and'"
					:disabled="readOnly"
				>
					{{ __("AND") }}
				</button>
				<button
					type="button"
					class="logic-btn"
					:class="{ active: group.op === 'or' }"
					@click="group.op = 'or'"
					:disabled="readOnly"
				>
					{{ __("OR") }}
				</button>
			</div>

			<div class="group-actions" v-if="!readOnly">
				<button
					class="fr-btn fr-btn--icon"
					@click="addCondition(group)"
					:title="__('Add Condition')"
				>
					<i class="fa fa-plus"></i>
				</button>
				<button
					class="fr-btn fr-btn--icon"
					@click="addGroup(group)"
					:title="__('Add Group')"
				>
					<i class="fa fa-folder-open-o"></i>
				</button>
				<button
					class="fr-btn fr-btn--icon"
					@click="addCollection(group)"
					:title="__('Add Collection')"
				>
					<i class="fa fa-table"></i>
				</button>
				<div class="action-divider"></div>
				<button
					class="fr-btn fr-btn--icon fr-btn--danger"
					@click="emit('remove')"
					:title="__('Remove Group')"
				>
					<i class="fa fa-times"></i>
				</button>
			</div>
		</div>

		<!-- Children -->
		<div class="group-content">
			<div v-if="!group.conditions?.length" class="empty-group-text">
				{{ __("Empty group. Add conditions using buttons above.") }}
			</div>
			<div v-for="(node, idx) in group.conditions" :key="node.id || idx" class="node-wrapper">
				<ConditionNode
					:node="node"
					:index="idx"
					:parentGroup="group"
					:docFields="docFields"
					:readOnly="readOnly"
				/>
			</div>
			<!-- Spacer for easier dropping -->
			<div class="group-drop-spacer" v-if="!readOnly"></div>
		</div>
	</div>
</template>

<style scoped>
.condition-group-ui {
	background: var(--fr-bg-hover);
	border: 1px solid var(--fr-border);
	border-radius: var(--fr-radius-lg);
	padding: var(--fr-space-6);
}

.group-header {
	display: flex;
	justify-content: space-between;
	align-items: center;
	margin-bottom: var(--fr-space-6);
}

.logic-toggle.small {
	background: var(--fr-border);
	padding: var(--fr-space-1);
	border-radius: var(--fr-radius-md);
	display: flex;
}

.logic-btn {
	border: none;
	background: transparent;
	padding: var(--fr-space-2) var(--fr-space-4);
	border-radius: var(--fr-radius-sm);
	font-size: var(--fr-text-xs);
	font-weight: var(--fr-weight-bold);
	color: var(--fr-text-muted);
	transition: all var(--fr-transition-fast);
	cursor: pointer;
}

.logic-btn.active {
	background: var(--fr-bg-card);
	color: var(--fr-accent);
	box-shadow: var(--fr-shadow-sm);
}

.condition-group-ui.drag-over {
	border-color: var(--fr-accent);
	background: var(--fr-accent-light);
	box-shadow: inset 0 0 0 2px var(--fr-accent);
}

.group-actions {
	display: flex;
	gap: var(--fr-space-2);
	align-items: center;
}

.group-actions .fr-btn--icon {
	border: 1px solid var(--fr-border);
	background: var(--fr-bg-card);
}

.group-actions .fr-btn--icon:hover {
	background: var(--fr-bg-muted);
	color: var(--fr-accent);
	border-color: var(--fr-border-strong);
}

.group-actions .fr-btn--icon.fr-btn--danger:hover {
	background: var(--fr-bg-danger);
	color: var(--fr-text-danger);
	border-color: var(--fr-border-danger);
}

.action-divider {
	width: 1px;
	height: 16px;
	background: var(--fr-border);
	margin: 0 var(--fr-space-2);
}

.group-content {
	padding-inline-start: var(--fr-space-6);
	border-inline-start: 2px solid var(--fr-border);
	display: flex;
	flex-direction: column;
	gap: var(--fr-space-4);
}

.empty-group-text {
	font-size: var(--fr-text-sm);
	color: var(--fr-text-muted);
	font-style: italic;
	padding: var(--fr-space-4) 0;
}

.node-wrapper {
	margin-bottom: var(--fr-space-2);
}

.group-drop-spacer {
	height: 20px;
	margin-top: var(--fr-space-2);
}
</style>
