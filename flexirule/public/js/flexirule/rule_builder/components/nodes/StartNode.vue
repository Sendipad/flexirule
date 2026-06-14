<script setup>
import { Handle, Position } from "@vue-flow/core";
import { useStore } from "../../stores";
import { getContract } from "../../../core/contracts";
import { computed } from "vue";
import { useNodeExecutionState } from "../../composables/useNodeExecutionState";
import NodeToolbar from "./NodeToolbar.vue";

const props = defineProps(["data", "label", "id", "selected", "sourcePosition"]);

const isHovered = ref(false);
const store = useStore();
const isReadOnly = computed(() => store.is_read_only);

import { ref, nextTick } from "vue";

const isEditing = ref(false);
const titleInput = ref(null);
const editedTitle = ref("");

const isHorizontal = computed(() => store.settings?.layout_direction !== "Top to Bottom");
const sourcePos = computed(
	() => props.sourcePosition || (isHorizontal.value ? Position.Right : Position.Bottom)
);

const displayLabel = computed(() => {
	const data = props.data || {};
	if (data.title) return data.title;
	if (data.document_type && data.trigger_event) {
		return `${data.document_type} / ${data.trigger_event}`;
	}
	if (data.trigger_type) return data.trigger_type;
	return props.label || __("Start");
});

const summaryData = computed(() => {
	const data = props.data || {};
	const parts = [];

	if (data.exposed_as_subrule) {
		parts.push(__("Sub-Rule"));
	}

	if (data.document_type && !data.trigger_event) {
		parts.push(`${__("Doc")}: ${data.document_type}`);
	}

	if (data.priority) parts.push(`${__("Priority")}: ${data.priority}`);
	return parts;
});

const nodeMeta = computed(() => {
	const actionType = props.data?.action_type || "Entry Action";
	const contract = getContract(actionType);
	const css = contract.css || {};

	return {
		color: css.color || "#10b981",
		icon: css.icon || "fa-play",
		typeLabel: __("TRIGGER"),
	};
});

const nodeIdRef = computed(() => props.id || "root");
const { isExecuted, isRunning, isErrored, executionOrder } = useNodeExecutionState(nodeIdRef);

function openConfig() {
	store.open_config(props.id || "start");
}

function startEditing() {
	if (isReadOnly.value) return;
	editedTitle.value = props.data?.title || displayLabel.value;
	isEditing.value = true;
	nextTick(() => {
		titleInput.value?.focus();
	});
}

function saveTitle() {
	if (!isEditing.value) return;
	isEditing.value = false;
	if (editedTitle.value !== (props.data?.title || displayLabel.value)) {
		store.update_node_data(props.id || "start", { title: editedTitle.value });
	}
}
</script>

<template>
	<div
		class="start-node-d"
		:class="{
			executed: isExecuted,
			'status-running': isRunning,
			'status-error': isErrored,
			'is-vertical': !isHorizontal,
			'is-read-only': isReadOnly,
		}"
		@mouseenter="isHovered = true"
		@mouseleave="isHovered = false"
	>
		<NodeToolbar
			:show="selected || isHovered"
			:is-read-only="isReadOnly"
			:allow-delete="false"
			@configure="openConfig"
		/>

		<!-- Execution Badge -->
		<div v-if="isExecuted" class="execution-badge" :title="__('Visit Order')">
			{{ executionOrder }}
		</div>
		<div class="node-body" :style="{ '--accent-color': nodeMeta.color }">
			<div class="icon-section">
				<i class="fa" :class="nodeMeta.icon"></i>
			</div>
			<div class="info-section">
				<div class="type-label">{{ nodeMeta.typeLabel }}</div>
				<div class="main-label-container" @dblclick.stop="startEditing">
					<template v-if="isEditing">
						<input
							ref="titleInput"
							v-model="editedTitle"
							class="main-label-input"
							@blur="saveTitle"
							@keyup.enter="saveTitle"
							@click.stop
						/>
					</template>
					<div v-else class="main-label">{{ displayLabel }}</div>
				</div>
				<div class="summary-line" v-if="summaryData.length">
					<span v-for="(p, i) in summaryData" :key="i" class="summary-part">
						{{ p }}
					</span>
				</div>
			</div>
		</div>
		<Handle
			type="source"
			:position="sourcePos"
			id="default"
			class="handle-source"
			:connectable="true"
		/>
	</div>
</template>

