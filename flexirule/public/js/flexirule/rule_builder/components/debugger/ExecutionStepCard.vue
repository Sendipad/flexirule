<template>
	<div
		class="execution-step-card"
		:class="[`status-${step.status}`, { active: isActive }]"
		@click="$emit('click')"
	>
		<div class="step-order">{{ step.order }}</div>
		<div class="step-content">
			<div class="step-label" :title="step.action">{{ step.action }}</div>
		</div>
		<div class="status-indicator">
			<i :class="statusIcon"></i>
		</div>
	</div>
</template>

<script setup>
import { computed } from "vue";

const props = defineProps({
	step: {
		type: Object,
		required: true,
	},
	isActive: {
		type: Boolean,
		default: false,
	},
});

defineEmits(["click"]);

const statusIcon = computed(() => {
	switch (props.step.status) {
		case "success":
			return "fa fa-check-circle";
		case "error":
			return "fa fa-exclamation-circle";
		case "skipped":
			return "fa fa-step-forward";
		default:
			return "fa fa-info-circle";
	}
});
</script>

<style scoped>
.execution-step-card {
	display: flex;
	align-items: center;
	padding: 4px 8px;
	gap: 6px;
	background: var(--fxr-surface-soft);
	border: 1px solid var(--fxr-border-subtle);
	border-radius: var(--fxr-radius-sm);
	cursor: pointer;
	transition: all 0.2s ease;
	min-width: 110px;
	max-width: 160px;
	flex-shrink: 0;
	height: 32px;
}

.execution-step-card:hover {
	border-color: var(--fxr-accent);
	background: var(--fxr-surface-2);
}

.execution-step-card.active {
	background: var(--fxr-surface-elevated);
	border-color: var(--fxr-accent);
	box-shadow: 0 0 0 1px var(--fxr-accent);
}

.step-order {
	font-size: 9px;
	font-weight: 700;
	color: var(--fxr-text-faint);
	background: var(--fxr-surface-2);
	width: 16px;
	height: 16px;
	display: flex;
	align-items: center;
	justify-content: center;
	border-radius: 4px;
}

.step-content {
	flex: 1;
	min-width: 0;
}

.step-label {
	font-size: 11px;
	font-weight: 600;
	color: var(--fxr-text-strong);
	white-space: nowrap;
	overflow: hidden;
	text-overflow: ellipsis;
}

.status-indicator {
	font-size: 12px;
	display: flex;
	align-items: center;
}

.status-success .status-indicator {
	color: var(--green-500);
}
.status-error .status-indicator {
	color: var(--red-500);
}
.status-skipped .status-indicator {
	color: var(--orange-500);
}

.status-error {
	border-color: var(--red-200);
	background: var(--red-50);
}

[data-theme="dark"] .status-error {
	background: rgba(220, 38, 38, 0.1);
	border-color: rgba(220, 38, 38, 0.4);
}
</style>
