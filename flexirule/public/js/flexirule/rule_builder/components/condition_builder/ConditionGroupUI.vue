<script setup>
import { inject } from "vue";
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

const { addCondition, addGroup, addCollection, removeNode } = inject("conditionActions");
</script>

<template>
	<div class="condition-group-ui">
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
					class="icon-action"
					@click="addCondition(group)"
					:title="__('Add Condition')"
				>
					<i class="fa fa-plus"></i>
				</button>
				<button class="icon-action" @click="addGroup(group)" :title="__('Add Group')">
					<i class="fa fa-folder-open-o"></i>
				</button>
				<button
					class="icon-action"
					@click="addCollection(group)"
					:title="__('Add Collection')"
				>
					<i class="fa fa-table"></i>
				</button>
				<div class="action-divider"></div>
				<button
					class="icon-action danger"
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
		</div>
	</div>
</template>

<style scoped>
.condition-group-ui {
	background: rgba(248, 250, 252, 0.5);
	border: 1px solid #e2e8f0;
	border-radius: 12px;
	padding: 12px;
}

.group-header {
	display: flex;
	justify-content: space-between;
	align-items: center;
	margin-bottom: 12px;
}

.logic-toggle.small {
	background: #f1f5f9;
	padding: 2px;
}

.logic-toggle.small .logic-btn {
	padding: 3px 10px;
	font-size: 10px;
}

.group-actions {
	display: flex;
	gap: 4px;
	align-items: center;
}

.icon-action {
	width: 26px;
	height: 26px;
	border-radius: 6px;
	border: 1px solid #e2e8f0;
	background: white;
	color: #64748b;
	display: flex;
	align-items: center;
	justify-content: center;
	cursor: pointer;
	font-size: 11px;
	transition: all 0.2s;
}

.icon-action:hover {
	background: #f1f5f9;
	color: var(--primary);
	border-color: #cbd5e1;
}

.icon-action.danger:hover {
	background: #fee2e2;
	color: #ef4444;
	border-color: #fecaca;
}

.action-divider {
	width: 1px;
	height: 16px;
	background: #e2e8f0;
	margin: 0 4px;
}

.group-content {
	padding-left: 16px;
	border-left: 2px solid #e2e8f0;
	display: flex;
	flex-direction: column;
	gap: 8px;
}

.empty-group-text {
	font-size: 11px;
	color: #94a3b8;
	font-style: italic;
	padding: 8px 0;
}

.node-wrapper {
	margin-bottom: 4px;
}
</style>
