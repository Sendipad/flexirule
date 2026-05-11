<script setup>
import { computed } from "vue";
import { Handle, Position } from "@vue-flow/core";
import { useRuleStore, useGraphStore, useUIStore } from "../../stores";
import { getContract } from "../../../core/contracts";
import { useNodeExecutionState } from "../../composables/useNodeExecutionState";

const props = defineProps(["data", "label", "id", "selected", "sourcePosition", "targetPosition"]);
const ruleStore = useRuleStore();
const graphStore = useGraphStore();
const uiStore = useUIStore();
// Legacy
const store = uiStore;

const isHorizontal = computed(() => ruleStore.settings?.layout_direction !== "Top to Bottom");

const targetPos = computed(
	() => props.targetPosition || (isHorizontal.value ? Position.Left : Position.Top)
);
const sourcePos = computed(
	() => props.sourcePosition || (isHorizontal.value ? Position.Right : Position.Bottom)
);

const isEffectiveDisabled = computed(() => {
	return graphStore.effectiveDisabledIds?.has(props.id);
});

const isReadOnly = computed(() => ruleStore.is_read_only);

const nodeMeta = computed(() => {
	const actionType = props.data?.action_type || "Process";
	const contract = getContract(actionType);
	const css = contract.css || {};

	return {
		color: css.color || "#0d6efd",
		icon: css.icon || "fa-cog",
		typeLabel: (actionType || "PROCESS").toUpperCase(),
	};
});

const nodeIdRef = computed(() => props.id);
const { isExecuted, isRunning, isErrored, executionOrder } = useNodeExecutionState(nodeIdRef);

const isConfigured = computed(() => {
	const actionType = props.data?.action_type;
	if (!actionType) return false;

	const contract = getContract(actionType);
	const requiredFields = contract.required_fields || [];
	const hasRequiredFields = requiredFields.every((fieldname) => {
		const value = props.data?.[fieldname];
		return value !== undefined && value !== null && value !== "";
	});

	if (!requiredFields.length) {
		return true;
	}

	const config = props.data?.config;
	const hasConfig =
		config &&
		(typeof config === "string"
			? config.trim() !== "" && config.trim() !== "{}"
			: Object.keys(config).length > 0);

	return hasRequiredFields || hasConfig;
});

function deleteNode() {
	frappe.confirm(__("Delete this node?"), () => graphStore.delete_node(props.id));
}

function openConfig() {
	ruleStore.open_config(props.id);
}

const hasDetails = computed(() => {
	const d = props.data || {};
	return d.reference_doctype || d.target_field || d.mutation_mode || d.variable_name;
});
const isTerminal = computed(() => {
	const actionType = props.data?.action_type || "Process";
	return getContract(actionType).terminal || false;
});
</script>

<template>
	<div
		:class="[
			'process-node-card',
			(data.action_type || 'process').toLowerCase().replace(/\s+/g, '-'),
			{
				selected: selected,
				disabled: isEffectiveDisabled,
				'is-read-only': isReadOnly,
				'test-executed': isExecuted,
				'test-running': isRunning,
				'test-error': isErrored,
				'is-vertical': !isHorizontal,
			},
		]"
		:style="{ '--accent-color': nodeMeta.color }"
	>
		<!-- Execution Badge -->
		<div v-if="isExecuted" class="execution-badge" :title="__('Visit Order')">
			{{ executionOrder }}
		</div>
		<Handle type="target" :position="targetPos" class="handle-target" />

		<!-- Header with Type and Icon -->
		<div class="node-header">
			<i class="fa" :class="nodeMeta.icon"></i>
			<span class="type-text">{{ nodeMeta.typeLabel }}</span>

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

		<!-- Main Content -->
		<div class="node-body">
			<div class="node-title">{{ data.action_label || label }}</div>
			<div class="node-subtitle" v-if="data.operation">
				{{ data.operation }}
			</div>

			<div class="node-details" v-if="hasDetails">
				<div class="detail-row" v-if="data.reference_doctype">
					<i class="fa fa-database"></i> {{ data.reference_doctype }}
					<span v-if="data.reference_docname" class="detail-muted"
						>/ {{ data.reference_docname }}</span
					>
				</div>
				<div class="detail-row" v-if="data.target_field">
					<i class="fa fa-crosshairs"></i> {{ data.target_field }}
				</div>
				<div class="detail-row" v-if="data.variable_name">
					<i class="fa fa-code"></i> {{ data.variable_name }}
				</div>
				<div class="detail-row" v-if="data.mutation_mode">
					<i class="fa fa-exchange"></i>
					<span class="detail-muted">{{ data.mutation_mode }}</span>
				</div>
			</div>
		</div>

		<!-- Footer/Status -->
		<div class="node-footer">
			<div class="config-status" :class="{ configured: isConfigured }">
				<i class="fa" :class="isConfigured ? 'fa-check-circle' : 'fa-circle-o'"></i>
				<span>{{ isConfigured ? __("Configured") : __("Not Configured") }}</span>
			</div>
		</div>

		<Handle
			v-if="!isTerminal"
			type="source"
			:position="sourcePos"
			id="default"
			class="handle-source"
		/>
	</div>
