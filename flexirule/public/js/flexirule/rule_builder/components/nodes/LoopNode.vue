<script setup>
import { computed } from "vue";
import { Handle, Position } from "@vue-flow/core";
import { useStore } from "../../stores";
import { useNodeExecutionState } from "../../composables/useNodeExecutionState";

const props = defineProps(["data", "label", "id", "selected", "sourcePosition", "targetPosition"]);
const store = useStore();

const isHorizontal = computed(() => store.settings?.layout_direction !== "Top to Bottom");

const targetPos = computed(
	() => props.targetPosition || (isHorizontal.value ? Position.Left : Position.Top)
);
// TB layout: For Each → Bottom (straight down), After Last → Left (bypass)
// LR layout: For Each → Right (straight right), After Last → Bottom (bypass)
const doPos = computed(() => (isHorizontal.value ? Position.Right : Position.Bottom));
const donePos = computed(() => (isHorizontal.value ? Position.Bottom : Position.Right));
const returnPos = computed(() => (isHorizontal.value ? Position.Top : Position.Left));

const isEffectiveDisabled = computed(() => {
	return store.effectiveDisabledIds?.has(props.id);
});

const isReadOnly = computed(() => store.is_read_only);

const nodeIdRef = computed(() => props.id);
const { isExecuted, isRunning, isErrored, executionOrder } = useNodeExecutionState(nodeIdRef);

function deleteNode() {
	frappe.confirm(__("Delete this node?"), () => store.delete_node(props.id));
}

function openConfig() {
	store.open_config(props.id);
}
</script>

<template>
	<div
		class="loop-node-card"
		:class="{
			selected: selected,
			disabled: isEffectiveDisabled,
			'is-read-only': isReadOnly,
			'debug-executed': isExecuted,
			'debug-running': isRunning,
			'debug-error': isErrored,
			'is-vertical': !isHorizontal,
		}"
	>
		<!-- Execution Badge -->
		<div v-if="isExecuted" class="execution-badge" :title="__('Visit Order')">
			{{ executionOrder }}
		</div>
		<Handle type="target" :position="targetPos" class="handle-target" />
		<!-- Return Handle for Loop Body -->
		<Handle type="target" :position="returnPos" id="return" class="handle-return" />

		<div class="node-header">
			<i class="fa fa-refresh icon-spin"></i>
			<span class="type-text">{{ __("LOOP") }}</span>
			<button
				v-if="!isReadOnly"
				class="action-btn toggle-btn"
				@click.stop="store.toggle_node_enabled(props.id)"
				:title="data.is_enabled === 0 ? __('Enable') : __('Disable')"
			>
				<i :class="['fa', data.is_enabled === 0 ? 'fa-toggle-off' : 'fa-toggle-on']"></i>
			</button>
			<button
				class="action-btn"
				@click.stop="openConfig"
				:title="isReadOnly ? __('View Configuration') : __('Configure')"
			>
				<i :class="['fa', isReadOnly ? 'fa-eye' : 'fa-pencil']"></i>
			</button>
			<button
				class="action-btn delete"
				@click.stop="deleteNode"
				v-if="selected && !isReadOnly"
			>
				<i class="fa fa-trash"></i>
			</button>
		</div>

		<div class="node-body">
			<div class="loop-title">{{ data.action_label || label }}</div>
			<div class="loop-subtext" v-if="data.config?.iterator">
				{{ __("Iterator:") }} {{ data.config.iterator }} {{ __("as") }}
				{{ data.return_variable || data.config?.alias || "item" }}
			</div>
		</div>

		<!-- Iteration Handle: For Each → body branch -->
		<!-- TB: exits Bottom | LR: exits Right -->
		<div :class="['out-port', isHorizontal ? 'out-right' : 'out-bottom']" class="out-do">
			<div class="bubble-label bubble-foreach">{{ __("For Each") }}</div>
			<Handle type="source" :position="doPos" id="default" class="handle-out handle-do" />
		</div>

		<!-- Done Handle: After Last → bypass branch -->
		<!-- TB: exits Right | LR: exits Bottom -->
		<div :class="['out-port', isHorizontal ? 'out-bottom' : 'out-right']" class="out-done">
			<div class="bubble-label bubble-afterlast">{{ __("After Last") }}</div>
			<Handle type="source" :position="donePos" id="false" class="handle-out handle-done" />
		</div>
	</div>
</template>

<style scoped>
.loop-node-card {
	width: 180px;
	background: #fff;
	border: 1px solid #fab005; /* Salesforce Yellow */
	border-radius: 8px;
	box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
	position: relative;
	transition: all 0.2s ease;
}

.loop-node-card:hover {
	box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
	transform: translateY(-2px);
}

.loop-node-card.selected {
	border-color: var(--primary);
	box-shadow: 0 0 0 2px rgba(var(--primary-rgb), 0.2);
}

.loop-node-card.is-vertical {
	width: 140px;
}

