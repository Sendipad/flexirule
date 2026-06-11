<template>
	<div
		class="execution-step-card"
		:class="[`status-${step.status}`, { active: isActive }]"
		@click="$emit('click')"
	>
		<div class="step-order">#{{ step.order }}</div>
		<div class="step-content">
			<div class="step-label" :title="step.action">{{ step.action }}</div>
			<div v-if="step.duration_ms !== null" class="step-duration" :title="durationTooltip">
				{{ step.duration_ms }}ms
				<i class="fa fa-info-circle duration-info-icon"></i>
			</div>
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

const durationTooltip = computed(() => {
	return __(
		"Execution durations are estimated for lab/UI profiling and may not be 100% accurate. Many micro-actions execute near 0ms natively."
	);
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
	border-radius: var(--fxr-radius-md);
	cursor: pointer;
	transition: all 0.2s ease;
	min-width: 140px;
	max-width: 180px;
	flex-shrink: 0;
	backdrop-filter: blur(8px);
}

[data-theme="dark"] .execution-step-card {
	background: rgba(45, 55, 72, 0.4);
	border-color: rgba(255, 255, 255, 0.1);
}

.execution-step-card:hover {
	transform: translateY(-2px);
	border-color: var(--fxr-accent);
	box-shadow: var(--fxr-shadow-md);
}

.execution-step-card.active {
	background: var(--fxr-surface-elevated);
	border-color: var(--fxr-accent);
	box-shadow: 0 0 0 2px var(--fxr-accent-soft);
}

.step-order {
	font-size: 9px;
	font-weight: 700;
	color: var(--fxr-text-faint);
	background: var(--fxr-surface-2);
	width: 18px;
	height: 18px;
	display: flex;
	align-items: center;
	justify-content: center;
	border-radius: 50%;
}

.step-content {
	flex: 1;
	min-width: 0;
}

.step-label {
	font-size: 12px;
	font-weight: 600;
	color: var(--fxr-text-strong);
	white-space: nowrap;
	overflow: hidden;
	text-overflow: ellipsis;
}

.step-duration {
	font-size: 10px;
	color: var(--fxr-text-soft);
}

.duration-info-icon {
	font-size: 8px;
	vertical-align: super;
	opacity: 0.6;
}

.status-indicator {
	font-size: 14px;
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
