<template>
	<div class="d-flex flex-column fxr-gap-2">
		<div class="form-group mb-0">
			<label class="fxr-label-sm">{{ __("True Value (If Condition Meets)") }}</label>
			<input
				v-model="localState.true_value"
				type="text"
				class="form-control form-control-sm"
				placeholder="e.g. Active or {doc.status}"
				:disabled="readOnly"
			/>
		</div>

		<div class="form-group mb-0">
			<label class="fxr-label-sm">{{ __("False Value (Otherwise)") }}</label>
			<input
				v-model="localState.false_value"
				type="text"
				class="form-control form-control-sm"
				placeholder="e.g. Inactive"
				:disabled="readOnly"
			/>
		</div>
	</div>
</template>

<script setup>
import { __ } from "../utils";

const props = defineProps({
	modelValue: { type: Object, default: () => ({}) },
	doctype: { type: String, default: "" },
	readOnly: { type: Boolean, default: false },
	variableOptions: { type: Array, default: () => [] },
});

const localState = props.modelValue;
</script>
