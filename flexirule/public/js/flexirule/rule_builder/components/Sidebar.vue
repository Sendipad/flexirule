<template>
	<div class="rule-sidebar fxr-accent-scope">
		<header class="sidebar-header">
			<div class="header-main">
				<div
					class="header-icon"
					v-if="actionPresentation"
					:style="{
						background: actionPresentation.background,
						color: actionPresentation.color,
					}"
				>
					<i :class="actionPresentation.icon"></i>
				</div>
				<h4 class="truncate">{{ sidebar_title }}</h4>
			</div>
			<button class="btn-close-subtle" @click="$emit('close')" :title="__('Close Sidebar')">
				<i class="fa fa-times"></i>
			</button>
		</header>

		<div class="sidebar-content v2-scrollbar" v-if="selectedNode">
			<!-- Validation Errors -->
			<div v-if="store.validation_errors?.length" class="sidebar-errors-container">
				<div v-for="(err, idx) in store.validation_errors" :key="idx" class="error-item">
					<i class="fa fa-exclamation-triangle"></i>
					<span>{{ err }}</span>
				</div>
			</div>

			<!-- Start Node: Keep existing behavior -->
			<template v-if="selectedNode.type === 'start'">
				<div class="config-section-card">
					<StartNodeProperties
						:nodeData="selectedNode.data"
						:readOnly="store.is_read_only"
						@update:field="update_start_field"
						@open:conditions="open_condition_dialog"
					/>
				</div>
			</template>

			<!-- Action Nodes: DocField-driven rendering -->
			<template v-else>
				<div v-if="selectedNode.type === 'selector'" class="selector-empty-state">
					<i class="fa fa-mouse-pointer opacity-20 mb-3" style="font-size: 32px"></i>
					<p class="text-muted small">
						{{ __("Choose an action type on the node card to continue.") }}
					</p>
				</div>

				<!-- Quick Action Button (Shows if Dialog mode) -->
				<div
					class="sidebar-dialog-trigger"
					v-if="
						isConfigurable &&
						selectedNode.type !== 'selector' &&
						store.settings?.action_config_mode === 'Dialog'
					"
				>
					<button class="fxr-btn fxr-btn--primary w-100" @click="open_config_dialog">
						<i class="fa fa-cog"></i> {{ __("Open Full Editor") }}
					</button>
				</div>

				<!-- Inline Properties (Shows if Sidebar mode) -->
				<div
					class="inline-properties-wrapper"
					v-if="
						selectedNode.type !== 'selector' &&
						(store.settings?.action_config_mode === 'Sidebar' ||
							!store.settings?.action_config_mode)
					"
				>
					<ActionFieldProperties
						:nodeData="selectedNode.data"
						:readOnly="store.is_read_only"
						@update:field="update_action_field"
						@open:conditions="open_condition_dialog"
						@open:config="open_config_dialog"
					/>
				</div>

				<!-- Delete Button -->
				<div class="sidebar-footer" v-if="!store.is_read_only">
					<button class="fxr-btn text-danger w-100" @click="delete_node">
						<i class="fa fa-trash-o"></i> {{ __("Delete Node") }}
					</button>
				</div>
			</template>
		</div>
	</div>
</template>

<script setup>
import { computed, onMounted } from "vue";
import { useRuleStore, useGraphStore, useUIStore } from "../stores";
import ActionFieldProperties from "./ActionFieldProperties.vue";
import StartNodeProperties from "./StartNodeProperties.vue";
import { getContract, getActionPresentation } from "../../core/contracts";
import { mapActionTypeToNodeType } from "../composables/useActionTypeMapper";

// Ensure ProcessConfigurator is loaded
import "../../core/ProcessConfigurator.js";

const emit = defineEmits(["close"]);
const ruleStore = useRuleStore();
const graphStore = useGraphStore();
const uiStore = useUIStore();
// Legacy support for remaining store. calls
const store = uiStore;

// Selected node from store - find the original reference for reactivity
const selectedNode = computed(() => {
	const id = uiStore.selected_id;
	if (!id) return null;
	return (graphStore.nodes || []).find((el) => el.id === id);
});

// Sidebar title
const sidebar_title = computed(() => {
	if (!selectedNode.value) return __("Properties");
	const data = selectedNode.value.data;
	if (data?.action_type === "Stop") {
		return data.operation === "Error" ? __("Raise Error") : __("Stop Flow");
	}
	if (data?.action_label) return data.action_label;
	if (data?.action_type) return __(data.action_type);
	return selectedNode.value.label || __("Properties");
});

const actionPresentation = computed(() => {
	const type = selectedNode.value?.data?.action_type || selectedNode.value?.type;
	return getActionPresentation(type);
});

// Check if node is configurable via modal
const isConfigurable = computed(() => {
	const type = selectedNode.value?.data?.action_type || selectedNode.value?.type;
	if (!type) return false;
	const contract = getContract(type);
	return contract?.configurable === true;
});

function update_start_field(fieldname, value) {
	if (!selectedNode.value?.data) return;
	selectedNode.value.data[fieldname] = value;
	graphStore.touch_node(selectedNode.value.id);
	ruleStore.mark_dirty();
}

