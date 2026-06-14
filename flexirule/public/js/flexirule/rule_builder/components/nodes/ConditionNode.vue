<script setup>
import { Handle, Position } from "@vue-flow/core";
import { useStore } from "../../stores";
import { getContract } from "../../../core/contracts";
import { computed } from "vue";
import { useNodeExecutionState } from "../../composables/useNodeExecutionState";
import NodeToolbar from "./NodeToolbar.vue";

const props = defineProps(["data", "label", "id", "selected", "sourcePosition", "targetPosition"]);

const isHovered = ref(false);
const store = useStore();

import { ref, nextTick } from "vue";

const isEditing = ref(false);
const titleInput = ref(null);
const editedTitle = ref("");

const isHorizontal = computed(() => store.settings?.layout_direction !== "Top to Bottom");

const targetPos = computed(
	() => props.targetPosition || (isHorizontal.value ? Position.Left : Position.Top)
);
const truePos = computed(() => (isHorizontal.value ? Position.Right : Position.Bottom));
const falsePos = computed(() => (isHorizontal.value ? Position.Bottom : Position.Right));

const isEffectiveDisabled = computed(() => {
	return store.effectiveDisabledIds?.has(props.id);
});

const isReadOnly = computed(() => store.is_read_only);

const nodeMeta = computed(() => {
	const actionType = props.data?.action_type || "Condition";
	const contract = getContract(actionType);
	const css = contract.css || {};

	return {
		color: css.color || "#fd7e14",
		icon: css.icon || "fa-question-circle",
		typeLabel: (actionType || "CONDITION").toUpperCase(),
	};
});

const conditionSummary = computed(() => {
	const config = props.data?.config;
	if (!config || !config.conditions || !config.conditions.length) return "";
	const count = config.conditions.length;
	const first = config.conditions[0];
	if (first && first.left && first.op) {
		const left = first.left.ref?.replace("doc.", "") || "?";
		const op = first.op;
		const right = first.right?.ref
			? first.right.ref.replace("doc.", "")
			: first.right?.value ?? "?";
		return `${left} ${op} ${right}${count > 1 ? ` (+${count - 1})` : ""}`;
	}
	return `${count} ${__("conditions")}`;
});

const nodeIdRef = computed(() => props.id);
const { isExecuted, isRunning, isErrored, executionOrder } = useNodeExecutionState(nodeIdRef);

const isConfigured = computed(() => {
	const config = props.data?.config;
	return !!(config && config.conditions && config.conditions.length > 0);
});

function deleteNode() {
	frappe.confirm(__("Delete this node?"), () => store.delete_node(props.id));
}

function openConfig() {
	store.open_config(props.id);
}

function startEditing() {
	if (isReadOnly.value) return;
	editedTitle.value = props.data?.title || props.data?.action_label || props.label;
	isEditing.value = true;
	nextTick(() => {
		titleInput.value?.focus();
	});
}

function saveTitle() {
	if (!isEditing.value) return;
	isEditing.value = false;
	if (editedTitle.value !== (props.data?.title || props.data?.action_label || props.label)) {
		store.update_node_data(props.id, { title: editedTitle.value });
	}
}
</script>

