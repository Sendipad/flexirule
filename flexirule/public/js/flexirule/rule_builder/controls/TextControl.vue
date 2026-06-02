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
	<div class="fxr-control" :class="{ editable: slots.label }">
		<!-- label -->
		<div v-if="slots.label" class="field-controls">
			<slot name="label" />
			<slot name="actions" />
		</div>
		<div v-else-if="df?.label" class="fxr-label" :class="{ reqd: df.reqd }">
			{{ __(df.label) }}
		</div>

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
		<div v-if="df.description" class="fxr-description">{{ __(df.description) }}</div>
	</div>
</template>

<style scoped>
textarea.form-control {
	height: auto !important;
	padding: 8px 10px !important;
}
</style>
