<script setup>
import { computed } from "vue";
/**
 * PercentSliderControl - Slider input for 0-100 values
 */

const props = defineProps({
	df: Object,
	modelValue: [Number, String],
	read_only: Boolean,
	showValidation: { type: Boolean, default: false },
});

const emit = defineEmits(["update:modelValue"]);

const value = computed({
	get: () => parseInt(props.modelValue) || props.df?.default || 50,
	set: (val) => emit("update:modelValue", parseInt(val)),
});

const isValid = computed(() => {
	if (!props.df?.reqd) return true;
	return props.modelValue !== undefined && props.modelValue !== null && props.modelValue !== "";
});

function validate() {
	const errors = [];
	if (!isValid.value) {
		errors.push(__("{0} is required").replace("{0}", props.df?.label || __("Field")));
	}
	return { valid: errors.length === 0, errors };
}

defineExpose({ validate });
</script>

<template>
	<div
		class="percent-slider-control fxr-control"
		:class="{ 'has-error': showValidation && !isValid }"
	>
		<label v-if="df.label" class="control-label">
			{{ __(df.label) }}
			<span v-if="df.reqd" class="text-danger">*</span>
		</label>

		<div class="slider-wrapper">
			<input
				type="range"
				class="form-range"
				min="0"
				max="100"
				:value="value"
				@input="value = $event.target.value"
				:disabled="read_only"
			/>
			<span class="slider-value">{{ value }}%</span>
		</div>

		<small v-if="df.description" class="form-text text-muted">{{ df.description }}</small>

		<!-- validation error -->
		<div v-if="showValidation && !isValid" class="fxr-error-msg">
			{{ __("{0} is required").replace("{0}", df?.label || __("Field")) }}
		</div>
	</div>
</template>

<style scoped>
.percent-slider-control {
	margin-bottom: 15px;
}
.control-label {
	font-size: 12px;
	font-weight: 500;
	margin-bottom: 5px;
	display: block;
}
.slider-wrapper {
	display: flex;
	align-items: center;
	gap: 10px;
}
.form-range {
	flex: 1;
}
.slider-value {
	min-width: 45px;
	text-align: right;
	font-size: 13px;
	font-weight: 500;
	color: var(--primary);
}
</style>