<template>
	<div
		class="condition-node-card"
		:class="{
			selected: selected,
			disabled: isEffectiveDisabled,
			'is-read-only': isReadOnly,
			executed: isExecuted,
			'status-running': isRunning,
			'status-error': isErrored,
		}"
		:style="{ '--accent-color': nodeMeta.color }"
		@mouseenter="isHovered = true"
		@mouseleave="isHovered = false"
	>
		<!-- Execution Badge -->
		<div v-if="isExecuted" class="execution-badge" :title="__('Visit Order')">
			{{ executionOrder }}
		</div>
		<NodeToolbar
			:show="selected || isHovered"
			:is-read-only="isReadOnly"
			@configure="openConfig"
			@delete="deleteNode"
		/>

		<!-- Input Handle -->
		<Handle type="target" :position="targetPos" class="handle-target" />

		<!-- Card Body -->
		<div class="node-header">
			<div class="header-left">
				<i class="fa" :class="nodeMeta.icon"></i>
				<span class="type-text">{{ nodeMeta.typeLabel }}</span>
			</div>
		</div>

		<div class="node-body">
			<div class="node-title-container" @dblclick.stop="startEditing">
				<template v-if="isEditing">
					<input
						ref="titleInput"
						v-model="editedTitle"
						class="node-title-input"
						@blur="saveTitle"
						@keyup.enter="saveTitle"
						@click.stop
					/>
				</template>
				<div v-else class="condition-text">
					{{ data.title || data.action_label || label }}
				</div>
			</div>
			<div class="node-data-footprint" v-if="conditionSummary">
				<span class="footprint-tag">
					<i class="fa fa-filter"></i> {{ conditionSummary }}
				</span>
			</div>
		</div>

		<!-- Footer/Status -->
		<div class="node-footer">
			<div class="config-status" :class="{ configured: isConfigured }">
				<i class="fa" :class="isConfigured ? 'fa-check-circle' : 'fa-circle-o'"></i>
				<span>{{ isConfigured ? __("Configured") : __("Not Configured") }}</span>
			</div>
		</div>

		<!-- True Output (Right/Bottom) -->
		<div :class="['out-port', isHorizontal ? 'out-right' : 'out-bottom']">
			<span class="port-label">{{ __("YES") }}</span>
			<Handle type="source" :position="truePos" id="true" class="handle-out handle-true" />
		</div>

		<!-- False Output (Bottom/Right) -->
		<div :class="['out-port', isHorizontal ? 'out-bottom' : 'out-right']">
			<span class="port-label">{{ __("NO") }}</span>
			<Handle type="source" :position="falsePos" id="false" class="handle-out handle-false" />
		</div>
	</div>
</template>

<style scoped>
.condition-node-card {
	width: 160px;
	background-color: var(--fxr-bg-card);
	border: 1px solid var(--fxr-border-subtle);
	border-radius: var(--fxr-radius-md);
	box-shadow: var(--fxr-shadow-md);
	position: relative;
	border-top: 4px solid var(--accent-color);
	transition: all 0.2s ease;
}

.condition-node-card:hover {
	box-shadow: var(--fxr-shadow-lg);
	border-color: var(--accent-color);
}

.condition-node-card.selected {
	box-shadow: 0 0 0 2px var(--accent-color);
	border-color: var(--accent-color);
}

.condition-node-card.is-read-only {
	cursor: default;
	background-color: var(--fxr-bg-input-disabled);
}

.condition-node-card.is-read-only .node-header {
	background-color: var(--fxr-bg-muted);
}

.condition-node-card.executed {
	box-shadow: 0 0 0 3px var(--fxr-success-soft);
}

.condition-node-card.outcome-true {
	background-color: var(--fxr-success-soft);
}

.condition-node-card.outcome-false {
	background-color: var(--fxr-danger-soft);
}

.execution-badge {
	position: absolute;
	top: -8px;
	left: -8px;
	background-color: #198754;
	color: #ffffff;
	width: 20px;
	height: 20px;
	border-radius: 50%;
	display: flex;
	align-items: center;
	justify-content: center;
	font-size: 10px;
	font-weight: 700;
	z-index: 10;
	box-shadow: var(--fxr-shadow-sm);
}

/* Header */
.node-header {
	display: flex;
	align-items: center;
	justify-content: space-between;
	padding: 6px 10px;
	border-bottom: 1px solid var(--fxr-border-subtle);
	gap: 6px;
}

.header-left {
	display: flex;
	align-items: center;
	gap: 6px;
	overflow: hidden;
}

.node-header i {
	color: var(--accent-color);
	font-size: 12px;
}

.type-text {
	font-size: 9px;
	font-weight: 800;
	color: var(--fxr-text-soft);
	letter-spacing: 0.8px;
	text-transform: uppercase;
	white-space: nowrap;
	overflow: hidden;
	text-overflow: ellipsis;
}

.header-actions {
	display: flex;
	gap: 4px;
}

