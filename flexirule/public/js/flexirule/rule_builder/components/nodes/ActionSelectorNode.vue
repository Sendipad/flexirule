<script setup>
import { ref, computed } from "vue";
import { Handle, Position } from "@vue-flow/core";
import { getOperationOptions, isTerminalAction } from "../../../core/contracts";
import { useStore } from "../../stores";
import { mapActionTypeToNodeType } from "../../composables/useActionTypeMapper";
import ActionZone from "../ActionZone.vue";

const props = defineProps(["data", "label", "id", "selected", "sourcePosition", "targetPosition"]);
const store = useStore();

const isHorizontal = computed(() => store.settings?.layout_direction !== "Top to Bottom");

const targetPos = computed(
	() => props.targetPosition || (isHorizontal.value ? Position.Left : Position.Top)
);
const sourcePos = computed(
	() => props.sourcePosition || (isHorizontal.value ? Position.Right : Position.Bottom)
);

const selectedPreset = ref({
	action_type: "Process",
	operation: null,
	process_name: null,
	selected_label: "Process",
});
const customLabel = ref("");

function onActionSelect(item) {
	selectedPreset.value = {
		action_type: item.action_type || "Process",
		operation: item.operation || null,
		process_name: item.process_name || null,
		selected_label: item.label || item.value || "Process",
	};
}

function onPaste() {
	// ActionSelectorNode currently doesn't directly support paste triggering within the card,
	// but we could implement it by emitting insert-node if needed.
	// For now, we follow the existing pattern where paste is mainly for edge insertion.
}

function onCreate() {
	const nodeIndex = store.nodes.findIndex((n) => n.id === props.id);

	if (nodeIndex === -1) return;

	const action_type = selectedPreset.value.action_type || "Process";
	const label =
		customLabel.value ||
		selectedPreset.value.operation ||
		selectedPreset.value.selected_label ||
		action_type;
	const nodeType = mapActionTypeToNodeType(action_type);
	const node = store.nodes[nodeIndex];
	if (!node) return;

	const nodeData = store.get_default_node_data(action_type.toLowerCase(), label);
	const suggestedParentId = node.data?.suggested_parent_id;
	const suggestedSourceHandle = node.data?.suggested_source_handle || "default";

	// Pre-fill process/operation data from selected preset
	if (selectedPreset.value.operation) {
		nodeData.operation = selectedPreset.value.operation;
	}
	if (selectedPreset.value.process_name) {
		nodeData.process_name = selectedPreset.value.process_name;
	}
	if (action_type === "Process" && nodeData.operation && !nodeData.process_name) {
		const matches = getOperationOptions("Process", {})
			.filter((op) => op.value === nodeData.operation && op.process_name)
			.map((op) => op.process_name);
		const unique = [...new Set(matches)];
		if (unique.length === 1) {
			nodeData.process_name = unique[0];
		}
	}

	// Upgrade the node
	store.nodes[nodeIndex].type = nodeType;
	store.nodes[nodeIndex].label = label;
	store.nodes[nodeIndex].data = {
		...nodeData,
		action_id: props.id,
		action_label: label,
		next_step_if_true: node.data?.next_step_if_true || nodeData.next_step_if_true,
		next_step_if_false: node.data?.next_step_if_false || nodeData.next_step_if_false,
		suggested_parent_id: null,
		suggested_source_handle: null,
	};

	if (suggestedParentId) {
		const edgeId = `e-${suggestedParentId}-${props.id}-${suggestedSourceHandle}`;
		const hasIncoming = store.edges.some((edge) => edge.target === props.id);
		if (!hasIncoming) {
			store.edges.push({
				id: edgeId,
				source: suggestedParentId,
				target: props.id,
				sourceHandle: suggestedSourceHandle,
				animated: suggestedParentId === "root",
			});
		}
	}

	// If the chosen node is terminal, remove any outgoing edges that might have existed
	if (isTerminalAction(action_type)) {
		store.edges = store.edges.filter((edge) => edge.source !== props.id);
		store.nodes[nodeIndex].data.next_step_if_true = null;
		store.nodes[nodeIndex].data.next_step_if_false = null;
	}

	store.select(props.id);
	store.show_sidebar = true;
	store.touch_node(props.id);
	store.mark_dirty();
}

function deleteNode() {
	frappe.confirm(__("Delete this node?"), () => store.delete_node(props.id));
}
</script>