<style scoped>
.start-node-d {
	position: relative;
	min-width: 140px;
}

.node-body {
	background-color: var(--accent-color);
	color: #ffffff;
	display: flex;
	align-items: center;
	padding: 8px 16px 8px 10px;
	border-radius: var(--fxr-radius-sm) 40px 40px var(--fxr-radius-sm); /* Reflected D-Shape */
	box-shadow: var(--fxr-shadow-sm);
	transition: all 0.2s ease;
	border: 1px solid rgba(255, 255, 255, 0.2);
}

.is-vertical .node-body {
	border-radius: 4px 4px 40px 40px;
	flex-direction: column;
	text-align: center;
	padding: 12px 10px;
	width: 120px;
}

.is-vertical .icon-section {
	margin-right: 0;
	margin-bottom: 6px;
}

.node-body:hover {
	transform: translateY(-1px);
	box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
	filter: brightness(0.9);
}

.icon-section {
	width: 28px;
	height: 28px;
	background: rgba(255, 255, 255, 0.2);
	border-radius: 50%;
	display: flex;
	align-items: center;
	justify-content: center;
	font-size: 10px;
	margin-right: 10px;
	flex-shrink: 0;
}

.is-read-only .node-body {
	filter: grayscale(0.4) opacity(0.8);
	cursor: default;
}

.info-section {
	display: flex;
	flex-direction: column;
	overflow: hidden;
}

.type-label {
	font-size: 8px;
	font-weight: 800;
	text-transform: uppercase;
	letter-spacing: 0.5px;
	opacity: 0.9;
	margin-bottom: 1px;
}

.main-label {
	font-size: 12px;
	font-weight: 700;
	white-space: nowrap;
	overflow: hidden;
	text-overflow: ellipsis;
}

.main-label-input {
	width: 100%;
	font-size: 12px;
	font-weight: 700;
	border: 1px solid rgba(255, 255, 255, 0.5);
	border-radius: 4px;
	padding: 1px 4px;
	outline: none;
	background: rgba(255, 255, 255, 0.2);
	color: white;
}

.is-vertical .main-label {
	white-space: normal;
	word-break: break-word;
	line-height: 1.2;
	font-size: 11px;
}

.summary-line {
	display: flex;
	flex-wrap: wrap;
	gap: 4px;
	margin-top: 2px;
	opacity: 0.8;
}

.summary-part {
	font-size: 8px;
	background: rgba(255, 255, 255, 0.15);
	padding: 0 4px;
	border-radius: 2px;
	white-space: nowrap;
}

.is-vertical .summary-line {
	justify-content: center;
}

.handle-source {
	background: white !important;
	border: 3px solid var(--accent-color) !important;
	width: 12px !important;
	height: 12px !important;
	z-index: 10 !important;
	cursor: crosshair !important;
}

/* Position handles based on direction */
.start-node-d:not(.is-vertical) .handle-source {
	right: -6px !important;
	top: 50% !important;
	transform: translateY(-50%) !important;
}

.is-vertical .handle-source {
	bottom: -6px !important;
	left: 50% !important;
	transform: translateX(-50%) !important;
}

.start-node-d.executed .node-body {
	box-shadow: 0 0 0 3px rgba(16, 185, 129, 0.4);
	background: #10b981;
}

.execution-badge {
	position: absolute;
	top: -6px;
	left: -6px;
	background-color: var(--fxr-bg-card);
	color: var(--accent-color);
	width: 18px;
	height: 18px;
	border-radius: 50%;
	display: flex;
	align-items: center;
	justify-content: center;
	font-size: 9px;
	font-weight: 700;
	z-index: 10;
	box-shadow: var(--fxr-shadow-sm);
	border: 2px solid var(--accent-color);
}

.action-btn {
	background: none;
	border: none;
	color: rgba(255, 255, 255, 0.6);
	cursor: pointer;
	padding: 4px;
	font-size: 12px;
	margin-left: auto;
}

.action-btn:hover {
	color: white;
}

/* RTL Support */
[dir="rtl"] .start-node-d:not(.is-vertical) .node-body {
	border-radius: 40px 4px 4px 40px;
	padding: 8px 10px 8px 16px;
}

[dir="rtl"] .icon-section {
	margin-left: 10px;
	margin-right: 0;
}

[dir="rtl"] .action-btn {
	margin-left: 0;
	margin-right: auto;
}
</style>
