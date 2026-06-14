<script setup>
import { computed } from "vue";
import { Handle, Position } from "@vue-flow/core";
import { useStore } from "../../stores";
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

const isConfigured = computed(() => {
	const config = props.data?.config;
	return !!(config && config.iterator);
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
		class="loop-node-card"
		:class="{
			selected: selected,
			disabled: isEffectiveDisabled,
			'is-read-only': isReadOnly,
			executed: isExecuted,
			'status-running': isRunning,
			'status-error': isErrored,
			'is-vertical': !isHorizontal,
		}"
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

		<Handle type="target" :position="targetPos" class="handle-target" />
		<!-- Return Handle for Loop Body -->
		<Handle type="target" :position="returnPos" id="return" class="handle-return" />

		<div class="node-header">
			<div class="header-left">
				<i class="fa fa-refresh icon-spin"></i>
				<span class="type-text">{{ __("LOOP") }}</span>
			</div>
			<div class="header-actions">
				<button
					v-if="!isReadOnly"
					class="action-btn toggle-btn"
					@click.stop="store.toggle_node_enabled(props.id)"
					:title="data.is_enabled === 0 ? __('Enable') : __('Disable')"
				>
					<i
						:class="['fa', data.is_enabled === 0 ? 'fa-toggle-off' : 'fa-toggle-on']"
					></i>
				</button>
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
				<div v-else class="loop-title">{{ data.title || data.action_label || label }}</div>
			</div>
			<div class="node-data-footprint" v-if="data.config?.iterator">
				<span class="footprint-tag">
					<i class="fa fa-code"></i> {{ data.config.iterator }}
				</span>
				<span class="footprint-tag">
					<i class="fa fa-arrow-right"></i>
					{{ data.return_variable || data.config?.alias || "item" }}
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
	background-color: var(--fxr-bg-card);
	border: 1px solid #fab005; /* Salesforce Yellow */
	border-radius: var(--fxr-radius-md);
	box-shadow: var(--fxr-shadow-md);
	position: relative;
	transition: all 0.2s ease;
}

.loop-node-card:hover {
	box-shadow: var(--fxr-shadow-lg);
	transform: translateY(-2px);
}

.loop-node-card.selected {
	border-color: var(--fxr-accent);
	box-shadow: 0 0 0 2px var(--fxr-accent-soft);
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
	background-color: var(--fxr-text-muted);
}

.node-header {
	background-color: #fab005;
	color: #ffffff;
	padding: 6px 12px;
	border-radius: var(--fxr-radius-sm) var(--fxr-radius-sm) 0 0;
	display: flex;
	align-items: center;
	justify-content: space-between;
	gap: 8px;
	font-weight: 800;
	font-size: 10px;
	letter-spacing: 0.8px;
	text-transform: uppercase;
}

.header-left {
	display: flex;
	align-items: center;
	gap: 8px;
	overflow: hidden;
}

.header-actions {
	display: flex;
	gap: 4px;
}

.icon-spin {
	animation: fa-spin 10s infinite linear;
}

.node-body {
	padding: 12px;
	text-align: center;
}

.loop-title {
	font-weight: 700;
	font-size: 13px;
	color: var(--fxr-text-strong);
	line-height: 1.3;
}

.is-vertical .loop-title {
	white-space: normal;
	word-break: break-word;
}

.node-title-input {
	width: 100%;
	font-size: 13px;
	font-weight: 700;
	border: 1px solid var(--fxr-accent);
	border-radius: 4px;
	padding: 2px 4px;
	outline: none;
	background: var(--fxr-bg-card);
	color: var(--fxr-text-strong);
}

.node-data-footprint {
	margin-top: 8px;
	display: flex;
	flex-wrap: wrap;
	justify-content: center;
	gap: 4px;
}

.footprint-tag {
	font-size: 9px;
	color: var(--fxr-text-secondary);
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
	padding: 4px 12px;
	background-color: var(--fxr-surface-soft);
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

/* Ports & Bubbles */
.out-port {
	position: absolute;
	z-index: 5;
	display: flex;
	align-items: center;
	justify-content: center;
}

.bubble-label {
	background-color: var(--fxr-bg-card);
	border: 1px solid var(--fxr-border);
	border-radius: 20px;
	padding: 4px 12px;
	font-size: 11px;
	font-weight: 600;
	color: var(--fxr-text-strong);
	white-space: nowrap;
	box-shadow: var(--fxr-shadow-sm);
	position: relative;
	z-index: 2;
}

/* "For Each" bubble — amber tint to match the loop header */
.bubble-foreach {
	border-color: #fab005;
	color: #92400e;
	background-color: #fffbeb;
}

[data-theme="dark"] .bubble-foreach {
	background-color: rgba(251, 176, 5, 0.1);
	color: #fbbf24;
}

/* "After Last" bubble — slate neutral */
.bubble-afterlast {
	border-color: var(--fxr-text-muted);
	color: var(--fxr-text-soft);
	background-color: var(--fxr-surface-soft);
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
	background-color: var(--fxr-bg-card) !important;
	border: 2px solid #fab005 !important;
	width: 10px !important;
	height: 10px !important;
	transition: all 0.2s ease !important;
}

.handle-target:hover,
.handle-return:hover {
	transform: scale(1.4) !important;
	border-color: var(--fxr-accent) !important;
	box-shadow: 0 0 0 4px var(--fxr-accent-soft);
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
	color: #ffffff;
	opacity: 0.8;
	cursor: pointer;
	padding: 2px;
}

.action-btn:hover {
	opacity: 1;
}

.action-btn.delete {
	margin-left: 4px;
}

/* Execution */
.executed {
	box-shadow: 0 0 0 3px var(--fxr-success-soft);
}

.execution-badge {
	position: absolute;
	top: -10px;
	right: -10px;
	background-color: #198754;
	color: #ffffff;
	border-radius: 12px;
	padding: 2px 8px;
	font-size: 10px;
	font-weight: bold;
	z-index: 20;
	box-shadow: var(--fxr-shadow-sm);
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
