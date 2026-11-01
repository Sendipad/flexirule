<script setup>
import { ref, useSlots, computed, watch } from "vue";

const props = defineProps({
	df: Object,
	fieldname: String,
	modelValue: [Boolean, Number],
	read_only: Boolean,
	hideLabel: Boolean,
	showValidation: { type: Boolean, default: false },
	indeterminate: { type: Boolean, default: false },
	size: { type: String, default: "md" }, // 'md' | 'sm'
});

const emit = defineEmits(["update:modelValue", "change"]);
const slots = useSlots();
const inputRef = ref(null);

const isChecked = computed(() => !!props.modelValue);

const isValid = computed(() => {
	if (!props.df?.reqd) return true;
	return isChecked.value;
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

function handleChange(event) {
	const checked = event.target.checked;
	// Frappe often uses 0 / 1 for Check fields when initialized as number
	const newValue = typeof props.modelValue === "number" ? (checked ? 1 : 0) : checked;
	emit("update:modelValue", newValue);
	emit("change", newValue);
}

watch(
	() => props.indeterminate,
	(val) => {
		if (inputRef.value) {
			inputRef.value.indeterminate = !!val;
		}
	},
	{ immediate: true }
);
</script>

<template>
	<div
		class="fxr-control fxr-check-control"
		:class="{
			'is-editable': slots.label,
			'no-label': hideLabel,
			'has-error': showValidation && !isValid,
			'is-disabled': read_only,
		}"
		v-fxr-fieldname="df?.fieldname || fieldname || null"
		@mouseenter="showTooltip = true"
		@mouseleave="showTooltip = false"
		@focusin="showTooltip = true"
		@focusout="showTooltip = false"
	>
		<!-- Custom Slot Label / Actions -->
		<label v-if="slots.label" class="field-controls fxr-checkbox-label">
			<input
				ref="inputRef"
				type="checkbox"
				class="fxr-checkbox-input"
				:class="{ 'fxr-checkbox-input--sm': size === 'sm' }"
				:checked="isChecked"
				:disabled="read_only"
				@change="handleChange"
			/>
			<slot name="label" />
			<slot name="actions" />
		</label>

		<!-- Standard Label -->
		<label v-else class="fxr-checkbox-label" :class="{ 'is-disabled': read_only }">
			<input
				ref="inputRef"
				type="checkbox"
				class="fxr-checkbox-input"
				:class="{ 'fxr-checkbox-input--sm': size === 'sm' }"
				:checked="isChecked"
				:disabled="read_only"
				@change="handleChange"
			/>
			<span v-if="df?.label && !hideLabel" class="label-area" :class="{ reqd: df.reqd }">
				{{ __(df.label) }}
			</span>
		</label>

		<!-- Tooltip Popup for Grid / Hidden Label Mode -->
		<div v-if="hideLabel && showTooltip && (df.label || df.description)" class="check-tooltip">
			<div class="tooltip-header" v-if="df.label">{{ __(df.label) }}</div>
			<div class="tooltip-body" v-if="df.description">{{ __(df.description) }}</div>
		</div>

		<!-- Standard description -->
		<div v-if="df.description && !hideLabel" class="description">
			{{ __(df.description) }}
		</div>

		<!-- Validation error -->
		<div v-if="showValidation && !isValid" class="fxr-error-msg">
			{{ __("{0} must be checked").replace("{0}", df?.label || __("Field")) }}
		</div>
	</div>
</template>

<style scoped>
/* ─── CheckControl – Unified Design ─── */
.fxr-check-control {
	position: relative;
	min-height: var(--fxr-input-height, 32px);
	display: flex;
	flex-direction: column;
	align-items: flex-start;
	justify-content: center;
}

.fxr-checkbox-label {
	display: inline-flex;
	align-items: center;
	gap: var(--fxr-space-3, 8px);
	cursor: pointer;
	margin: 0 !important;
	user-select: none;
}

.fxr-checkbox-label.is-disabled {
	cursor: not-allowed;
	color: var(--fxr-text-muted);
}

.label-area {
	font-size: var(--fxr-text-base, 14px);
	color: var(--fxr-text);
	font-weight: var(--fxr-weight-medium, 500);
	line-height: 1.4;
}

.label-area.reqd::after {
	content: " *";
	color: var(--fxr-text-danger);
}

.description {
	font-size: var(--fxr-text-xs, 12px);
	color: var(--fxr-text-muted);
	margin-top: var(--fxr-space-1, 4px);
	line-height: 1.4;
	padding-left: calc(16px + var(--fxr-space-3, 8px));
}

/* Tooltip */
.check-tooltip {
	position: absolute;
	bottom: 100%;
	left: 50%;
	transform: translateX(-50%);
	background-color: var(--fxr-bg-dark, #1e293b);
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
