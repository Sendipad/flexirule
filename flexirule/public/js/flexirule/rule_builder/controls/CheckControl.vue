<script setup>
import { ref, useSlots } from "vue";
const props = defineProps(["df", "modelValue", "read_only", "hideLabel"]);
defineEmits(["update:modelValue"]);
let slots = useSlots();
const showTooltip = ref(false);
</script>

<template>
	<div
		class="control fr-control checkbox"
		:class="{ editable: slots.label, 'no-label': hideLabel }"
		@mouseenter="showTooltip = true"
		@mouseleave="showTooltip = false"
		@focusin="showTooltip = true"
		@focusout="showTooltip = false"
	>
		<!-- checkbox -->
		<label v-if="slots.label" class="field-controls">
			<div class="checkbox fr-checkbox">
				<input type="checkbox" disabled />
				<slot name="label" />
			</div>
			<slot name="actions" />
		</label>
		<label v-else class="checkbox-label-container fr-checkbox">
			<input
				type="checkbox"
				:checked="modelValue"
				:disabled="read_only"
				@change="(event) => $emit('update:modelValue', event.target.checked)"
			/>
			<span v-if="df?.label && !hideLabel" class="label-area" :class="{ reqd: df.reqd }">{{
				__(df.label)
			}}</span>
		</label>

		<!-- Tooltip Popup for Grid / Hidden Label Mode -->
		<div v-if="hideLabel && showTooltip && (df.label || df.description)" class="check-tooltip">
			<div class="tooltip-header" v-if="df.label">{{ __(df.label) }}</div>
			<div class="tooltip-body" v-if="df.description">{{ __(df.description) }}</div>
		</div>

		<!-- standard description -->
		<div v-if="df.description && !hideLabel" class="mt-2 description">
			{{ __(df.description) }}
		</div>
	</div>
</template>

<style scoped>
/* ─── CheckControl – Unified Design ─── */
.fr-control {
	position: relative;
	min-height: var(--fr-input-height);
	display: flex;
	align-items: center;
}

.fr-checkbox {
	display: flex;
	align-items: center;
	gap: var(--fr-space-3);
	cursor: pointer;
	margin: 0 !important;
	user-select: none;
}

.fr-checkbox input {
	width: 16px;
	height: 16px;
	cursor: pointer;
	margin: 0 !important;
	border: 1px solid var(--fr-border);
	border-radius: var(--fr-radius-sm);
	transition: all var(--fr-transition-fast);
}

.fr-checkbox input:checked {
	background-color: var(--fr-accent);
	border-color: var(--fr-accent);
}

.label-area {
	font-size: var(--fr-text-base);
	color: var(--fr-text);
	font-weight: var(--fr-weight-medium);
}

.label-area.reqd::after {
	content: " *";
	color: var(--fr-text-danger);
}

.description {
	font-size: var(--fr-text-xs);
	color: var(--fr-text-muted);
	margin-top: var(--fr-space-2);
}

/* Tooltip */
.check-tooltip {
	position: absolute;
	bottom: 100%;
	left: 50%;
	transform: translateX(-50%);
	background: var(--fr-bg-dark, #1e293b);
	color: #fff;
	padding: var(--fr-space-3) var(--fr-space-4);
	border-radius: var(--fr-radius-md);
	font-size: var(--fr-text-xs);
	z-index: var(--fr-z-popover);
	min-width: 150px;
	max-width: 250px;
	box-shadow: var(--fr-shadow-lg);
	pointer-events: none;
	margin-bottom: var(--fr-space-2);
}

.check-tooltip::after {
	content: "";
	position: absolute;
	top: 100%;
	left: 50%;
	margin-left: -5px;
	border-width: 5px;
	border-style: solid;
	border-color: var(--fr-bg-dark, #1e293b) transparent transparent transparent;
}

.tooltip-header {
	font-weight: var(--fr-weight-bold);
	margin-bottom: var(--fr-space-1);
	border-bottom: 1px solid rgba(255, 255, 255, 0.1);
	padding-bottom: var(--fr-space-1);
}
</style>
