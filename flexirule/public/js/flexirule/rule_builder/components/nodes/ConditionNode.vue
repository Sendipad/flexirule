<script setup>
import { Handle, Position } from "@vue-flow/core";
import { useStore } from "../../stores";
import { getContract } from "../../../core/contracts";
import { computed } from "vue";

const props = defineProps(["data", "label", "id", "selected", "sourcePosition", "targetPosition"]);
const store = useStore();

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

const testResult = computed(() => {
	const path = store.test_execution_path || [];
	return path.find((entry) => entry.action_id === props.id);
});

function deleteNode() {
	frappe.confirm(__("Delete this node?"), () => store.delete_node(props.id));
}

function openConfig() {
	store.open_config(props.id);
}
</script>

<template>
	<div
		class="condition-node-card"
		:class="{
			selected: selected,
			disabled: isEffectiveDisabled,
			'is-read-only': isReadOnly,
			'test-executed': !!testResult,
			'outcome-true': testResult && testResult.result === true,
			'outcome-false': testResult && testResult.result === false,
		}"
		:style="{ '--accent-color': nodeMeta.color }"
	>
		<!-- Execution Badge -->
		<div v-if="testResult" class="execution-badge" :title="__('Visit Order')">
			{{ store.test_execution_path.indexOf(testResult) + 1 }}
		</div>
		<!-- Input Handle -->
		<Handle type="target" :position="targetPos" class="handle-target" />

		<!-- Card Body -->
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

		<div class="node-body">
			<div class="condition-text">{{ label }}</div>
			<div class="compact-summary" v-if="conditionSummary">
				{{ conditionSummary }}
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
	background: #fff;
	border: 1px solid #f0f4f7;
	border-radius: 8px;
	box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
	position: relative;
	border-top: 4px solid var(--accent-color);
	transition: all 0.2s ease;
}

.condition-node-card:hover {
	box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
	border-color: var(--accent-color);
}

.condition-node-card.selected {
	box-shadow: 0 0 0 2px var(--accent-color);
	border-color: var(--accent-color);
}

.condition-node-card.is-read-only {
	cursor: default;
	background-color: #fafbfc;
}

.condition-node-card.is-read-only .node-header {
	background-color: #f1f5f9;
}

.condition-node-card.test-executed {
	box-shadow: 0 0 0 3px #198754;
	border-color: #198754;
}

.condition-node-card.outcome-true {
	background-color: #f6ffed;
}

.condition-node-card.outcome-false {
	background-color: #fff1f0;
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
	padding: 6px 10px;
	border-bottom: 1px solid #f0f4f7;
	gap: 6px;
}

.node-header i {
	color: var(--accent-color);
	font-size: 12px;
}

.type-text {
	font-size: 9px;
	font-weight: 800;
	color: #6c757d;
	letter-spacing: 0.5px;
	flex: 1;
}

.action-btn {
	background: none;
	border: none;
	padding: 0 2px;
	cursor: pointer;
	color: #adb5bd;
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
	color: #1a1a1a;
	line-height: 1.2;
}

.compact-summary {
	font-size: 9px;
	color: #64748b;
	margin-top: 4px;
	font-family: monospace;
	word-break: break-all;
	max-width: 100%;
}

/* Ports/Handles */
.handle-target {
	width: 10px !important;
	height: 10px !important;
	background-color: #fff !important;
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
}

.out-right .port-label {
	top: -12px;
	left: 50%;
	transform: translateX(-50%);
}

.out-bottom .port-label {
	bottom: -12px;
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
	background: #fff !important;
	border-width: 2px !important;
	border-style: solid !important;
}

.handle-true {
	border-color: #198754 !important;
}
.handle-false {
	border-color: #dc3545 !important;
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
