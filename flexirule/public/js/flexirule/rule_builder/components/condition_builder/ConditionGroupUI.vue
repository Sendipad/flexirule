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
					class="fxr-btn fxr-btn--icon"
					@click="addCondition(group)"
					:title="__('Add Condition')"
				>
					<i class="fa fa-plus"></i>
				</button>
				<button
					class="fxr-btn fxr-btn--icon"
					@click="addGroup(group)"
					:title="__('Add Group')"
				>
					<i class="fa fa-folder-open-o"></i>
				</button>
				<button
					class="fxr-btn fxr-btn--icon"
					@click="addCollection(group)"
					:title="__('Add Collection')"
				>
					<i class="fa fa-table"></i>
				</button>
				<div class="action-divider"></div>
				<button
					class="fxr-btn fxr-btn--icon fxr-btn--danger"
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
	background: var(--fxr-bg-hover);
	border: 1px solid var(--fxr-border);
	border-radius: var(--fxr-radius-lg);
	padding: var(--fxr-space-3);
}

.group-header {
	display: flex;
	justify-content: space-between;
	align-items: center;
	margin-bottom: var(--fxr-space-3);
}

.logic-toggle.small {
	background: var(--fxr-border);
	padding: var(--fxr-space-1);
	border-radius: var(--fxr-radius-md);
	display: flex;
}

.logic-btn {
	border: none;
	background: transparent;
	padding: var(--fxr-space-2) var(--fxr-space-4);
	border-radius: var(--fxr-radius-sm);
	font-size: var(--fxr-text-xs);
	font-weight: var(--fxr-weight-bold);
	color: var(--fxr-text-muted);
	transition: all var(--fxr-transition-fast);
	cursor: pointer;
}

.logic-btn.active {
	background: var(--fxr-bg-card);
	color: var(--fxr-node-accent, var(--fxr-accent));
	box-shadow: var(--fxr-shadow-sm);
}

.condition-group-ui.drag-over {
	border-color: var(--fxr-node-accent, var(--fxr-accent));
	background: var(--fxr-node-accent-light, var(--fxr-accent-light));
	box-shadow: inset 0 0 0 2px var(--fxr-node-accent, var(--fxr-accent));
}

.group-actions {
	display: flex;
	gap: var(--fxr-space-2);
	align-items: center;
}

.group-actions .fxr-btn--icon {
	border: 1px solid var(--fxr-border);
	background: var(--fxr-surface);
	color: var(--fxr-text-secondary);
	transition: all var(--fxr-transition-fast);
}

.group-actions .fxr-btn--icon:hover,
.group-actions .fxr-btn--icon:focus-visible {
	background: var(--fxr-surface-2);
	color: var(--fxr-text-strong);
	border-color: var(--fxr-border-strong);
}

.group-actions .fxr-btn--icon.fxr-btn--danger:hover,
.group-actions .fxr-btn--icon.fxr-btn--danger:focus-visible {
	background: var(--fxr-bg-danger);
	color: var(--fxr-text-danger);
	border-color: var(--fxr-border-danger);
}

.action-divider {
	width: 1px;
	height: 16px;
	background: var(--fxr-border);
	margin: 0 var(--fxr-space-2);
}

.group-content {
	padding-inline-start: var(--fxr-space-4);
	border-inline-start: 2px solid var(--fxr-border);
	display: flex;
	flex-direction: column;
	gap: var(--fxr-space-2);
}

.empty-group-text {
	font-size: var(--fxr-text-xs);
	color: var(--fxr-text-muted);
	font-style: italic;
	padding: var(--fxr-space-2) 0;
}

.node-wrapper {
	margin-bottom: 0;
}

.group-drop-spacer {
	height: 12px;
	margin-top: var(--fxr-space-1);
}

@media (max-width: 768px) {
	.condition-group-ui {
		padding: var(--fxr-space-2);
	}

	.group-header {
		flex-direction: column;
		align-items: stretch;
		gap: var(--fxr-space-4);
	}

	.logic-toggle.small {
		width: 100%;
	}

	.logic-btn {
		flex: 1;
		height: 44px;
		display: flex;
		align-items: center;
		justify-content: center;
	}

	.group-actions {
		flex-wrap: wrap;
		gap: var(--fxr-space-2);
		justify-content: flex-start;
	}

	.group-actions .fxr-btn--icon {
		flex: 1;
		min-width: 44px;
		height: 44px;
		justify-content: center;
	}

	.group-actions .fxr-btn--icon i {
		font-size: 16px;
	}

	.action-divider {
		display: none;
	}

	.group-content {
		padding-inline-start: var(--fxr-space-3);
	}
}
</style>
