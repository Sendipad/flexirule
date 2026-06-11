<template>
	<div class="rule-sidebar">
		<div class="sidebar-header">
			<h4>{{ sidebar_title }}</h4>
			<button class="btn-close" @click="$emit('close')">×</button>
		</div>

		<div class="sidebar-content" v-if="selectedNode">
			<!-- Validation Errors -->
			<div v-if="store.validation_errors?.length" class="sidebar-errors mb-3">
				<div
					v-for="(err, idx) in store.validation_errors"
					:key="idx"
					class="d-flex align-items-start gap-2 text-danger small mb-1"
				>
					<i class="fa fa-exclamation-circle mt-1"></i>
					<span>{{ err }}</span>
				</div>
			</div>

			<!-- Start Node: Keep existing behavior -->
			<template v-if="selectedNode.type === 'start'">
				<StartNodeProperties
					:nodeData="selectedNode.data"
					:readOnly="store.is_read_only"
					@update:field="update_start_field"
					@open:conditions="open_condition_dialog"
				/>
			</template>

			<!-- Action Nodes: DocField-driven rendering -->
			<template v-else>
				<div v-if="selectedNode.type === 'selector'" class="selector-placeholder mb-3">
					<p class="text-muted small mb-2">
						{{
							__(
								"Choose an action type on the node card, then click Create to continue."
							)
						}}
					</p>
					<p class="text-muted small mb-0">
						{{
							__(
								"Full action settings only appear after this placeholder becomes a real Rule Action."
							)
						}}
					</p>
				</div>

				<!-- Quick Action Button (Shows if Dialog mode) -->
				<div
					class="sidebar-v2-preview mb-3"
					v-if="
						isConfigurable &&
						selectedNode.type !== 'selector' &&
						store.settings?.action_config_mode === 'Dialog'
					"
				>
					<button class="btn btn-sm btn-primary-light w-100" @click="open_config_dialog">
						<i class="fa fa-cog"></i> {{ __("Configure Action via Dialog") }}
					</button>
				</div>

				<!-- Inline Properties (Shows if Sidebar mode) -->
				<ActionFieldProperties
					v-if="
						selectedNode.type !== 'selector' &&
						(store.settings?.action_config_mode === 'Sidebar' ||
							!store.settings?.action_config_mode)
					"
					:nodeData="selectedNode.data"
					:readOnly="store.is_read_only"
					@update:field="update_action_field"
					@open:conditions="open_condition_dialog"
					@open:config="open_config_dialog"
				/>

				<!-- Delete Button -->
				<hr />
				<button
					class="btn btn-sm btn-danger w-100"
					@click="delete_node"
					:disabled="store.is_read_only"
				>
					<i class="fa fa-trash"></i> {{ __("Delete") }}
				</button>
			</template>
		</div>
	</div>
</template>

<script setup>
import { computed, onMounted } from "vue";
import { useRuleStore, useGraphStore, useUIStore } from "../stores";
import ActionFieldProperties from "./ActionFieldProperties.vue";
import StartNodeProperties from "./StartNodeProperties.vue";
import { getContract } from "../../core/contracts";
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

	// Support nested nodes natively when mapped
	if (
		fieldname === "rule" &&
		selectedNode.value.data.action_type === "Sub-Rule" &&
		oldValue !== value
	) {
		// store.expand_sub_rule_in_graph removed per user request
	}

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
	background: var(--fxr-surface, #fff);
}

.sidebar-v2-preview {
	padding: 10px 15px 5px;
	border-bottom: 1px solid var(--fxr-border-subtle, var(--border-color));
	background: var(--fxr-surface-2, var(--control-bg));
}

.selector-placeholder {
	padding: 12px;
	border: 1px dashed var(--fxr-border-subtle, var(--border-color));
	border-radius: 12px;
	background: color-mix(in srgb, var(--fxr-surface, #fff) 92%, var(--fxr-surface-2, #f3f5f7));
}

.btn-primary-light {
	background: var(--fxr-accent-soft, #eef2ff);
	color: var(--fxr-accent, #4f46e5);
	border: 1px solid color-mix(in srgb, var(--fxr-accent, #4f46e5) 22%, var(--fxr-surface));
	font-weight: 600;
	font-size: 11px;
}

.btn-primary-light:hover {
	background: color-mix(in srgb, var(--fxr-accent-soft, #eef2ff) 84%, var(--fxr-surface));
	border-color: color-mix(in srgb, var(--fxr-accent, #4f46e5) 32%, var(--fxr-surface));
}

.sidebar-header {
	display: flex;
	align-items: center;
	justify-content: space-between;
	padding: 12px 15px;
	border-bottom: 1px solid var(--fxr-border-subtle, var(--border-color));
	background: linear-gradient(
		180deg,
		color-mix(in srgb, var(--fxr-surface, #fff) 96%, var(--fxr-surface-2, #f3f5f7)),
		var(--fxr-surface, #fff)
	);
}

.sidebar-header h4 {
	margin: 0;
	font-size: 14px;
	font-weight: 600;
	color: var(--fxr-text-strong, var(--text-color));
}

.header-nav {
	display: flex;
	gap: 15px;
}

.nav-tab {
	background: none;
	border: none;
	font-size: 13px;
	font-weight: 600;
	color: var(--fxr-text-soft);
	padding: 0 0 4px 0;
	cursor: pointer;
	border-bottom: 2px solid transparent;
	outline: none;
}

.nav-tab.active {
	color: var(--fxr-accent);
	border-bottom-color: var(--fxr-accent);
}

.btn-close {
	background: none;
	border: none;
	font-size: 18px;
	cursor: pointer;
	color: var(--fxr-text-soft, var(--text-muted));
	padding: 0;
}

.sidebar-content {
	flex: 1;
	padding: 15px;
	overflow-y: auto;
}

hr {
	margin: 15px 0;
	border: none;
	border-top: 1px solid var(--fxr-border-subtle, var(--border-color));
}

.w-100 {
	width: 100%;
}
</style>
```