function update_action_field(fieldname, value) {
	if (!selectedNode.value?.data) return;

	// Special handling for certain fields
	if (fieldname === "action_label") {
		selectedNode.value.label = value;
	}

	// Handle next_step fields - update edges
	if (fieldname === "next_step_if_true" || fieldname === "next_step_if_false") {
		update_edge(fieldname, value);
	}

	// Handle process_name change - reset operation
	if (fieldname === "process_name" && selectedNode.value.data.process_name !== value) {
		selectedNode.value.data.operation = null;
		selectedNode.value.data.config = null;
	}

	// Handle operation change - reset config
	if (fieldname === "operation" && selectedNode.value.data.operation !== value) {
		selectedNode.value.data.config = null;
	}

	// Handle action_type change - update node type
	if (fieldname === "action_type" && selectedNode.value.data.action_type !== value) {
		selectedNode.value.type = map_action_type(value);
	}

	const oldValue = selectedNode.value.data[fieldname];
	selectedNode.value.data[fieldname] = value;

	store.touch_node(selectedNode.value.id);
	store.mark_dirty();
}

function map_action_type(actionType) {
	return mapActionTypeToNodeType(actionType);
}

function update_edge(field, newTarget) {
	const nodeId = selectedNode.value.id;
	const handleType =
		field === "next_step_if_true"
			? selectedNode.value.data?.action_type === "Condition"
				? "true"
				: "default"
			: "false";

	// Remove existing edge
	graphStore.edges = graphStore.edges.filter(
		(el) => !(el.source === nodeId && el.sourceHandle === handleType)
	);

	// Add new edge if target specified
	if (newTarget) {
		graphStore.edges.push({
			id: `e-${nodeId}-${newTarget}-${handleType}`,
			source: nodeId,
			target: newTarget,
			sourceHandle: handleType,
		});
	}
}

function delete_node() {
	if (selectedNode.value) {
		graphStore.delete_node(selectedNode.value.id);
		emit("close");
	}
}

async function open_config_dialog() {
	uiStore.open_config_modal("setup");
}

async function open_condition_dialog() {
	uiStore.open_config_modal("logic");
}

// Load Rule Action metadata on mount
onMounted(async () => {
	if (!frappe.get_meta("Rule Action")) {
		await frappe.model.with_doctype("Rule Action");
	}
});
</script>

<style scoped>
.rule-sidebar {
	width: 100%;
	height: 100%;
	display: flex;
	flex-direction: column;
	background: var(--fr-bg-surface);
}

.sidebar-header {
	display: flex;
	align-items: center;
	justify-content: space-between;
	padding: 16px 20px;
	border-bottom: 1px solid var(--fr-border);
}

.header-main {
	display: flex;
	align-items: center;
	gap: 12px;
	min-width: 0;
}

.header-icon {
	width: 28px;
	height: 28px;
	border-radius: 6px;
	display: flex;
	align-items: center;
	justify-content: center;
	font-size: 14px;
	flex-shrink: 0;
}

.sidebar-header h4 {
	margin: 0;
	font-size: 14px;
	font-weight: 700;
	color: var(--fr-text);
}

.btn-close-subtle {
	width: 24px;
	height: 24px;
	display: flex;
	align-items: center;
	justify-content: center;
	background: transparent;
	border: none;
	color: var(--fr-text-muted);
	border-radius: 4px;
	cursor: pointer;
	transition: all 0.15s;
}

.btn-close-subtle:hover {
	background: var(--fr-bg-muted);
	color: var(--fr-text);
}

.sidebar-content {
	flex: 1;
	padding: 20px;
	overflow-y: auto;
	display: flex;
	flex-direction: column;
	gap: 20px;
}

.sidebar-errors-container {
	display: flex;
	flex-direction: column;
	gap: 8px;
	background: #fef2f2;
	border: 1px solid #fecaca;
	border-radius: var(--fr-radius-lg);
	padding: 12px;
}

.error-item {
	display: flex;
	gap: 10px;
	font-size: 12px;
	color: var(--fr-danger);
	line-height: 1.4;
}

.error-item i {
	margin-top: 2px;
}

.selector-empty-state {
	flex: 1;
	display: flex;
	flex-direction: column;
	align-items: center;
	justify-content: center;
	text-align: center;
	padding: 40px 20px;
}

.sidebar-dialog-trigger {
	padding: 16px;
	background: var(--fr-primary-subtle);
	border: 1px solid rgba(36, 144, 239, 0.2);
	border-radius: var(--fr-radius-lg);
}

.inline-properties-wrapper {
	display: flex;
	flex-direction: column;
}

.sidebar-footer {
	margin-top: auto;
	padding-top: 20px;
	border-top: 1px solid var(--fr-border-subtle);
}

.w-100 {
	width: 100%;
}

.truncate {
	white-space: nowrap;
	overflow: hidden;
	text-overflow: ellipsis;
}

.v2-scrollbar::-webkit-scrollbar {
	width: 4px;
}
.v2-scrollbar::-webkit-scrollbar-thumb {
	background: var(--fr-gray-300);
	border-radius: 10px;
}
</style>
