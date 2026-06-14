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
				executed: isExecuted,
				'status-running': isRunning,
				'status-error': isErrored,
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
			<div class="header-left">
				<i class="fa" :class="nodeMeta.icon"></i>
				<span class="type-text">{{ nodeMeta.typeLabel.toUpperCase() }}</span>
			</div>

			<div class="header-right">
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
		</div>

		<!-- Main Content -->
		<div class="node-body">
			<div class="node-title">{{ data.action_label || label }}</div>
			<div class="node-subtitle" v-if="data.operation">
				{{ data.operation }}
			</div>

			<div class="node-details" v-if="hasDetails">
				<div class="detail-tag" v-if="data.reference_doctype">
					<i class="fa fa-database"></i>
					<span>{{ data.reference_doctype }}</span>
				</div>
				<div class="detail-tag mutation" v-if="data.mutation_mode">
					<i class="fa fa-bolt"></i>
					<span>{{ data.mutation_mode }}</span>
				</div>
				<div class="detail-row" v-if="data.target_field">
					<i class="fa fa-crosshairs"></i> {{ data.target_field }}
				</div>
				<div class="detail-row" v-if="data.variable_name">
					<i class="fa fa-code"></i> {{ data.variable_name }}
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
	background-color: var(--fxr-bg-card);
	border: 1px solid var(--fxr-border);
	border-radius: var(--fxr-radius-md);
	box-shadow: var(--fxr-shadow-md);
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
	box-shadow: var(--fxr-shadow-lg);
	border-color: var(--accent-color);
}

.process-node-card.is-read-only {
	cursor: default;
	filter: grayscale(0.5);
	opacity: 0.8;
}

.process-node-card.is-read-only .node-header {
	background-color: var(--fxr-bg-muted);
}

.process-node-card.is-read-only .action-btn:not(.delete) {
	color: var(--primary);
	opacity: 0.7;
}

.process-node-card.selected {
	box-shadow: 0 0 0 2px var(--accent-color);
	border-color: var(--accent-color);
}

.process-node-card.executed {
	box-shadow: 0 0 0 3px var(--fxr-success-soft);
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
	padding: 8px 12px;
	border-bottom: 1px solid var(--fxr-border-subtle);
}

.header-left {
	display: flex;
	align-items: center;
	gap: 8px;
}

.header-right {
	display: flex;
	align-items: center;
	gap: 4px;
}

.node-header i {
	color: var(--accent-color);
	font-size: 12px;
}

.type-text {
	font-size: 9px;
	font-weight: 800;
	color: var(--fxr-text-soft);
	letter-spacing: 0.6px;
	text-transform: uppercase;
}

.action-btn {
	background: none;
	border: none;
	padding: 2px 4px;
	cursor: pointer;
	color: var(--fxr-text-faint);
	font-size: 11px;
}

.action-btn.delete:hover {
	color: var(--fxr-text-danger);
}

/* Body */
.node-body {
	padding: 12px;
	min-height: 50px;
}

.node-title {
	font-size: 13px;
	font-weight: 700;
	color: var(--fxr-text-strong);
	margin-bottom: 4px;
	line-height: 1.2;
}

.is-vertical .node-title {
	white-space: normal;
	word-break: break-word;
}

.node-subtitle {
	font-size: 11px;
	color: var(--fxr-text-soft);
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
	margin-top: 8px;
	padding-top: 8px;
	border-top: 1px dashed var(--fxr-border-subtle);
	display: flex;
	flex-direction: column;
	gap: 6px;
}

.detail-tag {
	display: inline-flex;
	align-items: center;
	gap: 4px;
	background-color: var(--fxr-bg-muted);
	color: var(--fxr-text-secondary);
	padding: 2px 6px;
	border-radius: 4px;
	font-size: 9px;
	font-weight: 600;
	width: fit-content;
	max-width: 100%;
}

.detail-tag i {
	font-size: 8px;
	color: var(--fxr-text-faint);
}

.detail-tag.mutation {
	background-color: var(--fxr-accent-light);
	color: var(--fxr-accent);
}

.detail-tag.mutation i {
	color: var(--fxr-accent);
}

.detail-row {
	font-size: 9.5px;
	color: var(--fxr-text-secondary);
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
	color: var(--fxr-text-faint);
	width: 12px;
	text-align: center;
}

.detail-muted {
	color: var(--fxr-text-faint);
}

/* Footer */
.node-footer {
	padding: 8px 12px;
	background-color: color-mix(in srgb, var(--fxr-surface-soft) 80%, var(--fxr-bg-muted));
	border-bottom-left-radius: var(--fxr-radius-md);
	border-bottom-right-radius: var(--fxr-radius-md);
	border-top: 1px solid var(--fxr-border-subtle);
}

.config-status {
	display: flex;
	align-items: center;
	gap: 6px;
	font-size: 10px;
	cursor: pointer;
	color: var(--fxr-text-faint);
}

.config-status.configured {
	color: var(--fxr-text-success, #198754);
}

.config-status:hover {
	opacity: 0.8;
}

/* Handles */
.handle-target,
.handle-source {
	width: 10px !important;
	height: 10px !important;
	background-color: var(--fxr-bg-card) !important;
	border: 2px solid var(--accent-color) !important;
}

/* RTL Support */
[dir="rtl"] .process-node-card:not(.is-vertical) {
	border-left: 1px solid var(--fxr-border);
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
