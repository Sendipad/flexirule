<!-- Used as Text, Small Text & Long Text Control -->
<script setup>
import { computed, useSlots } from "vue";
const props = defineProps(["df", "modelValue", "read_only"]);
let emit = defineEmits(["update:modelValue"]);
let slots = useSlots();

let height = computed(() => {
	if (props.df?.fieldtype == "Small Text") {
		return "150px";
	}
	return "300px";
});
</script>

<template>
	<div class="control" :class="{ editable: slots.label }">
		<!-- label -->
		<div v-if="slots.label" class="field-controls">
			<slot name="label" />
			<slot name="actions" />
		</div>
		<div v-else-if="df?.label" class="control-label label">{{ __(df.label) }}</div>

		<!-- textarea input -->
		<textarea
			v-if="slots.label"
			:style="{ height: height, maxHeight: df?.max_height ?? '' }"
			class="form-control"
			type="text"
			readonly
		/>
		<textarea
			v-else
			:style="{ height: height, maxHeight: df?.max_height ?? '' }"
			class="form-control"
			type="text"
			:value="modelValue"
			:disabled="read_only || df.read_only"
			@input="(event) => $emit('update:modelValue', event.target.value)"
		/>

		<!-- description -->
		<div v-if="df.description" class="mt-2 description">{{ __(df.description) }}</div>
	</div>
</template>

<style scoped>
/* ─── TextControl – Unified Design ─── */
.control-label {
	font-size: var(--fxr-text-sm);
	font-weight: var(--fxr-weight-medium);
	margin-bottom: var(--fxr-space-2);
	color: var(--fxr-text-secondary);
}

.description {
	font-size: var(--fxr-text-xs);
	color: var(--fxr-text-muted);
}

textarea.form-control {
	font-size: var(--fxr-input-font-size);
	padding: var(--fxr-input-padding-y) var(--fxr-input-padding-x);
	border: 1px solid var(--fxr-border);
	border-radius: var(--fxr-radius-md);
	transition: border-color var(--fxr-transition-fast), box-shadow var(--fxr-transition-fast);
}

textarea.form-control:focus {
	border-color: var(--fxr-border-focus);
	box-shadow: var(--fxr-shadow-focus);
}

textarea.form-control:hover:not(:disabled):not(:focus) {
	border-color: var(--fxr-border-strong);
}
</style>