</template>

<style scoped>
.process-node-card {
	width: 220px;
	background: #fff;
	border: 1px solid #d1d8dd;
	border-radius: 8px;
	box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
	position: relative;
	overflow: visible;
	border-left: 4px solid var(--accent-color);
	transition: all 0.2s ease;
}

.process-node-card.is-vertical {
	width: 140px;
	border-left: none;
	border-top: 4px solid var(--accent-color);
}

.process-node-card:hover {
	box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
	border-color: var(--accent-color);
}

.process-node-card.is-read-only {
	cursor: default;
	filter: grayscale(0.5);
	opacity: 0.8;
}

.process-node-card.is-read-only .node-header {
	background-color: #f1f5f9;
}

.process-node-card.is-read-only .action-btn:not(.delete) {
	color: var(--primary);
	opacity: 0.7;
}

.process-node-card.selected {
	box-shadow: 0 0 0 2px var(--accent-color);
	border-color: var(--accent-color);
}

.process-node-card.test-executed {
	box-shadow: 0 0 0 3px #198754;
	border-color: #198754;
}

.execution-badge {
	position: absolute;
	top: -8px;
	left: -8px;
	background: #198754;
	color: #fff;
	width: 20px;
	height: 20px;
	border-radius: 50%;
	display: flex;
	align-items: center;
	justify-content: center;
	font-size: 10px;
	font-weight: 700;
	z-index: 10;
	box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
}

/* Header */
.node-header {
	display: flex;
	align-items: center;
	padding: 8px 12px;
	border-bottom: 1px solid #f0f4f7;
	gap: 8px;
}

.node-header i {
	color: var(--accent-color);
	font-size: 12px;
}

.type-text {
	font-size: 10px;
	font-weight: 700;
	color: #6c757d;
	letter-spacing: 0.5px;
	flex: 1;
}

.header-actions {
	display: flex;
	gap: 4px;
}

.action-btn {
	background: none;
	border: none;
	padding: 2px 4px;
	cursor: pointer;
	color: #adb5bd;
	font-size: 11px;
}

.action-btn.delete:hover {
	color: #dc3545;
}

/* Body */
.node-body {
	padding: 12px;
	min-height: 50px;
}

.node-title {
	font-size: 13px;
	font-weight: 600;
	color: #1a1a1a;
	margin-bottom: 4px;
	line-height: 1.2;
}

.is-vertical .node-title {
	white-space: normal;
	word-break: break-word;
}

.node-subtitle {
	font-size: 11px;
	color: #6c757d;
	font-style: italic;
	white-space: nowrap;
	overflow: hidden;
	text-overflow: ellipsis;
	margin-bottom: 4px;
}

.is-vertical .node-subtitle {
	white-space: normal;
}

.node-details {
	margin-top: 6px;
	padding-top: 6px;
	border-top: 1px dashed #e2e8f0;
	display: flex;
	flex-direction: column;
	gap: 3px;
}

.detail-row {
	font-size: 9.5px;
	color: #475569;
	display: flex;
	align-items: center;
	gap: 4px;
	white-space: nowrap;
	overflow: hidden;
	text-overflow: ellipsis;
}

.is-vertical .detail-row {
	white-space: normal;
	flex-wrap: wrap;
}

.detail-row i {
	color: #94a3b8;
	width: 12px;
	text-align: center;
}

.detail-muted {
	color: #94a3b8;
}

/* Footer */
.node-footer {
	padding: 6px 12px;
	background-color: #f8fcfd;
	border-bottom-left-radius: 8px;
	border-bottom-right-radius: 8px;
	border-top: 1px solid #f0f4f7;
}

.config-status {
	display: flex;
	align-items: center;
	gap: 6px;
	font-size: 10px;
	cursor: pointer;
	color: #adb5bd;
}

.config-status.configured {
	color: #198754;
}

.config-status:hover {
	opacity: 0.8;
}

/* Handles */
.handle-target,
.handle-source {
	width: 10px !important;
	height: 10px !important;
	background-color: #fff !important;
	border: 2px solid var(--accent-color) !important;
}

/* RTL Support */
[dir="rtl"] .process-node-card:not(.is-vertical) {
	border-left: 1px solid #d1d8dd;
	border-right: 4px solid var(--accent-color);
}

[dir="rtl"] .node-header {
	flex-direction: row;
}

[dir="rtl"] .type-text {
	text-align: right;
}

[dir="rtl"] .action-btn {
	margin-left: 0;
	margin-right: auto;
}

[dir="rtl"] .detail-row {
	flex-direction: row;
}

[dir="rtl"] .detail-row i {
	margin-right: 0;
	margin-left: 6px;
}
</style>