.loop-node-card.is-read-only {
	cursor: default;
	filter: grayscale(0.5);
	opacity: 0.8;
}

.loop-node-card.is-read-only .node-header {
	background-color: #94a3b8;
}

.node-header {
	background: #fab005;
	color: #fff;
	padding: 6px 12px;
	border-radius: 7px 7px 0 0;
	display: flex;
	align-items: center;
	gap: 8px;
	font-weight: 700;
	font-size: 10px;
	letter-spacing: 0.5px;
}

.icon-spin {
	animation: fa-spin 10s infinite linear;
}

.node-body {
	padding: 12px;
	text-align: center;
}

.loop-title {
	font-weight: 600;
	font-size: 13px;
	color: #2d3748;
	line-height: 1.2;
}

.is-vertical .loop-title {
	white-space: normal;
	word-break: break-word;
}

.loop-subtext {
	font-size: 10px;
	color: #718096;
	margin-top: 4px;
	word-break: break-all;
}

.is-vertical .loop-subtext {
	white-space: normal;
}

/* Ports & Bubbles */
.out-port {
	position: absolute;
	z-index: 5;
	display: flex;
	align-items: center;
	justify-content: center;
}

.bubble-label {
	background: #fff;
	border: 1px solid #cbd5e0;
	border-radius: 20px;
	padding: 4px 12px;
	font-size: 11px;
	font-weight: 600;
	color: #4a5568;
	white-space: nowrap;
	box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
	position: relative;
	z-index: 2;
}

/* "For Each" bubble — amber tint to match the loop header */
.bubble-foreach {
	border-color: #fab005;
	color: #92400e;
	background: #fffbeb;
}

/* "After Last" bubble — slate neutral */
.bubble-afterlast {
	border-color: #94a3b8;
	color: #334155;
	background: #f8fafc;
}

/* Position for LR */
.out-right {
	right: -40px;
	top: 50%;
	transform: translateY(-50%);
}

.out-bottom {
	bottom: -20px;
	left: 50%;
	transform: translateX(-50%);
}

.out-top {
	top: -20px;
	left: 50%;
	transform: translateX(-50%);
}

/* Handles */
.loop-node-card:not(.is-vertical) .handle-done {
	top: auto !important;
	bottom: -5px !important;
	left: 50% !important;
}

.loop-node-card:not(.is-vertical) .handle-return {
	left: 50% !important;
	top: -5px !important;
}

.loop-node-card:not(.is-vertical) .handle-target {
	left: -5px !important;
	top: 50% !important;
}

.loop-node-card:not(.is-vertical) .handle-do {
	right: -5px !important;
	top: 50% !important;
}

/* Position for TB */
.loop-node-card.is-vertical .out-bottom {
	bottom: -20px;
	left: 50%;
	transform: translateX(-50%);
}

.loop-node-card.is-vertical .out-right {
	right: -40px;
	top: 50%;
	transform: translateY(-50%);
}

.loop-node-card.is-vertical .out-left {
	left: -40px;
	top: 50%;
	transform: translateY(-50%);
}

/* Handles */
.handle-out {
	position: absolute !important;
	z-index: 1 !important;
	opacity: 0; /* Hide the dot, use the bubble center */
}

/* Make sure the edge starts from the bubble */
.out-right .handle-out {
	right: -5px;
}
.out-bottom .handle-out {
	bottom: -5px;
}

.handle-target,
.handle-return {
	background: #fff !important;
	border: 2px solid #fab005 !important;
	width: 10px !important;
	height: 10px !important;
	transition: all 0.2s ease !important;
}

.handle-target:hover,
.handle-return:hover {
	transform: scale(1.4) !important;
	border-color: var(--primary) !important;
	box-shadow: 0 0 0 4px rgba(var(--primary-rgb), 0.2);
}

.is-vertical .handle-target {
	top: -5px !important;
}

.is-vertical .handle-return {
	top: 50% !important;
	left: -5px !important;
}

.handle-return {
	z-index: 10 !important;
}

.action-btn {
	background: none;
	border: none;
	color: #fff;
	opacity: 0.8;
	cursor: pointer;
	padding: 2px;
	margin-left: auto;
}

.action-btn:hover {
	opacity: 1;
}

.action-btn.delete {
	margin-left: 4px;
}

/* Execution */
.debug-executed {
	border-left: 4px solid var(--green-500);
}

.execution-badge {
	position: absolute;
	top: -10px;
	right: -10px;
	background: var(--green-500);
	color: white;
	border-radius: 12px;
	padding: 2px 8px;
	font-size: 10px;
	font-weight: bold;
	z-index: 20;
	box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
}

.out-right .port-label {
	margin-right: 4px;
}
.out-bottom .port-label {
	margin-bottom: 4px;
}

.out-do .port-label {
	color: #fab005;
}
/* RTL Support */
[dir="rtl"] .node-header {
	flex-direction: row;
}

[dir="rtl"] .action-btn {
	margin-left: 0;
	margin-right: auto;
}
</style>