<template>
	<div
		class="action-selector-card"
		:class="{
			selected: selected,
			'is-vertical': !isHorizontal,
		}"
	>
		<Handle type="target" :position="targetPos" class="handle-target" />

		<div class="node-header">
			<i class="fa fa-plus-circle"></i>
			<span class="header-text">{{ __("New Action") }}</span>
			<button class="delete-btn" @click.stop="deleteNode" v-if="selected">
				<i class="fa fa-trash"></i>
			</button>
		</div>

		<div class="node-body">
			<div class="form-group search-group">
				<label class="small text-muted">{{ __("Action Type") }}</label>
				<div class="search-wrapper">
					<ActionZone
						:placeholder="__('Search actions...')"
						:show-paste="false"
						:auto-focus="false"
						@select="onActionSelect"
						@paste="onPaste"
					/>
					<div v-if="selectedPreset.operation" class="selected-operation-preview">
						<span class="badge-chip">{{ selectedPreset.action_type }}</span>
						<span class="selected-operation-text">
							{{ selectedPreset.operation }}
						</span>
						<span v-if="selectedPreset.process_name" class="selected-process-name">
							({{ selectedPreset.process_name }})
						</span>
					</div>
				</div>
			</div>
			<div class="form-group">
				<label class="small text-muted">{{ __("Label") }}</label>
				<input
					type="text"
					v-model="customLabel"
					class="form-control input-xs"
					:placeholder="__('Enter label...')"
					@keyup.enter="onCreate"
				/>
			</div>
			<button class="btn btn-primary btn-xs btn-block mt-2" @click="onCreate">
				{{ __("Create") }}
			</button>
		</div>

		<div class="node-footer">
			<span class="text-muted small">{{ __("Configure to proceed") }}</span>
		</div>

		<Handle type="source" :position="sourcePos" id="default" class="handle-source" />
	</div>
</template>

<style scoped>
.action-selector-card {
	width: 260px;
	background: #fff;
	border: 2px dashed #d1d8dd;
	border-radius: 8px;
	box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
	position: relative;
	transition: all 0.2s ease;
}

.action-selector-card.selected {
	border-color: var(--primary);
	border-style: solid;
	box-shadow: 0 0 0 2px rgba(var(--primary-rgb), 0.2);
}

.node-header {
	display: flex;
	align-items: center;
	padding: 8px 12px;
	border-bottom: 1px solid #f0f4f7;
	gap: 8px;
	background: #f8f9fa;
	border-radius: 8px 8px 0 0;
}

.node-header i {
	color: var(--primary);
	font-size: 14px;
}

.header-text {
	font-size: 11px;
	font-weight: 700;
	color: #6c757d;
	flex: 1;
}

.delete-btn {
	background: none;
	border: none;
	padding: 2px;
	cursor: pointer;
	color: #adb5bd;
}

.delete-btn:hover {
	color: #dc3545;
}

.node-body {
	padding: 12px;
	display: flex;
	flex-direction: column;
	max-height: 500px;
}

.search-wrapper {
	max-height: 300px;
	display: flex;
	flex-direction: column;
	border: 1px solid #e2e8f0;
	border-radius: 6px;
	padding-bottom: 4px;
}

.search-wrapper :deep(.popover-search) {
	border-bottom: none;
}

.search-wrapper :deep(.popover-body) {
	max-height: 200px;
}

.form-group {
	margin-bottom: 8px;
}

.form-group label {
	display: block;
	margin-bottom: 2px;
}

.selected-operation-preview {
	display: flex;
	align-items: center;
	gap: 6px;
	margin: 6px 8px 0;
	flex-wrap: wrap;
}

.badge-chip {
	background: #eef2ff;
	color: #4338ca;
	border: 1px solid #c7d2fe;
	border-radius: 10px;
	padding: 1px 6px;
	font-size: 10px;
	font-weight: 700;
}

.selected-operation-text {
	font-size: 10px;
	font-weight: 600;
	color: #1f2937;
}

.selected-process-name {
	font-size: 10px;
	color: #6b7280;
}

.node-footer {
	padding: 6px 12px;
	background-color: #f8fcfd;
	border-bottom-left-radius: 8px;
	border-bottom-right-radius: 8px;
	border-top: 1px solid #f0f4f7;
	text-align: center;
}

.handle-target,
.handle-source {
	width: 10px !important;
	height: 10px !important;
	background-color: #fff !important;
	border: 2px solid #d1d8dd !important;
	z-index: 10 !important;
}

.action-selector-card:not(.is-vertical) .handle-target {
	left: -5px !important;
	top: 50% !important;
	transform: translateY(-50%) !important;
}

.action-selector-card:not(.is-vertical) .handle-source {
	right: -5px !important;
	top: 50% !important;
	transform: translateY(-50%) !important;
}

.is-vertical .handle-target {
	top: -5px !important;
	left: 50% !important;
	transform: translateX(-50%) !important;
}

.is-vertical .handle-source {
	bottom: -5px !important;
	left: 50% !important;
	transform: translateX(-50%) !important;
}

.action-selector-card.selected .handle-target,
.action-selector-card.selected .handle-source {
	border-color: var(--primary) !important;
}
</style>