.action-btn {
	background: none;
	border: none;
	padding: 0 2px;
	cursor: pointer;
	color: var(--fxr-text-faint);
	font-size: 10px;
}

.action-btn:hover {
	color: #dc3545;
}

/* Body */
.node-body {
	padding: 10px;
	text-align: center;
	min-height: 40px;
	display: flex;
	align-items: center;
	justify-content: center;
}

.condition-text {
	font-size: 11px;
	font-weight: 700;
	color: var(--fxr-text-strong);
	line-height: 1.3;
}

.node-title-input {
	width: 100%;
	font-size: 11px;
	font-weight: 700;
	border: 1px solid var(--fxr-accent);
	border-radius: 4px;
	padding: 2px 4px;
	outline: none;
	background: var(--fxr-bg-card);
	color: var(--fxr-text-strong);
}

.node-data-footprint {
	margin-top: 6px;
	display: flex;
	justify-content: center;
}

.footprint-tag {
	font-size: 9px;
	color: var(--fxr-text-soft);
	background: var(--fxr-surface-2);
	padding: 2px 6px;
	border-radius: 4px;
	display: flex;
	align-items: center;
	gap: 4px;
	max-width: 100%;
	overflow: hidden;
	text-overflow: ellipsis;
	white-space: nowrap;
}

.footprint-tag i {
	color: var(--fxr-text-faint);
	font-size: 8px;
}

/* Footer */
.node-footer {
	padding: 4px 10px;
	background-color: var(--fxr-surface-soft);
	border-bottom-left-radius: var(--fxr-radius-md);
	border-bottom-right-radius: var(--fxr-radius-md);
	border-top: 1px solid var(--fxr-border-subtle);
}

.config-status {
	display: flex;
	align-items: center;
	justify-content: center;
	gap: 6px;
	font-size: 9px;
	cursor: pointer;
	color: var(--fxr-text-faint);
}

.config-status.configured {
	color: var(--fxr-text-success, #198754);
}

/* Ports/Handles */
.handle-target {
	width: 10px !important;
	height: 10px !important;
	background-color: var(--fxr-bg-card) !important;
	border: 2px solid var(--accent-color) !important;
}

.out-port {
	position: absolute;
	display: flex;
	flex-direction: column;
	align-items: center;
	z-index: 5;
}

.out-right {
	right: -30px;
	top: 50%;
	transform: translateY(-50%);
	flex-direction: row;
}

.out-bottom {
	bottom: -22px;
	left: 50%;
	transform: translateX(-50%);
	flex-direction: column;
}

.port-label {
	font-size: 8px;
	font-weight: 800;
	position: absolute;
	background-color: var(--fxr-bg-card);
	border-radius: 999px;
	padding: 1px 4px;
	box-shadow: var(--fxr-shadow-sm);
	line-height: 1.2;
	color: var(--fxr-text-strong);
}

.out-right .port-label {
	top: -16px;
	left: 12px;
	transform: none;
}

.out-bottom .port-label {
	bottom: -16px;
	left: 50%;
	transform: translateX(-50%);
}

.handle-true .port-label {
	color: #198754;
}
.handle-false .port-label {
	color: #dc3545;
}

/* Specific True/False colors for labels */
.out-port:has(.handle-true) .port-label {
	color: #198754;
}
.out-port:has(.handle-false) .port-label {
	color: #dc3545;
}

.handle-out {
	position: relative !important;
	transform: none !important;
	top: auto !important;
	width: 10px !important;
	height: 10px !important;
	background-color: var(--fxr-bg-card) !important;
	border-width: 2px !important;
	border-style: solid !important;
}

.handle-true {
	border-color: #198754 !important;
}
.handle-false {
	border-color: var(--fxr-text-danger) !important;
}
/* RTL Support */
[dir="rtl"] .condition-node-card .out-right .port-label {
	left: auto;
	right: 50%;
	transform: translateX(50%);
}

[dir="rtl"] .condition-node-card .out-bottom .port-label {
	left: auto;
	right: 50%;
	transform: translateX(50%);
}
</style>
