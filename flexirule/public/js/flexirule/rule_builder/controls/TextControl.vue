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
	font-size: var(--fr-text-sm);
	font-weight: var(--fr-weight-medium);
	margin-bottom: var(--fr-space-2);
	color: var(--fr-text-secondary);
}

.description {
	font-size: var(--fr-text-xs);
	color: var(--fr-text-muted);
}

textarea.form-control {
	font-size: var(--fr-input-font-size);
	padding: var(--fr-input-padding-y) var(--fr-input-padding-x);
	border: 1px solid var(--fr-border);
	border-radius: var(--fr-radius-md);
	transition:
		border-color var(--fr-transition-fast),
		box-shadow var(--fr-transition-fast);
}

textarea.form-control:focus {
	border-color: var(--fr-border-focus);
	box-shadow: var(--fr-shadow-focus);
}

textarea.form-control:hover:not(:disabled):not(:focus) {
	border-color: var(--fr-border-strong);
}
</style>
