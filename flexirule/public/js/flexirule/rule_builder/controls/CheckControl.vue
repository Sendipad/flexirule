<script setup>
import { ref, useSlots } from "vue";
const props = defineProps(["df", "modelValue", "read_only", "hideLabel"]);
defineEmits(["update:modelValue"]);
let slots = useSlots();
const showTooltip = ref(false);
</script>

<template>
	<div
		class="fxr-control checkbox"
		:class="{ editable: slots.label, 'no-label': hideLabel }"
		@mouseenter="showTooltip = true"
		@mouseleave="showTooltip = false"
		@focusin="showTooltip = true"
		@focusout="showTooltip = false"
	>
		<!-- checkbox -->
		<label v-if="slots.label" class="field-controls">
			<div class="checkbox fxr-checkbox">
				<input type="checkbox" disabled />
				<slot name="label" />
			</div>
			<slot name="actions" />
		</label>
		<label v-else class="checkbox-label-container fxr-checkbox">
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
		<div v-if="df.description && !hideLabel" class="fxr-description">
			{{ __(df.description) }}
		</div>
	</div>
</template>

<style scoped>
.fxr-control {
	position: relative;
	min-height: 32px;
	display: flex;
	align-items: center;
	margin-bottom: 8px;
}

.fxr-checkbox {
	display: flex;
	align-items: center;
	gap: 8px;
	cursor: pointer;
	margin: 0 !important;
	user-select: none;
}

.fxr-checkbox input {
	width: 16px;
	height: 16px;
	cursor: pointer;
	margin: 0 !important;
	accent-color: var(--fr-primary);
}

.label-area {
	font-size: var(--fr-text-sm);
	color: var(--fr-text);
	font-weight: 500;
}

.label-area.reqd::after {
	content: " *";
	color: var(--fr-danger);
}

/* Tooltip */
.check-tooltip {
	position: absolute;
	bottom: 100%;
	left: 50%;
	transform: translateX(-50%);
	background: var(--fr-gray-900);
	color: #fff;
	padding: 8px 12px;
	border-radius: var(--fr-radius-md);
	font-size: 11px;
	z-index: 1000;
	min-width: 150px;
	max-width: 250px;
	box-shadow: var(--fr-shadow-lg);
	pointer-events: none;
	margin-bottom: 8px;
}

.check-tooltip::after {
	content: "";
	position: absolute;
	top: 100%;
	left: 50%;
	margin-left: -5px;
	border-width: 5px;
	border-style: solid;
	border-color: var(--fr-gray-900) transparent transparent transparent;
}

.tooltip-header {
	font-weight: 700;
	margin-bottom: 4px;
	border-bottom: 1px solid rgba(255, 255, 255, 0.1);
	padding-bottom: 4px;
}
</style>
