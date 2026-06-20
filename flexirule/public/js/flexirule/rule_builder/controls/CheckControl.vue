<script setup>
import { ref, useSlots, computed } from "vue";
const props = defineProps({
	df: Object,
	fieldname: String,
	modelValue: [Boolean, Number],
	read_only: Boolean,
	hideLabel: Boolean,
	showValidation: { type: Boolean, default: false },
});
const emit = defineEmits(["update:modelValue"]);
let slots = useSlots();

const isValid = computed(() => {
	if (!props.df?.reqd) return true;
	return !!props.modelValue;
});

function validate() {
	const errors = [];
	if (!isValid.value) {
		errors.push(__("{0} must be checked").replace("{0}", props.df?.label || __("Field")));
	}
	return { valid: errors.length === 0, errors };
}

defineExpose({ validate });
const showTooltip = ref(false);
</script>

<template>
	<div
		class="control fxr-control checkbox"
		:class="{
			editable: slots.label,
			'no-label': hideLabel,
			'has-error': showValidation && !isValid,
		}"
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
		<div v-if="df.description && !hideLabel" class="mt-2 description">
			{{ __(df.description) }}
		</div>

		<!-- validation error -->
		<div v-if="showValidation && !isValid" class="fxr-error-msg">
			{{ __("{0} must be checked").replace("{0}", df?.label || __("Field")) }}
		</div>
	</div>
</template>

<style scoped>
/* ─── CheckControl – Unified Design ─── */
.fxr-control {
	position: relative;
	min-height: var(--fxr-input-height);
	display: flex;
	align-items: center;
}

.fxr-checkbox {
	display: flex;
	align-items: center;
	gap: var(--fxr-space-3);
	cursor: pointer;
	margin: 0 !important;
	user-select: none;
}

.fxr-checkbox input {
	width: 16px;
	height: 16px;
	cursor: pointer;
	margin: 0 !important;
	border: 1px solid var(--fxr-border);
	border-radius: var(--fxr-radius-sm);
	transition: all var(--fxr-transition-fast);
}

.fxr-checkbox input:checked {
	background-color: var(--fxr-accent);
	border-color: var(--fxr-accent);
}

.label-area {
	font-size: var(--fxr-text-base);
	color: var(--fxr-text);
	font-weight: var(--fxr-weight-medium);
}

.label-area.reqd::after {
	content: " *";
	color: var(--fxr-text-danger);
}

.description {
	font-size: var(--fxr-text-xs);
	color: var(--fxr-text-muted);
	margin-top: var(--fxr-space-2);
}

/* Tooltip */
.check-tooltip {
	position: absolute;
	bottom: 100%;
	left: 50%;
	transform: translateX(-50%);
	background-color: var(--fxr-bg-dark);
	color: #ffffff;
	padding: var(--fxr-space-3) var(--fxr-space-4);
	border-radius: var(--fxr-radius-md);
	font-size: var(--fxr-text-xs);
	z-index: var(--fxr-z-popover);
	min-width: 150px;
	max-width: 250px;
	box-shadow: var(--fxr-shadow-lg);
	pointer-events: none;
	margin-bottom: var(--fxr-space-2);
}

.check-tooltip::after {
	content: "";
	position: absolute;
	top: 100%;
	left: 50%;
	margin-left: -5px;
	border-width: 5px;
	border-style: solid;
	border-color: var(--fxr-bg-dark, #1e293b) transparent transparent transparent;
}

.tooltip-header {
	font-weight: var(--fxr-weight-bold);
	margin-bottom: var(--fxr-space-1);
	border-bottom: 1px solid rgba(255, 255, 255, 0.1);
	padding-bottom: var(--fxr-space-1);
}
</style>
